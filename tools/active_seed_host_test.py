import io
import json
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import active_seed_host as host
from active_seed_policy import GLOBAL_GUARDS

H = "a" * 40
SHA = "b" * 64
P = "/mnt/user/Filmek/Test.mkv"


class FakeTransport:
    def __init__(self):
        self.state = "uploading"
        self.calls = []

    def snapshot(self, hashes):
        return [{"hash": H, "content_path": "/data/Test.mkv", "state": self.state,
                 "progress": 1.0, "dlspeed": 0,
                 "upspeed": 100 if self.state == "uploading" else 0,
                 "ratio": 2.0}]

    def stop(self, hashes):
        self.calls.append("stop")
        self.state = "stoppedUP"

    def start(self, hashes):
        self.calls.append("start")
        self.state = "stalledUP"


def evidence(transport):
    return {"torrents": transport.snapshot([H]),
            "guards": {g: "pass" for g in GLOBAL_GUARDS},
            "owner_hashes": [H], "expected_paths": [P],
            "verified_paths": [P], "stable": True, "no_writers": True,
            "namespace_unchanged": True}


class VMHostTest(unittest.TestCase):
    def run_case(self, *, prior_report=False, marker=True, peer=True,
                 native_failure=False):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            report = base / "active-seed-vm-last.json"
            if prior_report:
                report.write_text(json.dumps({"requires_inspection": True}))
            marker_file = base / "marker"
            if marker:
                marker_file.write_text(host.MARKER_CONTENT)
            api = FakeTransport()
            native_calls = []
            def native_execute(key, expected, days, before_native):
                native_calls.append(key)
                before_native(SHA)
                if native_failure:
                    raise OSError("simulated native failure")
                return {"state": "moved", "bytes": 10, "sha256": SHA,
                        "destination": "/mnt/disk4/Filmek/Test.mkv"}
            fake_native = SimpleNamespace(
                LAST=base/"last.json", PID=base/"mover.pid",
                needs_inspection=lambda report: report.get("requires_inspection", False),
                guards=lambda owned: {k: "pass" for k in (
                    "backup", "parity", "integrity", "mount", "mover",
                    "cooldown", "capacity", "open_files", "namespace")},
                execute_file=native_execute)
            with patch.object(host, "open", return_value=io.StringIO(), create=True), \
                 patch.object(host.fcntl, "flock", return_value=None):
                if native_failure:
                    with self.assertRaises(host.UnitInspectionRequired):
                        host.run_vm_trial(
                            marker=marker_file, report_path=report,
                            initial_evidence=lambda: evidence(api),
                            fresh_evidence=lambda: evidence(api),
                            transport=api,
                            inventory={P: {"signature": [1, 2, 10, 3, 4],
                                           "first_seen": 100}},
                            days=7, verify_files=lambda: {"hashes_match": True,
                                "logical_paths_unchanged": True, "all_complete": True,
                                "resumed": True},
                            verify_peer=lambda hashes: peer, sleep=lambda _: None,
                            native_module=fake_native)
                    result = {"state": "failed"}
                else:
                    result = host.run_vm_trial(
                        marker=marker_file, report_path=report,
                        initial_evidence=lambda: evidence(api),
                        fresh_evidence=lambda: evidence(api),
                        transport=api,
                        inventory={P: {"signature": [1, 2, 10, 3, 4],
                                       "first_seen": 100}},
                        days=7, verify_files=lambda: {"hashes_match": True,
                            "logical_paths_unchanged": True, "all_complete": True,
                            "resumed": True},
                        verify_peer=lambda hashes: peer, sleep=lambda _: None,
                        native_module=fake_native)
            stored = json.loads(report.read_text()) if report.exists() else None
            self.assertFalse(fake_native.PID.exists())
            return result, stored, api.calls, native_calls

    def test_vm_move_preserves_full_ledger_after_peer_verification(self):
        result, stored, events, moves = self.run_case()
        self.assertEqual(result["state"], "completed")
        self.assertEqual(events, ["stop", "start"])
        self.assertEqual(moves, [P])
        self.assertEqual(stored["state"], "completed")
        self.assertEqual(len(stored["verified_files"]), 1)
        self.assertFalse(stored["requires_inspection"])
        self.assertTrue(stored["peer_upload_verified"])

    def test_missing_marker_never_calls_api_or_native(self):
        result, stored, events, moves = self.run_case(marker=False)
        self.assertEqual(result["state"], "blocked")
        self.assertIsNone(stored)
        self.assertEqual(events, [])
        self.assertEqual(moves, [])

    def test_prior_vm_report_blocks_without_overwriting_it(self):
        result, stored, events, moves = self.run_case(prior_report=True)
        self.assertEqual(result["state"], "blocked")
        self.assertTrue(stored["requires_inspection"])
        self.assertEqual(events, [])
        self.assertEqual(moves, [])

    def test_native_failure_retains_ledger_and_inspection(self):
        _, stored, events, moves = self.run_case(native_failure=True)
        self.assertEqual(stored["state"], "inspection_required")
        self.assertTrue(stored["requires_inspection"])
        self.assertEqual(events, ["stop", "start"])
        self.assertEqual(moves, [P])


if __name__ == "__main__":
    unittest.main()
