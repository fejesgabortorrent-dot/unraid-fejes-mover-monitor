import unittest

from active_seed_policy import (GLOBAL_GUARDS, assess_unit,
                                classify_completed_seed, validate_transition)


def torrent(**updates):
    row = {"hash": "a" * 40, "content_path": "/data/Film.mkv",
           "state": "uploading", "progress": 1.0,
           "upspeed": 2048, "dlspeed": 0, "ratio": 1.5}
    row.update(updates)
    return row


def evidence(**changes):
    row = {"torrents": [torrent()], "guards": {key: "pass" for key in GLOBAL_GUARDS},
           "owner_hashes": ["a" * 40],
           "expected_paths": ["/mnt/user/Filmek/Film.mkv"],
           "verified_paths": ["/mnt/user/Filmek/Film.mkv"],
           "stable": True, "no_writers": True, "namespace_unchanged": True}
    row.update(changes)
    return row


class ActiveSeedPolicyTests(unittest.TestCase):
    def test_active_upload_is_only_coordination_candidate(self):
        self.assertEqual(classify_completed_seed(torrent()), "active_coordination_required")
        result = assess_unit(**evidence())
        self.assertEqual(result["decision"], "coordination_required")
        self.assertFalse(result["execute_allowed"])
        self.assertTrue(result["actively_uploading"])

    def test_completed_idle_seed_needs_coordination_too(self):
        result = assess_unit(**evidence(torrents=[
            torrent(state="stalledUP", upspeed=0)]))
        self.assertFalse(result["actively_uploading"])
        self.assertFalse(result["execute_allowed"])

    def test_no_incomplete_or_actively_writing_torrent(self):
        for change in ({"progress": .99}, {"state": "downloading", "progress": .5},
                       {"state": "checkingUP"}, {"state": "moving"},
                       {"dlspeed": 1}, {"state": "stoppedUP"},
                       {"state": "error"}):
            with self.subTest(change=change):
                self.assertEqual(assess_unit(**evidence(torrents=[
                    torrent(**change)]))["decision"], "blocked")

    def test_unverifiable_api_snapshot_denied(self):
        for change in ({"ratio": None}, {"upspeed": -1}, {"hash": ""},
                       {"content_path": "relative"}, {"state": "unknown"}):
            with self.subTest(change=change):
                self.assertEqual(assess_unit(**evidence(torrents=[
                    torrent(**change)]))["decision"], "blocked")
        self.assertEqual(assess_unit(**evidence(torrents=[]))["reason"],
                         "owners_unverified")

    def test_every_global_guard_is_mandatory(self):
        for guard in GLOBAL_GUARDS:
            with self.subTest(guard=guard):
                guards = {key: "pass" for key in GLOBAL_GUARDS}
                guards[guard] = "unknown"
                result = assess_unit(**evidence(guards=guards))
                self.assertEqual(result["reason"], "guard_not_passed")

    def test_no_partial_group_or_ambiguous_ownership(self):
        self.assertEqual(assess_unit(**evidence(verified_paths=[]))["reason"],
                         "partial_or_ambiguous_unit")
        self.assertEqual(assess_unit(**evidence(owner_hashes=["b" * 40]))["reason"],
                         "owners_unverified")
        self.assertEqual(assess_unit(**evidence(
            torrents=[torrent(), torrent()]))["reason"], "owners_unverified")

    def test_unknown_writes_or_mapping_block(self):
        for field in ("stable", "no_writers", "namespace_unchanged"):
            with self.subTest(field=field):
                args = evidence(**{field: None})
                self.assertEqual(assess_unit(**args)["reason"],
                                 "file_or_namespace_unverified")

    def test_peer_proof_required_for_success(self):
        before = assess_unit(**evidence())
        after = {"owner_hashes": before["owner_hashes"]}
        flags = {"files_verified": True, "logical_paths_unchanged": True,
                 "complete": True, "resumed": True, "peer_upload_verified": True}
        self.assertTrue(validate_transition(before, after, **flags)["verified"])
        for field in flags:
            with self.subTest(field=field):
                changed = dict(flags, **{field: False})
                self.assertFalse(validate_transition(before, after, **changed)["verified"])
        self.assertFalse(validate_transition(before, {
            "owner_hashes": ["c" * 40]}, **flags)["verified"])


if __name__ == "__main__":
    unittest.main()
