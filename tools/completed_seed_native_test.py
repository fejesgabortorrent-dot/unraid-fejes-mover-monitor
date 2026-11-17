"""Admission regressions for the explicit immediate completed-seed path."""
from pathlib import Path
from types import SimpleNamespace
import unittest
import os
import tempfile
from unittest.mock import patch

from test_support import install
install()
import selective_mover as native
from selection_policy import REQUIRED_GUARDS


class CompletedSeedAdmission(unittest.TestCase):
    key = '/mnt/user/Filmek/new/movie.mkv'
    expected = {'signature': [1, 2, 10, 3, 4], 'first_seen': 999.0}
    info = SimpleNamespace(st_dev=1, st_ino=2, st_size=10, st_mtime_ns=3, st_ctime_ns=4)

    def test_transient_integrity_activity_retries_only_before_native_intent(self):
        with patch.object(native, '_execute_file', side_effect=[native.IntegrityBusy(), {'state': 'moved'}]) as execute, \
             patch.object(native.time, 'sleep') as sleep:
            self.assertEqual(native.execute_completed_seed_file(self.key, self.expected, 1, lambda h: None),
                             {'state': 'moved'})
            self.assertEqual(execute.call_count, 2)
            sleep.assert_called_once_with(2)

    def test_integrity_wait_is_bounded_and_any_native_intent_blocks_retry(self):
        with patch.object(native, '_execute_file', side_effect=native.IntegrityBusy()), \
             patch.object(native.time, 'monotonic', side_effect=[0, 121]), \
             patch.object(native.time, 'sleep') as sleep:
            with self.assertRaises(native.IntegrityBusy):
                native.execute_completed_seed_file(self.key, self.expected, 1, lambda h: None)
            sleep.assert_not_called()
        def after_intent(key, expected, days, callback, candidate):
            callback('a' * 64)
            raise native.IntegrityBusy()
        with patch.object(native, '_execute_file', side_effect=after_intent) as execute, \
             patch.object(native.time, 'sleep') as sleep:
            with self.assertRaises(native.IntegrityBusy):
                native.execute_completed_seed_file(self.key, self.expected, 1, lambda h: None)
            execute.assert_called_once()
            sleep.assert_not_called()

    def candidate(self, change=None, guards=None, opened=None, expected=None, rejection=None):
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
            return native.completed_seed_candidate(self.key, expected or self.expected, 30,
                                                   rejection=rejection)[1]

    def test_diagnostic_reason_preserves_the_guard_without_admitting_the_file(self):
        for kwargs, reason in (({'opened': {self.key}}, 'source_open'),
                ({'change': {'state': 'uploading'}}, 'owner_not_quiescent_complete_seed'),
                ({'guards': {g: 'wait' if g == 'backup' else 'pass' for g in REQUIRED_GUARDS}}, 'guard_backup')):
            rejected = []
            self.assertFalse(self.candidate(**kwargs, rejection=rejected))
            self.assertEqual(rejected, [reason])

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

    def test_historical_or_stale_pid_latch_cannot_be_ignored(self):
        with tempfile.TemporaryDirectory() as directory:
            pid = Path(directory) / 'mover.pid'
            for text, recorded in ((str(os.getpid()), os.getpid()+1),
                                   (str(os.getpid()+1), os.getpid())):
                pid.write_text(text)
                with patch.object(native, 'PID', pid), patch.object(native, 'read_json',
                     return_value={'requires_inspection': True, 'coordination_pid': recorded}):
                    with self.assertRaises(native.InspectionRequired): native.guards(owned=True)

    def test_own_ledger_does_not_bypass_other_native_guards(self):
        with tempfile.TemporaryDirectory() as directory:
            pid = Path(directory) / 'mover.pid'; pid.write_text(str(os.getpid()))
            with patch.object(native, 'PID', pid), patch.object(native, 'read_json',
                 return_value={'requires_inspection': True, 'coordination_pid': os.getpid()}):
                with self.assertRaisesRegex(ValueError, 'Advanced cache mode required'):
                    native.guards(owned=True)


if __name__ == '__main__':
    unittest.main()
