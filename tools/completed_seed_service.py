#!/usr/bin/env python3
"""Explicit owner opt-in: one backed-up completed-seed unit per worker run.

Completion replaces age and ratio. Existing maintenance, capacity, cooldown,
ownership, locking, inspection and per-file native verification remain required.
The existing scheduler is the only scheduler; this module creates no cron job.
"""
import fcntl
from collections import Counter
import time
import shutil
from cache_hysteresis import evaluate, limits

import completed_seed_pilot as pilot

n = pilot.n


def configured(settings):
    value = settings.get('completed_seed_mode', False)
    if type(value) is not bool:
        raise ValueError('Completed seed mode must be explicitly boolean')
    return value


def sync_cycle(settings):
    usage = shutil.disk_usage(n.POOL_ROOT)
    path = n.BASE / 'completed-cache-cycle.json'
    scope = {k: getattr(n.PROFILE, k) for k in ('pool', 'share', 'torrent_container')}
    state = evaluate(settings, n.read_json(path, {}), usage.total, usage.free, scope)
    n.atomic_json(path, state)
    return state


def run(origin='manual'):
    settings = n.read_json(n.CONFIG, {})
    if not configured(settings):
        return {'state': 'blocked', 'reason': 'completed_seed_mode_not_enabled'}
    pilot.environment()
    limit = min(n.batch_bytes(settings.get('batch_gib', 16)), pilot.LIMIT)
    with open('/var/run/fejes-completed-service.lock', 'a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if n.PID.exists() or n.needs_inspection(n.read_json(n.LAST, {})):
            return {'state': 'blocked', 'reason': 'mover_or_inspection'}
        cycle = sync_cycle(settings)
        if not cycle['active']:
            return {'state': 'deferred', 'reason': 'cache_cycle_inactive', 'cache_cycle': cycle}
        guards = n.guards()
        if any(state != 'pass' for state in guards.values()):
            return {'state': 'deferred', 'reason': 'native_guard_not_passed'}
        # Real first and second observations; no synthetic age or ratio values.
        n.collect(update=True)
        units = [unit for unit in pilot.plan() if unit['bytes'] <= limit]
        if not units:
            return {'state': 'nothing_eligible', 'reason': 'no_bounded_complete_unit'}
        prepared = pilot.prepare(units[0]['unit_digest'], service_settings=settings, origin=origin)
        # Record cooldown before taking native intent. The host then repeats all
        # guards under the normal mover/integrity/configuration locks.
        n.atomic_json(n.ATTEMPT, int(time.time()))
        result = pilot.run(prepared['authorization'])
        result['cache_cycle'] = sync_cycle(settings)
        return result


def preview(report, update=False):
    """Replace age/ratio eligibility with a fresh read-only completion plan."""
    settings = n.read_json(n.CONFIG, {})
    if not configured(settings):
        return report
    limit = min(n.batch_bytes(settings.get('batch_gib', 16)), pilot.LIMIT)
    units = [unit for unit in pilot.plan() if unit['bytes'] <= limit]
    members = {key: unit for unit in units for key in unit['paths']}
    forecast = report['forecast']
    forecast['completed_seed_mode'] = True
    forecast['completed_seed_limit_bytes'] = limit
    forecast['cache_start_percent'], forecast['cache_stop_percent'] = limits(settings)
    for row in forecast['rows']:
        row.update(age_ready_at=None, ratio_target_met=False, unit_blockers=[], unit_blocker_count=0)
        unit = members.get(n.ROOT + '/' + row['file'])
        row['reason'] = 'ready' if unit else 'completed_seed_unverified'
        if unit:
            row.update(unit_files=unit['files'], unit_bytes=unit['bytes'])
    report.update(completed_seed_mode=True, candidate_count=len(members),
                  skipped_counts=dict(Counter(row['reason'] for row in forecast['rows'] if row['reason'] != 'ready')))
    if update:
        n.atomic_json(n.FORECAST, forecast)
    return report
