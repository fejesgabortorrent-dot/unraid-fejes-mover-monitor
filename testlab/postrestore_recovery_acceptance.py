#!/usr/bin/env python3
"""VM-only recovery fixture using already-moved data; never repeats movement.

An owned child exits without cleanup after persisting a synthetic restored/full
ledger and its PID. Real disk hashes and torrent evidence must then pass the
normal recovery. This is not a native-I/O crash or power-loss simulation.
"""
from pathlib import Path
import contextlib
import fcntl
import hashlib
import json
import os
import shutil
import sys

import active_seed_acceptance as h

TREE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TREE / 'tools'))
import selective_recovery as r
n = r.mover
BASE = Path('/mnt/disk1/fm-acceptance/pr48-postrestore-recovery-v1')


def main():
    h.lab.environment()
    assert os.uname().nodename == 'FejesMover-Test'
    assert n.ROOT == '/mnt/user/fejesmover' and n.PROFILE.torrent_container == 'fm-qbit'
    assert not BASE.exists() and not n.PID.exists()
    assert not n.needs_inspection(n.read_json(n.LAST, {}))
    assert n.read_json(n.BASE / 'automation.json', {})['enabled'] is False
    BASE.mkdir(mode=0o700)
    candidates = sorted(BASE.parent.glob('fejes-completed-seed-pilot-*'),
                        key=lambda p: p.stat().st_mtime, reverse=True)
    source = next(p for p in candidates if (p/'outcome.json').exists()
        and json.loads((p/'outcome.json').read_text()).get('seed_ready_verified') is True)
    directory = BASE/'fixture'
    directory.mkdir(mode=0o700)
    for name in ('unit.json','authorization.json','rollback.tgz'):
        shutil.copy2(source/name, directory/name)
    unit = json.loads((directory/'unit.json').read_text())
    assert unit['bytes'] <= 33554432
    report = json.loads((source/'active-seed-pilot-last.json').read_text())
    rows = report['verified_files']
    assert len(rows) == len(unit['paths'])
    report.update(state='native_verified', requires_inspection=True,
        active_file_started=False, native_outcome={'state':'moved'},
        coordination={'phase':'restored','quiesced':True,
                      'owners':unit['owners'],'resume':unit['owners']})
    for key in ('active_file','active_sha256','seed_ready_verified','peer_upload_verified'):
        report.pop(key, None)
    original = n.LAST.read_bytes()
    attempt = n.ATTEMPT.read_bytes() if n.ATTEMPT.exists() else None
    old = BASE.parent/'current.json'
    old_hash = hashlib.sha256(old.read_bytes()).hexdigest()
    (BASE/'native-last-before.json').write_bytes(original)
    child = os.fork()
    if child == 0:
        with contextlib.ExitStack() as stack:
            for name in (*r.LOCKS, 'fejes-mover-config.lock'):
                f = stack.enter_context(open('/var/run/'+name,'a'))
                fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
            assert not n.PID.exists()
            n.PID.write_text(str(os.getpid()))
            n.atomic_json(directory/'active-seed-pilot-last.json',report)
            n.atomic_json(n.LAST,dict(report,version=2,
                stage='completed_seed_coordination',coordination_pid=os.getpid(),
                moved_files=len(rows),moved_bytes=sum(x['bytes'] for x in rows)))
            os._exit(17)
    _, status = os.waitpid(child,0)
    assert os.waitstatus_to_exitcode(status) == 17
    try:
        assert not Path('/proc',str(child)).exists() and n.PID.read_text()==str(child)
        r.BACKUP_DIR=BASE/'recovery-backups'
        before = n.LAST.read_bytes()
        checked=r.run('inspect',pilot_directory=directory)
        assert n.LAST.read_bytes()==before and n.PID.read_text()==str(child)
        assert checked['checked_destinations']==len(rows) and checked['orphan_pid']==str(child)
        result=r.run('recover',checked['report_sha256'],r.CONFIRM,directory)
        assert result['recovered'] is True and result['future_movement_started'] is False
        assert not n.PID.exists() and not n.needs_inspection(n.read_json(n.LAST,{}))
        assert hashlib.sha256(old.read_bytes()).hexdigest()==old_hash
        proof={'success':True,'fixture':'synthetic restored ledger, actual dead owned child',
               'no_media_movement':True,'old_acceptance_unchanged':True,
               'inspection':checked,'recovery':result}
        n.atomic_json(BASE/'proof.json',proof)
        print(json.dumps(proof,indent=2),flush=True)
    finally:
        (BASE/'native-last-after-test.json').write_bytes(n.LAST.read_bytes())
        if n.PID.exists():
            assert n.PID.read_text()==str(child) and not Path('/proc',str(child)).exists()
            n.PID.unlink()
        n.LAST.write_bytes(original)
        if attempt is None:
            if n.ATTEMPT.exists(): n.ATTEMPT.unlink()
        else: n.ATTEMPT.write_bytes(attempt)
        assert n.LAST.read_bytes()==original
        print('ORIGINAL_VM_STATE_RESTORED',flush=True)


if __name__=='__main__':
    main()
