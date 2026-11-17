#!/usr/bin/env python3
"""Backed-up, single-unit owner pilot; no scheduler or implicit installation.

plan reads only. prepare binds a chosen unit digest to private rollback/evidence.
run requires that authorization and moves at most 32 GiB / 128 files once.
Seed readiness and genuinely observed post-move peer traffic are reported
separately: an idle seed is not a failed file move or evidence of peer traffic.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import posixpath
import subprocess
import stat
import tarfile
import time

import selective_mover as n
from selective_preview import atomic_json, read_json
from selection_policy import unit_groups, within
from torrent_preflight import host_path
from qbit_seed_transport import DockerQbitTransport
from active_seed_host import run_owner_pilot

RUNNING = {'uploading', 'stalledUP', 'queuedUP'}
LIMIT = 32 * 1024**3


def environment():
    host = os.uname().nodename
    if host == 'FejesMover-Test':
        serials = subprocess.check_output(['lsblk', '-dn', '-o', 'SERIAL'], text=True).split()
        if not {'FMTESTPARITY24', 'FMTESTDATA16', 'FMTESTCACHE08'}.issubset(serials):
            raise ValueError('Disposable disks missing')
        root = Path('/mnt/disk1/fm-acceptance')
    elif host == 'FejesNAS':
        if (n.PROFILE.pool, n.PROFILE.share, n.PROFILE.torrent_container) != ('cache', 'Filmek', 'binhex-qbittorrentvpn'):
            raise ValueError('Owner NAS profile mismatch')
        root = Path('/mnt/disk5/biztonsagi_mentesek')
    else:
        raise ValueError('Unsupported pilot host')
    if not os.path.ismount(root.parents[0] if host == 'FejesMover-Test' else Path('/mnt/disk5')):
        raise ValueError('Evidence disk not mounted')
    if any(p.is_symlink() for p in (root, *root.parents)):
        raise ValueError('Evidence path is a symlink')
    return root


def digest_paths(paths):
    return hashlib.sha256(json.dumps(sorted(paths), separators=(',', ':')).encode()).hexdigest()


def files_api(digest):
    # Hash comes from the authenticated full snapshot and is validated first.
    DockerQbitTransport._hash_args([digest])
    result = subprocess.run(['docker', 'exec', n.PROFILE.torrent_container, 'curl',
        '--fail', '--silent', '--show-error', '--max-time', '10',
        'http://127.0.0.1:8080/api/v2/torrents/files?hash=' + digest],
        capture_output=True, text=True, check=True, timeout=13)
    rows = json.loads(result.stdout)
    if not isinstance(rows, list) or not rows:
        raise ValueError('API file list missing')
    return rows


def mapped_files(owner, mounts):
    result = {}
    for f in files_api(owner['hash']):
        name = f.get('name')
        if (not isinstance(name, str) or name.startswith('/') or '..' in name.split('/')
                or f.get('progress') != 1 or f.get('priority', 0) <= 0
                or type(f.get('size')) is not int or f['size'] < 0):
            raise ValueError('Incomplete/ambiguous torrent file')
        key = host_path(posixpath.join(owner['save_path'], name), mounts)
        if key in result:
            raise ValueError('Duplicate API file')
        result[key] = f['size']
    return result


def no_writers(keys):
    for directory in Path('/proc').glob('[0-9]*/fd'):
        try:
            for fd in directory.iterdir():
                try:
                    target = os.readlink(fd).removesuffix(' (deleted)')
                    if not target.startswith('/mnt/'):
                        continue
                    try:
                        key = n.canonical(target)
                    except ValueError:
                        continue  # An unrelated storage namespace cannot alias a validated source.
                    if key not in keys:
                        continue
                    lines = (directory.parent / 'fdinfo' / fd.name).read_text().splitlines()
                    flags = int(next(x.split()[1] for x in lines if x.startswith('flags:')), 8)
                    if flags & os.O_ACCMODE:
                        return False
                except FileNotFoundError:
                    continue
        except FileNotFoundError:
            continue
    return True


def validate_retained_logical(key, size):
    path = Path(key)
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError('Linked retained logical path')
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_size != size:
        raise ValueError('Retained logical file absent or wrong size')


def retained_members(members, selected):
    """Bind existing array members without moving or claiming to rehash them.

    A completed torrent may already span cache and array. Every unselected API
    member must have exactly one regular, unchanged array placement and no cache
    copy. This is not permission to split or move an incomplete torrent.
    """
    retained = {}
    for key, size in members.items():
        if key in selected:
            continue
        if not key.startswith(n.ROOT + '/') or '..' in key.split('/'):
            raise ValueError('Retained member outside profile')
        source = n.SOURCE / Path(key).relative_to(n.ROOT)
        if any(p.is_symlink() for p in source.parents):
            raise ValueError('Linked retained cache parent')
        targets = n.destinations(source)
        if source.exists() or source.is_symlink() or len(targets) != 1:
            raise ValueError('Retained member missing or duplicated')
        target = targets[0]
        if any(p.is_symlink() for p in (target, *target.parents)):
            raise ValueError('Linked retained member')
        info = target.lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size != size:
            raise ValueError('Retained member type or size changed')
        validate_retained_logical(key, size)
        retained[key] = {'destination': str(target), 'signature': n.signature(info)}
    return retained


def collect(previous=None):
    previous = previous if previous is not None else read_json(n.INVENTORY, {'files': {}})['files']
    files, current = n.inventory_adapter.inventory(time.time(), previous)
    torrents, mounts = n.torrent_snapshot()
    return files, current, torrents, mounts


def owners_for(keys, torrents, mounts):
    return [t for t in torrents if any(within(k, host_path(t['content_path'], mounts)) or
             within(host_path(t['content_path'], mounts), k) for k in keys)]


def plan():
    files, current, torrents, mounts = collect()
    bypath = {f['path']: f for f in files}
    result = []
    for group in unit_groups(files, n.ROOT, torrents, mounts):
        size = sum(current[k]['signature'][2] for k in group)
        if size > LIMIT or len(group) > 128 or any(within(k, n.ROOT + '/EMBY') for k in group):
            continue
        owners = owners_for(group, torrents, mounts)
        if not owners or any(t.get('progress') != 1 or t.get('state') not in RUNNING or t.get('dlspeed') != 0 for t in owners):
            continue
        if any(not bypath[k]['stable'] or not bypath[k]['regular'] or bypath[k]['symlink'] or bypath[k]['nlink'] != 1 for k in group):
            continue
        try:
            retained, api_membership = {}, {}
            for t in owners:
                members = mapped_files(t, mounts)
                api_membership[t['hash']] = members
                retained.update(retained_members(members, group))
                if any(members[k] != current[k]['signature'][2] for k in members if k in group):
                    raise ValueError('Selected API member size changed')
            if not no_writers(set(group) | set(retained)):
                continue
            for key in group:
                p = n.SOURCE / Path(key).relative_to(n.ROOT)
                n.valid_file(p)
                if n.destinations(p):
                    raise ValueError('Existing array copy')
        except (ValueError, OSError, subprocess.SubprocessError):
            continue
        result.append({'unit_digest': digest_paths(group), 'paths': sorted(group),
                       'bytes': size, 'files': len(group), 'owners': sorted(t['hash'] for t in owners),
                       'inventory': {k: current[k] for k in group},
                       'retained_members': retained, 'api_membership': api_membership})
    return sorted(result, key=lambda x: -x['bytes'])


def prepare(chosen, service_settings=None):
    root = environment()
    if n.PID.exists() or n.needs_inspection(read_json(n.LAST, {})):
        raise ValueError('Existing mover/inspection')
    guards = n.guards()
    if any(v != 'pass' for v in guards.values()):
        raise ValueError('Real native guards not ready')
    units = [u for u in plan() if u['unit_digest'] == chosen]
    if len(units) != 1:
        raise ValueError('Chosen unit changed or is unavailable')
    unit = units[0]
    if service_settings is not None:
        if (n.read_json(n.CONFIG, {}) != service_settings
                or service_settings.get('completed_seed_mode') is not True):
            raise ValueError('Configured service settings changed')
        unit['service_settings'] = dict(service_settings)
    directory = root / ('fejes-completed-seed-pilot-' + str(time.time_ns()))
    directory.mkdir(mode=0o700)
    archive = directory / 'rollback.tgz'
    with tarfile.open(archive, 'x:gz') as tar:
        for p in (n.BASE, Path('/boot/config/plugins/fejes.mover.monitor.plg'),
                  Path('/usr/local/emhttp/plugins/fejes.mover.monitor'), n.PROFILE.launcher):
            if p.exists():
                tar.add(p, arcname=str(p).lstrip('/'))
    archive.chmod(0o600)
    with tarfile.open(archive, 'r:gz') as tar:
        for member in tar:
            if member.isfile():
                with tar.extractfile(member) as stream:
                    while stream.read(1024**2):
                        pass
    hashes = {}
    for key in unit['paths']:
        p = n.SOURCE / Path(key).relative_to(n.ROOT)
        if n.signature(n.valid_file(p)) != unit['inventory'][key]['signature']:
            raise ValueError('Unit changed while preparing')
        hashes[key] = n.sha256(p)
    _, _, torrents, mounts = collect(unit['inventory'])
    owners = owners_for(unit['paths'], torrents, mounts)
    logical = {t['hash']: {k: t[k] for k in ('content_path', 'save_path')} for t in owners}
    atomic_json(directory / 'unit.json', dict(unit, sha256=hashes, logical_paths=logical))
    with archive.open('rb') as stream:
        backup_digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    atomic_json(directory / 'authorization.json', {'version': 1, 'host': os.uname().nodename,
        'profile': {'pool': n.PROFILE.pool, 'share': n.PROFILE.share, 'torrent_container': n.PROFILE.torrent_container},
        'scope_paths': unit['paths'], 'rollback_sha256': backup_digest})
    return {'authorization': str(directory / 'authorization.json'),
            'bytes': unit['bytes'], 'files': unit['files']}


class Evidence:
    def __init__(self, directory):
        self.directory = directory
        self.unit = read_json(directory / 'unit.json', {})
        self.keys = self.unit['paths']
        self.inventory = self.unit['inventory']
        self.post_uploaded = None

    def snapshot(self):
        if ('service_settings' in self.unit
                and n.read_json(n.CONFIG, {}) != self.unit['service_settings']):
            raise ValueError('Configured service settings changed')
        files, current, torrents, mounts = collect(self.inventory)
        groups = [g for g in unit_groups(files, n.ROOT, torrents, mounts) if set(g).intersection(self.keys)]
        if len(groups) != 1 or set(groups[0]) != set(self.keys):
            raise ValueError('Whole unit changed')
        owners = owners_for(self.keys, torrents, mounts)
        if sorted(t['hash'] for t in owners) != self.unit['owners']:
            raise ValueError('Owners changed')
        for t in owners:
            if {k: t[k] for k in ('content_path', 'save_path')} != self.unit['logical_paths'][t['hash']]:
                raise ValueError('Torrent namespace changed')
            members = mapped_files(t, mounts)
            if (members != self.unit['api_membership'][t['hash']]
                    or any(members[k] != current[k]['signature'][2] for k in members if k in self.keys)):
                raise ValueError('API file membership changed')
        retained = {}
        for t in owners:
            retained.update(retained_members(self.unit['api_membership'][t['hash']], self.keys))
        if retained != self.unit['retained_members']:
            raise ValueError('Retained array members changed')
        for key in self.keys:
            p = n.SOURCE / Path(key).relative_to(n.ROOT)
            if current[key] != self.inventory[key] or n.sha256(p) != self.unit['sha256'][key] or n.destinations(p):
                raise ValueError('Source changed or target exists')
        owned = n.PID.exists() and n.PID.read_text() == str(os.getpid())
        guards = n.guards(owned=owned)
        prior = read_json(n.LAST, {})
        own_ledger = owned and prior.get('coordination_pid') == os.getpid()
        guards['inspection'] = 'pass' if own_ledger or not n.needs_inspection(prior) else 'unknown'
        bypath = {f['path']: f for f in files}
        return {'torrents': owners, 'guards': guards, 'owner_hashes': self.unit['owners'],
                'expected_paths': self.keys, 'verified_paths': self.keys,
                'stable': all(bypath[k]['stable'] for k in self.keys),
                'no_writers': no_writers(set(self.keys) | set(retained)), 'namespace_unchanged': True}

    def verify_files(self):
        for key in self.keys:
            p = n.SOURCE / Path(key).relative_to(n.ROOT)
            targets = n.destinations(p)
            if p.exists() or len(targets) != 1 or n.sha256(targets[0]) != self.unit['sha256'][key] or n.sha256(Path(key)) != self.unit['sha256'][key]:
                raise ValueError('Post-move file verification failed')
        torrents, mounts = n.torrent_snapshot()
        rows = {t['hash']: t for t in torrents if t['hash'] in self.unit['owners']}
        if sorted(rows) != self.unit['owners']:
            raise ValueError('Post-move owners changed')
        for digest, t in rows.items():
            if (t['progress'] != 1 or t['state'] not in RUNNING or t['dlspeed'] != 0
                    or {k: t[k] for k in ('content_path', 'save_path')} != self.unit['logical_paths'][digest]):
                raise ValueError('Seed readiness/namespace not verified')
            members = mapped_files(t, mounts)
            if members != self.unit['api_membership'][digest]:
                raise ValueError('Post-move API membership changed')
            if retained_members(members, self.keys) != {
                    k: v for k, v in self.unit['retained_members'].items() if k in members}:
                raise ValueError('Post-move retained array members changed')
        self.post_uploaded = {digest: t['uploaded'] for digest, t in rows.items()}
        atomic_json(self.directory / 'seed-ready.json', {'verified': True, 'peer_upload_baseline': self.post_uploaded})
        return {'hashes_match': True, 'logical_paths_unchanged': True, 'all_complete': True, 'resumed': True}

    def verify_peer(self, hashes):
        transport = DockerQbitTransport(n.PROFILE.torrent_container)
        deadline = time.monotonic() + 10
        while True:
            rows = transport.snapshot(hashes)
            deltas = {t['hash']: t['uploaded'] - self.post_uploaded[t['hash']] for t in rows}
            if all(v > 0 for v in deltas.values()) or time.monotonic() >= deadline:
                break
            time.sleep(1)
        observed = all(v > 0 for v in deltas.values())
        atomic_json(self.directory / 'peer-observation.json', {'actual_upload_observed': observed, 'uploaded_deltas': deltas})
        return observed


def run(authorization):
    environment()
    directory = Path(authorization).parent
    evidence = Evidence(directory)
    result = run_owner_pilot(authorization=authorization, report_path=directory / 'active-seed-pilot-last.json',
        initial_evidence=evidence.snapshot, fresh_evidence=evidence.snapshot,
        transport=DockerQbitTransport(n.PROFILE.torrent_container), inventory=evidence.inventory,
        verify_files=evidence.verify_files, verify_peer=evidence.verify_peer, sleep=time.sleep,
        native_module=n)
    atomic_json(directory / 'outcome.json', result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['plan', 'prepare', 'run'])
    parser.add_argument('--unit-digest')
    parser.add_argument('--authorization')
    args = parser.parse_args()
    environment()
    if args.action == 'plan':
        print(json.dumps([{'unit_digest': u['unit_digest'], 'bytes': u['bytes'], 'files': u['files']} for u in plan()], indent=2))
    elif args.action == 'prepare':
        print(json.dumps(prepare(args.unit_digest), indent=2))
    elif not args.authorization:
        parser.error('run requires the exact prepared authorization path')
    else:
        print(json.dumps(run(args.authorization), indent=2))


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print('PILOT_STOPPED: ' + type(error).__name__ + ': ' + str(error)[:200])
        raise SystemExit(2)
