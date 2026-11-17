import json
import unittest
from types import SimpleNamespace

from qbit_seed_transport import DockerQbitTransport, TorrentTransportError

A = "a" * 40
B = "b" * 40


class TransportTests(unittest.TestCase):
    def test_snapshot_filters_only_requested_owner(self):
        calls = []
        def runner(command, **kwargs):
            calls.append(command)
            records = [{"hash": A}, {"hash": B}]
            return SimpleNamespace(returncode=0, stdout=json.dumps(records))
        transport = DockerQbitTransport(runner=runner)
        self.assertEqual(transport.snapshot([A]), [{"hash": A}])
        self.assertEqual(calls[0][-1],
                         "http://127.0.0.1:8080/api/v2/torrents/info")
        self.assertNotIn("--data-urlencode", calls[0])
        self.assertIn("--request", calls[0])
        self.assertEqual(calls[0][calls[0].index("--request")+1], "GET")

    def test_stop_start_are_hash_scoped_posts(self):
        calls = []
        def runner(command, **kwargs):
            calls.append(command)
            return SimpleNamespace(returncode=0, stdout="")
        transport = DockerQbitTransport(runner=runner)
        transport.stop([A])
        transport.start([B])
        self.assertTrue(all("--data-urlencode" in call for call in calls))
        self.assertEqual(calls[0][calls[0].index("--data-urlencode")+1],
                         "hashes="+A)
        self.assertEqual(calls[1][calls[1].index("--data-urlencode")+1],
                         "hashes="+B)
        self.assertEqual([c[-1].rsplit("/",1)[-1] for c in calls],
                         ["stop", "start"])

    def test_api_failure_rejected(self):
        def runner(*args, **kwargs):
            return SimpleNamespace(returncode=22, stdout="", stderr="secret")
        with self.assertRaises(TorrentTransportError):
            DockerQbitTransport(runner=runner).snapshot([A])

    def test_missing_hash_rejected(self):
        def runner(*args, **kwargs):
            return SimpleNamespace(returncode=0, stdout=json.dumps([{"hash": B}]))
        with self.assertRaises(TorrentTransportError):
            DockerQbitTransport(runner=runner).snapshot([A])

    def test_reject_global_selection_and_bad_container(self):
        with self.assertRaises(ValueError):
            DockerQbitTransport(container="x;rm")
        transport = DockerQbitTransport(runner=lambda *a, **k: None)
        for hashes in (["all"], [A,A], [], ["bad"], [None]):
            with self.subTest(hashes=hashes):
                with self.assertRaises(ValueError):
                    transport.stop(hashes)


if __name__ == "__main__":
    unittest.main()
