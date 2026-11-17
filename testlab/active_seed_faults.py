#!/usr/bin/env python3
"""Real VM-only API outage and before-native process-loss acceptance.

Never kills a VM or the native mover. SIGKILL targets only our own waiting
test child, after a real hash-scoped stop and durable before-stop journal.
Recovery is explicit, hash-scoped, and preserves the failed report/latch.
"""
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

import active_seed_acceptance as h

h.BASE = Path('/mnt/disk1/fm-acceptance/pr48-fault-tests')


def intact(native, state):
    for f in state['files']:
        p = native.SOURCE / state['run'] / f['name']
        if not p.is_file() or native.sha256(p) != f['sha256'] or native.destinations(p):
            raise RuntimeError('Fault-test source/destination changed')


def trial(native, evidence, transport, report):
    from active_seed_host import run_vm_trial
    return run_vm_trial(marker=h.BASE / 'vm-marker', report_path=report,
        initial_evidence=evidence.snapshot, fresh_evidence=evidence.snapshot,
        transport=transport, inventory=evidence.inventory, days=1,
        verify_files=evidence.verify_files, verify_peer=evidence.verify_peer,
        sleep=time.sleep, native_module=native, completed_seed=True)


def child():
    native = h.environment()
    state = json.loads((h.BASE / 'fixture.json').read_text())
    evidence = h.Evidence(native, state)
    evidence.snapshot()
    from qbit_seed_transport import DockerQbitTransport
    class HoldAfterRealStop(DockerQbitTransport):
        def stop(self, hashes):
            super().stop(hashes)
            h.write_new(h.BASE / 'child-stopped.json', {'pid': os.getpid(), 'hashes': hashes})
            time.sleep(120)  # Parent kills this owned test child, never native I/O.
    trial(native, evidence, HoldAfterRealStop(h.lab.SEED), h.BASE / 'active-seed-vm-last.json')


def main():
    native = h.environment()
    h.prepare()  # Fresh data only; refuses an existing fault-test directory.
    state = json.loads((h.BASE / 'fixture.json').read_text())
    evidence = h.Evidence(native, state)
    evidence.snapshot()
    from qbit_seed_transport import DockerQbitTransport
    transport = DockerQbitTransport(h.lab.SEED)
    outage_dir = h.BASE / 'api-outage'
    outage_dir.mkdir()
    outage_report = outage_dir / 'active-seed-vm-last.json'
    failed_closed = False
    h.lab.command(['docker', 'stop', '--time', '10', h.lab.SEED])
    try:
        try:
            trial(native, evidence, transport, outage_report)
        except Exception:
            failed_closed = True
    finally:
        h.lab.command(['docker', 'start', h.lab.SEED])
        deadline = time.monotonic() + 40
        while True:
            try:
                h.lab.authenticate(h.lab.SEED)
                break
            except RuntimeError:
                if time.monotonic() >= deadline:
                    raise
                time.sleep(1)
    intact(native, state)
    if not failed_closed or native.PID.exists() or outage_report.exists():
        raise RuntimeError('API outage did not fail before mutation/report')
    h.write_new(outage_dir / 'proof.json', {'real_container_outage': True,
                 'native_not_started': True, 'sources_intact': True, 'owned_pid_cleaned': True})

    process = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), '--owned-child'])
    report = h.BASE / 'active-seed-vm-last.json'
    try:
        deadline = time.monotonic() + 40
        while not (h.BASE / 'child-stopped.json').exists():
            if process.poll() is not None or time.monotonic() >= deadline:
                raise RuntimeError('Owned child did not reach before-native boundary')
            time.sleep(.25)
        ledger = json.loads(report.read_text())
        if (ledger.get('coordination', {}).get('phase') != 'before_stop' or
                ledger['coordination']['resume'] != [state['hash']] or
                not ledger['requires_inspection']):
            raise RuntimeError('Durable restoration intent not verified')
        row = h.lab.torrent(h.lab.SEED, state['hash'])
        if row['state'] not in {'stoppedUP', 'pausedUP'}:
            raise RuntimeError('Real stop not confirmed')
        os.kill(process.pid, signal.SIGKILL)
        process.wait(timeout=10)
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=10)
    before = hashlib.sha256(report.read_bytes()).hexdigest()
    outcome = trial(native, evidence, transport, report)
    if outcome != {'state': 'blocked', 'reason': 'prior_vm_report_requires_review'}:
        raise RuntimeError('Interrupted report did not block repeat trial')
    intact(native, state)
    # Explicit recovery after reviewing the exact ledger and all source hashes.
    transport.start(ledger['coordination']['resume'])
    h.lab.wait_complete(h.lab.SEED, state['hash'])
    if native.PID.read_text() != str(process.pid):
        raise RuntimeError('PID ownership changed; refusing stale PID cleanup')
    try:
        os.kill(process.pid, 0)
    except ProcessLookupError:
        native.PID.unlink()
    else:
        raise RuntimeError('Owned child still alive')
    if hashlib.sha256(report.read_bytes()).hexdigest() != before:
        raise RuntimeError('Interrupted ledger unexpectedly changed')
    proof = {'api_outage_passed': True, 'real_stop_then_owned_child_sigkill': True,
             'native_not_started': True, 'all_source_hashes_match': True,
             'repeat_attempt_blocked': True, 'exact_original_torrent_resumed': True,
             'stale_owned_pid_removed_after_death_check': True,
             'original_report_and_inspection_latch_preserved': True,
             'not_tested': ['VM power loss', 'process loss during native I/O', 'production host']}
    h.write_new(h.BASE / 'fault-proof.json', proof)
    print(json.dumps(proof, indent=2))


if __name__ == '__main__':
    try:
        child() if sys.argv[1:] == ['--owned-child'] else main()
    except Exception as error:
        print('FAULT_TEST_REQUIRES_INSPECTION: ' + type(error).__name__ + ': ' + str(error)[:200], file=sys.stderr)
        raise SystemExit(2)
