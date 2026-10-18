import contextlib
import io
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import wire_mover_gate as wire

FIXTURE = Path(__file__).resolve().parents[1] / 'tests/fixtures/threshold-reviewed.sh'


class MoverWiringTest(unittest.TestCase):
    def test_exact_reviewed_source_roundtrip_and_preserved_settings(self):
        source = FIXTURE.read_text().replace('KUSZOB_GIB=300', 'KUSZOB_GIB=250')
        changed = wire.rewrite_launcher(source)
        self.assertEqual(wire.rewrite_launcher(changed), changed)
        self.assertEqual(wire.rewrite_launcher(changed, remove=True), source)
        self.assertIn('KUSZOB_GIB=250', changed)
        self.assertLess(changed.index(wire.GATE_BLOCK), changed.index(wire.STAMP))
        self.assertLess(changed.index('if [[ -r "$ALLAPOT" ]]'), changed.index(wire.GATE_BLOCK))
        subprocess.run(['bash', '-n'], input=changed, text=True, check=True)

    def test_unreviewed_source_or_moved_gate_is_rejected(self):
        source = FIXTURE.read_text()
        for invalid in (source.replace('mover start', 'mover stop'), source+'\n',
                        wire.rewrite_launcher(source).replace(wire.GATE_BLOCK, '').replace(wire.START, wire.GATE_BLOCK+wire.START),
                        source.replace('KUSZOB_GIB=300', 'KUSZOB_GIB=$(touch /tmp/wrong)')):
            with self.assertRaises(ValueError):
                wire.rewrite_launcher(invalid)

    def run_fixture(self, gate_code, free_kib=100*1024*1024, mounted=True, previous=None):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'bin').mkdir()
            (root/'cache').mkdir()
            (root/'media').mkdir()
            source = wire.rewrite_launcher(FIXTURE.read_text())
            replacements = {
                '/mnt/cache':str(root/'cache'), '/mnt/user/Filmek':str(root/'media'),
                '/var/run/filmek_mover_last_attempt':str(root/'attempt'),
                '/var/run/fejes-mover-launch.lock':str(root/'lock'),
                '/var/run/mover.pid':str(root/'mover.pid'),
                '/tmp/appdata.backup/running':str(root/'backup.pid'),
                '/proc/mdstat':str(root/'mdstat'),
                '/usr/local/sbin/mover':str(root/'bin/mover'),
            }
            for old, new in replacements.items():
                source = source.replace(old, new)
            (root/'mdstat').write_text('mdResync=0\n')
            if previous is not None:
                (root/'attempt').write_text(previous)
            scripts = {
                'python3': '#!/bin/bash\nif [[ "$1" == "-c" ]]; then exit '+('0' if mounted else '1')+'; fi\necho called >> "'+str(root/'guard-called')+'"\nexit '+str(gate_code)+'\n',
                'df': '#!/bin/bash\nprintf "Filesystem 1024-blocks Used Available Capacity Mounted\\nfixture 1000000000 0 '+str(free_kib)+' 1%% fixture\\n"\n',
                'mover': '#!/bin/bash\necho "$@" > "'+str(root/'mover-called')+'"\n',
            }
            for name, text in scripts.items():
                (root/'bin'/name).write_text(text)
                (root/'bin'/name).chmod(0o700)
            env = dict(os.environ, PATH=str(root/'bin')+':'+os.environ['PATH'])
            result = subprocess.run(['bash'], input=source, text=True, capture_output=True, env=env)
            return result, {name:(root/name).read_text() for name in ('attempt','mover-called','guard-called') if (root/name).exists()}

    def test_busy_and_unavailable_do_not_write_attempt_or_start_mover(self):
        for code in (10, 20, 127):
            result, files = self.run_fixture(code)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('guard-called', files)
            self.assertNotIn('attempt', files)
            self.assertNotIn('mover-called', files)

    def test_ready_records_attempt_and_starts_existing_mover(self):
        result, files = self.run_fixture(0)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(files['attempt'].strip().isdigit())
        self.assertEqual(files['mover-called'], 'start\n')

    def test_above_threshold_skips_api_and_resets_attempt(self):
        result, files = self.run_fixture(10, free_kib=633*1024*1024, previous='123\n')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(files, {})

    def test_unmounted_cache_never_reaches_api_or_mover(self):
        result, files = self.run_fixture(0, mounted=False)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(files, {})

    def test_existing_cooldown_still_precedes_api(self):
        import time
        previous = str(int(time.time()))+'\n'
        result, files = self.run_fixture(0, previous=previous)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(files, {'attempt':previous})

    def test_check_only_then_apply_and_offline_remove(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            launcher = root/'script'
            original = FIXTURE.read_text()
            launcher.write_text(original)
            with patch.object(wire,'LAUNCHER',launcher), patch.object(wire,'BACKUPS',root/'backups'), patch.object(wire,'LOCK',str(root/'lock')), patch.object(wire,'SETTINGS_LOCK',str(root/'settings-lock')), patch.object(wire,'check_environment') as check, contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(wire.main([]), 0)
                self.assertEqual(launcher.read_text(), original)
                self.assertFalse((root/'backups').exists())
                self.assertEqual(wire.main(['--apply']), 0)
                self.assertEqual(launcher.read_text(), wire.rewrite_launcher(original))
                check.reset_mock()
                self.assertEqual(wire.main(['--remove']), 0)
                check.assert_not_called()
                self.assertEqual(launcher.read_text(), original)
                self.assertEqual(len(list((root/'backups').glob('*.txt'))), 2)


if __name__ == '__main__':
    unittest.main()
