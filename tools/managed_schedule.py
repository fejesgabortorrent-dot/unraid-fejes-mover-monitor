#!/usr/bin/env python3
"""Opt-in scheduler settings and guarded tick; never enable on installation."""
import json
import os
import fcntl
import subprocess
import tempfile
import time
from pathlib import Path
from selective_profile import load_profile

CONFIG = Path('/boot/config/plugins/fejes.mover.monitor/automation.json')
RUNTIME = Path('/usr/local/emhttp/plugins/fejes.mover.monitor/FejesMoverRuntime.php')


def load(path=None, profile=None):
    path = CONFIG if path is None else Path(path)
    if path.is_symlink():
        raise ValueError('Symlink automation settings')
    if not path.exists():
        return None
    data = json.loads(path.read_text())
    return validate(data, profile)


def validate(data, profile=None):
    if not isinstance(data, dict) or type(data.get('version')) is not int or data['version'] != 1:
        raise ValueError('Unknown automation settings')
    if type(data.get('enabled')) is not bool:
        raise ValueError('Explicit automation choice required')
    profile = profile or load_profile()
    expected = {k:getattr(profile,k) for k in ('pool','share','torrent_container')}
    if data.get('scope') != expected:
        raise ValueError('Automation scope changed; configure again')
    for key, low, high in (('threshold_gib',1,1048576),('cooldown_minutes',1,10080)):
        if type(data.get(key)) is not int or not low <= data[key] <= high:
            raise ValueError('Invalid '+key)
    if type(data.get('interval_minutes')) is not int or data['interval_minutes'] not in (5,10,15,30):
        raise ValueError('Invalid schedule interval')
    return data


def cron_text(settings):
    """Render only this plugin's cron entry. Caller must validate via load()."""
    if settings is None or not settings['enabled']:
        return ''
    interval = settings['interval_minutes']
    if type(interval) is not int or interval not in (5,10,15,30):
        raise ValueError('Invalid schedule interval')
    return (f'*/{interval} * * * * /usr/bin/python3 '
            '/boot/config/plugins/fejes.mover.monitor/tools/managed_schedule.py tick '
            '>/dev/null 2>&1\n')


def tick():
    # The executor rereads settings under its config lock. This early check is
    # not a substitute for any movement guard or an authorization to move.
    settings = load()
    if settings is None or not settings['enabled'] or not RUNTIME.is_file():
        return {'state':'deferred','reason':'managed_automation_disabled'}
    import selective_mover
    return selective_mover.run()


CRON = CONFIG.parent / 'managed-schedule.cron'
LOCK = Path('/var/run/fejes-mover-config.lock')


def atomic_write(path, text):
    if path.is_symlink():raise ValueError('Symlink destination')
    path.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(prefix='.schedule-',dir=path.parent)
    try:
        with os.fdopen(fd,'w') as stream:
            stream.write(text);stream.flush();os.fsync(stream.fileno())
        os.replace(tmp,path)
    finally:
        if os.path.exists(tmp):os.unlink(tmp)


def refresh_cron():
    # Some Unraid releases ship update_cron with CRLF line endings. Direct
    # exec then fails with ENOEXEC; invoking the known Bash script through its
    # interpreter works across those releases.
    subprocess.run(['bash','/usr/local/sbin/update_cron'],check=True,timeout=15,capture_output=True)


def sync(remove=False):
    with LOCK.open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        text='' if remove else cron_text(load())
        atomic_write(CRON,text)
        refresh_cron()


def configure(data):
    with LOCK.open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        data=validate(data)
        runtime=json.loads((CONFIG.parent/'settings.json').read_text())
        if data['enabled'] and (runtime.get('mode')!='advanced' or runtime.get('pool')!=data['scope']['pool']):
            raise ValueError('Matching Advanced mode required')
        if CONFIG.is_symlink() or CRON.is_symlink():raise ValueError('Symlink settings')
        previous={p.name:p.read_text() if p.exists() else None for p in (CONFIG,CRON)}
        backup=CONFIG.parent/'backups'/('automation-'+str(time.time_ns())+'.json')
        atomic_write(backup,json.dumps(previous))
        # A failed scheduler update must leave movement disabled, not silently
        # return to legacy authorization. The executor checks under the same lock.
        atomic_write(CONFIG,json.dumps(dict(data,enabled=False)))
        atomic_write(CRON,cron_text(data))
        refresh_cron()
        atomic_write(CONFIG,json.dumps(data))
        return {'saved':True,'enabled':data['enabled']}


if __name__ == '__main__':
    import argparse
    import sys
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['tick','preview-cron','configure','sync','remove-cron'])
    args=parser.parse_args()
    try:
        if args.action=='tick':print(json.dumps(tick()))
        elif args.action=='configure':print(json.dumps(configure(json.load(sys.stdin))))
        elif args.action in ('sync','remove-cron'):sync(args.action=='remove-cron')
        else:print(cron_text(load()),end='')
    except (OSError,ValueError,TypeError,KeyError,subprocess.SubprocessError):
        print(json.dumps({'saved':False,'state':'deferred','reason':'automation_settings_unverified'}))
        raise SystemExit(20)
