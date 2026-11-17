#!/usr/bin/env python3
"""Fresh VM-only acceptance of a complete torrent already spanning two tiers.

Stage one verified member with the real native engine under all four locks,
then let the bounded pilot discover and move only the remaining cache member.
This is deliberate fixture preparation, not recovery of an ambiguous operation.
No old fixture is reset or replayed. The original Nov 10 proof stays unchanged.
"""
from contextlib import ExitStack
import fcntl
import hashlib
import json
import os
from pathlib import Path
import sys
import time

import active_seed_acceptance as h

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import completed_seed_pilot as pilot
from active_seed_host import LOCK_NAMES
from qbit_seed_transport import DockerQbitTransport
from seed_coordination import SeedCoordinator

BASE = Path('/mnt/disk1/fm-acceptance/pr48-hybrid-v1')


def run():
    h.lab.environment()
    assert os.uname().nodename == 'FejesMover-Test'
    h.BASE = BASE
    n = h.environment()
    assert not BASE.exists()
    old = Path('/mnt/disk1/fm-acceptance/current.json')
    old_digest = hashlib.sha256(old.read_bytes()).hexdigest()
    config = n.BASE / 'automation.json'
    backup = config.with_name('automation.json.pr48-hybrid-backup')
    saved = config.read_bytes()
    assert json.loads(saved)['enabled'] is False and not backup.exists()
    config.rename(backup)
    try:
        h.prepare()
        h.write_new(BASE / 'automation-before.json', json.loads(saved))
        fixture = json.loads((BASE / 'fixture.json').read_text())
        inventory = json.loads((BASE / 'inventory.json').read_text())['files']
        keys = sorted(inventory)
        transport = DockerQbitTransport(h.lab.SEED)
        coordinator = SeedCoordinator(transport, journal=lambda value:
            h.write_new(BASE / ('staging-coordination-' + str(time.time_ns()) + '.json'), value))
        with ExitStack() as stack:
            for name in LOCK_NAMES:
                lock = stack.enter_context(open('/var/run/' + name, 'a'))
                fcntl.flock(lock, (fcntl.LOCK_SH if name == 'fejes-mover-config.lock'
                                  else fcntl.LOCK_EX) | fcntl.LOCK_NB)
            assert not n.PID.exists() and not n.needs_inspection(n.read_json(n.LAST, {}))
            fd = os.open(n.PID, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, 'w') as stream:
                stream.write(str(os.getpid()))
                stream.flush()
                os.fsync(stream.fileno())
            token = None
            try:
                token = coordinator.prepare([fixture['hash']])
                result = n.execute_completed_seed_file(keys[0], inventory[keys[0]], 1,
                    lambda checksum: h.write_new(BASE / 'staging-native-intent.json',
                                                 {'source': keys[0], 'sha256': checksum}))
                h.write_new(BASE / 'staging-native-result.json', result)
                if result.get('state') != 'moved':
                    raise RuntimeError('Fixture staging did not verify movement')
            finally:
                try:
                    if token is not None:
                        coordinator.restore(token)
                finally:
                    if n.PID.read_text() == str(os.getpid()):
                        n.PID.unlink()
        # Two genuine observations; no age or timestamp overrides.
        n.collect(update=True)
        units = [u for u in pilot.plan() if keys[1] in u['paths']]
        assert len(units) == 1
        unit = units[0]
        assert unit['paths'] == [keys[1]] and set(unit['retained_members']) == {keys[0]}
        h.write_new(BASE / 'hybrid-discovery.json', unit)
        authorization = pilot.prepare(unit['unit_digest'])['authorization']
        pilot.run(authorization)
        outcome = json.loads((Path(authorization).parent / 'outcome.json').read_text())
        assert outcome['state'] in {'completed', 'completed_seed_ready'}
        assert outcome['native_verified'] is True
        for item in fixture['files']:
            source = n.SOURCE / fixture['run'] / item['name']
            targets = n.destinations(source)
            assert not source.exists() and len(targets) == 1
            assert n.sha256(targets[0]) == item['sha256']
            assert n.sha256(Path(n.ROOT) / fixture['run'] / item['name']) == item['sha256']
        assert hashlib.sha256(old.read_bytes()).hexdigest() == old_digest
        proof = {'success': True, 'fresh_fixture_bytes': fixture['bytes'],
                 'retained_array_members': 1, 'newly_moved_cache_members': 1,
                 'original_array_member_not_recopied': True,
                 'all_physical_and_logical_hashes_verified': True,
                 'old_acceptance_proof_unchanged': True, 'outcome': outcome}
        h.write_new(BASE / 'hybrid-proof.json', proof)
        print(json.dumps(proof, indent=2))
    finally:
        assert not config.exists() and backup.read_bytes() == saved
        backup.rename(config)
        print('DISABLED_AUTOMATION_RESTORED', config.read_bytes() == saved)


if __name__ == '__main__':
    run()
