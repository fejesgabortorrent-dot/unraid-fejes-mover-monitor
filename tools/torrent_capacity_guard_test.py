import unittest

from torrent_capacity_guard import plan, apply


class Adapter:
    def __init__(self):
        self.calls = []

    def pause(self, value):
        self.calls.append(("pause", value))

    def resume(self, value):
        self.calls.append(("resume", value))


class CapacityGuardTest(unittest.TestCase):
    def test_low_capacity_pauses_downloads_but_not_seeds(self):
        result = plan([
            {"hash": "a", "state": "downloading"},
            {"hash": "b", "state": "uploading"},
            {"hash": "c", "state": "stalledDL"},
        ], 9, 10, 20)
        self.assertEqual(result.action, "pause")
        self.assertEqual(result.hashes, ("a", "c"))
        self.assertIn("Alacsony", result.warning)

    def test_recovery_resumes_only_owned_hashes(self):
        result = plan([], 20, 10, 20, owned_paused=("a", "a", "manual"))
        adapter = Adapter()
        self.assertEqual(apply(adapter, result), ("a", "manual"))
        self.assertEqual(adapter.calls, [("resume", "a"), ("resume", "manual")])

    def test_hysteresis_does_not_flap(self):
        result = plan([{ "hash": "a", "state": "downloading" }], 15, 10, 20)
        self.assertEqual(result.action, "none")
        self.assertEqual(result.hashes, ())

    def test_invalid_snapshot_fails_closed(self):
        with self.assertRaises(ValueError):
            plan([{ "hash": "a", "state": "unknown" }], 1, 10, 20)


if __name__ == "__main__":
    unittest.main()
