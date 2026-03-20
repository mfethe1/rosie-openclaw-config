import json
import os
import unittest
from pathlib import Path
from unittest import mock

import cron_health_fixer

class TestCronHealthFixer(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = Path("/tmp/test_cron_health_fixer_dir")
        self.tmp_dir.mkdir(parents=True, exist_ok=True)
        self.jobs_file = self.tmp_dir / "jobs.json"
        self.shared_state = self.tmp_dir / "shared-state.json"
        
        self.patcher1 = mock.patch("cron_health_fixer.JOBS_FILE", self.jobs_file)
        self.patcher2 = mock.patch("cron_health_fixer.SHARED_STATE_FILE", self.shared_state)
        self.patcher1.start()
        self.patcher2.start()

    def tearDown(self):
        self.patcher1.stop()
        self.patcher2.stop()
        if self.jobs_file.exists():
            self.jobs_file.unlink()
        if self.shared_state.exists():
            self.shared_state.unlink()
        self.tmp_dir.rmdir()

    def test_extract_blocked_targets_empty(self):
        self.assertEqual(cron_health_fixer._extract_blocked_targets_from_shared_state(), set())

    def test_extract_blocked_targets(self):
        self.shared_state.write_text(json.dumps({
            "dependency_notes": {
                "delivery_failures_12345": "error",
                "other_key": "val",
                "delivery_failures_9999": "error"
            }
        }))
        self.assertEqual(
            cron_health_fixer._extract_blocked_targets_from_shared_state(),
            {"-12345", "-9999"}
        )

    def test_resolve_default_delivery_to(self):
        with mock.patch.dict(os.environ, {"OPENCLAW_DEFAULT_DELIVERY_TO": "-4444"}):
            self.assertEqual(cron_health_fixer._resolve_default_delivery_to(set()), "-4444")
            self.assertIsNone(cron_health_fixer._resolve_default_delivery_to({"-4444"}))

    def test_resolve_default_delivery_to_empty(self):
        with mock.patch.dict(os.environ, {"OPENCLAW_DEFAULT_DELIVERY_TO": ""}):
            self.assertIsNone(cron_health_fixer._resolve_default_delivery_to(set()))

    def test_fix_jobs_no_file(self):
        self.assertEqual(cron_health_fixer.fix_jobs(), [])

    def test_fix_jobs_fixes_applied(self):
        jobs_data = [
            {
                "name": "Hourly Self-Improvement",
                "enabled": False,
                "delivery": {"channel": "last", "mode": "announce", "to": "-12345"},
                "payload": {"model": "gemini-3-flash", "timeoutSeconds": 10}
            },
            {
                "name": "Other Job",
                "delivery": {"channel": "telegram", "to": "-1003753060481"}
            }
        ]
        self.jobs_file.write_text(json.dumps(jobs_data))
        
        self.shared_state.write_text(json.dumps({
            "dependency_notes": {"delivery_failures_12345": "blocked"}
        }))
        
        with mock.patch.dict(os.environ, {"OPENCLAW_DEFAULT_DELIVERY_TO": "-9999"}):
            fixes = cron_health_fixer.fix_jobs(dry_run=False)
            
        self.assertTrue(len(fixes) > 0)
        
        fixed_data = json.loads(self.jobs_file.read_text())
        job1 = fixed_data[0]
        self.assertTrue(job1["enabled"])
        self.assertEqual(job1["delivery"]["channel"], "telegram")
        self.assertEqual(job1["delivery"]["to"], "-9999")
        self.assertEqual(job1["payload"]["model"], "anthropic/claude-haiku-4-5")
        self.assertEqual(job1["payload"]["timeoutSeconds"], 45)
        
        job2 = fixed_data[1]
        self.assertEqual(job2["delivery"]["to"], "-9999")

    def test_fix_jobs_dry_run(self):
        original_json = json.dumps([{"name": "Hourly Self-Improvement", "enabled": False}])
        self.jobs_file.write_text(original_json)
        
        fixes = cron_health_fixer.fix_jobs(dry_run=True)
        self.assertTrue(len(fixes) > 0)
        self.assertEqual(self.jobs_file.read_text(), original_json)

    def test_fix_jobs_dict_format(self):
        jobs_data = {"jobs": [{"name": "Hourly Self-Improvement", "enabled": False}]}
        self.jobs_file.write_text(json.dumps(jobs_data))
        
        cron_health_fixer.fix_jobs(dry_run=False)
        
        fixed_data = json.loads(self.jobs_file.read_text())
        self.assertIsInstance(fixed_data, dict)
        self.assertTrue(fixed_data["jobs"][0]["enabled"])

if __name__ == '__main__':
    unittest.main()
