#!/usr/bin/env python3
"""Deterministic real-scanner presence test; explicitly pause/resume lab Bunker."""
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import seed_acceptance as lab
lab.environment();lab.authenticate(lab.SEED)
root=Path('/mnt/disk1/fm-acceptance/guarded')
state=json.loads((root/'current.json').read_text())
source=Path(state['source'])
assert hashlib.sha256(source.read_bytes()).hexdigest()==state['sha256']
probe=root/('integrity-probe-'+str(time.time_ns())+'.bin')
with probe.open('xb') as stream:
    for _ in range(64):stream.write(b'\0'*1024**2)
probe.chmod(0o600)
scanner='/usr/local/emhttp/plugins/dynamix.file.integrity/scripts/bunker'
process=subprocess.Popen([scanner,'-aq',str(probe)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
try:
    process.send_signal(signal.SIGSTOP)
    deadline=time.monotonic()+3
    while 'State:\tT' not in Path('/proc',str(process.pid),'status').read_text():
        if time.monotonic()>deadline:raise RuntimeError('Could not suspend lab scanner')
        time.sleep(0.02)
    sys.path.insert(0,'/boot/config/plugins/fejes.mover.monitor/tools')
    import selective_mover as mover
    result=mover.run()
    assert result['state']=='deferred' and 'integrity' in result['blockers']
    assert result['moved_files']==0 and not result['requires_inspection']
    assert source.is_file() and mover.sha256(source)==state['sha256']
finally:
    if process.poll() is None:process.send_signal(signal.SIGCONT)
    try:process.wait(timeout=45)
    except subprocess.TimeoutExpired:
        process.terminate();process.wait(timeout=5)
        raise
assert process.returncode==0
assert os.getxattr(probe,'user.sha256').decode()==hashlib.sha256(probe.read_bytes()).hexdigest()
evidence=dict(kind='real_bunker_process_paused_then_resumed',result=result,scanner_exit=process.returncode,
              scanner_completed_and_hash_verified=True,source_intact=True,
              limitation='Proves scanner presence deferral, not mid-native scan race or sustained load')
p=root/('integrity-deferral-'+str(time.time_ns())+'.json');p.write_text(json.dumps(evidence,indent=2));p.chmod(0o600)
print('PASS: real scanner presence deferred movement; scanner resumed and completed; source intact; no latch')
