#!/usr/bin/env python3
"""Host-independent regression checks for partial unit pre-native deferral.

Run from repository root:
    python3 testlab/partial_unit_deferral.py

Only the pure policy function is loaded from the production module; no Unraid
mounts, torrent clients, or filesystem writes are required.
"""
import ast
from pathlib import Path
import unittest


def load_policy():
    source = Path(__file__).resolve().parents[1] / 'tools' / 'selective_mover.py'
    tree = ast.parse(source.read_text(encoding='utf-8'))
    matches = [node for node in tree.body
               if isinstance(node, ast.FunctionDef)
               and node.name == 'safe_pre_native_partial_deferral']
    assert len(matches) == 1
    ns = {}
    exec(compile(ast.Module(body=matches, type_ignores=[]), str(source), 'exec'), ns)
    return ns['safe_pre_native_partial_deferral']


policy = load_policy()


def report(**overrides):
    base = {
        'active_file_started': False,
        'verified_files': [
            {'bytes': 917351686, 'sha256': 'a' * 64,
             'destination': '/mnt/disk4/Filmek/example.mkv'}],
        'moved_files': 1,
        'moved_bytes': 917351686,
    }
    base.update(overrides)
    return base


class PartialUnitDeferralTests(unittest.TestCase):
    def test_pre_native_eligible_skip_is_recoverable(self):
        for reason in ('fresh_conditions_changed',
                       'source_or_destination_changed', 'open_file'):
            with self.subTest(reason=reason):
                self.assertTrue(policy(report(), 1, {'state': 'skipped', 'reason': reason}))

    def test_native_intent_must_latch(self):
        self.assertFalse(policy(report(active_file_started=True), 1,
                                {'state': 'skipped', 'reason': 'open_file'}))

    def test_native_retained_source_must_latch(self):
        self.assertFalse(policy(report(), 1,
                                {'state': 'skipped', 'reason': 'native_retained_source'}))

    def test_incomplete_evidence_must_latch(self):
        self.assertFalse(policy(report(moved_bytes=1), 1,
                                {'state': 'skipped', 'reason': 'open_file'}))
        self.assertFalse(policy(report(verified_files=[]), 1,
                                {'state': 'skipped', 'reason': 'open_file'}))

    def test_no_earlier_move_is_not_partial_recovery(self):
        self.assertFalse(policy(report(), 0,
                                {'state': 'skipped', 'reason': 'open_file'}))

    def test_missing_or_ambiguous_evidence_must_latch(self):
        self.assertFalse(policy(report(active_file_started=None), 1,
                                {'state': 'skipped', 'reason': 'open_file'}))
        self.assertFalse(policy(report(verified_files=[{'bytes': -1}]), 1,
                                {'state': 'skipped', 'reason': 'open_file'}))


if __name__ == '__main__':
    unittest.main()
