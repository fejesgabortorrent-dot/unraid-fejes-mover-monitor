import contextlib
import io
import pathlib
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import integrity_preflight as guard

CONFIG = 'folders=""\nexclude=""\nfiles=""\n'
SCRIPT = '''#!/bin/bash
# This is an auto-generated file, do not change manually!
#
[[ $(grep -Po '^mdResync=\\K\\S+' /proc/mdstat) -ne 0 ]] && exit 0
[[ $((10#$(date +%W)%5)) -eq 0 ]] && nice -n19 ionice -c2 -n7 /usr/local/emhttp/plugins/dynamix.file.integrity/scripts/bunker -Vqj  -n -L /mnt/disk1 >/dev/null &
exit 0
'''


class IntegrityTest(unittest.TestCase):
    def test_only_inserts_exclusions_preserving_existing_guards(self):
        result, count = guard.prepare_script(SCRIPT, CONFIG, ["/mnt/user/Media/Series.Name"], lambda p: True)
        self.assertEqual(count, 1)
        self.assertEqual(result.replace("-F 'Series\\.Name' ", ""), SCRIPT)
        subprocess.run(["bash", "-n"], input=result, text=True, check=True)

    def test_static_and_live_folders_are_merged_and_deduplicated(self):
        config = 'folders="Series.Name,Other"\nexclude="Downloads"\nfiles=""\n'
        result, count = guard.prepare_script(SCRIPT, config,
            ["/mnt/user/Media/Series.Name", "/mnt/disk3/Media/Series.Name"], lambda p: True)
        self.assertEqual(count, 2)
        self.assertIn("-F 'Other,Series\\.Name'", result)
        self.assertIn("-E Downloads", result)

    def test_empty_dynamic_exclusions_preserve_script(self):
        self.assertEqual(guard.prepare_script(SCRIPT, CONFIG, [], lambda p: False), (SCRIPT, 0))

    def test_unsafe_masks_and_missing_paths_fail_closed(self):
        for path in ("/mnt/user/Media/Bad,Name", "/mnt/user/Media/Bad/Name$()", "/mnt/unknown/Series"):
            with self.assertRaises(ValueError):
                guard.prepare_script(SCRIPT, CONFIG, [path], lambda p: True)
        with self.assertRaises(ValueError):
            guard.prepare_script(SCRIPT, CONFIG, ["/mnt/user/Media/Series"], lambda p: False)

    def test_changed_script_and_unsupported_config_fail_closed(self):
        for source in (SCRIPT.replace(guard.TOKEN, "bunker -V "),
                       SCRIPT.replace("/mnt/disk1", "/mnt/user/Media"),
                       SCRIPT.replace("-Vqj ", "-Vqj -F Other "), "echo bad"):
            with self.assertRaises(ValueError):
                guard.prepare_script(source, CONFIG, [], lambda p: True)
        for config in (CONFIG + 'folders="Duplicate"\n', CONFIG.replace('files=""', 'files="*.tmp"')):
            with self.assertRaises(ValueError):
                guard.prepare_script(SCRIPT, config, [], lambda p: True)

    def test_literal_regex_matches_only_intended_directory_in_bunker_sed(self):
        name = "Series.Name+Release-HUN"
        mask = guard.folder_pattern(name)
        data = f"/mnt/disk3/Media/{name}/episode.mkv\n/mnt/disk3/Media/Other/episode.mkv\n"
        expr = r"/\/mnt\/disk[0-9]+\/.*" + mask + r"\//d"
        result = subprocess.run(["sed", "-r", expr], input=data, text=True, capture_output=True, check=True)
        self.assertEqual(result.stdout, "/mnt/disk3/Media/Other/episode.mkv\n")

    def test_api_failure_does_not_start_bash(self):
        with patch.object(guard, "read_snapshot", side_effect=ValueError("PRIVATE")), patch.object(guard.subprocess, "run") as run:
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(guard.main([]), 20)
            run.assert_not_called()
            self.assertNotIn("PRIVATE", out.getvalue())

    def test_check_only_does_not_hash_or_write_configuration(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            config, script = root / "config", root / "schedule"
            config.write_text(CONFIG)
            script.write_text(SCRIPT)
            snapshot = ([{"progress": 1, "state": "stalledUP"}], [])
            with patch.object(guard, "read_snapshot", return_value=snapshot), patch.object(guard.subprocess, "run") as run:
                with contextlib.redirect_stdout(io.StringIO()):
                    code = guard.main(["--config", str(config), "--script", str(script), "--check-only"])
                self.assertEqual(code, 0)
                self.assertEqual(run.call_args_list[0].args[0], ["bash", "-n"])
                self.assertEqual(run.call_count, 1)
            self.assertEqual(config.read_text(), CONFIG)
            self.assertEqual(script.read_text(), SCRIPT)


if __name__ == "__main__":
    unittest.main()
