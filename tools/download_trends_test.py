import unittest
from datetime import datetime, timezone
from download_trends import record, render

class TrendsTests(unittest.TestCase):
    def test_first_sample_is_baseline_and_same_day_replaces(self):
        now = datetime(2026, 11, 22, tzinfo=timezone.utc)
        h = record([], {'total': 7}, now)
        self.assertEqual(record(h, {'total': 9}, now), [{'date':'2026-11-22','total':9}])
        self.assertIn('korábbi hónapok nem állíthatók vissza', render(h))
    def test_counter_decrease_is_visible(self):
        h = [{'date':'2026-11-01','total':10},{'date':'2026-11-02','total':4}]
        self.assertIn('<td>4</td>', render(h))
        self.assertIn('Csökkenés lehetséges', render(h))
    def test_invalid_history_fails_closed(self):
        with self.assertRaises(ValueError):
            render([{'date':'2026-11-01','total':-1}])
        with self.assertRaises(ValueError):
            record([{'date':'2026-11-23','total':1}], {'total':2}, datetime(2026,11,22,tzinfo=timezone.utc))

if __name__ == '__main__':
    unittest.main()
