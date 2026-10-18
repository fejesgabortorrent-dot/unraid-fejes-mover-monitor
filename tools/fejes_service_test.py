import contextlib
import fcntl
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import fejes_service as service
import wire_integrity_cron as wire


class ServiceTest(unittest.TestCase):
    def test_capacity_estimate_and_missing_bytes(self):
        self.assertEqual(service.capacity([{'amount_left': 40}, {'amount_left': 30}], 100, 20)['pressure'], 'ok')
        self.assertEqual(service.capacity([{'amount_left': 90}], 100, 20)['pressure'], 'warning')
        for invalid in (None, True, -1, 2.5, '30'):
            self.assertEqual(service.capacity([{'amount_left': invalid}], 100, 20)['pressure'], 'unknown')

    def test_status_does_not_trust_unmounted_cache_or_leak_paths(self):
        torrent = {'state': 'downloading', 'progress': .2, 'content_path': '/data/PRIVATE', 'amount_left': 50}
        mounts = [{'Type': 'bind', 'Destination': '/data', 'Source': '/mnt/user/PRIVATE'}]
        with patch.object(service, 'read_snapshot', return_value=([torrent], mounts)), patch.object(service.os.path, 'ismount', return_value=False):
            report = service.status()
        self.assertEqual(report['torrent'], 'defer')
        self.assertEqual(report['cache'], 'unavailable')
        self.assertNotIn('PRIVATE', json.dumps(report))

    def test_active_cron_requires_exact_single_job(self):
        configured = '0 5 * * 0 ' + wire.REPLACEMENT + ' &> /dev/null\n'
        for active, expected in [(configured, 'wired'), (configured*2, 'not_verified'),
                                 (configured.replace('0 5', '0 6'), 'not_verified')]:
            def read(path, *args, **kwargs):
                return active if str(path) == '/etc/cron.d/root' else configured
            with patch.object(Path, 'read_text', read), patch.object(service, 'read_snapshot', side_effect=OSError()), patch.object(service.os.path, 'ismount', return_value=False):
                self.assertEqual(service.status()['integrity_active'], expected)

    def test_gate_never_executes_for_busy_unknown_or_unmounted_state(self):
        with tempfile.TemporaryDirectory() as directory:
            launcher = Path(directory) / 'script'
            marker = Path(directory) / 'timestamp'
            original = '#!/bin/bash\nprintf ran > ' + str(marker) + '\n'
            launcher.write_text(original)
            with patch.object(service, 'LAUNCHER', launcher), patch.object(service, 'LOCK', str(Path(directory)/'lock')):
                for torrent, cache in [('defer','available'), ('unavailable','available'), ('no_torrent_blocker','unavailable')]:
                    with patch.object(service, 'status', return_value={'torrent':torrent,'cache':cache}), patch.object(service.subprocess, 'run') as run, contextlib.redirect_stdout(io.StringIO()):
                        self.assertIn(service.run_mover('qbit'), (10,20))
                        run.assert_not_called()
                        self.assertFalse(marker.exists())
                        self.assertEqual(launcher.read_text(), original)

    def test_ready_gate_runs_original_script_with_existing_checks(self):
        with tempfile.TemporaryDirectory() as directory:
            launcher = Path(directory) / 'script'
            marker = Path(directory) / 'timestamp'
            # The existing guard can refuse even when torrent preflight passes.
            launcher.write_text('#!/bin/bash\nexit 7\nprintf ran > ' + str(marker) + '\n')
            with patch.object(service, 'LAUNCHER', launcher), patch.object(service, 'LOCK', str(Path(directory)/'lock')), patch.object(service, 'status', return_value={'torrent':'no_torrent_blocker','cache':'available'}), patch.object(service.Path, 'exists', return_value=False):
                self.assertEqual(service.run_mover('qbit'), 7)
            self.assertFalse(marker.exists())

    def test_concurrent_guard_cannot_launch(self):
        with tempfile.TemporaryDirectory() as directory:
            lock_path = str(Path(directory)/'lock')
            with open(lock_path, 'w') as held:
                fcntl.flock(held, fcntl.LOCK_EX | fcntl.LOCK_NB)
                with patch.object(service, 'LOCK', lock_path), patch.object(service, 'status') as status, contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(service.run_mover('qbit'), 10)
                    status.assert_not_called()

    def test_uninstall_restores_cron_offline_and_preserves_backup(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cron = root / 'integrity-check.cron'
            source = '# Schedule\n0 5 * * 0 '+wire.REPLACEMENT+' &> /dev/null\n'
            cron.write_text(source)
            with patch.object(wire, 'ROOT', root), patch.object(wire, 'LOCK', str(root/'lock')), patch.object(wire, 'reload_cron') as reload, patch.object(wire.subprocess, 'run') as run, contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(wire.main(remove=True), 0)
                run.assert_not_called()
                reload.assert_called_once()
                self.assertEqual(wire.main(remove=True), 0)
            self.assertEqual(cron.read_text(), source.replace(wire.REPLACEMENT, wire.ORIGINAL))
            backups = list(root.glob('*.txt'))
            self.assertEqual(len(backups), 1)
            self.assertEqual(backups[0].read_text(), source)

    def test_failed_uninstall_reload_rolls_back_integrated_cron(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cron = root/'integrity-check.cron'
            source = '0 5 * * 0 '+wire.REPLACEMENT+' &> /dev/null\n'
            cron.write_text(source)
            with patch.object(wire, 'ROOT', root), patch.object(wire, 'LOCK', str(root/'lock')), patch.object(wire, 'reload_cron', side_effect=[OSError(), None]):
                with self.assertRaises(OSError):
                    wire.main(remove=True)
            self.assertEqual(cron.read_text(), source)


if __name__ == '__main__':
    unittest.main()
