#!/usr/bin/env python3
"""Regression coverage for independent Mover files and conservative ownership.

These are pure unit tests; no Unraid move or Docker operation is performed.
Cases cover the reviewed grouping change without executing native movement.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from selection_policy import unit_groups

ROOT = '/mnt/cache/Filmek'
MOUNTS = [{'Type': 'bind', 'Source': '/mnt/cache', 'Destination': '/mnt/cache'}]


def f(relative):
    return {'path': ROOT + '/' + relative}


class IndependentUnitGroupingTests(unittest.TestCase):
    def test_independent_episode_files_do_not_become_one_season_unit(self):
        files = [f('Series/Season01/Episode01.mkv'),
                 f('Series/Season01/Episode02.mkv'),
                 f('Series/Season01/Episode03.mkv')]
        groups = unit_groups(files, ROOT, [], [])
        self.assertEqual(sorted(map(len, groups)), [1, 1, 1])

    def test_exact_name_video_and_subtitle_remain_together(self):
        files = [f('Movie/Movie.mkv'), f('Movie/Movie.srt')]
        groups = unit_groups(files, ROOT, [], [])
        self.assertEqual(sorted(map(len, groups)), [2])

    def test_shared_torrent_owner_keeps_files_atomic(self):
        files = [f('Series/Season01/Episode01.mkv'),
                 f('Series/Season01/Episode02.mkv')]
        torrents = [{'content_path': ROOT + '/Series/Season01'}]
        groups = unit_groups(files, ROOT, torrents, MOUNTS)
        self.assertEqual(sorted(map(len, groups)), [2])

    def test_nested_owner_relationship_keeps_files_atomic(self):
        files = [f('Shows/Season01/A.mkv'), f('Shows/Season01/B.mkv'),
                 f('Shows/Season01/C.mkv')]
        torrents = [{'content_path': ROOT + '/Shows/Season01'},
                    {'content_path': ROOT + '/Shows/Season01/A.mkv'}]
        groups = unit_groups(files, ROOT, torrents, MOUNTS)
        self.assertEqual(sorted(map(len, groups)), [3])

    def test_generic_poster_preserves_whole_directory(self):
        files = [f('FilmA/FilmA.mkv'), f('FilmA/Trailer.mkv'),
                 f('FilmA/poster.jpg')]
        groups = unit_groups(files, ROOT, [], [])
        self.assertEqual(sorted(map(len, groups)), [3])

    def test_episode_sidecar_without_merging_another_episode(self):
        files = [f('Shows/S01/E01.mkv'), f('Shows/S01/E01.srt'),
                 f('Shows/S01/E02.mkv')]
        groups = unit_groups(files, ROOT, [], [])
        self.assertEqual(sorted(map(len, groups)), [1, 2])

    def test_unknown_file_preserves_directory(self):
        files = [f('Show/S01/E01.mkv'), f('Show/S01/E02.mkv'),
                 f('Show/S01/custom.unknown')]
        groups = unit_groups(files, ROOT, [], [])
        self.assertEqual(sorted(map(len, groups)), [3])

    def test_out_of_root_file_rejected(self):
        with self.assertRaises(ValueError):
            unit_groups([{'path': '/tmp/outside.mkv'}], ROOT, [], [])


if __name__ == '__main__':
    unittest.main()
