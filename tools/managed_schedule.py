#!/usr/bin/env python3
"""Opt-in scheduler settings and guarded tick; never enable on installation."""
import json
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


if __name__ == '__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['tick','preview-cron'])
    args=parser.parse_args()
    try:
        if args.action=='tick':print(json.dumps(tick()))
        else:print(cron_text(load()),end='')
    except (OSError,ValueError,TypeError,KeyError):
        print(json.dumps({'state':'deferred','reason':'automation_settings_unverified'}))
        raise SystemExit(20)
