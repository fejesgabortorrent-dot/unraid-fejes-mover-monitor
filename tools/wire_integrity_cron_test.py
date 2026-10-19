import pathlib
import tempfile
import unittest
from unittest.mock import patch

import wire_integrity_cron as wire


class WiringTest(unittest.TestCase):
    def test_reload_uses_explicit_bash_for_unraid_script(self):
        with patch.object(wire.subprocess, "run") as run:
            wire.reload_cron()
        run.assert_called_once_with(["bash", "/usr/local/sbin/update_cron"], check=True)

    def test_preserves_schedule_and_does_not_duplicate_jobs(self):
        source = "# Generated file integrity check schedule:\n0 5 * * 0 " + wire.ORIGINAL + " &> /dev/null\n\n"
        updated = wire.rewrite_cron(source)
        self.assertEqual(updated, source.replace(wire.ORIGINAL, wire.REPLACEMENT))
        self.assertEqual(wire.rewrite_cron(updated), updated)

    def test_rejects_absent_multiple_or_unreviewed_commands(self):
        for source in ("", "# no job\n", "0 5 * * 0 bash /wrong/path\n",
                       "0 5 * * 0 " + wire.ORIGINAL + " && touch /tmp/unexpected\n",
                       ("0 5 * * 0 " + wire.ORIGINAL + " &> /dev/null\n") * 2):
            with self.assertRaises(ValueError):
                wire.rewrite_cron(source)

    def test_atomic_replace_preserves_requested_mode_and_cleans_temp(self):
        with tempfile.TemporaryDirectory() as root:
            path = pathlib.Path(root) / "job.cron"
            path.write_text("old")
            wire.atomic_write(path, "new", 0o600)
            self.assertEqual(path.read_text(), "new")
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertEqual(list(path.parent.iterdir()), [path])


if __name__ == "__main__":
    unittest.main()
