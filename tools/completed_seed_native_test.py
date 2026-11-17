"""Admission regressions for the explicit immediate completed-seed path."""
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from test_support import install
install()
import selective_mover as native
from selection_policy import REQUIRED_GUARDS


class CompletedSeedAdmission(unittest.TestCase):
    key = '/mnt/user/Filmek/new/movie.mkv'
    expected = {'signature': [1, 2, 10, 3, 4], 'first_seen': 999.0}
    info = SimpleNamespace(st_dev=1, st_ino=2, st_size=10, st_mtime_ns=3, st_ctime_ns=4)

    def candidate(self, change=None, guards=None, opened=None, expected=None):
        torrent = {'content_path': '/data/new', 'state': 'stoppedUP', 'progress': 1,
                   'upspeed': 0, 'dlspeed': 0, 'ratio': 0, 'completion_on': 999}
        torrent.update(change or {})
        with patch.object(native, 'ROOT', '/mnt/user/Filmek'), \
             patch.object(native, 'SOURCE', Path('/mnt/cache/Filmek')), \
             patch.object(native, 'valid_file', return_value=self.info), \
             patch.object(native.inventory_adapter, 'open_paths', return_value=opened or set()), \
             patch.object(native, 'torrent_snapshot', return_value=(
                 [torrent], [{'Type': 'bind', 'Source': native.ROOT, 'Destination': '/data'}])), \
             patch.object(native, 'guards', return_value=guards or {g: 'pass' for g in REQUIRED_GUARDS}), \
             patch.object(native.time, 'time', return_value=1000):
            return native.completed_seed_candidate(self.key, expected or self.expected, 30)[1]

    def test_fresh_complete_seed_does_not_wait_for_age_or_ratio(self):
        self.assertTrue(self.candidate())

    def test_each_real_guard_still_blocks(self):
        for guard in REQUIRED_GUARDS:
            with self.subTest(guard=guard):
                self.assertFalse(self.candidate(guards={g: 'wait' if g == guard else 'pass' for g in REQUIRED_GUARDS}))

    def test_running_incomplete_checking_or_nonzero_rates_block(self):
        for change in ({'state': 'uploading'}, {'progress': .99}, {'state': 'checkingUP'},
                       {'state': 'error'}, {'upspeed': 1}, {'dlspeed': 1}, {'upspeed': None}):
            with self.subTest(change=change):
                self.assertFalse(self.candidate(change))

    def test_missing_owner_open_file_changed_signature_and_future_inventory_block(self):
        self.assertFalse(self.candidate({'content_path': '/data/unrelated'}))
        self.assertFalse(self.candidate(opened={self.key}))
        self.assertFalse(self.candidate(expected=dict(self.expected, signature=[1, 2, 11, 3, 4])))
        self.assertFalse(self.candidate(expected=dict(self.expected, first_seen=1001)))

    def test_normal_executor_keeps_ordinary_age_policy(self):
        with patch.object(native, '_execute_file', return_value={'state': 'skipped'}) as executor:
            native.execute_file(self.key, self.expected, 7)
        self.assertIs(executor.call_args.args[-1], native.fresh_candidate)


if __name__ == '__main__':
    unittest.main()
