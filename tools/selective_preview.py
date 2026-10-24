#!/usr/bin/env python3
"""Live inventory and read-only selection preview. No movement entry point."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import tempfile
import time
from collections import Counter
from selection_policy import plan, age_days
from torrent_preflight import read_snapshot, absolute_path
from fejes_service import dry_run

CONFIG = Path('/boot/config/plugins/fejes.mover.monitor/selective.json')
INVENTORY = Path('/boot/config/plugins/fejes.mover.monitor/selective-inventory.json')
SOURCE = Path('/mnt/cache/Filmek')
CANONICAL = '/mnt/user/Filmek'


def read_json(path, default):
    if path.is_symlink():
        raise ValueError('Symlink configuration')
    if not path.exists():
        return default
    return json.loads(path.read_text())


def atomic_json(path, data):
    payload = json.dumps(data, allow_nan=False, sort_keys=True).encode()
    fd, temporary = tempfile.mkstemp(prefix='.selective-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        if Path(temporary).read_bytes() != payload:
            raise OSError('Readback failed')
        os.replace(temporary, path)
        directory=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY)
        try:os.fsync(directory)
        finally:os.close(directory)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def canonical(path):
    path = absolute_path(path)
    # Known Unraid views only; the scanner itself traverses physical cache only.
    match = re.match(r'^/mnt/(?:cache|user0|disk[1-9][0-9]*)(/.*)?$', path)
    if match:
        return '/mnt/user' + (match[1] or '')
    if path == '/mnt/user' or path.startswith('/mnt/user/'):
        return path
    raise ValueError('Unrecognized host path namespace')


def open_paths():
    paths = set()
    for directory in Path('/proc').glob('[0-9]*/fd'):
        try:
            for fd in directory.iterdir():
                try:
                    target = os.readlink(fd)
                    if target.startswith('/mnt/'):
                        paths.add(canonical(target.removesuffix(' (deleted)')))
                except FileNotFoundError:
                    pass  # Process closed this descriptor during enumeration.
        except FileNotFoundError:
            pass
    return paths


def inventory(now, previous):
    if not os.path.ismount('/mnt/cache') or SOURCE.is_symlink() or not SOURCE.is_dir():
        raise ValueError('Source unavailable')
    opened = open_paths()
    files, current = [], {}
    device = SOURCE.stat().st_dev
    def fail(error):
        raise error
    for folder, directories, names in os.walk(SOURCE, followlinks=False, onerror=fail):
        directories[:] = [name for name in directories
                          if not (Path(folder)/name).is_symlink()]
        for name in names:
            path = Path(folder)/name
            info = path.lstat()
            if info.st_dev != device:
                raise ValueError('Nested mount')
            key = canonical(str(path))
            signature = [info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns]
            old = previous.get(key, {})
            same = old.get('signature') == signature
            first = old.get('first_seen') if same else now
            if type(first) not in (int, float) or not 0 <= first <= now:
                raise ValueError('Invalid inventory time')
            current[key] = {'signature': signature, 'first_seen': first}
            files.append(dict(path=key, regular=stat.S_ISREG(info.st_mode),
                              symlink=stat.S_ISLNK(info.st_mode), nlink=info.st_nlink,
                              open=key in opened, stable=same,
                              mtime=info.st_mtime, first_seen=first))
    return files, current


def integrity_observation(proc=Path('/proc'), run=Path('/var/run')):
    """Read-only evidence, never a movement authorization or a queue-drained claim."""
    watcher = b'/usr/local/emhttp/plugins/dynamix.file.integrity/scripts/watcher'
    try:
        listeners = 0
        for entry in proc.glob('[0-9]*/cmdline'):
            try:
                args = entry.read_bytes().split(b'\0')
            except FileNotFoundError:
                continue
            if watcher in args:
                listeners += 1
        pipes = sum(stat.S_ISFIFO(p.lstat().st_mode) for p in run.glob('hash.pipe.disk*'))
        return {'state': 'observed' if listeners and pipes else 'incomplete',
                'listeners': listeners, 'pipes': pipes,
                'movement_verified': False}
    except OSError:
        return {'state': 'unknown', 'movement_verified': False}


def collect(update_inventory=False):
    settings = read_json(CONFIG, {'version': 1, 'age_days': 7})
    if settings.get('version') != 1:
        raise ValueError('Unknown configuration version')
    days = age_days(settings.get('age_days'))
    now = time.time()
    previous = read_json(INVENTORY, {'version': 1, 'files': {}})
    if previous.get('version') != 1 or not isinstance(previous.get('files'), dict):
        raise ValueError('Invalid inventory')
    files, current = inventory(now, previous['files'])
    torrents, mounts = read_snapshot('binhex-qbittorrentvpn', 5)
    mounts = [dict(m, Source=canonical(m['Source'])) if m.get('Type') == 'bind' and
              m.get('Source', '').startswith('/mnt/') else m for m in mounts]
    # Require every resolved torrent path to be canonical, including completed ones.
    from torrent_preflight import host_path
    for torrent in torrents:
        resolved = host_path(torrent.get('content_path'), mounts)
        if canonical(resolved) != resolved:
            raise ValueError('Unresolved torrent namespace')
    report = dry_run()
    checks = {c['key']: c['state'] for c in report['dry_run']['checks']}
    guards = {k: checks.get(k, 'unknown') for k in ('backup', 'parity', 'mover', 'cooldown', 'capacity')}
    guards.update(mount='pass', namespace='pass', open_files='pass')
    # Cron wiring alone does not establish runtime watcher/hash safety.
    guards['integrity'] = 'unknown'
    if checks.get('launcher') != 'pass':
        guards['mount'] = 'unknown'
    result = plan(files, torrents, mounts, guards, days=days,
                  now=time.time(), observed_at=now, root=CANONICAL)
    # Selection diagnostics remain useful with global start blockers, but they
    # are explicitly hypothetical and can never authorize execution.
    selection_guards = dict(guards)
    selection_guards.update({key: 'pass' for key in selection_guards})
    selection = plan(files, torrents, mounts, selection_guards, days=days,
                     now=time.time(), observed_at=now, root=CANONICAL)
    if update_inventory:
        atomic_json(INVENTORY, {'version': 1, 'files': current})
    return {'age_days': days, 'execution_allowed': False, 'decision': result['decision'],
            'blockers': sorted(set(result['blockers'] + ['live_movement_not_integrated'])),
            'integrity_observation': integrity_observation(), 'selection_decision': selection['decision'],
            'candidate_count': len(selection['candidates']), 'file_count': len(files),
            'skipped_counts': dict(Counter(i['reason'] for i in selection['skipped'])),
            'inventory_updated': update_inventory, 'live_movement': 'not_integrated'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['preview', 'observe'])
    args = parser.parse_args()
    try:
        with open('/var/run/fejes-selective-inventory.lock', 'a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            print(json.dumps(collect(args.action == 'observe'), allow_nan=False))
        return 0
    except (OSError, ValueError, TypeError, KeyError, AttributeError, RuntimeError, subprocess.SubprocessError):
        print(json.dumps({'execution_allowed': False, 'decision': 'unknown',
                          'error': 'Inventory or protection state could not be verified'}))
        return 20


if __name__ == '__main__':
    raise SystemExit(main())
