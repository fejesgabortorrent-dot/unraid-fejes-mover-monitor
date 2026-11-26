import json
from pathlib import Path
import tempfile
import unittest
from statistics_history import record_run


class HistoryTests(unittest.TestCase):
    def test_records_aggregate_without_private_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'history.json'
            result={'state':'completed','started':100.0,'finished':103.0,
                    'moved_files':2,'moved_bytes':268435456,
                    'verified_files':[{'source':'/private/name.mkv'}]}
            record_run(result,'scheduled',path)
            rows=json.loads(path.read_text())
            self.assertEqual(rows,[{'finished':103.0,'origin':'scheduled','state':'completed',
                'moved_files':2,'moved_bytes':268435456,'started':100.0}])
            self.assertNotIn('private',path.read_text())

    def test_invalid_existing_history_is_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'history.json'
            path.write_text('{bad')
            with self.assertRaises(json.JSONDecodeError):
                record_run({'state':'deferred','finished':100},path=path)
            self.assertEqual(path.read_text(),'{bad')


if __name__=='__main__': unittest.main()
