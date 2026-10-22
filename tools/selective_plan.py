#!/usr/bin/env python3
"""Experimental read-only per-torrent plan. Never invokes Mover or qB writes.

Not packaged or enabled: live Unraid movement/seed acceptance is required.
"""
import math
import posixpath
from pathlib import PurePosixPath
from torrent_preflight import BUSY_STATES, SEED_STATES, host_path


def canonical(path):
    if (not isinstance(path, str) or not path.startswith('/')
            or any(c in path for c in ('\x00', '\n', '\r'))
            or '..' in PurePosixPath(path).parts):
        raise ValueError('Unsafe path')
    return posixpath.normpath(path)


def within(path, root):
    return path == root or path.startswith(root.rstrip('/') + '/')


def pool_relative(path, pool, share):
    path = canonical(path)
    roots = (f'/mnt/user/{share}', f'/mnt/{pool}/{share}')
    for root in roots:
        if within(path, root):
            return posixpath.relpath(path, root)
    raise ValueError('Torrent path outside the selected share')


def build_plan(torrents, mounts, file_lists, candidates, *, pool='cache', share='Filmek'):
    """Plan exact regular-file candidates from a validated inventory.

    file_lists maps torrent hashes to qB /torrents/files responses. All torrents
    must have a verified file list, including completed torrents (shared payloads).
    candidates: relative path, regular, symlink, nlink. No recursive directory
    submission is allowed. Missing/ambiguous state invalidates the whole plan.
    Caller must refresh API, mounts and filesystem before *each* real move.
    """
    if any(not isinstance(v, str) or not v or not all(c.isalnum() or c in '_-' for c in v)
           for v in (pool, share)):
        raise ValueError('Unsupported pool/share')
    if not isinstance(torrents, list) or not torrents or not isinstance(mounts, list):
        raise ValueError('Snapshot unavailable')
    if not isinstance(file_lists, dict) or not isinstance(candidates, list):
        raise ValueError('File inventory unavailable')
    protected, owners, known_hashes = set(), {}, set()
    for torrent in torrents:
        if not isinstance(torrent, dict):
            raise ValueError('Malformed torrent')
        progress, state, digest = (torrent.get(k) for k in ('progress', 'state', 'hash'))
        if (type(progress) not in (int, float) or not math.isfinite(progress)
                or not 0 <= progress <= 1 or not isinstance(state, str)
                or state not in BUSY_STATES | SEED_STATES
                or not isinstance(digest, str) or len(digest) not in (40, 64)
                or any(c not in '0123456789abcdefABCDEF' for c in digest)
                or digest.lower() in known_hashes):
            raise ValueError('Unverified torrent state')
        digest = digest.lower()
        known_hashes.add(digest)
        # Bind-mount mapping must be consistent for the save path and every file.
        save = canonical(torrent.get('save_path'))
        mapped_save = canonical(host_path(save, mounts))
        files = file_lists.get(digest)
        if not isinstance(files, list) or not files:
            raise ValueError('Missing torrent file list')
        busy = progress < 1 or state in BUSY_STATES
        content = canonical(host_path(torrent.get('content_path'), mounts))
        # If qB reports a different temporary root, stop rather than guessing.
        if not within(content, mapped_save):
            raise ValueError('Temporary download root needs explicit mapping')
        for item in files:
            if not isinstance(item, dict):
                raise ValueError('Malformed torrent file')
            name = item.get('name')
            if (not isinstance(name, str) or not name or name.startswith('/')
                    or any(c in name for c in ('\x00', '\n', '\r'))
                    or '..' in PurePosixPath(name).parts):
                raise ValueError('Unsafe torrent filename')
            full = canonical(host_path(posixpath.join(save, name), mounts))
            if not within(full, mapped_save):
                raise ValueError('Ambiguous nested bind mount')
            try:
                relative = pool_relative(full, pool, share)
            except ValueError:
                continue  # Verified other share; hardlinks still require review.
            owners.setdefault(relative, set()).add(digest)
            if busy:
                protected.update((relative, relative + '.!qB'))
    result = []
    seen = set()
    for item in candidates:
        if not isinstance(item, dict):
            raise ValueError('Invalid filesystem entry')
        relative = item.get('path')
        if (not isinstance(relative, str) or relative in ('', '.') or relative.startswith('/')
                or any(c in relative for c in ('\x00', '\n', '\r'))
                or '..' in PurePosixPath(relative).parts
                or posixpath.normpath(relative) != relative or relative in seen):
            raise ValueError('Unsafe or duplicate candidate')
        seen.add(relative)
        if relative in protected:
            decision, reason = 'skip', 'busy_torrent'
        elif item.get('symlink') is not False or item.get('regular') is not True:
            decision, reason = 'skip', 'unsupported_file_type'
        elif type(item.get('nlink')) is not int or item['nlink'] != 1:
            decision, reason = 'skip', 'hardlink_review_required'
        else:
            decision, reason = 'candidate', 'completed_or_non_torrent'
        result.append({'path': relative, 'decision': decision, 'reason': reason,
                       'torrent_count': len(owners.get(relative, ()))})
    return {'mode': 'read_only_plan', 'live_acceptance': False, 'entries': result,
            'candidate_count': sum(r['decision'] == 'candidate' for r in result),
            'skipped_count': sum(r['decision'] == 'skip' for r in result)}


def pressure_policy(free_bytes, reserve_bytes, *, pause_downloads=False):
    if any(type(v) is not int or v < 0 for v in (free_bytes, reserve_bytes)):
        raise ValueError('Capacity unavailable')
    if type(pause_downloads) is not bool:
        raise ValueError('Pause option must be explicit boolean')
    low = free_bytes < reserve_bytes
    return {'alert': low, 'pause_requested': low and pause_downloads,
            'automatic_action_performed': False}

