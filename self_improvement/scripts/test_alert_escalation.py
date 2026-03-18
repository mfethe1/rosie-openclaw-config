import json
import os
import tempfile
import unittest
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Add the scripts directory to the Python path
import sys
sys.path.insert(0, str(Path(__file__).parent))

from alert_escalation import (
    Blocker,
    _parse_dt,
    _is_unresolved,
    find_stale_critical_blockers,
    filter_by_cooldown,
    build_message,
)

class TestAlertEscalation(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        
    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_parse_dt(self):
        dt = _parse_dt("2026-03-18T12:00:00Z")
        self.assertIsNotNone(dt)
        self.assertEqual(dt.tzinfo, timezone.utc)
        self.assertEqual(dt.hour, 12)

        dt = _parse_dt("2026-03-18T12:00:00")
        self.assertIsNotNone(dt)
        self.assertEqual(dt.tzinfo, timezone.utc)

        self.assertIsNone(_parse_dt(""))
        self.assertIsNone(_parse_dt(None))
        self.assertIsNone(_parse_dt("invalid"))

    def test_is_unresolved(self):
        self.assertTrue(_is_unresolved({"priority": "HIGH"}))
        self.assertFalse(_is_unresolved({"priority": "RESOLVED"}))
        self.assertFalse(_is_unresolved({"priority": "HIGH", "resolved_at": "2026-03-18T12:00:00Z"}))
        self.assertTrue(_is_unresolved({}))

    def test_find_stale_critical_blockers(self):
        shared_state_file = self.temp_dir / "shared-state.json"
        
        now = datetime.now(timezone.utc)
        old_time = (now - timedelta(hours=30)).isoformat()
        recent_time = (now - timedelta(hours=10)).isoformat()
        
        payload = {
            "active_blockers": [
                {"id": "b1", "priority": "CRITICAL", "owner": "Mack", "description": "stale critical", "raised_at": old_time},
                {"id": "b2", "priority": "HIGH", "owner": "Mack", "description": "recent high", "raised_at": recent_time},
                {"id": "b3", "priority": "MEDIUM", "owner": "Mack", "description": "stale medium", "raised_at": old_time},
                {"id": "b4", "priority": "CRITICAL", "owner": "Mack", "description": "resolved critical", "raised_at": old_time, "resolved_at": old_time},
                {"id": "b5", "priority": "HIGH", "owner": "Mack", "description": "stale high", "updated_at": old_time}
            ]
        }
        
        shared_state_file.write_text(json.dumps(payload))
        
        # Test with min_age_hours = 24
        blockers = find_stale_critical_blockers(shared_state_file, 24)
        
        self.assertEqual(len(blockers), 2)
        self.assertEqual(blockers[0].blocker_id, "b1")  # CRITICAL first
        self.assertEqual(blockers[1].blocker_id, "b5")  # HIGH second
        self.assertEqual(blockers[0].priority, "CRITICAL")
        self.assertEqual(blockers[1].priority, "HIGH")
        
    def test_filter_by_cooldown(self):
        state_file = self.temp_dir / "alert_state.json"
        
        now = datetime.now(timezone.utc)
        recently_alerted = (now - timedelta(hours=10)).isoformat()
        long_ago_alerted = (now - timedelta(hours=30)).isoformat()
        
        state_payload = {
            "last_alerted": {
                "b1": recently_alerted,
                "b2": long_ago_alerted
            }
        }
        state_file.write_text(json.dumps(state_payload))
        
        blockers = [
            Blocker(blocker_id="b1", priority="CRITICAL", owner="Mack", description="", age_hours=40, raised_at=None, updated_at=None),
            Blocker(blocker_id="b2", priority="HIGH", owner="Mack", description="", age_hours=50, raised_at=None, updated_at=None),
            Blocker(blocker_id="b3", priority="CRITICAL", owner="Mack", description="", age_hours=30, raised_at=None, updated_at=None)
        ]
        
        # Cooldown is 24 hours. b1 is in cooldown, b2 is out of cooldown, b3 is new.
        filtered = filter_by_cooldown(blockers, state_file, 24)
        
        self.assertEqual(len(filtered), 2)
        ids = [b.blocker_id for b in filtered]
        self.assertIn("b2", ids)
        self.assertIn("b3", ids)
        self.assertNotIn("b1", ids)

    def test_build_message(self):
        blockers = [
            Blocker(blocker_id=f"b{i}", priority="CRITICAL", owner="Mack", description=f"desc{i}", age_hours=30, raised_at=None, updated_at=None)
            for i in range(10)
        ]
        
        msg = build_message(blockers, 24)
        self.assertIn("10 HIGH/CRITICAL blockers unresolved", msg)
        self.assertIn("b0 [CRITICAL]", msg)
        self.assertIn("b7 [CRITICAL]", msg)
        self.assertNotIn("b8 [CRITICAL]", msg)  # Should be truncated
        self.assertIn("...and 2 more", msg)

if __name__ == '__main__':
    unittest.main()
