import importlib.util
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'testlab'))
import active_seed_acceptance as harness


class RecheckWait(unittest.TestCase):
    def test_old_complete_row_does_not_hide_incomplete_file_recheck(self):
        state = {'hash': 'a'*40, 'run': 'unit', 'files': [{'name': 'a.mkv', 'bytes': 10}]}
        good = [{'name': 'unit/a.mkv', 'size': 10, 'progress': 1, 'priority': 1}]
        bad = [dict(good[0], progress=.5)]
        clock = [0.0]
        def sleep(seconds): clock[0] += seconds
        rows = iter([good, bad, bad, good, good, good, good, good, good])
        with patch.object(harness.lab, 'torrent', return_value={'progress': 1, 'state': 'stalledUP'}), \
             patch.object(harness, 'api_files', side_effect=lambda *a: next(rows)), \
             patch.object(harness.time, 'monotonic', side_effect=lambda: clock[0]), \
             patch.object(harness.time, 'sleep', side_effect=sleep):
            harness.wait_rechecked(state)
        self.assertGreaterEqual(clock[0], 3.5)

    def test_missing_file_membership_never_passes(self):
        state = {'hash': 'a'*40, 'run': 'unit', 'files': [{'name': 'a.mkv', 'bytes': 10}]}
        clock = [0.0]
        def sleep(seconds): clock[0] += seconds
        with patch.object(harness.lab, 'torrent', return_value={'progress': 1, 'state': 'uploading'}), \
             patch.object(harness, 'api_files', return_value=[]), \
             patch.object(harness.time, 'monotonic', side_effect=lambda: clock[0]), \
             patch.object(harness.time, 'sleep', side_effect=sleep):
            with self.assertRaises(RuntimeError): harness.wait_rechecked(state, timeout=2)


if __name__ == '__main__':
    unittest.main()
