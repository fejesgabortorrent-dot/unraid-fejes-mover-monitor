#!/usr/bin/env python3
"""Disposable FejesMover-Test only: real qBittorrent/native-component seed test.

This deliberately does NOT certify the full guarded batch runner: new torrents
cannot satisfy the production one-day age floor during an immediate test.
No production helper/configuration is rewritten; component overrides are scoped
to this process. There are no public trackers, published ports or data deletes.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

BASE = Path('/mnt/disk1/fm-acceptance')
SOURCE = Path('/mnt/cache/fejesmover')
NETWORK = 'fm-lab'
SEED = 'fm-qbit'
PEER = 'fm-peer'
COOKIE = '/tmp/fm-acceptance.cookies'
URL = 'http://127.0.0.1:8080/api/v2/'


class MissingTestTorrent(RuntimeError):
    pass


def command(args, data=None, secret=False, timeout=60):
    result = subprocess.run(args, input=data, text=True, capture_output=True, timeout=timeout)
    if result.returncode:
        # Never expose generated passwords, cookies, API payloads or logs.
        raise RuntimeError('Sensitive operation failed' if secret else
                           'Command failed: ' + ' '.join(args[:3]))
    return result.stdout


def environment():
    if Path('/proc/sys/kernel/hostname').read_text().strip() != 'FejesMover-Test':
        raise RuntimeError('Disposable guest hostname required')
    disks = command(['lsblk', '-dn', '-o', 'SERIAL']).split()
    if not {'FMTESTPARITY24', 'FMTESTDATA16', 'FMTESTCACHE08'} <= set(disks):
        raise RuntimeError('Expected disposable virtual disks missing')
    for p in (BASE, SOURCE, Path('/mnt/disk1/appdata/fm-peer')):
        if any(x.is_symlink() for x in (p, *p.parents)):
            raise RuntimeError('Symlink test path rejected')
    if not all(os.path.ismount(p) for p in ('/mnt/cache', '/mnt/disk1', '/mnt/user')):
        raise RuntimeError('Guest storage mounts required')
    network = json.loads(command(['docker', 'network', 'inspect', NETWORK]))[0]
    if network.get('Internal') is not True:
        raise RuntimeError('Internal-only test network required')
    BASE.mkdir(mode=0o700, exist_ok=True)


def container(name):
    item = json.loads(command(['docker', 'inspect', name]))[0]
    if not item['State']['Running'] or item['HostConfig'].get('PortBindings'):
        raise RuntimeError('Running container with no published ports required')
    if set(item['NetworkSettings']['Networks']) != {NETWORK}:
        raise RuntimeError('Container is not isolated to test network')
    source = '/mnt/user/fejesmover' if name == SEED else '/mnt/disk1/fm-peer'
    if not any(m['Type'] == 'bind' and m['Source'] == source and
               m['Destination'] == '/data' for m in item['Mounts']):
        raise RuntimeError('Reviewed test data binding required')
    return item


def authenticate(name):
    inspected=container(name)
    # A successful existing session can be reused without changing credentials.
    probe = subprocess.run(['docker', 'exec', name, 'curl', '-q', '-fsS',
                            '-b', COOKIE, URL + 'app/version'], capture_output=True, text=True)
    if probe.returncode:
        # Ignore credentials from previous container starts, including stderr.
        raw = subprocess.run(['docker','logs','--since',inspected['State']['StartedAt'],name],
                             capture_output=True,text=True,timeout=15)
        if raw.returncode:raise RuntimeError('Current startup log unavailable')
        matches = re.findall(r'temporary password[^\n]*?:\s*(\S+)', raw.stdout + raw.stderr, re.I)
        if not matches:
            raise RuntimeError('Generated temporary credential unavailable; no password changed')
        reply = command(['docker', 'exec', name, 'curl', '-q', '-fsS', '-c', COOKIE,
                         '--data-urlencode', 'username=admin', '--data-urlencode',
                         'password=' + matches[-1], URL + 'auth/login'], secret=True)
        # An authenticated read is authoritative even when login returns an empty 200 body.
        verified = command(['docker','exec',name,'curl','-q','-fsS','-b',COOKIE,URL+'app/version'],secret=True)
        if not re.fullmatch(r'v?\d+\.\d+[^\s]*',verified.strip()):
            raise RuntimeError('Authenticated test API version unavailable')
    # The production adapter invokes curl inside the container. Give that curl
    # an authenticated local session, rather than disabling WebUI authentication.
    config = 'cookie = "' + COOKIE + '"\n'
    command(['docker', 'exec', '-i', name, 'sh', '-c',
             'umask 077; cat > /root/.curlrc; chmod 600 ' + COOKIE], config, secret=True)


def api(name, endpoint, fields=None, torrent=False):
    args = ['docker', 'exec', name, 'curl', '-q', '-fsS', '--max-time', '15', '-b', COOKIE]
    if fields is not None:
        for key, value in fields.items():
            args += ['-F' if torrent else '--data-urlencode', key + '=' + str(value)]
    result = command(args + [URL + endpoint], secret=True)
    return json.loads(result) if endpoint in {'torrents/info', 'app/preferences'} else result


def save(state):
    path = BASE / 'current.json'
    temp = BASE / 'current.json.tmp'
    temp.write_text(json.dumps(state, indent=2) + '\n')
    temp.chmod(0o600)
    temp.replace(path)


def torrent(name, digest):
    rows = api(name, 'torrents/info')
    matches = [x for x in rows if x['hash'] == digest]
    if len(matches) != 1:
        raise MissingTestTorrent('Expected unique test torrent missing')
    return matches[0]


def wait_complete(name, digest, seconds=45):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        try:
            item = torrent(name, digest)
        except MissingTestTorrent:
            time.sleep(1)
            continue
        if item.get('progress') == 1 and item.get('state') in {'stalledUP', 'uploading', 'queuedUP', 'forcedUP'}:
            return item
        if item.get('state') in {'error', 'missingFiles'}:
            raise RuntimeError('Test torrent reported unavailable content')
        time.sleep(1)
    raise RuntimeError('Bounded torrent completion wait expired')


def encode(value):
    if isinstance(value, int):
        return b'i' + str(value).encode() + b'e'
    if isinstance(value, str):
        value = value.encode()
    if isinstance(value, bytes):
        return str(len(value)).encode() + b':' + value
    if isinstance(value, dict):
        return b'd' + b''.join(encode(k) + encode(v) for k, v in sorted(value.items())) + b'e'
    raise TypeError('Unsupported torrent metadata')


def prepare():
    seed = container(SEED)
    names = command(['docker', 'ps', '-a', '--format', '{{.Names}}']).splitlines()
    if PEER not in names:
        peer_data = Path('/mnt/disk1/fm-peer')
        peer_data.mkdir(exist_ok=True)
        os.chown(peer_data, 99, 100)
        peer_data.chmod(0o775)
        command(['docker', 'run', '-d', '--name', PEER, '--network', NETWORK,
                 '--memory', '512m', '-e', 'PUID=99', '-e', 'PGID=100',
                 '-v', '/mnt/disk1/appdata/fm-peer:/config',
                 '-v', '/mnt/disk1/fm-peer:/data', seed['Image']])
    container(PEER)
    for name in (SEED, PEER):
        deadline = time.monotonic() + 30
        while True:
            try:
                authenticate(name)
                break
            except RuntimeError:
                if time.monotonic() >= deadline:
                    raise
                time.sleep(1)
    run = 'seedproof-' + str(time.time_ns())
    source = SOURCE / run / 'seedproof.bin'
    source.parent.mkdir(parents=True, exist_ok=False)
    payload = os.urandom(16 * 1024**2)
    source.write_bytes(payload)
    source.chmod(0o644)
    piece = 256 * 1024
    info = dict(length=len(payload), name='seedproof.bin', **{'piece length': piece,
                'pieces': b''.join(hashlib.sha1(payload[i:i+piece]).digest()
                                   for i in range(0, len(payload), piece)), 'private': 1})
    metadata = BASE / (run + '.torrent')
    metadata.write_bytes(encode({'info': info}))
    digest = hashlib.sha1(encode(info)).hexdigest()
    for name in (SEED, PEER):
        command(['docker', 'cp', str(metadata), name + ':/tmp/fm-lab.torrent'])
    state = dict(version=1, run=run, hash=digest, sha256=hashlib.sha256(payload).hexdigest(),
                 bytes=len(payload), source=str(source), image_id=seed['Image'],
                 status='prepared', preflight='not yet exercised', seed_verified=False)
    save(state)
    api(SEED, 'torrents/add', dict(torrents='@/tmp/fm-lab.torrent',
                savepath='/data/' + run, skip_checking='false', autoTMM='false'), torrent=True)
    verify_prepared(state)


def verify_prepared(state):
    if state['status'] != 'prepared':
        raise RuntimeError('Prepared state required')
    authenticate(SEED)
    source = Path(state['source'])
    if hashlib.sha256(source.read_bytes()).hexdigest() != state['sha256']:
        raise RuntimeError('Prepared source content differs')
    # Current qBittorrent can return an empty 200 body. Authoritative state,
    # not a historical response string, determines whether the add succeeded.
    item = wait_complete(SEED, state['hash'])
    state.update(status='seeding_before_move', seed_version=api(SEED, 'app/version'),
                 torrent_state_before=item['state'], torrent_progress_before=item['progress'])
    save(state)
    print('PASS: private test torrent verified complete by real qBittorrent; no public tracker or port.')


def component(state):
    """Explicit component acceptance; never portray this as the full runner."""
    if state['status'] != 'seeding_before_move':
        raise RuntimeError('Fresh prepared run required; no repeated move')
    authenticate(SEED)
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
    import selective_mover as mover
    from torrent_preflight import read_snapshot, assess, host_path
    rows, mounts = read_snapshot(SEED, 5)
    if assess(rows, mounts)['decision'] != 'no_torrent_blocker':
        raise RuntimeError('Real torrent API reported a blocker')
    item = torrent(SEED, state['hash'])
    if item['state'] not in {'stalledUP', 'queuedUP'} or item['upspeed'] or item['dlspeed']:
        raise RuntimeError('Idle complete test torrent required')
    p = Path(state['source'])
    key = '/mnt/user/fejesmover/' + state['run'] + '/seedproof.bin'
    if host_path(item['content_path'], mounts) != key or item['progress'] != 1:
        raise RuntimeError('Real content namespace not verified')
    if mover.sha256(p) != state['sha256']:
        raise RuntimeError('Initial test content differs')
    mover.SOURCE = SOURCE
    # Sole simulated boundary: this newly created torrent is not one day old.
    # Full fresh_candidate covers more than age: all that is explicitly excluded
    # from the acceptance claim. Real snapshot checks above are additional checks.
    mover.fresh_candidate = lambda *args, **kwargs: (p, True)
    result = mover.execute_file(key, {}, 1)
    target = Path('/mnt/disk1/fejesmover') / state['run'] / 'seedproof.bin'
    if result.get('state') != 'moved' or p.exists() or mover.sha256(target) != state['sha256']:
        raise RuntimeError('Native component move did not verify')
    state.update(status='component_moved', result=result, cache_source_absent=True,
                 preflight='fresh_candidate simulated in this process; full runner unverified')
    save(state)
    api(SEED, 'torrents/recheck', {'hashes': state['hash']})
    time.sleep(2)
    item = wait_complete(SEED, state['hash'])
    state.update(status='rechecked_after_move', recheck_progress=item['progress'],
                 recheck_state=item['state'], logical_path_preserved=item['content_path'] == '/data/' + state['run'] + '/seedproof.bin')
    save(state)
    print('PASS: real native component move and real qBittorrent recheck after movement; full preflight unverified.')


def transfer(state):
    if state['status'] != 'rechecked_after_move':
        raise RuntimeError('Successful post-move recheck required')
    for name in (SEED, PEER):
        authenticate(name)
    try:
        torrent(PEER, state['hash'])
    except MissingTestTorrent:
        api(PEER, 'torrents/add', dict(torrents='@/tmp/fm-lab.torrent',
                    savepath='/data/' + state['run'], skip_checking='false', autoTMM='false'), torrent=True)
    seed = container(SEED)
    ip = seed['NetworkSettings']['Networks'][NETWORK]['IPAddress']
    port = api(SEED, 'app/preferences')['listen_port']
    api(PEER, 'torrents/addPeers', {'hashes': state['hash'], 'peers': ip + ':' + str(port)})
    item = wait_complete(PEER, state['hash'])
    target = Path('/mnt/disk1/fm-peer') / state['run'] / 'seedproof.bin'
    actual = hashlib.sha256(target.read_bytes()).hexdigest()
    deadline = time.monotonic() + 10
    while True:
        item = torrent(PEER, state['hash'])
        seed_item = torrent(SEED, state['hash'])
        if (item.get('downloaded', 0) >= state['bytes'] and
                seed_item.get('uploaded', 0) >= state['bytes']) or time.monotonic() >= deadline:
            break
        time.sleep(1)
    state.update(peer_hash_matches=actual == state['sha256'],
                 peer_downloaded_observed=item.get('downloaded'),
                 seed_uploaded_observed=seed_item.get('uploaded'),
                 peer_progress_observed=item.get('progress'))
    save(state)
    if actual != state['sha256'] or item.get('downloaded', 0) < state['bytes'] or seed_item.get('uploaded', 0) < state['bytes']:
        raise RuntimeError('Peer content or byte-count evidence incomplete')
    state.update(status='peer_transfer_verified', seed_verified=True, peer_sha256=actual,
                 peer_downloaded=item['downloaded'], seed_uploaded=seed_item['uploaded'],
                 limits='Native component plus real torrent continuity/peer transfer only; full guarded runner, tracker credit and age acceptance unverified.')
    save(state)
    print('PASS: peer downloaded all test bytes after movement; SHA-256 matched; seeder upload counted.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['prepare', 'verify-prepared', 'move-component', 'transfer', 'status'])
    args = parser.parse_args()
    environment()
    if args.action == 'prepare':
        prepare()
    else:
        state = json.loads((BASE / 'current.json').read_text())
        if args.action == 'verify-prepared':
            verify_prepared(state)
        elif args.action == 'move-component':
            component(state)
        elif args.action == 'transfer':
            transfer(state)
        else:
            print(json.dumps({k: v for k, v in state.items() if k not in {'source', 'hash'}}, indent=2))


if __name__ == '__main__':
    main()
