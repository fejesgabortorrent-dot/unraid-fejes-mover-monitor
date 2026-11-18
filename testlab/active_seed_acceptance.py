#!/usr/bin/env python3
"""Real completed-seed acceptance, exclusively in FejesMover-Test.

Fresh multi-file private data; no age overrides, guard mocks, production
installation, global torrent operations, data deletion or old-test replay.
The new explicit completed-seed native entry point intentionally has no
age/ratio admission rule. The ordinary age-based runner is unchanged.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import seed_acceptance as lab

SOURCE_TREE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SOURCE_TREE / 'tools'))
BASE = Path('/mnt/disk1/fm-acceptance/pr48-completed-seed-v1')


def write_new(path, value):
    with Path(path).open('x', encoding='utf-8') as stream:
        os.fchmod(stream.fileno(), 0o600)
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.flush()
        os.fsync(stream.fileno())


def environment():
    lab.environment()
    for name in (lab.SEED, lab.PEER):
        lab.container(name)
    if any(p.is_symlink() for p in (BASE, *BASE.parents)):
        raise RuntimeError('Symlink evidence path rejected')
    import selective_mover as native
    if (str(native.SOURCE) != '/mnt/cache/fejesmover' or
            native.ROOT != '/mnt/user/fejesmover' or
            native.PROFILE.torrent_container != lab.SEED):
        raise RuntimeError('Disposable test profile required')
    return native


def encode(value):
    if isinstance(value, list):
        return b'l' + b''.join(encode(v) for v in value) + b'e'
    if isinstance(value, dict):
        return b'd' + b''.join(encode(k) + encode(v) for k, v in sorted(value.items())) + b'e'
    return lab.encode(value)


def api_files(name, digest):
    return json.loads(lab.api(name, 'torrents/files?hash=' + digest))


def prove_api_files(rows, state):
    expected = {state['run'] + '/' + f['name']: f['bytes'] for f in state['files']}
    if (not isinstance(rows, list) or len(rows) != len(expected) or
            {f.get('name'): f.get('size') for f in rows} != expected or
            any(f.get('progress') != 1 or f.get('priority', 0) <= 0 for f in rows)):
        raise RuntimeError('Complete API file membership not verified')


def wait_rechecked(state, timeout=60):
    """A POST/recheck reply can precede the asynchronous state transition.

    Require both the torrent and every API file to remain complete over a
    two-second observation window, rather than accepting the first old row.
    """
    deadline = time.monotonic() + timeout
    complete_since = None
    while time.monotonic() < deadline:
        row = lab.torrent(lab.SEED, state['hash'])
        complete = row.get('progress') == 1 and row.get('state') in {'uploading', 'stalledUP', 'queuedUP'}
        try:
            prove_api_files(api_files(lab.SEED, state['hash']), state)
        except RuntimeError:
            complete = False
        if complete:
            if complete_since is None:
                complete_since = time.monotonic()
            if time.monotonic() - complete_since >= 2:
                return row
        else:
            complete_since = None
        time.sleep(.5)
    raise RuntimeError('Bounded recheck/file-completeness wait expired')


def wait_active(state):
    deadline = time.monotonic() + 45
    while time.monotonic() < deadline:
        seed = lab.torrent(lab.SEED, state['hash'])
        peer = lab.torrent(lab.PEER, state['hash'])
        if seed['state'] == 'uploading' and seed['upspeed'] > 0 and 0 < peer['progress'] < .9:
            return {'seed_uploaded': seed['uploaded'], 'peer_downloaded': peer['downloaded'],
                    'seed_upspeed': seed['upspeed'], 'peer_progress': peer['progress']}
        if peer['progress'] >= .9:
            raise RuntimeError('Peer finished too early; no move attempted')
        time.sleep(.5)
    raise RuntimeError('Active peer transfer not observed; no move attempted')


def prepare():
    native = environment()
    # Existing reports and fixtures are never overwritten or reset.
    if BASE.exists():
        raise RuntimeError('Prior PR48 fixture exists; inspect it instead')
    for name in (lab.SEED, lab.PEER):
        lab.authenticate(name)
    if native.PID.exists() or native.needs_inspection(native.read_json(native.LAST, {})):
        raise RuntimeError('Existing mover or inspection latch')
    guards = native.guards()
    if any(v != 'pass' for v in guards.values()):
        raise RuntimeError('Native guards are not ready')
    BASE.mkdir(mode=0o700)
    run = 'pr48-seed-' + str(time.time_ns())
    folder = native.SOURCE / run
    folder.mkdir(mode=0o755)
    files, pieces, pending = [], [], b''
    for name in ('part-a.mkv', 'part-b.mkv'):
        payload = os.urandom(16 * 1024**2)
        p = folder / name
        with p.open('xb') as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        p.chmod(0o644)
        files.append({'name': name, 'bytes': len(payload), 'sha256': hashlib.sha256(payload).hexdigest()})
        pending += payload
        while len(pending) >= 256 * 1024:
            pieces.append(hashlib.sha1(pending[:256 * 1024]).digest())
            pending = pending[256 * 1024:]
    if pending:
        pieces.append(hashlib.sha1(pending).digest())
    info = {'name': run, 'files': [{'length': f['bytes'], 'path': [f['name']]} for f in files],
            'piece length': 256 * 1024, 'pieces': b''.join(pieces), 'private': 1}
    metadata = BASE / 'fixture.torrent'
    metadata.write_bytes(encode({'info': info}))
    digest = hashlib.sha1(encode(info)).hexdigest()
    state = {'version': 1, 'run': run, 'hash': digest, 'files': files,
             'created': time.time(), 'bytes': sum(f['bytes'] for f in files),
             'source_tree': str(SOURCE_TREE), 'claim': 'fresh completed seed; no age or ratio wait'}
    # Persist ownership before sending either add request.
    write_new(BASE / 'fixture.json', state)
    for name in (lab.SEED, lab.PEER):
        if any(t['hash'] == digest for t in lab.api(name, 'torrents/info')):
            raise RuntimeError('Fixture torrent already present')
        lab.command(['docker', 'cp', str(metadata), name + ':/tmp/pr48-live.torrent'])
        lab.api(name, 'torrents/add', {'torrents': '@/tmp/pr48-live.torrent',
                'savepath': '/data', 'skip_checking': 'false', 'autoTMM': 'false',
                'stopped': 'true'}, torrent=True)
    lab.api(lab.SEED, 'torrents/start', {'hashes': digest})
    lab.wait_complete(lab.SEED, digest)
    prove_api_files(api_files(lab.SEED, digest), state)
    # A real first observation, followed later by an independent second scan.
    _, inventory = native.inventory_adapter.inventory(time.time(), {})
    keys = [native.ROOT + '/' + run + '/' + f['name'] for f in files]
    write_new(BASE / 'inventory.json', {'files': {k: inventory[k] for k in keys}})
    write_new(BASE / 'marker', {'notice': 'VM identity is independently verified on every action'})
    (BASE / 'vm-marker').write_text('FEJESMOVER_DISPOSABLE_TEST_VM_V1')
    print('PREPARED: fresh 32 MiB two-file private torrent; prior tests preserved.')


def no_writers(keys, native):
    for directory in Path('/proc').glob('[0-9]*/fd'):
        try:
            for fd in directory.iterdir():
                try:
                    target = os.readlink(fd)
                    if not target.startswith('/mnt/'):
                        continue
                    if native.canonical(target.removesuffix(' (deleted)')) not in keys:
                        continue
                    lines = (fd.parent.parent / 'fdinfo' / fd.name).read_text().splitlines()
                    flags = int(next(x.split()[1] for x in lines if x.startswith('flags:')), 8)
                    if flags & os.O_ACCMODE:
                        return False
                except FileNotFoundError:
                    continue
        except FileNotFoundError:
            continue
    return True


class Evidence:
    def __init__(self, native, state):
        self.native, self.state = native, state
        self.saved = json.loads((BASE / 'inventory.json').read_text())['files']
        self.keys = sorted(self.saved)
        self.inventory = None
        self.paths = None
        self.post = None

    def snapshot(self):
        n, s = self.native, self.state
        files, current = n.inventory_adapter.inventory(time.time(), self.saved)
        torrents, mounts = n.torrent_snapshot()
        from selection_policy import unit_groups, within
        groups = [g for g in unit_groups(files, n.ROOT, torrents, mounts) if set(g).intersection(self.keys)]
        if len(groups) != 1 or sorted(groups[0]) != self.keys:
            raise RuntimeError('Whole file unit membership changed')
        from torrent_preflight import host_path
        owners = [t for t in torrents if any(within(k, host_path(t['content_path'], mounts)) or
                  within(host_path(t['content_path'], mounts), k) for k in self.keys)]
        if len(owners) != 1 or owners[0]['hash'] != s['hash']:
            raise RuntimeError('Unexpected overlapping torrent owner')
        row = owners[0]
        paths = {'content_path': row['content_path'], 'save_path': row['save_path']}
        if host_path(row['content_path'], mounts) != n.ROOT + '/' + s['run']:
            raise RuntimeError('Logical torrent path mismatch')
        if self.paths is None:
            self.paths = paths
        elif self.paths != paths:
            raise RuntimeError('Logical torrent paths changed')
        prove_api_files(api_files(lab.SEED, s['hash']), s)
        bypath = {f['path']: f for f in files}
        stable = all(bypath[k]['stable'] and current[k] == self.saved[k] for k in self.keys)
        for f in s['files']:
            p = n.SOURCE / s['run'] / f['name']
            if n.sha256(p) != f['sha256'] or n.destinations(p):
                raise RuntimeError('Fixture baseline or destination changed')
        guards = n.guards(owned=n.PID.exists() and n.PID.read_text() == str(os.getpid()))
        prior = n.read_json(n.LAST, {})
        guards['inspection'] = 'unknown' if n.needs_inspection(prior) else 'pass'
        self.inventory = {k: current[k] for k in self.keys}
        return {'torrents': owners, 'guards': guards, 'owner_hashes': [s['hash']],
                'expected_paths': self.keys, 'verified_paths': self.keys, 'stable': stable,
                'no_writers': no_writers(set(self.keys), n), 'namespace_unchanged': True}

    def verify_files(self):
        n, s = self.native, self.state
        for f in s['files']:
            source = n.SOURCE / s['run'] / f['name']
            targets = n.destinations(source)
            key = Path(n.ROOT) / s['run'] / f['name']
            if source.exists() or len(targets) != 1 or n.sha256(targets[0]) != f['sha256'] or n.sha256(key) != f['sha256']:
                raise RuntimeError('Post-move physical/logical hash verification failed')
        lab.api(lab.SEED, 'torrents/recheck', {'hashes': s['hash']})
        row = wait_rechecked(s)
        prove_api_files(api_files(lab.SEED, s['hash']), s)
        if self.paths != {'content_path': row['content_path'], 'save_path': row['save_path']}:
            raise RuntimeError('Post-move torrent path changed')
        peer = lab.torrent(lab.PEER, s['hash'])
        self.post = {'seed_uploaded': row['uploaded'], 'peer_downloaded': peer['downloaded'],
                     'time': time.time()}
        write_new(BASE / 'post-move-baseline.json', self.post)
        return {'hashes_match': True, 'logical_paths_unchanged': True,
                'all_complete': row['progress'] == 1, 'resumed': row['state'] in {'uploading', 'stalledUP', 'queuedUP'}}

    def verify_peer(self, hashes):
        s = self.state
        if hashes != [s['hash']] or self.post is None:
            return False
        lab.api(lab.PEER, 'torrents/setDownloadLimit', {'hashes': s['hash'], 'limit': 0})
        connect_peer(s)
        peer = lab.wait_complete(lab.PEER, s['hash'], seconds=90)
        deadline = time.monotonic() + 10
        while True:
            seed = lab.torrent(lab.SEED, s['hash'])
            if seed['uploaded'] > self.post['seed_uploaded'] or time.monotonic() > deadline:
                break
            time.sleep(.5)
        for f in s['files']:
            target = Path('/mnt/disk1/fm-peer') / s['run'] / f['name']
            if self.native.sha256(target) != f['sha256']:
                return False
        proof = {'seed_uploaded_after': seed['uploaded'], 'peer_downloaded_after': peer['downloaded'],
                 'seed_uploaded_delta_after_move': seed['uploaded'] - self.post['seed_uploaded'],
                 'peer_downloaded_delta_after_move': peer['downloaded'] - self.post['peer_downloaded'],
                 'peer_complete': peer['progress'] == 1, 'peer_file_hashes_match': True}
        write_new(BASE / 'peer-proof.json', proof)
        return (proof['seed_uploaded_delta_after_move'] > 0 and
                proof['peer_downloaded_delta_after_move'] > 0 and proof['peer_complete'])


def connect_peer(state):
    seed = lab.container(lab.SEED)
    ip = seed['NetworkSettings']['Networks'][lab.NETWORK]['IPAddress']
    port = lab.api(lab.SEED, 'app/preferences')['listen_port']
    lab.api(lab.PEER, 'torrents/addPeers', {'hashes': state['hash'], 'peers': ip + ':' + str(port)})


def run():
    native = environment()
    report = BASE / 'active-seed-vm-last.json'
    if report.exists() or (BASE / 'run-intent.json').exists():
        raise RuntimeError('Prior trial exists; inspection required, no automatic retry')
    state = json.loads((BASE / 'fixture.json').read_text())
    for name in (lab.SEED, lab.PEER):
        lab.authenticate(name)
    evidence = Evidence(native, state)
    snapshot = evidence.snapshot()
    from active_seed_policy import assess_unit
    if assess_unit(**snapshot)['decision'] != 'coordination_required':
        raise RuntimeError('Real preflight failed; no torrent mutation')
    write_new(BASE / 'run-intent.json', {'created': time.time(), 'hash': state['hash'], 'scope': evidence.keys})
    lab.api(lab.PEER, 'torrents/setDownloadLimit', {'hashes': state['hash'], 'limit': 65536})
    lab.api(lab.PEER, 'torrents/start', {'hashes': state['hash']})
    connect_peer(state)
    write_new(BASE / 'active-before-move.json', wait_active(state))
    from active_seed_host import run_vm_trial
    # No mock/patch or execute_file wrapper: all actual native checks run twice.
    outcome = run_vm_trial(marker=BASE / 'vm-marker', report_path=report,
                initial_evidence=evidence.snapshot, fresh_evidence=evidence.snapshot,
                transport=__import__('qbit_seed_transport').DockerQbitTransport(lab.SEED),
                inventory=evidence.inventory, days=1, verify_files=evidence.verify_files,
                verify_peer=evidence.verify_peer, sleep=time.sleep,
                native_module=native, completed_seed=True)
    write_new(BASE / 'outcome.json', outcome)
    print(json.dumps(outcome, indent=2))


def main():
    global BASE
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['preflight', 'prepare', 'status', 'run'])
    parser.add_argument('--case', choices=['v1', 'v2'], default='v2')
    args = parser.parse_args()
    BASE = BASE.with_name('pr48-completed-seed-' + args.case)
    action = args.action
    if action == 'preflight':
        native = environment()
        for name in (lab.SEED, lab.PEER):
            lab.authenticate(name)
        print(json.dumps({'guards': native.guards(),
                          'inspection': native.needs_inspection(native.read_json(native.LAST, {})),
                          'fixture_exists': BASE.exists()}, indent=2))
    elif action == 'prepare':
        prepare()
    elif action == 'run':
        run()
    else:
        native = environment()
        s = json.loads((BASE / 'fixture.json').read_text())
        for name in (lab.SEED, lab.PEER):
            lab.authenticate(name)
        evidence = Evidence(native, s)
        snapshot = evidence.snapshot()
        from active_seed_policy import assess_unit
        print(json.dumps({'decision': assess_unit(**snapshot), 'guards': snapshot['guards'],
                          'stable': snapshot['stable'], 'no_writers': snapshot['no_writers']}, indent=2))


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        # Keep credential-bearing requests and traces out of user-visible output.
        print('BLOCKED_OR_INSPECTION_REQUIRED: ' + type(error).__name__, file=sys.stderr)
        if isinstance(error, RuntimeError):
            print(str(error)[:200], file=sys.stderr)
        raise SystemExit(2)
