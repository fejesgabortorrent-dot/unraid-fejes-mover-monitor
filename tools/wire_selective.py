#!/usr/bin/env python3
"""Reviewed opt-in dispatch; default is check-only, never starts movement."""
import argparse
import datetime
import fcntl
import hashlib
from pathlib import Path
import subprocess
import sys

from wire_mover_gate import LAUNCHER, LOCK_BLOCK, DISPATCH_BLOCK, rewrite_launcher
from wire_integrity_cron import atomic_write

def prepare(source):
    reviewed=rewrite_launcher(source)
    if reviewed!=source: raise ValueError('Existing launcher is not the reviewed guarded version')
    if DISPATCH_BLOCK in source: return source
    if source.count(LOCK_BLOCK)!=1: raise ValueError('Ambiguous dispatch location')
    result=source.replace(LOCK_BLOCK,DISPATCH_BLOCK+LOCK_BLOCK,1)
    if rewrite_launcher(result)!=result: raise ValueError('Dispatch validation failed')
    return result

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply',action='store_true')
    args=parser.parse_args()
    with open('/var/run/fejes-mover-settings.lock','a') as settings,open('/var/run/fejes-mover-launch.lock','a') as launch:
        for lock in (settings,launch): fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if LAUNCHER.is_symlink() or Path('/var/run/mover.pid').exists(): raise ValueError('Busy or invalid launcher')
        source=LAUNCHER.read_text();changed=prepare(source)
        subprocess.run(['bash','-n'],input=changed,text=True,capture_output=True,check=True)
        import selective_mover
        check=selective_mover.preview(False)
        if check['blockers']: raise ValueError('Selective guards do not permit activation')
        if not args.apply:
            print('CHECK ONLY: keep 15-minute schedule, threshold and cooldown; delegate existing Filmek script to age-filtered native executor.')
            print('Before SHA256:',hashlib.sha256(source.encode()).hexdigest())
            print('After SHA256:',hashlib.sha256(changed.encode()).hexdigest())
            print('No configuration or schedule changed. No movement started.')
            return 0
        if source==changed:
            print('Selective dispatch already wired. No movement started.');return 0
        backup=Path('/boot/config/plugins/fejes.mover.monitor/backups')/('selective-dispatch-before-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')+'.sh')
        backup.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
        atomic_write(backup,source,0o600)
        if backup.read_text()!=source or LAUNCHER.read_text()!=source: raise ValueError('Concurrent change or backup failure')
        atomic_write(LAUNCHER,changed,LAUNCHER.stat().st_mode&0o777)
        if LAUNCHER.read_text()!=changed: raise ValueError('Readback failed')
        print('Selective dispatch wired; existing schedule/threshold/cooldown preserved. No movement started.')
        print('Backup:',backup)
    return 0

if __name__=='__main__':
    try: raise SystemExit(main())
    except (OSError,ValueError,subprocess.SubprocessError):
        print('Dispatch not activated: required state could not be verified.');raise SystemExit(20)
