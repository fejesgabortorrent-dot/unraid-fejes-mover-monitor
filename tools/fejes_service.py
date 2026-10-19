#!/usr/bin/env python3
"""Shared read-only diagnostics and an opt-in guarded legacy Mover launcher."""
import argparse
import fcntl
import json
import os
import re
import time
from pathlib import Path
import shutil
import subprocess
import sys

from torrent_preflight import assess, read_snapshot
from wire_integrity_cron import ORIGINAL, REPLACEMENT, rewrite_cron
from wire_mover_gate import rewrite_launcher

ROOT = Path('/boot/config/plugins/dynamix.file.integrity')
LAUNCHER = Path('/boot/config/plugins/user.scripts/scripts/Filmek_Mover_Threshold/script')
CACHE = '/mnt/cache'
LOCK = '/var/run/fejes-mover-launch.lock'
ERRORS = (ValueError, TypeError, KeyError, AttributeError, OSError, subprocess.SubprocessError)
BACKUP_MARKER = Path('/tmp/appdata.backup/running')
MDSTAT = Path('/proc/mdstat')
ATTEMPT = Path('/var/run/filmek_mover_last_attempt')
MOVER_PID = Path('/var/run/mover.pid')
SHARE = Path('/mnt/user/Filmek')


def dry_run(container='binhex-qbittorrentvpn'):
    """Read-only decision snapshot. Never execute a launcher or write a timestamp."""
    report = status(container)
    checks = []
    def add(key, state, detail=''):
        checks.append({'key': key, 'state': state, 'detail': detail})
    threshold = wait = None
    try:
        if LAUNCHER.is_symlink():
            raise ValueError('Symlink')
        source = LAUNCHER.read_text()
        rewrite_launcher(source)  # Reject drift; known guards only.
        if not SHARE.is_dir():
            raise ValueError('Required share unavailable')
        threshold = int(re.search(r'^KUSZOB_GIB=([0-9]+)$', source, re.M)[1])
        wait = int(re.search(r'^UJRA_PROBALKOZAS_MP=([0-9]+)$', source, re.M)[1])
        add('launcher', 'pass')
    except (IndexError, *ERRORS):
        add('launcher', 'unknown')
    free = report.get('cache_free_bytes')
    if report.get('cache') != 'available' or type(free) is not int or threshold is None:
        add('capacity', 'unknown')
    else:
        add('capacity', 'pass' if free < threshold*1024**3 else 'wait',
            {'free_gib': round(free/1024**3, 1), 'threshold_gib': threshold})
    decision = report.get('torrent')
    add('torrent', 'pass' if decision == 'no_torrent_blocker' else
        'wait' if decision == 'defer' else 'unknown', report.get('blocking_torrents'))
    try:
        if BACKUP_MARKER.exists():
            raw = BACKUP_MARKER.read_text().strip()
            if not raw.isdigit() or int(raw) <= 1:
                raise ValueError('Invalid backup PID')
            try:
                os.kill(int(raw), 0)
                add('backup', 'wait')
            except ProcessLookupError:
                add('backup', 'pass')
        else:
            add('backup', 'pass')
    except ERRORS:
        add('backup', 'unknown')
    try:
        values = re.findall(r'^mdResync=([0-9]+)$', MDSTAT.read_text(), re.M)
        if len(values) != 1:
            raise ValueError('Parity status missing')
        add('parity', 'pass' if int(values[0]) == 0 else 'wait')
    except ERRORS:
        add('parity', 'unknown')
    add('mover', 'wait' if MOVER_PID.exists() else 'pass')
    try:
        if wait is None:
            raise ValueError('Retry interval unknown')
        if ATTEMPT.exists():
            raw = ATTEMPT.read_text().strip()
            if not raw.isdigit():
                raise ValueError('Invalid timestamp')
            remaining = max(0, int(raw)+wait*60-int(time.time()))
            add('cooldown', 'wait' if remaining else 'pass', {'remaining_seconds': remaining})
        else:
            add('cooldown', 'pass', {'remaining_seconds': 0})
    except ERRORS:
        add('cooldown', 'unknown')
    states = {c['state'] for c in checks}
    report['dry_run'] = {'decision': 'unknown' if 'unknown' in states else
                         'wait' if 'wait' in states else 'ready',
                         'checks': checks, 'read_only': True}
    return report


def capacity(torrents, free, reserve):
    """All unfinished bytes are an upper bound, including array-backed downloads."""
    remaining = 0
    for item in torrents:
        value = item.get('amount_left')
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            return {'remaining_upper_bound_bytes': None, 'pressure': 'unknown'}
        remaining += value
    return {'remaining_upper_bound_bytes': remaining,
            'pressure': 'warning' if free < remaining + reserve else 'ok'}


def cron_state(source):
    try:
        expected = rewrite_cron(source)
    except ValueError:
        return 'unknown'
    return 'wired' if source == expected else 'original'


def status(container='binhex-qbittorrentvpn', reserve_gib=20):
    result = {'torrent': 'unavailable', 'cache': 'unavailable',
              'integrity_config': 'unknown', 'integrity_active': 'unknown',
              'legacy_launcher_present': LAUNCHER.is_file(),
              'mover_gate': 'manual_integration_required'}
    try:
        launcher = LAUNCHER.read_text()
        result['mover_gate'] = 'wired' if rewrite_launcher(launcher) == launcher else 'original'
    except ERRORS:
        result['mover_gate'] = 'unknown'
    # No media filenames, trackers, subprocess output or protected paths in reports.
    try:
        configured = (ROOT / 'integrity-check.cron').read_text()
        result['integrity_config'] = cron_state(configured)
        active = Path('/etc/cron.d/root').read_text()
        jobs = [line.split(None, 5) for line in active.splitlines()
                if line.strip() and not line.lstrip().startswith('#')]
        wanted = [line.split(None, 5) for line in configured.splitlines()
                  if line.strip() and not line.lstrip().startswith('#')]
        related = [job for job in jobs if len(job) == 6 and
                   (REPLACEMENT in job[5] or ORIGINAL in job[5])]
        result['integrity_active'] = ('wired' if result['integrity_config'] == 'wired'
                                      and related == wanted else 'not_verified')
    except OSError:
        pass
    snapshot = None
    try:
        torrents, mounts = read_snapshot(container, 5)
        decision = assess(torrents, mounts)
        snapshot = torrents
        result.update(torrent=decision['decision'],
                      checked_torrents=decision['checked_torrents'],
                      blocking_torrents=decision['blocking_torrents'])
    except ERRORS:
        pass
    try:
        if not os.path.ismount(CACHE):
            raise ValueError('Cache is not mounted')
        usage = shutil.disk_usage(CACHE)
        result.update(cache='available', cache_free_bytes=usage.free,
                      cache_total_bytes=usage.total, reserve_gib=reserve_gib)
        if snapshot is not None:
            result.update(capacity(snapshot, usage.free, reserve_gib * 1024**3))
    except ERRORS:
        pass
    return result


def run_mover(container):
    # Only this opt-in entry point starts the pre-existing automation. Its own
    # backup/parity/threshold/cooldown checks and timestamp writes remain intact.
    # No cron or User Scripts file is rewritten here.
    try:
        with open(LOCK, 'w') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            report = status(container)
            if (report['cache'] != 'available' or report['torrent'] == 'unavailable'
                    or not LAUNCHER.is_file() or LAUNCHER.is_symlink()):
                print('Mover deferred: required state or legacy launcher unavailable.')
                return 20
            if report['torrent'] != 'no_torrent_blocker':
                print('Mover deferred: unfinished or busy torrents. Cache pressure: ' +
                      report.get('pressure', 'unknown') + '.')
                return 10
            if Path('/var/run/mover.pid').exists():
                print('Mover deferred: Mover PID file is present.')
                return 10
            subprocess.run(['bash', '-n', str(LAUNCHER)], check=True,
                           capture_output=True, timeout=5)
            # Reject accidental recursion if this wrapper was copied into the
            # legacy script. The original script must remain at LAUNCHER.
            if any(marker in LAUNCHER.read_text() for marker in ('fejes_service.py', 'BEGIN FEJES MOVER LOCK')):
                raise ValueError('Recursive launcher')
            return subprocess.run(['bash', str(LAUNCHER)]).returncode
    except BlockingIOError:
        print('Mover deferred: another guarded launch is active.')
        return 10
    except ERRORS:
        print('Mover deferred: launch could not be verified.')
        return 20


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['status', 'dry-run', 'run-mover'])
    parser.add_argument('--container', default='binhex-qbittorrentvpn')
    args = parser.parse_args(argv)
    if not args.container or args.container.startswith('-'):
        parser.error('Invalid container name')
    if args.action == 'run-mover':
        return run_mover(args.container)
    print(json.dumps(dry_run(args.container) if args.action == 'dry-run' else status(args.container), allow_nan=False))
    return 0


if __name__ == '__main__':
    sys.exit(main())
