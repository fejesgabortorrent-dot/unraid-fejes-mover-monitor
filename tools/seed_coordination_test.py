import unittest

from seed_coordination import SeedCoordinator, CoordinationError


class FakeQbit:
    def __init__(self, *, stop_fails=False, start_fails=False, mutate=False):
        self.records = [{"hash": "a"*40, "progress": 1.0,
                         "dlspeed": 0, "state": "uploading"},
                        {"hash": "b"*40, "progress": 1.0,
                         "dlspeed": 0, "state": "stalledUP"}]
        self.calls = []
        self.stop_fails = stop_fails
        self.start_fails = start_fails
        self.mutate = mutate

    def snapshot(self, hashes):
        if self.mutate:
            return self.records[:1]
        return [dict(r) for r in self.records if r["hash"] in hashes]

    def stop(self, hashes):
        self.calls.append(("stop", list(hashes)))
        if self.stop_fails:
            raise RuntimeError("API failed")
        for r in self.records:
            if r["hash"] in hashes:
                r["state"] = "stoppedUP"

    def start(self, hashes):
        self.calls.append(("start", list(hashes)))
        if self.start_fails:
            raise RuntimeError("API failed")
        for r in self.records:
            if r["hash"] in hashes:
                r["state"] = "stalledUP"


class CoordinationTests(unittest.TestCase):
    def test_full_group_quiesces_and_restores_original_state(self):
        api = FakeQbit()
        flow = SeedCoordinator(api, sleep=lambda _: None)
        owners = ["a"*40, "b"*40]
        token = flow.prepare(owners)
        self.assertEqual(token["resume"], owners)
        self.assertTrue(token["quiesced"])
        outcome = flow.restore(token)
        self.assertTrue(outcome["restored"])
        self.assertFalse(outcome["peer_upload_verified"])
        self.assertEqual(api.calls, [("stop", owners), ("start", owners)])

    def test_reject_incomplete_before_any_mutation(self):
        api = FakeQbit()
        api.records[0]["progress"] = 0.8
        with self.assertRaises(CoordinationError):
            SeedCoordinator(api).prepare(["a"*40, "b"*40])
        self.assertEqual(api.calls, [])

    def test_reject_missing_owner_before_any_mutation(self):
        api = FakeQbit(mutate=True)
        with self.assertRaises(CoordinationError):
            SeedCoordinator(api).prepare(["a"*40, "b"*40])
        self.assertEqual(api.calls, [])

    def test_stop_failure_attempts_restore_and_does_not_authorize_move(self):
        api = FakeQbit(stop_fails=True)
        with self.assertRaises(CoordinationError):
            SeedCoordinator(api, sleep=lambda _: None).prepare(["a"*40, "b"*40])
        self.assertEqual([call[0] for call in api.calls], ["stop", "start"])

    def test_missing_restore_token_rejected(self):
        with self.assertRaises(CoordinationError):
            SeedCoordinator(FakeQbit()).restore({})

    def test_resume_failure_never_claims_success(self):
        api = FakeQbit(start_fails=True)
        flow = SeedCoordinator(api, sleep=lambda _: None)
        token = flow.prepare(["a"*40, "b"*40])
        with self.assertRaises(RuntimeError):
            flow.restore(token)

    def test_no_global_commands_in_transport_contract(self):
        api = FakeQbit()
        flow = SeedCoordinator(api, sleep=lambda _: None)
        flow.prepare(["a"*40])
        self.assertEqual(api.calls, [("stop", ["a"*40])])


if __name__ == "__main__":
    unittest.main()
