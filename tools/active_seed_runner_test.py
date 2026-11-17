import unittest

from active_seed_policy import GLOBAL_GUARDS
from active_seed_runner import run_unit, UnitInspectionRequired

HASH = "a" * 40
PATH = "/mnt/user/Filmek/movie.mkv"


def torrent(state="uploading"):
    return {"hash": HASH, "content_path": "/data/movie.mkv", "progress": 1.0,
            "upspeed": 1024 if state == "uploading" else 0,
            "dlspeed": 0, "ratio": 1.8, "state": state}


def evidence(state="uploading", **overrides):
    value = dict(torrents=[torrent(state)],
                 guards={key: "pass" for key in GLOBAL_GUARDS},
                 owner_hashes=[HASH],
                 expected_paths=[PATH], verified_paths=[PATH],
                 stable=True, no_writers=True, namespace_unchanged=True)
    value.update(overrides)
    return value


class Transport:
    def __init__(self, fail_restore=False):
        self.state = "uploading"
        self.events = []
        self.fail_restore = fail_restore

    def snapshot(self, hashes):
        self.events.append("snapshot")
        return [torrent(self.state)]

    def stop(self, hashes):
        self.events.append("stop")
        self.state = "stoppedUP"

    def start(self, hashes):
        self.events.append("start")
        if self.fail_restore:
            raise RuntimeError("API failed")
        self.state = "stalledUP"


class ActiveSeedRunnerTests(unittest.TestCase):
    def call(self, transport=None, *, authorized=True, preflight=None,
             move=None, file_check=None, peer=None, initial=None, require_peer=True):
        transport = transport or Transport()
        count = {"move": 0}
        def native():
            count["move"] += 1
            return {"verified": True}
        result = run_unit(
            snapshot=initial if initial is not None else evidence(),
            transport=transport,
            preflight=preflight or (lambda: evidence(state=transport.state)),
            move_unit=move or native,
            verify_files=file_check or (lambda: {"hashes_match": True,
                "logical_paths_unchanged": True, "all_complete": True,
                "resumed": True}),
            verify_peer=peer or (lambda hashes: True),
            sleep=lambda seconds: None, vm_test_authorized=authorized,
            require_peer_upload=require_peer)
        return result, transport, count

    def test_opt_in_required_without_torrent_mutation(self):
        result, api, stats = self.call(authorized=False)
        self.assertEqual(result["state"], "blocked")
        self.assertEqual(api.events, [])
        self.assertEqual(stats["move"], 0)

    def test_successful_order_with_peer_evidence(self):
        result, api, stats = self.call()
        self.assertEqual(result["state"], "completed")
        self.assertEqual(stats["move"], 1)
        self.assertLess(api.events.index("stop"), api.events.index("start"))

    def test_changed_preflight_defers_and_resumes_without_move(self):
        api = Transport()
        result, api, stats = self.call(
            api, preflight=lambda: evidence(state=api.state, no_writers=False))
        self.assertEqual(result["state"], "deferred")
        self.assertEqual(stats["move"], 0)
        self.assertIn("start", api.events)

    def test_native_failure_requires_inspection_and_restores(self):
        api = Transport()
        def broken():
            raise OSError("native I/O uncertainty")
        with self.assertRaises(UnitInspectionRequired):
            self.call(api, move=broken)
        self.assertIn("start", api.events)

    def test_restoration_failure_requires_inspection(self):
        with self.assertRaises(UnitInspectionRequired):
            self.call(Transport(fail_restore=True))

    def test_missing_peer_evidence_is_not_success(self):
        with self.assertRaises(UnitInspectionRequired):
            self.call(peer=lambda hashes: False)

    def test_explicit_idle_pilot_reports_readiness_without_claiming_peer_upload(self):
        result, _, stats = self.call(peer=lambda hashes: False, require_peer=False)
        self.assertEqual(result['state'], 'completed_seed_ready')
        self.assertTrue(result['seed_ready_verified'])
        self.assertFalse(result['peer_upload_verified'])
        self.assertEqual(stats['move'], 1)

    def test_idle_pilot_still_rejects_missing_file_or_resume_evidence(self):
        with self.assertRaises(UnitInspectionRequired):
            self.call(peer=lambda hashes: False, require_peer=False,
                      file_check=lambda: {'hashes_match': True, 'all_complete': True,
                                         'logical_paths_unchanged': True, 'resumed': False})

    def test_idle_pilot_api_failure_is_not_downgraded_to_no_peer(self):
        def unavailable(hashes):
            raise RuntimeError('API unavailable')
        with self.assertRaises(UnitInspectionRequired):
            self.call(peer=unavailable, require_peer=False)

    def test_unchanged_invalid_guard_never_stops_torrent(self):
        result, api, stats = self.call(initial=evidence(
            guards={key: "unknown" for key in GLOBAL_GUARDS}))
        self.assertEqual(result["state"], "deferred")
        self.assertEqual(api.events, [])
        self.assertEqual(stats["move"], 0)


if __name__ == "__main__":
    unittest.main()
