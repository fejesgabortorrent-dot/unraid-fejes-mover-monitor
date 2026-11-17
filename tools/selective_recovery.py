#!/usr/bin/env python3
"""Explicit, evidence-backed recovery of a latched selective Mover report.

inspect: read-only feasibility check, never clears the latch.
recover --approve SHA256 --confirm: writes a verified HDD backup before atomically
marking the already verified movement as deferred. No media files are moved,
modified, deleted, or rechecked through qBittorrent's mutating API.
"""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import time
from urllib.parse import quote
import posixpath

from selective_preview import atomic_json
from torrent_preflight import host_path, SEED_STATES
import selective_mover as mover

BACKUP_DIR = Path('/mnt/disk5/biztonsagi_mentesek/fejes-mover-recovery')
LOCKS = ('fejes-mover-launch.lock', 'fejes-integrity-cron.lock',
         'fejes-selective-inventory.lock')
CONFIRM = 'I_UNDERSTAND_RECOVERY'
VALID_SHA = re.compile(r'^[0-9a-f]{64}$')


def validate_report(report):
    """Pure gate: never accept historical native intent or absent ledger evidence."""
    if not isinstance(report, dict) or report.get('version') != 2:
        raise ValueError('Unsupported report version')
    if (report.get('state') != 'error' or report.get('requires_inspection') is not True
            or report.get('active_file_started') is not False
            or report.get('stage') != 'file_preflight'
            or report.get('error_code') != 'required_state_unverified'):
        raise ValueError('Report is not an eligible pre-native inspection latch')
    rows = report.get('verified_files')
    count = report.get('moved_files')
    total = report.get('moved_bytes')
    if not isinstance(rows, list) or type(count) is not int or count < 1 or len(rows) != count:
        raise ValueError('Incomplete moved-file ledger')
    if type(total) is not int or total <= 0:
        raise ValueError('Invalid moved-byte total')
    if report.get('active_sha256'):
        raise ValueError('Unresolved native intent checksum')
    if report.get('scope') != f'{mover.PROFILE.pool}/{mover.PROFILE.share} -> Array; selected files only':
        raise ValueError('Movement scope differs from installed profile')
    seen = set()
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError('Invalid evidence entry')
        src, dst = row.get('source'), row.get('destination')
        digest, size = row.get('sha256'), row.get('bytes')
        if (not isinstance(src, str) or not src.startswith(mover.ROOT + '/')
                or not isinstance(dst, str) or not re.fullmatch(r'/mnt/disk[1-9][0-9]*/.+', dst)
                or type(size) is not int or size <= 0
                or not isinstance(digest, str) or not VALID_SHA.fullmatch(digest)
                or src in seen):
            raise ValueError('Incomplete or ambiguous moved-file evidence')
        seen.add(src)
        relative = src.removeprefix(mover.ROOT + '/')
        if dst.split('/', 3)[-1] != mover.PROFILE.share + '/' + relative:
            raise ValueError('Destination differs from original user-share path')
        signature = row.get('source_signature')
        if (not isinstance(signature, list) or len(signature) != 5
                or any(type(v) is not int for v in signature)
                or signature[2] != size):
            raise ValueError('Missing original physical signature')
    if sum(r['bytes'] for r in rows) != total:
        raise ValueError('Moved-byte evidence mismatch')
    return rows


def validate_pilot_report(report, unit):
    """Translate only a fully journaled, restored, pre-native pilot deferral.

    Original source signatures and checksums come from the private preparation
    snapshot, never from the current files. Physical verification is separate.
    """
    if (report.get('version') != 2 or report.get('state') != 'inspection_required'
            or report.get('stage') != 'completed_seed_coordination'
            or report.get('active_file_started') is not False
            or report.get('requires_inspection') is not True
            or report.get('active_sha256')):
        raise ValueError('Pilot has unresolved native intent')
    coordination = report.get('coordination', {})
    paths, owners = unit.get('paths'), unit.get('owners')
    if (not isinstance(paths, list) or not paths or len(paths) > 128
            or len(paths) != len(set(paths)) or set(paths) != set(report.get('scope_paths', []))
            or any(not isinstance(p, str) or not p.startswith(mover.ROOT + '/')
                   or '..' in p.split('/') or any(c in p for c in ('\n', '\r', '\x00')) for p in paths)
            or not isinstance(owners, list) or not owners or len(owners) != len(set(owners))
            or any(not isinstance(h, str) or not re.fullmatch('[a-fA-F0-9]{40}', h) for h in owners)
            or coordination.get('phase') != 'restored' or coordination.get('quiesced') is not True
            or sorted(coordination.get('owners', [])) != sorted(owners)
            or sorted(coordination.get('resume', [])) != sorted(owners)):
        raise ValueError('Pilot scope or restoration evidence incomplete')
    if report.get('active_file') not in paths:
        raise ValueError('Pilot deferral file missing')
    inventory, hashes = unit.get('inventory', {}), unit.get('sha256', {})
    if set(inventory) != set(paths) or set(hashes) != set(paths):
        raise ValueError('Preparation snapshot incomplete')
    for p in paths:
        signature = inventory[p].get('signature')
        if (not isinstance(signature, list) or len(signature) != 5
                or any(type(v) is not int or v < 0 for v in signature)
                or not isinstance(hashes[p], str) or not VALID_SHA.fullmatch(hashes[p])):
            raise ValueError('Invalid preparation evidence')
    rows = report.get('verified_files', [])
    if (not rows or len(rows) >= len(paths) or report['active_file'] in {r.get('source') for r in rows}
            or sum(inventory[p]['signature'][2] for p in paths) > 32 * 1024**3):
        raise ValueError('Pilot is not a bounded partial unit')
    enriched = []
    for row in rows:
        src = row.get('source')
        if src not in inventory or row.get('sha256') != hashes[src]:
            raise ValueError('Ledger differs from original preparation')
        enriched.append(dict(row, source_signature=inventory[src]['signature']))
    translated = dict(report, state='error', stage='file_preflight',
        error_code='required_state_unverified', verified_files=enriched,
        scope=f'{mover.PROFILE.pool}/{mover.PROFILE.share} -> Array; selected files only')
    return validate_report(translated)


def pilot_evidence(directory, report):
    directory = Path(directory)
    if (any(p.is_symlink() for p in (directory, *directory.parents))
            or directory.stat().st_uid != 0 or directory.stat().st_mode & 0o077):
        raise ValueError('Pilot evidence directory is not private')
    def load(name):
        path = directory / name
        if path.is_symlink() or path.stat().st_uid != 0:
            raise ValueError('Untrusted pilot evidence')
        return json.loads(path.read_text())
    unit = load('unit.json')
    original = load('active-seed-pilot-last.json')
    authorization = load('authorization.json')
    if (authorization.get('host') != os.uname().nodename
            or authorization.get('profile') != {'pool': mover.PROFILE.pool,
                'share': mover.PROFILE.share, 'torrent_container': mover.PROFILE.torrent_container}
            or authorization.get('scope_paths') != unit.get('paths')
            or any(report.get(k) != original.get(k) for k in original if k != 'version')):
        raise ValueError('Pilot and installed report differ')
    archive = directory / 'rollback.tgz'
    if archive.is_symlink():
        raise ValueError('Linked rollback archive')
    with archive.open('rb') as stream:
        if hashlib.file_digest(stream, 'sha256').hexdigest() != authorization.get('rollback_sha256'):
            raise ValueError('Rollback archive changed')
    return unit, validate_pilot_report(report, unit)


def check_retained(unit, rows):
    moved = {r['source'] for r in rows}
    retained = 0
    for key in unit['paths']:
        if key in moved:
            continue
        path = mover.SOURCE / Path(key).relative_to(mover.ROOT)
        signature = unit['inventory'][key]['signature']
        if (mover.signature(mover.valid_file(path)) != signature or mover.destinations(path)
                or mover.sha256(path) != unit['sha256'][key]
                or mover.sha256(Path(key)) != unit['sha256'][key]
                or mover.signature(mover.valid_file(path)) != signature):
            raise ValueError('Retained file changed or has an array copy')
        retained += 1
    return retained


def current_torrent_evidence(rows):
    """Read-only qBittorrent audit for each original torrent file in touched units."""
    items, mounts = mover.torrent_snapshot()
    mounted = {m.get('Destination'): m.get('Source') for m in mounts if m.get('Type') == 'bind'}
    if not any(source == mover.ROOT and dest == '/data' for dest, source in mounted.items()):
        raise ValueError('Torrent data binding differs from approved user share')
    touched = []
    for t in items:
        if not isinstance(t, dict) or not isinstance(t.get('hash'), str):
            raise ValueError('Invalid torrent identity')
        path = host_path(t.get('content_path'), mounts)
        for row in rows:
            src = row['source']
            if src == path or src.startswith(path.rstrip('/') + '/'):
                touched.append(t)
                break
    if not touched:
        raise ValueError('No matching qBittorrent torrent for verified media')
    seen = set()
    verified = 0
    for t in touched:
        h = t['hash']
        if h in seen or not re.fullmatch(r'[0-9a-fA-F]{40}', h):
            raise ValueError('Duplicate or invalid torrent identifier')
        seen.add(h)
        if t.get('progress') != 1 or t.get('state') not in SEED_STATES:
            raise ValueError('Affected torrent is not complete and seed-capable')
        save = t.get('save_path')
        if not isinstance(save, str):
            raise ValueError('Torrent save path unavailable')
        url = 'http://127.0.0.1:8080/api/v2/torrents/files?hash=' + quote(h, safe='')
        proc = subprocess.run(['docker','exec',mover.PROFILE.torrent_container,
                               'curl','--fail','--silent','--show-error',
                               '--connect-timeout','10','--max-time','15',url],
                              capture_output=True,text=True,timeout=22,check=True)
        data = json.loads(proc.stdout)
        if not isinstance(data,list) or not data:
            raise ValueError('Torrent file list unavailable')
        for file in data:
            name = file.get('name')
            size = file.get('size')
            if (not isinstance(name,str) or name.startswith('/') or
                    '..' in name.split('/') or type(size) is not int or size < 0 or
                    file.get('progress') != 1):
                raise ValueError('Torrent file metadata invalid or incomplete')
            mapped = host_path(posixpath.join(save,name),mounts)
            if not mapped.startswith(mover.ROOT + '/'):
                raise ValueError('Torrent file escapes validated share')
            p = Path(mapped)
            if p.is_symlink() or not p.is_file() or p.stat().st_size != size:
                raise ValueError('Torrent file absent, linked or wrong size')
            verified += 1
    # A second snapshot detects changing membership, identity, state or paths.
    post, post_mounts = mover.torrent_snapshot()
    if mounts != post_mounts:
        raise ValueError('Torrent mount binding changed during inspection')
    def snapshot(items):
        return {t['hash']: (t.get('progress'),t.get('state'),
                            t.get('content_path'),t.get('save_path')) for t in items}
    if snapshot(items) != snapshot(post):
        raise ValueError('Torrent membership or state changed during inspection')
    return {'matched_torrents':len(touched),'verified_torrent_files':verified,
            'torrent_membership_stable':True}


def check_media(rows):
    disks = set(mover.array_disks())
    checked = 0
    for row in rows:
        src = Path(row['source'])
        relative = src.relative_to(mover.ROOT)
        physical_src = mover.SOURCE / relative
        dst = Path(row['destination'])
        if dst.parent == dst or not any(dst.is_relative_to(d) for d in disks):
            raise ValueError('Destination disk is not a healthy array member')
        if physical_src.exists() or physical_src.is_symlink():
            raise ValueError('Verified source still exists on cache')
        if src.is_symlink() or not src.is_file():
            raise ValueError('User-share path unavailable or linked')
        if any(part.is_symlink() for part in (dst,*dst.parents) if part != Path('/')):
            raise ValueError('Destination contains symbolic links')
        info = dst.lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size != row['bytes']:
            raise ValueError('Destination file type or size changed')
        target_list = mover.destinations(physical_src)
        if target_list != [dst]:
            raise ValueError('Missing or duplicate array destination')
        if mover.sha256(dst) != row['sha256'] or mover.sha256(src) != row['sha256']:
            raise ValueError('Destination or user-share SHA256 mismatch')
        checked += 1
    return checked


def storage_quiet():
    if mover.PID.exists() or Path('/var/run/fejes-selective-last-attempt.lock').exists():
        raise ValueError('Mover activity cannot be excluded')
    scrub = subprocess.check_output(['btrfs','scrub','status',str(mover.POOL_ROOT)],
                                    timeout=12,text=True)
    if not re.search(r'^Status:\s+finished$',scrub,re.M) or 'no errors found' not in scrub:
        raise ValueError('Cache scrub unfinished or unhealthy')
    stats = subprocess.check_output(['btrfs','device','stats',str(mover.POOL_ROOT)],
                                    timeout=12,text=True)
    if not stats.strip() or any(not s.split()[-1].isdigit() or int(s.split()[-1]) for s in stats.splitlines()):
        raise ValueError('Cache device statistics unavailable or unhealthy')
    for node in Path('/proc').glob('[0-9]*/cmdline'):
        try:
            parts = node.read_bytes().split(b'\0')
        except (OSError,PermissionError):
            raise ValueError('Cannot establish maintenance process state')
        if any(p.endswith(b'/bunker') for p in parts):
            raise ValueError('Integrity scan in progress')


def read_report():
    if mover.LAST.is_symlink():
        raise ValueError('Symlink report prohibited')
    raw = mover.LAST.read_bytes()
    if not raw:
        raise ValueError('Empty prior report')
    return raw, hashlib.sha256(raw).hexdigest(),json.loads(raw)


def inspect_locked(pilot_directory=None):
    storage_quiet()
    raw, digest, report = read_report()
    if pilot_directory is None:
        rows = validate_report(report)
        retained = {}
    else:
        from completed_seed_pilot import no_writers, owners_for
        unit, rows = pilot_evidence(pilot_directory, report)
        def physical_snapshot():
            snapshot = {}
            for key in unit['paths']:
                source = mover.SOURCE / Path(key).relative_to(mover.ROOT)
                targets = mover.destinations(source)
                if source.exists():
                    if targets:
                        raise ValueError('Duplicate physical placement')
                    mover.valid_file(source)
                    target = source
                else:
                    if len(targets) != 1:
                        raise ValueError('Ambiguous physical placement')
                    target = targets[0]
                snapshot[key] = (str(target), mover.signature(target.lstat()))
            return snapshot
        before = physical_snapshot()
        if not no_writers(set(unit['paths'])):
            raise ValueError('Unit has an active writer')
        retained = {'checked_retained_files': check_retained(unit, rows)}
    checked = check_media(rows)
    torrents = current_torrent_evidence(rows)
    if pilot_directory is not None:
        items, mounts = mover.torrent_snapshot()
        owners = owners_for(unit['paths'], items, mounts)
        if (sorted(t['hash'] for t in owners) != sorted(unit['owners'])
                or any({k: t.get(k) for k in ('content_path', 'save_path')}
                       != unit['logical_paths'].get(t['hash']) for t in owners)
                or physical_snapshot() != before or not no_writers(set(unit['paths']))):
            raise ValueError('Unit changed during recovery inspection')
    if hashlib.sha256(mover.LAST.read_bytes()).hexdigest() != digest:
        raise ValueError('Prior report changed during inspection')
    return raw, digest, report, {'checked_destinations':checked,**torrents,**retained}


def backup_locked(raw, digest):
    if not Path('/mnt/disk5').is_mount():
        raise ValueError('Physical backup disk5 is not mounted')
    if BACKUP_DIR.is_symlink():
        raise ValueError('Recovery backup directory is a symlink')
    BACKUP_DIR.mkdir(parents=True,exist_ok=True,mode=0o700)
    if BACKUP_DIR.is_symlink():
        raise ValueError('Recovery backup path changed')
    path = BACKUP_DIR / ('selective-before-recovery-' + digest[:16] + '.json')
    fd = os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    try:
        with os.fdopen(fd,'wb') as out:
            out.write(raw)
            out.flush()
            os.fsync(out.fileno())
    except BaseException:
        raise
    if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
        raise ValueError('Backup readback mismatch')
    dirfd = os.open(BACKUP_DIR,os.O_RDONLY|os.O_DIRECTORY)
    try: os.fsync(dirfd)
    finally: os.close(dirfd)
    return path


def run(action, approval=None, confirm=None, pilot_directory=None):
    locks=[]
    try:
        for name in LOCKS:
            lock=open('/var/run/'+name,'a')
            locks.append(lock)
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        lock=open('/var/run/fejes-mover-config.lock','a')
        locks.append(lock)
        fcntl.flock(lock,fcntl.LOCK_SH|fcntl.LOCK_NB)
        raw,digest,prior,checks=inspect_locked(pilot_directory) if pilot_directory else inspect_locked()
        if action == 'inspect':
            return {'eligible':True,'requires_explicit_approval':True,
                    'report_sha256':digest,**checks}
        if (not isinstance(approval,str) or approval != digest or
                confirm != CONFIRM):
            raise ValueError('Explicit matching approval token required')
        # Reinspect under the same coordination locks; do not act on stale results.
        raw2,digest2,prior2,checks2=inspect_locked(pilot_directory) if pilot_directory else inspect_locked()
        if digest2 != digest or checks2 != checks or raw2 != raw:
            raise ValueError('Evidence changed before recovery')
        backup=backup_locked(raw,digest)
        if hashlib.sha256(mover.LAST.read_bytes()).hexdigest() != digest:
            raise ValueError('Report changed before atomic update')
        # Cooldown before unlocking: failed recoveries may only cause a longer wait.
        mover.atomic_json(mover.ATTEMPT,int(time.time()))
        record=dict(prior2)
        record.update(state='deferred',reason='manually_verified_inspection_recovery',
                      requires_inspection=False,active_file_started=False)
        record.pop('error_code',None)
        record.pop('error',None)
        for key in ('active_file','active_signature','active_sha256'):
            record.pop(key,None)
        record['recovery']={'version':1,'prior_sha256':digest,'checked_at':time.time(),
                            'checked_destinations':checks['checked_destinations'],
                            'matched_torrents':checks['matched_torrents'],
                            'verified_torrent_files':checks['verified_torrent_files'],
                            'historical_torrent_continuity':'not_available',
                            'operator_approved':True}
        mover.atomic_json(mover.LAST,record)
        if mover.needs_inspection(mover.read_json(mover.LAST,{})):
            raise ValueError('Post-recovery latch state could not be verified')
        return {'recovered':True,'prior_sha256':digest,
                'backup':str(backup),'new_state':'deferred',
                'future_movement_started':False,**checks}
    finally:
        for lock in reversed(locks):
            lock.close()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['inspect','recover'])
    parser.add_argument('--approve',default=None,help='Exact SHA256 from a successful inspect')
    parser.add_argument('--confirm',default=None,help='Explicit risk acknowledgement')
    parser.add_argument('--pilot-directory',default=None,help='Private original bounded-pilot evidence directory')
    args=parser.parse_args()
    try:
        output=run(args.action,args.approve,args.confirm,args.pilot_directory)
        print(json.dumps(output,sort_keys=True))
        return 0
    except (OSError,ValueError,TypeError,KeyError,RuntimeError,
            subprocess.SubprocessError,json.JSONDecodeError):
        # No private torrent names, arguments, source paths or exception traces in UI.
        print(json.dumps({'eligible':False,'recovered':False,
                          'error':'Safety evidence unavailable or inconsistent; inspection latch unchanged'}))
        return 20


if __name__=='__main__':
    raise SystemExit(main())
