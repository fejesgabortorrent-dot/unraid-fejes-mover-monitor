import copy
import unittest

from active_seed_native import move_verified_unit
from active_seed_runner import UnitInspectionRequired

A = "/mnt/user/Filmek/Movie/film.mkv"
B = "/mnt/user/Filmek/Movie/film.srt"
SHA = "a" * 64


def inventory(paths):
    return {p: {"signature": [1, 2 + i, 100 + i, 3, 4],
                "first_seen": 1000} for i, p in enumerate(paths)}


class NativeBridgeTests(unittest.TestCase):
    def run_bridge(self, paths=None, move=None, authorized=True, inv=None):
        paths = paths if paths is not None else [A, B]
        inv = inv if inv is not None else inventory(paths)
        journal = []
        def persist(state):
            journal.append(copy.deepcopy(state))
        def native(path, expected, days, before_native):
            before_native(SHA)
            return {"state": "moved", "bytes": expected["signature"][2],
                    "sha256": SHA, "destination": "/mnt/disk4/Filmek/" + path.split("/")[-1]}
        if move is None:
            move = native
        result = move_verified_unit(expected_paths=paths, inventory=inv, days=7,
                                    execute_file=move, persist=persist,
                                    test_vm_authorized=authorized)
        return result, journal

    def test_moves_all_and_journals_intent_before_each_native_invocation(self):
        result, journal = self.run_bridge()
        self.assertTrue(result["verified"])
        self.assertEqual(result["files"], 2)
        self.assertEqual(journal[-1]["state"], "native_verified")
        intents = [row for row in journal if row["state"] == "native_intent"]
        self.assertEqual(len(intents), 2)
        self.assertTrue(all(row["requires_inspection"] for row in intents))
        self.assertEqual(len(journal[-1]["verified_files"]), 2)

    def test_no_authorization_means_no_move(self):
        calls = []
        result, journal = self.run_bridge(authorized=False, move=lambda *args:
                                           calls.append(args))
        self.assertFalse(result["verified"])
        self.assertFalse(journal)
        self.assertFalse(calls)

    def test_pre_native_skip_can_defer_only_before_first_file(self):
        result, journal = self.run_bridge(move=lambda *args:
                                          {"state": "skipped", "reason": "open_file"})
        self.assertFalse(result["verified"])
        self.assertEqual(result["reason"], "pre_native_skip")
        self.assertEqual(journal[-1]["state"], "deferred")

    def test_partial_unit_skip_sticks_inspection(self):
        calls = [0]
        def native(path, expected, days, before_native):
            calls[0] += 1
            if calls[0] == 2:
                return {"state": "skipped", "reason": "file_changed"}
            before_native(SHA)
            return {"state": "moved", "bytes": expected["signature"][2],
                    "sha256": SHA, "destination": "/mnt/disk4/Filmek/film.mkv"}
        journal = []
        def persist(state):
            journal.append(copy.deepcopy(state))
        with self.assertRaises(UnitInspectionRequired):
            move_verified_unit(expected_paths=[A, B], inventory=inventory([A, B]),
                               days=7, execute_file=native, persist=persist,
                               test_vm_authorized=True)
        self.assertEqual(journal[-1]["state"], "inspection_required")
        self.assertEqual(len(journal[-1]["verified_files"]), 1)
        self.assertEqual(journal[-1]['native_outcome'],
                         {'state': 'skipped', 'reason': 'file_changed'})
        self.assertFalse(journal[-1]['active_file_started'])

    def test_native_exception_sticks_inspection(self):
        def native(path, expected, days, before_native):
            before_native(SHA)
            raise OSError("I/O uncertain")
        journal = []
        with self.assertRaises(UnitInspectionRequired):
            move_verified_unit(expected_paths=[A], inventory=inventory([A]), days=7,
                               execute_file=native,
                               persist=lambda state: journal.append(copy.deepcopy(state)),
                               test_vm_authorized=True)
        self.assertTrue(journal[-1]["requires_inspection"])

    def test_reject_unverified_scope_without_native(self):
        cases = [(["/mnt/cache/a"], inventory(["/mnt/cache/a"])),
                 ([A, A], inventory([A])), ([A], {}),
                 ([A], {A: {"signature": [1], "first_seen": 2}})]
        for paths, inv in cases:
            with self.subTest(paths=paths):
                result, journal = self.run_bridge(paths, inv=inv)
                self.assertFalse(result["verified"])
                self.assertFalse(journal)


if __name__ == "__main__":
    unittest.main()
