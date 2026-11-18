from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from test_support import install
install()
import completed_seed_pilot as pilot


class PersistentRunJournal(unittest.TestCase):
    def test_private_log_is_durable_and_summary_is_bounded(self):
        import json
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary); run=root/'run'; run.mkdir()
            with patch.object(pilot.n,'BASE',root):
                for step in range(45): pilot.event(run,'file_verified',step=step,files=45)
            rows=[json.loads(line) for line in (run/'events.jsonl').read_text().splitlines()]
            summary=json.loads((root/'completed-seed-events.json').read_text())
            self.assertEqual(len(rows),45)
            self.assertEqual(len(summary['events']),40)
            self.assertEqual(summary['events'][-1]['step'],44)
            self.assertEqual((run/'events.jsonl').stat().st_mode & 0o077,0)

    def test_credentials_and_arbitrary_fields_cannot_enter_event_schema(self):
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaises(ValueError):
                pilot.event(Path(temporary),'failure',password='secret')
            self.assertFalse((Path(temporary)/'events.jsonl').exists())


class RetainedArrayMembers(unittest.TestCase):
    def test_changed_service_settings_block_before_collecting_or_stopping(self):
        evidence=pilot.Evidence.__new__(pilot.Evidence)
        evidence.unit={'service_settings':{'completed_seed_mode':True,'cache_start_percent':75}}
        with patch.object(pilot.n,'read_json',return_value={'completed_seed_mode':False}), \
             patch.object(pilot,'collect') as collect:
            with self.assertRaisesRegex(ValueError,'settings changed'):
                evidence.snapshot()
        collect.assert_not_called()

    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        root = Path(directory.name)
        self.source = root / 'cache' / 'Filmek'
        self.source.mkdir(parents=True)
        self.target = root / 'disk1' / 'Filmek' / 'unit' / 'movie.mkv'
        self.target.parent.mkdir(parents=True)
        self.target.write_bytes(b'completed')
        self.key = '/mnt/user/Filmek/unit/movie.mkv'
        for name, value in [('ROOT', '/mnt/user/Filmek'), ('SOURCE', self.source),
                            ('destinations', lambda p: [self.target])]:
            patched = patch.object(pilot.n, name, value)
            patched.start()
            self.addCleanup(patched.stop)
        logical = patch.object(pilot, 'validate_retained_logical')
        logical.start()
        self.addCleanup(logical.stop)

    def test_complete_existing_array_member_is_bound_without_movement(self):
        with patch.object(pilot.n, 'sha256') as digest:
            result = pilot.retained_members({self.key: 9}, [])
        self.assertEqual(result[self.key]['destination'], str(self.target))
        digest.assert_not_called()
        self.assertEqual(self.target.read_bytes(), b'completed')

    def test_cache_duplicate_size_change_or_missing_array_is_rejected(self):
        with self.assertRaises(ValueError):
            pilot.retained_members({self.key: 10}, [])
        with patch.object(pilot.n, 'destinations', return_value=[]):
            with self.assertRaises(ValueError):
                pilot.retained_members({self.key: 9}, [])
        source = self.source / 'unit' / 'movie.mkv'
        source.parent.mkdir()
        source.write_bytes(b'completed')
        with self.assertRaises(ValueError):
            pilot.retained_members({self.key: 9}, [])

    def test_unselected_member_cannot_escape_profile(self):
        with self.assertRaises(ValueError):
            pilot.retained_members({'/mnt/user/Other/movie.mkv': 9}, [])

    def test_unavailable_logical_member_is_rejected(self):
        with patch.object(pilot, 'validate_retained_logical', side_effect=ValueError('unavailable')):
            with self.assertRaises(ValueError):
                pilot.retained_members({self.key: 9}, [])
