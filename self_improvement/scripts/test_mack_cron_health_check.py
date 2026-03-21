import json
import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta, timezone
from io import StringIO

import self_improvement.scripts.mack_cron_health_check as mack_cron_health_check

class TestMackCronHealthCheck(unittest.TestCase):

    @patch('self_improvement.scripts.mack_cron_health_check.JOBS_PATH')
    def test_get_mack_crons_no_file(self, mock_jobs_path):
        mock_jobs_path.exists.return_value = False
        with patch('sys.stdout', new=StringIO()) as fake_out:
            result = mack_cron_health_check.get_mack_crons()
            self.assertEqual(result, [])
            self.assertIn("ERROR: cron/jobs.json not found", fake_out.getvalue())

    @patch('self_improvement.scripts.mack_cron_health_check.JOBS_PATH')
    def test_get_mack_crons_success(self, mock_jobs_path):
        mock_jobs_path.exists.return_value = True
        mock_jobs_path.read_text.return_value = json.dumps({
            "jobs": [
                {"id": "1", "name": "mack-loop"},
                {"id": "2", "name": "winnie-loop"},
                {"id": "3", "name": "Macklemore review"}
            ]
        })
        result = mack_cron_health_check.get_mack_crons()
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["id"], "1")
        self.assertEqual(result[1]["id"], "3")

    @patch('self_improvement.scripts.mack_cron_health_check.JOBS_PATH')
    def test_get_mack_crons_error(self, mock_jobs_path):
        mock_jobs_path.exists.return_value = True
        mock_jobs_path.read_text.side_effect = json.JSONDecodeError("Expecting value", "", 0)
        with patch('sys.stdout', new=StringIO()) as fake_out:
            result = mack_cron_health_check.get_mack_crons()
            self.assertEqual(result, [])
            self.assertIn("ERROR fetching Mack crons", fake_out.getvalue())

    def test_check_cron_status(self):
        timestamp = 1770944400000 # 2026-02-13T01:00:00Z
        cron = {"updatedAtMs": timestamp, "enabled": True}
        status = mack_cron_health_check.check_cron_status(cron)
        self.assertEqual(status["status"], "OK")
        self.assertEqual(status["timestamp"], "2026-02-13T01:00:00")
        self.assertTrue(status["enabled"])

    def test_check_cron_status_unknown(self):
        cron = {"enabled": False}
        status = mack_cron_health_check.check_cron_status(cron)
        self.assertEqual(status["status"], "UNKNOWN")
        self.assertIsNone(status["timestamp"])
        self.assertFalse(status["enabled"])

    @patch('self_improvement.scripts.mack_cron_health_check.get_mack_crons')
    def test_main_not_enough_crons(self, mock_get_crons):
        mock_get_crons.return_value = [{"id": "1", "name": "mack-loop"}]
        with patch('sys.stdout', new=StringIO()) as fake_out:
            result = mack_cron_health_check.main()
            self.assertEqual(result, 0)
            self.assertIn("WARN: <2 Mack crons found", fake_out.getvalue())

    @patch('self_improvement.scripts.mack_cron_health_check.get_mack_crons')
    @patch('self_improvement.scripts.mack_cron_health_check.random.sample')
    def test_main_ok(self, mock_sample, mock_get_crons):
        now = datetime.now(timezone.utc).timestamp() * 1000
        mock_crons = [
            {"id": "1", "name": "mack-1", "enabled": True, "updatedAtMs": now},
            {"id": "2", "name": "mack-2", "enabled": True, "updatedAtMs": now}
        ]
        mock_get_crons.return_value = mock_crons
        mock_sample.return_value = mock_crons
        
        with patch('sys.stdout', new=StringIO()) as fake_out:
            result = mack_cron_health_check.main()
            self.assertEqual(result, 0)
            self.assertIn("✓ Mack cron sample OK", fake_out.getvalue())

    @patch('self_improvement.scripts.mack_cron_health_check.get_mack_crons')
    @patch('self_improvement.scripts.mack_cron_health_check.random.sample')
    def test_main_stale_and_disabled(self, mock_sample, mock_get_crons):
        stale_ms = (datetime.now(timezone.utc) - timedelta(hours=3)).timestamp() * 1000
        mock_crons = [
            {"id": "1", "name": "mack-stale", "enabled": True, "updatedAtMs": stale_ms},
            {"id": "2", "name": "mack-disabled", "enabled": False}
        ]
        mock_get_crons.return_value = mock_crons
        mock_sample.return_value = mock_crons
        
        with patch('sys.stdout', new=StringIO()) as fake_out:
            result = mack_cron_health_check.main()
            self.assertEqual(result, 1)
            output = fake_out.getvalue()
            self.assertIn("CRON 1 (mack-stale): not updated in >2h", output)
            self.assertIn("CRON 2 (mack-disabled): disabled", output)

if __name__ == '__main__':
    unittest.main()
