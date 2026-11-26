"""Small, aggregate-only history for the local Mover statistics panel."""
import fcntl
import json
import os
from pathlib import Path
import tempfile
import time

HISTORY = Path('/boot/config/plugins/fejes.mover.monitor/run-history.json')
MAX_ROWS = 4000
MAX_BYTES = 2_000_000


def _load(path):
    if path.is_symlink():
        raise ValueError('History path must not be a symlink')
    try:
        if path.stat().st_size > MAX_BYTES:
            raise ValueError('History is too large')
        rows = json.loads(path.read_text())
    except FileNotFoundError:
        return []
    if not isinstance(rows, list):
        raise ValueError('Invalid history')
    clean = []
    for row in rows:
        if not isinstance(row, dict) or type(row.get('finished')) not in (int, float):
            raise ValueError('Invalid history row')
        clean.append(row)
    return clean[-MAX_ROWS:]


def _atomic(path, value):
    fd, temporary = tempfile.mkstemp(prefix='.run-history-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as output:
            json.dump(value, output, separators=(',', ':'), allow_nan=False)
            output.flush()
            os.fsync(output.fileno())
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def record_run(result, origin='manual', path=HISTORY):
    """Append one terminal aggregate. File names and torrent identifiers are excluded."""
    if not isinstance(result, dict):
        raise ValueError('Result must be an object')
    state = result.get('state')
    if not isinstance(state, str) or len(state) > 80:
        raise ValueError('Invalid state')
    finished = result.get('finished', time.time())
    if type(finished) not in (int, float) or not (0 < finished < 10**11):
        raise ValueError('Invalid finish time')
    started = result.get('started')
    row = {
        'finished': finished,
        'origin': origin if origin in {'manual', 'scheduled', 'diagnostic'} else 'manual',
        'state': state,
        'moved_files': max(0, int(result.get('moved_files', 0) or 0)),
        'moved_bytes': max(0, int(result.get('moved_bytes', 0) or 0)),
    }
    if type(started) in (int, float) and 0 < started <= finished:
        row['started'] = started
    reason = result.get('reason') or result.get('error_code')
    if isinstance(reason, str) and len(reason) <= 120:
        row['reason'] = reason
    path = Path(path)
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    lock_path = Path(str(path) + '.lock')
    if lock_path.is_symlink():
        raise ValueError('History lock must not be a symlink')
    with open(lock_path, 'a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        rows = _load(path)
        rows.append(row)
        _atomic(path, rows[-MAX_ROWS:])
    return row
