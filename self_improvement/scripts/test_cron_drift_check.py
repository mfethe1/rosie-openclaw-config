import unittest
from datetime import timedelta
from cron_drift_check import is_market_hours_only, parse_interval, parse_last_run

class TestCronDriftCheck(unittest.TestCase):
    def test_is_market_hours_only(self):
        self.assertTrue(is_market_hours_only("cron */5 9-16 * * 1-5"))
        self.assertFalse(is_market_hours_only("cron */5 * * * *"))
        self.assertTrue(is_market_hours_only("cron 0 4-9 * * 1-5"))

    def test_parse_interval(self):
        self.assertEqual(parse_interval("every 3h"), timedelta(hours=3))
        self.assertEqual(parse_interval("every 15m"), timedelta(minutes=15))
        self.assertEqual(parse_interval("every 10 min"), timedelta(minutes=10))
        self.assertEqual(parse_interval("cron */5 * * * *"), timedelta(minutes=5))
        self.assertEqual(parse_interval("cron 0 4 * * *"), timedelta(hours=24))
        self.assertEqual(parse_interval("cron 0 */2 * * *"), timedelta(hours=2))
        self.assertEqual(parse_interval("cron 0 9-16/3 * * *"), timedelta(hours=3))
        self.assertEqual(parse_interval("cron 0 4 * * 1-5"), timedelta(hours=24))

    def test_parse_last_run(self):
        self.assertIsNone(parse_last_run("-"))
        self.assertIsNone(parse_last_run(""))
        self.assertEqual(parse_last_run("5m ago"), timedelta(minutes=5))
        self.assertEqual(parse_last_run("2h ago"), timedelta(hours=2))
        self.assertEqual(parse_last_run("3d ago"), timedelta(days=3))
        self.assertEqual(parse_last_run("<1m ago"), timedelta(minutes=0))

if __name__ == '__main__':
    unittest.main()
