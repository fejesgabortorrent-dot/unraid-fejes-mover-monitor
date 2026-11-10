#!/usr/bin/env python3
"""Real installed-runner acceptance, restricted to the disposable VM.

No helper patches, time overrides, or modified age evidence are permitted.
Prepare starts a fresh private test torrent; a later run must genuinely age.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import seed_acceptance as lab

CONFIG=Path('/boot/config/plugins/fejes.mover.monitor')
ROOT=Path('/mnt/disk1/fm-acceptance/guarded')
lab.BASE=ROOT

def write_json(path,value):
    with path.open('x') as f:
        os.chmod(path,0o600)
        json.dump(value,f,indent=2);f.flush();os.fsync(f.fileno())

def environment():
    lab.environment()
    lab.container(lab.SEED);lab.container(lab.PEER)

def prepare():
    environment()
    if (ROOT/'current.json').exists():raise RuntimeError('Existing guarded test must be preserved')
    if any((CONFIG/n).exists() for n in ('settings.json','selective-profile.json','selective.json','selective-last.json')):
        raise RuntimeError('Expected fresh lab configuration; refusing to replace evidence')
    root=Path(__file__).resolve().parents[1]
    sys.path.insert(0,str(CONFIG/'tools'))
    from wire_mover_gate import rewrite_launcher,LOCK_BLOCK,DISPATCH_BLOCK
    source=(root/'tests/fixtures/threshold-reviewed.sh').read_text()
    launcher=rewrite_launcher(source).replace(LOCK_BLOCK,DISPATCH_BLOCK+LOCK_BLOCK,1)
    assert rewrite_launcher(launcher)==launcher
    subprocess.run(['bash','-n'],input=launcher,text=True,check=True)
    target=Path('/boot/config/plugins/user.scripts/scripts/FejesMover_Lab/script')
    if target.exists():raise RuntimeError('Lab launcher already exists')
    backup=ROOT/'boot-before-guarded.tgz'
    subprocess.run(['tar','-czf',str(backup),'-C','/boot','config'],check=True)
    backup.chmod(0o600)
    target.parent.mkdir(parents=True)
    with target.open('x') as f:f.write(launcher)
    target.chmod(0o700)
    write_json(CONFIG/'settings.json',dict(version=1,mode='advanced',pool='cache'))
    write_json(CONFIG/'selective-profile.json',dict(version=1,pool='cache',share='fejesmover',torrent_container='fm-qbit',launcher_script='FejesMover_Lab'))
    write_json(CONFIG/'selective.json',dict(version=1,age_days=1,ratio_target=0,batch_gib=16))
    lab.prepare()
    import selective_preview as preview
    _,current=preview.inventory(time.time(),{})
    preview.atomic_json(preview.INVENTORY,dict(version=1,files=current))
    print('PASS: fresh real test torrent; one-day age required; no schedule added')

def status():
    environment()
    s=json.loads((ROOT/'current.json').read_text())
    lab.authenticate(lab.SEED)
    row=lab.torrent(lab.SEED,s['hash'])
    print(json.dumps(dict(status=s['status'],progress=row['progress'],torrent_state=row['state'],
        completed_at=row['completion_on'],earliest_from_completion=row['completion_on']+86400,
        now=int(time.time()),source_on_cache=Path(s['source']).is_file()),indent=2))

def run(action):
    environment()
    lab.authenticate(lab.SEED)
    # Load the installed helper with its real profile and all real guards.
    sys.path.insert(0,str(CONFIG/'tools'))
    import selective_mover as mover
    before=json.loads((ROOT/'current.json').read_text())
    source=Path(before['source'])
    if not source.is_file() or mover.sha256(source)!=before['sha256']:
        raise RuntimeError('Guarded source must exist and match baseline')
    if action=='api-failure':
        # Genuine unavailability, confined to the isolated lab seeder.
        lab.command(['docker','stop','--time','10',lab.SEED])
    try:
        result=mover.run()
    finally:
        if action=='api-failure':lab.command(['docker','start',lab.SEED])
    stamp=str(time.time_ns())
    write_json(ROOT/(action+'-'+stamp+'.json'),result)
    if action=='api-failure':
        assert result['state']=='deferred' and result['error_code']=='torrent_snapshot_unavailable'
        assert result['moved_files']==0 and not result['requires_inspection']
        assert source.is_file() and mover.sha256(source)==before['sha256']
        print('PASS: real API outage deferred; zero files moved; source intact; no inspection latch')
    else:
        print(json.dumps(result,indent=2))
        if result.get('moved_files'):
            target=Path('/mnt/disk1/fejesmover')/before['run']/'seedproof.bin'
            assert not source.exists() and mover.sha256(target)==before['sha256']
            assert result['state']=='completed' and not result['requires_inspection']
            lab.authenticate(lab.SEED)
            row=lab.torrent(lab.SEED,before['hash'])
            assert row['progress']==1
            before.update(status='guarded_moved',result=result,seed_verified=False)
            lab.save(before)
            print('PASS: real guarded runner moved verified content; peer transfer still pending')

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('action',choices=['prepare','status','run','api-failure'])
a=p.parse_args()
if a.action=='prepare':prepare()
elif a.action=='status':status()
else:run(a.action)
