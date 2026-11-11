#!/usr/bin/env python3
"""Verify peer transfer after a genuine guarded move, only in the isolated VM.

Never moves files, prepares new data, or changes age evidence. Existing component
evidence remains separate. Run only after guarded_acceptance.py run succeeds.
"""
import hashlib
import json
from pathlib import Path
import time

import seed_acceptance as lab


def main():
    lab.BASE = Path('/mnt/disk1/fm-acceptance/guarded')
    lab.environment()
    for name in (lab.SEED, lab.PEER):
        lab.container(name)
        lab.authenticate(name)
    state = json.loads((lab.BASE / 'current.json').read_text())
    if state['status'] not in {'guarded_moved', 'rechecked_after_guarded_move'}:
        raise RuntimeError('Verified full guarded move required; no component fallback')
    result = state.get('result', {})
    if (result.get('state') != 'completed' or result.get('moved_files') != 1
            or result.get('moved_bytes') != state['bytes'] or result.get('requires_inspection')):
        raise RuntimeError('Completed guarded runner evidence required')
    run = state['run']
    if not run.startswith('seedproof-') or not run[10:].isdigit():
        raise RuntimeError('Unexpected test directory')
    source = lab.SOURCE / run / 'seedproof.bin'
    target = Path('/mnt/disk1/fejesmover') / run / 'seedproof.bin'
    if source.exists() or target.is_symlink() or not target.is_file():
        raise RuntimeError('Source absence and regular array destination required')
    if hashlib.sha256(target.read_bytes()).hexdigest() != state['sha256']:
        raise RuntimeError('Array destination differs from baseline')
    row = lab.torrent(lab.SEED, state['hash'])
    logical = '/data/' + run + '/seedproof.bin'
    if row['content_path'] != logical:
        raise RuntimeError('Logical torrent path changed')
    lab.api(lab.SEED, 'torrents/recheck', {'hashes': state['hash']})
    time.sleep(2)
    row = lab.wait_complete(lab.SEED, state['hash'])
    if row['content_path'] != logical:
        raise RuntimeError('Logical torrent path changed during recheck')
    # Persist an explicit guarded checkpoint so an interrupted transfer can resume.
    state.update(status='rechecked_after_guarded_move', recheck_progress=row['progress'],
                 recheck_state=row['state'], logical_path_preserved=True)
    lab.save(state)
    lab.transfer(state, expected_status='rechecked_after_guarded_move',
                 limits='Full installed guarded runner plus post-move recheck and isolated peer transfer. Public tracker credit, production VPN, power-loss and broad compatibility remain unverified.')


if __name__ == '__main__':
    main()
