#!/usr/bin/env python3
"""Fresh acceptance through the actually installed scheduler entrypoint.

Only FejesMover-Test. Uses real valid 2/1-percent thresholds for its nearly
empty 8 GiB cache, without faking timestamps, capacity or guards. Cron stays
empty. The original disabled automation and selection settings are restored.
"""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import time

import active_seed_acceptance as h

TREE = Path(__file__).resolve().parents[1]
TOOLS = Path('/boot/config/plugins/fejes.mover.monitor/tools')
sys.path.insert(0, str(TOOLS))
import selective_mover as n
import completed_seed_pilot as pilot

BASE = Path('/mnt/disk1/fm-acceptance/pr48-installed-tick-v1')


def run():
    h.lab.environment()
    assert os.uname().nodename == 'FejesMover-Test'
    assert n.ROOT == '/mnt/user/fejesmover' and n.PROFILE.torrent_container == h.lab.SEED
    for line in (TREE / 'SHA256SUMS').read_text().splitlines():
        digest, name = line.split('  ', 1)
        if name.startswith('tools/'):
            assert hashlib.sha256((TOOLS / Path(name).name).read_bytes()).hexdigest() == digest
    assert not BASE.exists() and not n.PID.exists() and not n.needs_inspection(n.read_json(n.LAST, {}))
    BASE.mkdir(mode=0o700)
    automation = n.BASE / 'automation.json'
    original_automation = automation.read_bytes()
    original_selection = n.CONFIG.read_bytes()
    assert json.loads(original_automation)['enabled'] is False
    cron = n.BASE / 'managed-schedule.cron'
    cron_before = cron.read_bytes()
    assert not cron_before.strip()
    cycle = n.BASE / 'completed-cache-cycle.json'
    cycle_backup = cycle.with_name('completed-cache-cycle.json.pr48-tick-backup')
    cycle_result = cycle.with_name('completed-cache-cycle.json.pr48-tick-result')
    assert not cycle_backup.exists() and not cycle_result.exists()
    if cycle.exists():
        cycle.rename(cycle_backup)
    (BASE / 'automation-before.json').write_bytes(original_automation)
    (BASE / 'selection-before.json').write_bytes(original_selection)
    old = Path('/mnt/disk1/fm-acceptance/current.json')
    old_hash = hashlib.sha256(old.read_bytes()).hexdigest()
    try:
        selection = dict(json.loads(original_selection), completed_seed_mode=True,
                         age_days=30, ratio_target=100, batch_gib=32,
                         cache_start_percent=2, cache_stop_percent=1)
        n.atomic_json(n.CONFIG, selection)
        n.atomic_json(automation, {'version': 1, 'enabled': True,
            'scope': {k: getattr(n.PROFILE, k) for k in ('pool', 'share', 'torrent_container')},
            'threshold_gib': 300, 'cooldown_minutes': 1, 'interval_minutes': 30})
        deadline = time.monotonic() + 65
        while True:
            guards = n.guards()
            if all(v == 'pass' for v in guards.values()):
                break
            if (time.monotonic() >= deadline or any(v != 'pass' and k not in
                    {'integrity', 'cooldown'} for k, v in guards.items())):
                raise RuntimeError('Installed tick preflight not ready')
            time.sleep(2)
        h.BASE = BASE / 'fixture'
        h.prepare()
        fixture = json.loads((h.BASE / 'fixture.json').read_text())
        expected = {n.ROOT + '/' + fixture['run'] + '/' + item['name'] for item in fixture['files']}
        n.collect(update=True)
        units = pilot.plan()
        assert units and set(units[0]['paths']) == expected
        result = subprocess.run(['python3', str(TOOLS / 'managed_schedule.py'), 'tick'],
            capture_output=True, text=True, env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))
        (BASE / 'installed-tick.log').write_text(result.stdout + result.stderr)
        assert result.returncode == 0
        outcome = json.loads(result.stdout)
        assert outcome['state'] in {'completed', 'completed_seed_ready'}
        assert outcome['native_verified'] is True and outcome['cache_cycle']['active'] is True
        report = n.read_json(n.LAST, {})
        assert report['moved_files'] == 2 and report['moved_bytes'] == 33554432
        assert report['requires_inspection'] is False and report['state'] == 'completed'
        for item in fixture['files']:
            source = n.SOURCE / fixture['run'] / item['name']
            targets = n.destinations(source)
            assert not source.exists() and len(targets) == 1
            assert n.sha256(targets[0]) == item['sha256']
            assert n.sha256(Path(n.ROOT) / fixture['run'] / item['name']) == item['sha256']
        assert hashlib.sha256(old.read_bytes()).hexdigest() == old_hash
        proof = {'success': True, 'installed_scheduler_entrypoint': True,
                 'fresh_fixture_bytes': fixture['bytes'], 'fresh_fixture_files': 2,
                 'configured_age_days': 30, 'configured_ratio_target': 100,
                 'completion_replaced_age_and_ratio': True,
                 'real_vm_cache_thresholds': [2, 1], 'cron_never_enabled': True,
                 'old_acceptance_unchanged': True, 'outcome': outcome}
        h.write_new(BASE / 'installed-tick-proof.json', proof)
        print(json.dumps(proof, indent=2))
    finally:
        assert not n.PID.exists() and cron.read_bytes() == cron_before
        if cycle.exists():
            cycle.rename(cycle_result)
        if cycle_backup.exists():
            cycle_backup.rename(cycle)
        automation.write_bytes(original_automation)
        n.CONFIG.write_bytes(original_selection)
        assert automation.read_bytes() == original_automation and n.CONFIG.read_bytes() == original_selection
        print('ORIGINAL_DISABLED_AUTOMATION_SELECTION_AND_CRON_RESTORED')


if __name__ == '__main__':
    run()
