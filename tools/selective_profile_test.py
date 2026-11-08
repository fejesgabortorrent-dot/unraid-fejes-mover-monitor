import json
from pathlib import Path
import tempfile
import unittest

from selective_profile import DEFAULT, load_profile


class SelectiveProfileTest(unittest.TestCase):
    def test_missing_profile_keeps_owner_compatibility(self):
        with tempfile.TemporaryDirectory() as directory:
            profile = load_profile(Path(directory) / 'missing.json')
        self.assertEqual(profile, DEFAULT)
        self.assertEqual(profile.source, Path('/mnt/cache/Filmek'))
        self.assertEqual(profile.canonical, '/mnt/user/Filmek')

    def test_explicit_profile_derives_scoped_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'profile.json'
            path.write_text(json.dumps({
                'version': 1,
                'pool': 'fast_cache',
                'share': 'Media_01',
                'torrent_container': 'qbittorrent-vpn',
                'launcher_script': 'Media_01_Mover',
            }), encoding='utf-8')
            profile = load_profile(path)
        self.assertEqual(str(profile.source), '/mnt/fast_cache/Media_01')
        self.assertEqual(profile.canonical, '/mnt/user/Media_01')
        self.assertTrue(str(profile.share_config).endswith('/Media_01.cfg'))

    def test_invalid_profile_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'profile.json'
            path.write_text(json.dumps({
                'version': 1,
                'pool': '../cache',
                'share': 'Media',
                'torrent_container': 'qbit',
                'launcher_script': 'Mover',
            }), encoding='utf-8')
            with self.assertRaises(ValueError):
                load_profile(path)


if __name__ == '__main__':
    unittest.main()
