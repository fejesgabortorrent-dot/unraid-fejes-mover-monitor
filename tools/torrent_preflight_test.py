import contextlib
import io
import json
import subprocess
import unittest
from unittest.mock import patch

import torrent_preflight as guard

MOUNTS = [{"Type": "bind", "Destination": "/data", "Source": "/mnt/user/Media"}]


def torrent(progress=1, state="stalledUP", path="/data/Film"):
    return {"progress": progress, "state": state, "content_path": path}


class PreflightTest(unittest.TestCase):
    def test_complete_seed_states_pass(self):
        for state in guard.SEED_STATES:
            with self.subTest(state=state):
                self.assertEqual(guard.assess([torrent(state=state)], MOUNTS)["exit_code"], 0)

    def test_incomplete_stopped_and_nearly_complete_torrents_block(self):
        for progress, state in [(0.3, "stoppedDL"), (0.999999, "stalledDL"), (0.4, "downloading")]:
            with self.subTest(state=state):
                self.assertEqual(guard.assess([torrent(progress, state)], MOUNTS)["exit_code"], 10)

    def test_checking_and_moving_block_even_at_one_hundred_percent(self):
        for state in ("checkingUP", "checkingResumeData", "moving", "allocating"):
            self.assertEqual(guard.assess([torrent(state=state)], MOUNTS)["exit_code"], 10)

    def test_shared_path_is_still_protected_and_deduplicated(self):
        result = guard.assess([torrent(), torrent(0.5, "stoppedDL"), torrent(0.9, "downloading")], MOUNTS)
        self.assertEqual(result["blocking_torrents"], 2)
        self.assertEqual(result["protected_paths"], ["/mnt/user/Media/Film"])

    def test_longest_bind_mount_and_directory_boundary(self):
        mounts = MOUNTS + [{"Type": "bind", "Destination": "/data/Shows", "Source": "/mnt/user/Shows"}]
        self.assertEqual(guard.host_path("/data/Shows/Series", mounts), "/mnt/user/Shows/Series")
        with self.assertRaises(ValueError):
            guard.host_path("/database/Film", mounts)

    def test_empty_and_malformed_snapshots_fail_closed(self):
        for data in ([], {}, None, [None], [torrent(True)], [torrent(float("nan"))],
                     [torrent(1.1)], [torrent(state="error")], [torrent(state="missingFiles")],
                     [torrent(state="futureUnknownState")]):
            with self.subTest(data=data):
                with self.assertRaises(ValueError):
                    guard.assess(data, MOUNTS)

    def test_missing_and_unsafe_unfinished_paths_fail_closed(self):
        for path in (None, "", "/data/../Other", "/unmapped/Film", "/data/Film\x00"):
            with self.assertRaises(ValueError):
                guard.assess([torrent(0.2, "downloading", path)], MOUNTS)

    def test_api_and_docker_errors_defer_without_leaking_output(self):
        for exc in (subprocess.TimeoutExpired("docker", 5), FileNotFoundError(),
                    subprocess.CalledProcessError(22, "curl", stderr="PRIVATE"),
                    json.JSONDecodeError("PRIVATE", "", 0)):
            with patch.object(guard, "read_snapshot", side_effect=exc):
                out = io.StringIO()
                with contextlib.redirect_stdout(out):
                    self.assertEqual(guard.main([]), 20)
                self.assertNotIn("PRIVATE", out.getvalue())

    def test_plain_output_omits_paths_and_json_reports_them(self):
        data = ([torrent(0.2, "downloading")], MOUNTS)
        with patch.object(guard, "read_snapshot", return_value=data):
            for argv in ([], ["--json"]):
                out = io.StringIO()
                with contextlib.redirect_stdout(out):
                    self.assertEqual(guard.main(argv), 10)
                self.assertEqual("/mnt/user/Media/Film" in out.getvalue(), bool(argv))

    def test_snapshot_only_uses_read_only_commands_with_bounds(self):
        replies = [subprocess.CompletedProcess([], 0, json.dumps(MOUNTS)),
                   subprocess.CompletedProcess([], 0, json.dumps([torrent()]))]
        with patch.object(guard.subprocess, "run", side_effect=replies) as run:
            self.assertEqual(guard.read_snapshot("qbit", 5), ([torrent()], MOUNTS))
        calls = run.call_args_list
        self.assertEqual(calls[0].args[0], ["docker", "inspect", "--format", "{{json .Mounts}}", "qbit"])
        self.assertEqual(calls[1].args[0][-1], "http://127.0.0.1:8080/api/v2/torrents/info")
        self.assertNotIn("-X", calls[1].args[0])
        self.assertEqual(calls[1].kwargs["timeout"], 7)


if __name__ == "__main__":
    unittest.main()
