#!/usr/bin/env python3
"""Add an opt-in torrent gate to the reviewed legacy threshold script."""
import argparse
import datetime
import fcntl
import hashlib
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

from torrent_preflight import assess, read_snapshot
from wire_integrity_cron import atomic_write

LAUNCHER = Path('/boot/config/plugins/user.scripts/scripts/Filmek_Mover_Threshold/script')
BACKUPS = Path('/boot/config/plugins/fejes.mover.monitor/backups')
LOCK = '/var/run/fejes-mover-launch.lock'
SETTINGS_LOCK = '/var/run/fejes-mover-settings.lock'
GUARD = Path('/boot/config/plugins/fejes.mover.monitor/tools/torrent_preflight.py')
BASE_HASH = '111a0e8afd56149f3fc9ab153f1e6c5f726bf84e3e0f2dbf6becd62e871df9e3'
START = '[[ -d "$POOL" ]]'
STAMP = '''printf '%s\\n' "$MOST" > "$ALLAPOT"'''
LOCK_BLOCK = '''# BEGIN FEJES MOVER LOCK v1
exec 9>/var/run/fejes-mover-launch.lock
if ! flock -n 9; then
    log "Masik vedett Mover-inditas fut | Mover halasztva"
    exit 0
fi
python3 -c 'import os,sys; sys.exit(0 if os.path.ismount(sys.argv[1]) else 1)' "$POOL" || hiba "A cache pool nincs felcsatolva"
# END FEJES MOVER LOCK v1

'''
GATE_BLOCK = '''# BEGIN FEJES MOVER TORRENT GATE v1
if python3 /boot/config/plugins/fejes.mover.monitor/tools/torrent_preflight.py; then
    :
else
    log "Torrentellenorzes halasztast kert | Mover nem indul | Varakozasi idobelyeg valtozatlan"
    exit 0
fi
# END FEJES MOVER TORRENT GATE v1

'''

DISPATCH_BLOCK = '''# BEGIN FEJES SELECTIVE DISPATCH v1
# The age-filtered executor owns the same maintenance/launch locks.
exec python3 /boot/config/plugins/fejes.mover.monitor/tools/selective_mover.py run
# END FEJES SELECTIVE DISPATCH v1

'''


def rewrite_launcher(source, remove=False):
    selective = source.count(DISPATCH_BLOCK) == 1
    if selective:
        if remove:
            raise ValueError('Selective dispatch must be explicitly restored before removing legacy guards')
        source = source.replace(DISPATCH_BLOCK, '', 1)
    has_blocks = LOCK_BLOCK in source and GATE_BLOCK in source
    original = source.replace(LOCK_BLOCK, '', 1).replace(GATE_BLOCK, '', 1) if has_blocks else source
    normalized = re.sub(r'^(KUSZOB_GIB|UJRA_PROBALKOZAS_MP)=[0-9]+$', r'\1=VALUE', original, flags=re.M)
    if hashlib.sha256(normalized.encode()).hexdigest() != BASE_HASH:
        raise ValueError('Launcher differs from the reviewed format')
    expected = original.replace(START, LOCK_BLOCK + START, 1).replace(STAMP, GATE_BLOCK + STAMP, 1)
    if has_blocks and source != expected:
        raise ValueError('Gate placement differs from reviewed format')
    if selective:
        expected = expected.replace(LOCK_BLOCK, DISPATCH_BLOCK + LOCK_BLOCK, 1)
    return original if remove else expected


def check_environment():
    if not GUARD.is_file() or shutil.which('flock') is None or not os.path.ismount('/mnt/cache'):
        raise ValueError('Guard, lock utility or mounted cache unavailable')
    torrents, mounts = read_snapshot('binhex-qbittorrentvpn', 5)
    result = assess(torrents, mounts)
    values = [t.get('amount_left') for t in torrents]
    if not all(type(n) is int and n >= 0 for n in values):
        raise ValueError('Remaining download size unavailable')
    if shutil.disk_usage('/mnt/cache').free < sum(values) + 20 * 1024**3:
        raise ValueError('Insufficient conservative download headroom')
    # Also run the exact installed guard, not only this downloaded module.
    probe = subprocess.run(['python3', str(GUARD)], capture_output=True, text=True, timeout=20)
    if probe.returncode not in (0, 10):
        raise ValueError('Installed guard could not verify torrents')
    print('Blocking torrents:', result['blocking_torrents'])


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--apply', action='store_true')
    group.add_argument('--remove', action='store_true')
    args = parser.parse_args(argv)
    if args.remove and not LAUNCHER.exists():
        return 0
    # Same locks as the legacy settings editor and the installed guarded launch.
    with open(SETTINGS_LOCK, 'w') as settings, open(LOCK, 'w') as launch:
        for lock in (settings, launch):
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if LAUNCHER.is_symlink():
            raise ValueError('Launcher is a symlink')
        source = LAUNCHER.read_text()
        if args.remove and 'FEJES MOVER' not in source:
            return 0
        changed = rewrite_launcher(source, remove=args.remove)
        subprocess.run(['bash', '-n'], input=changed, text=True, check=True, capture_output=True, timeout=5)
        if not args.remove:
            check_environment()
        if not args.apply and not args.remove:
            print('Check only: reviewed launcher and capacity verified. No changes or Mover start.')
            return 0
        if source == changed:
            print('Launcher already has the requested integration. No Mover started.')
            return 0
        if Path('/var/run/mover.pid').exists():
            raise ValueError('Mover PID file is present')
        BACKUPS.mkdir(parents=True, exist_ok=True)
        backup = BACKUPS / ('mover-gate-before-' + datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f') + '.txt')
        shutil.copy2(LAUNCHER, backup)
        if backup.read_text() != source or LAUNCHER.read_text() != source:
            raise ValueError('Launcher changed during preparation')
        atomic_write(LAUNCHER, changed, LAUNCHER.stat().st_mode & 0o777)
        print('Mover gate removed.' if args.remove else 'Mover gate installed in the existing launcher.')
        print('Backup:', backup)
        print('No schedule changed. No Mover started.')
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (ValueError, OSError, subprocess.SubprocessError) as exc:
        print('Mover wiring did not complete:', type(exc).__name__)
        sys.exit(20)
