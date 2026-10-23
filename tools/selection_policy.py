#!/usr/bin/env python3
"""Pure selection policy; never authorizes or executes a live move.

Inputs must be collected by a trusted host adapter. Files and torrent content
paths must use one canonical host namespace (not mixed /mnt/user and disk paths).
"""
import math
from torrent_preflight import absolute_path, host_path, assess

AGE_OPTIONS = (7, 14, 30)
DEFAULT_AGE_DAYS = 7
QUIET_STATES = {'stalledUP', 'queuedUP', 'stoppedUP', 'pausedUP'}
REQUIRED_GUARDS = ('backup', 'parity', 'integrity', 'mount', 'mover',
                   'cooldown', 'capacity', 'open_files', 'namespace')


def age_days(value):
    if type(value) is not int or value not in AGE_OPTIONS:
        raise ValueError('Age must be 7, 14 or 30 days')
    return value


def timestamp(value):
    if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
        raise ValueError('Unverifiable timestamp')
    return value


def within(path, parent):
    return path == parent or path.startswith(parent.rstrip('/') + '/')


def protected_content(torrents, mounts, now, days):
    # Reuse fail-closed validation, but never turn a global DEFER into a start.
    assess(torrents, mounts)
    protected = set()
    for torrent in torrents:
        path = host_path(torrent.get('content_path'), mounts)
        if torrent['progress'] < 1 or torrent['state'] not in QUIET_STATES:
            protected.add(path)
            continue
        completed = timestamp(torrent.get('completion_on'))
        if completed == 0 or completed > now:
            raise ValueError('Completion time unavailable')
        # Do not equate zero bandwidth with idle: explicit quiet state AND
        # verified zero rates are needed. Completed active seeds are excluded.
        rates = [torrent.get('upspeed'), torrent.get('dlspeed')]
        if any(type(rate) is not int or rate < 0 for rate in rates):
            raise ValueError('Transfer activity unavailable')
        if any(rates) or now - completed < days * 86400:
            protected.add(path)
    return protected


def plan(files, torrents, mounts, guards, *, days=DEFAULT_AGE_DAYS, now,
         observed_at, root):
    """Return private candidate paths, not an execution manifest or permission.

    Age uses the most recent of mtime, first_seen and known torrent completion.
    first_seen is required: copied old timestamps must not age new cache arrivals.
    Unknown global data produces no candidates. Local uncertainty skips that file.
    A second fresh observation and execution-time coordination remain mandatory.
    """
    result = {'read_only': True, 'execution_allowed': False,
              'age_days': days, 'candidates': [], 'skipped': [], 'blockers': []}
    try:
        days = age_days(days)
        now, observed_at = timestamp(now), timestamp(observed_at)
        if not 0 <= now - observed_at <= 30:
            raise ValueError('Snapshot stale or from the future')
        root = absolute_path(root)
        if root == '/':
            raise ValueError('Unbounded source root')
        if not isinstance(guards, dict):
            raise ValueError('Missing guards')
        result['blockers'] = [key for key in REQUIRED_GUARDS
                              if guards.get(key) != 'pass']
        if result['blockers']:
            result['decision'] = 'blocked'
            return result
        protected = protected_content(torrents, mounts, now, days)
        if not isinstance(files, list):
            raise ValueError('Invalid inventory')
        seen = set()
        for item in files:
            if not isinstance(item, dict):
                raise ValueError('Invalid inventory entry')
            path = absolute_path(item.get('path'))
            if path in seen or path == root or not within(path, root):
                raise ValueError('Duplicate or out-of-root file')
            seen.add(path)
            reason = None
            if any(within(path, p) or within(p, path) for p in protected):
                reason = 'protected_content'
            elif (item.get('regular') is not True or item.get('symlink') is not False
                  or type(item.get('nlink')) is not int or item['nlink'] != 1):
                reason = 'unsupported_file'
            elif item.get('open') is not False or item.get('stable') is not True:
                reason = 'busy_or_unverified'
            else:
                try:
                    modified = timestamp(item.get('mtime'))
                    arrived = timestamp(item.get('first_seen'))
                    if max(modified, arrived) > now:
                        reason = 'unknown_age'
                    elif now - max(modified, arrived) < days * 86400:
                        reason = 'too_young'
                except ValueError:
                    reason = 'unknown_age'
            if reason:
                result['skipped'].append({'path': path, 'reason': reason})
            else:
                result['candidates'].append(path)
        result['decision'] = 'preview_only'
    except (ValueError, TypeError, KeyError, AttributeError):
        # Avoid publishing partial candidates after an invalid snapshot.
        result.update(decision='unknown', candidates=[], skipped=[],
                      blockers=['unverifiable_snapshot'])
    return result


def main(argv=None):
    import argparse
    import json
    import sys
    parser = argparse.ArgumentParser(description='Read-only selective Mover preview; no execution')
    parser.add_argument('snapshot', help='Trusted, canonical host inventory JSON')
    parser.add_argument('--days', type=int, choices=AGE_OPTIONS, default=DEFAULT_AGE_DAYS)
    parser.add_argument('--include-paths', action='store_true', help='Private local diagnostic output')
    args = parser.parse_args(argv)
    try:
        with open(args.snapshot, encoding='utf-8') as stream:
            snapshot = json.load(stream)
        output = plan(**snapshot, days=args.days)
    except (OSError, ValueError, TypeError):
        print(json.dumps({'decision': 'unknown', 'execution_allowed': False}))
        return 20
    if not args.include_paths:
        from collections import Counter
        output['candidate_count'] = len(output.pop('candidates'))
        output['skipped_counts'] = dict(Counter(item['reason'] for item in output.pop('skipped')))
    print(json.dumps(output, ensure_ascii=False, allow_nan=False))
    return 0 if output['decision'] == 'preview_only' else 20


if __name__ == '__main__':
    import sys
    sys.exit(main())
