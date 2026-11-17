import unittest

from cache_hysteresis import evaluate, limits


class CacheCycle(unittest.TestCase):
    settings = {'completed_seed_mode': True, 'cache_start_percent': 75, 'cache_stop_percent': 65}
    scope = {'pool': 'cache', 'share': 'Filmek', 'torrent_container': 'qbit'}

    def test_drain_stays_active_between_thresholds_and_stops_at_lower_boundary(self):
        state = evaluate(self.settings, {}, 100, 26, self.scope)
        self.assertFalse(state['active'])
        state = evaluate(self.settings, state, 100, 25, self.scope)
        self.assertTrue(state['active'])
        state = evaluate(self.settings, state, 100, 30, self.scope)
        self.assertTrue(state['active'])
        state = evaluate(self.settings, state, 100, 35, self.scope)
        self.assertFalse(state['active'])
        self.assertFalse(evaluate(self.settings, state, 100, 30, self.scope)['active'])

    def test_changed_scope_or_thresholds_does_not_inherit_an_active_cycle(self):
        active = evaluate(self.settings, {}, 100, 20, self.scope)
        self.assertFalse(evaluate(self.settings, active, 100, 30, {'pool': 'other'})['active'])
        changed = dict(self.settings, cache_start_percent=80)
        self.assertFalse(evaluate(changed, active, 100, 30, self.scope)['active'])

    def test_invalid_boundaries_capacity_and_state_fail_closed(self):
        for start, stop in [(65, 75), (75, 75), (100, 65), (75, 0), (True, 65), (75, '65')]:
            with self.subTest(start=start, stop=stop), self.assertRaises(ValueError):
                limits(dict(self.settings, cache_start_percent=start, cache_stop_percent=stop))
        for total, free in [(0, 0), (100, -1), (100, 101), (True, 0), (100, None)]:
            with self.subTest(total=total, free=free), self.assertRaises(ValueError):
                evaluate(self.settings, {}, total, free, self.scope)
        with self.assertRaises(ValueError):
            evaluate(self.settings, {'version': 1, 'active': 'true'}, 100, 20, self.scope)

    def test_defaults_are_explicit_completion_mode_only(self):
        self.assertIsNone(limits({}))
        self.assertEqual(limits({'completed_seed_mode': True}), (75, 65))
