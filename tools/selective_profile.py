#!/usr/bin/env python3
"""Validated profile for the opt-in selective mover.

The owner-tested profile remains the safe default, but paths and the torrent
container are no longer embedded in the movement engine.  Invalid or partial
profiles fail closed and never enable a new scope implicitly.
"""
from dataclasses import dataclass
import json
from pathlib import Path
import re

BASE = Path('/boot/config/plugins/fejes.mover.monitor')
PROFILE_PATH = BASE / 'selective-profile.json'
_NAME = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$')


def _name(value, field):
    if not isinstance(value, str) or not _NAME.fullmatch(value):
        raise ValueError(f'Invalid profile {field}')
    return value


def _script(value):
    value = _name(value, 'launcher_script')
    if '/' in value or '\\' in value or value in {'.', '..'}:
        raise ValueError('Invalid profile launcher_script')
    return value


@dataclass(frozen=True)
class SelectiveProfile:
    pool: str
    share: str
    torrent_container: str
    launcher_script: str

    @property
    def source(self):
        return Path('/mnt') / self.pool / self.share

    @property
    def canonical(self):
        return '/mnt/user/' + self.share

    @property
    def share_config(self):
        return Path('/boot/config/shares') / (self.share + '.cfg')

    @property
    def launcher(self):
        return Path('/boot/config/plugins/user.scripts/scripts') / self.launcher_script / 'script'


DEFAULT = SelectiveProfile('cache', 'Filmek', 'binhex-qbittorrentvpn', 'Filmek_Mover_Threshold')


def load_profile(path=PROFILE_PATH):
    """Load an explicit profile, preserving the owner profile when absent.

    A profile is configuration only; callers still need Advanced mode and all
    existing safety guards before movement can start.
    """
    path = Path(path)
    if path.is_symlink():
        raise ValueError('Symlink profile configuration')
    if not path.exists():
        return DEFAULT
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError('Unreadable profile configuration') from exc
    if not isinstance(data, dict) or data.get('version') != 1:
        raise ValueError('Unknown profile configuration')
    values = {
        'pool': _name(data.get('pool'), 'pool'),
        'share': _name(data.get('share'), 'share'),
        'torrent_container': _name(data.get('torrent_container'), 'torrent_container'),
        'launcher_script': _script(data.get('launcher_script')),
    }
    return SelectiveProfile(**values)
