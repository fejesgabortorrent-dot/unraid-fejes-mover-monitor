"""Private failure evidence in disposable files; never starts movement."""
import os
from pathlib import Path
import stat
import tempfile
import unittest
from unittest.mock import patch
import selective_mover as mover

class FailureDiagnostics(unittest.TestCase):
    def test_private_exception_and_active_file_are_persisted(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(mover,'LAST',Path(folder)/'last.json'):
            report={'started':123,'stage':'file_verification_or_move','requires_inspection':True}
            try:
                raise RuntimeError('fixture backend failure')
            except RuntimeError:
                mover.record_failure(report,'/private/fixture\nname')
            log=Path(folder)/'selective-error.log'
            self.assertIn('RuntimeError: fixture backend failure',log.read_text())
            self.assertIn('Active file="/private/fixture\\nname"',log.read_text())
            self.assertEqual(stat.S_IMODE(log.stat().st_mode),0o600)
            self.assertTrue(report['requires_inspection'])

    def test_symlink_is_not_followed_and_latch_is_preserved(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(mover,'LAST',Path(folder)/'last.json'):
            target=Path(folder)/'retained';target.write_text('unchanged')
            (Path(folder)/'selective-error.log').symlink_to(target)
            report={'requires_inspection':True}
            try:
                raise ValueError('fixture error')
            except ValueError:
                mover.record_failure(report)
            self.assertEqual(target.read_text(),'unchanged')
            self.assertTrue(report['requires_inspection'])

    def test_unavailable_log_never_clears_failure(self):
        with patch.object(mover,'LAST',Path('/nonexistent-fixture-path/absent/last.json')):
            report={'state':'error','requires_inspection':True}
            try:
                raise OSError('fixture error')
            except OSError:
                mover.record_failure(report)
            self.assertEqual(report,{'state':'error','requires_inspection':True})
