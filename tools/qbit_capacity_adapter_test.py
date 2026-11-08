import unittest

from qbit_capacity_adapter import QbitCapacityAdapter
from torrent_capacity_guard import apply, plan


class AdapterTest(unittest.TestCase):
    def test_pause_and_resume_use_expected_endpoints_without_logging_data(self):
        calls = []
        adapter = QbitCapacityAdapter(
            "http://127.0.0.1:8080", "SID=private",
            transport=lambda url, data: calls.append((url, data)),
        )
        adapter.pause("ABCDEF12")
        adapter.resume("ABCDEF12")
        self.assertEqual(calls, [
            ("http://127.0.0.1:8080/api/v2/torrents/pause", b"hashes=ABCDEF12"),
            ("http://127.0.0.1:8080/api/v2/torrents/resume", b"hashes=ABCDEF12"),
        ])

    def test_cookie_is_not_sent_to_injected_transport_as_payload(self):
        seen = []
        adapter = QbitCapacityAdapter("http://localhost:8080", "SID=secret", lambda u, d: seen.append((u, d)))
        adapter.pause("12345678")
        self.assertNotIn(b"secret", seen[0][1])

    def test_invalid_input_fails_closed(self):
        with self.assertRaises(ValueError):
            QbitCapacityAdapter("not-a-url", "SID=x")
        adapter = QbitCapacityAdapter("http://localhost:8080", "SID=x")
        with self.assertRaises(ValueError):
            adapter.pause("bad hash")

    def test_capacity_policy_and_adapter_are_connected_without_live_network(self):
        calls = []
        adapter = QbitCapacityAdapter(
            "http://127.0.0.1:8080", "SID=private",
            transport=lambda url, data: calls.append((url, data)),
        )
        decision = plan([
            {"hash": "DOWN1234", "state": "downloading"},
            {"hash": "SEED1234", "state": "uploading"},
        ], 9, 10, 20)
        self.assertEqual(apply(adapter, decision), ("DOWN1234",))
        self.assertEqual(calls, [
            ("http://127.0.0.1:8080/api/v2/torrents/pause", b"hashes=DOWN1234"),
        ])
        recovered = plan([], 20, 10, 20, owned_paused=("DOWN1234",))
        self.assertEqual(apply(adapter, recovered), ("DOWN1234",))
        self.assertEqual(calls[-1], (
            "http://127.0.0.1:8080/api/v2/torrents/resume", b"hashes=DOWN1234"))


if __name__ == "__main__":
    unittest.main()
