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

class FailureCategories(unittest.TestCase):
    def test_torrent_snapshot_failure_has_safe_specific_code(self):
        import subprocess
        command=['docker','exec','binhex-qbittorrentvpn','curl','--fail','http://127.0.0.1:8080/api/v2/torrents/info']
        self.assertEqual(mover.failure_code(subprocess.CalledProcessError(1,command)),'torrent_snapshot_unavailable')

    def test_other_commands_and_io_failures_are_not_misclassified(self):
        import subprocess
        for error in (OSError('lock unavailable'),subprocess.CalledProcessError(1,['docker','exec','other','curl','http://127.0.0.1:8080/api/v2/torrents/info']),subprocess.CalledProcessError(1,'private command')):
            self.assertEqual(mover.failure_code(error),'required_state_unverified')

class ProcessEvidence(unittest.TestCase):
    def test_private_process_evidence_is_bounded_and_line_safe(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(mover,'LAST',Path(folder)/'last.json'):
            try:
                raise mover.NativeMoveError(7,'prefix-not-retained'+('x'*5000)+'\nprivate failure')
            except mover.NativeMoveError:
                mover.record_failure({'started':456,'requires_inspection':True})
            text=(Path(folder)/'selective-error.log').read_text()
            self.assertIn('Process exit=7',text)
            self.assertIn('\\nprivate failure',text)
            import json
            detail=json.loads(next(line.split('=',1)[1] for line in text.splitlines() if line.startswith('Process stderr=')))
            self.assertEqual(len(detail),4096)
            self.assertNotIn('prefix-not-retained',detail)
            self.assertEqual(stat.S_IMODE((Path(folder)/'selective-error.log').stat().st_mode),0o600)
