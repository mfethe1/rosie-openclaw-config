import unittest
from shared_state_validator import validate_data

class TestSharedStateValidator(unittest.TestCase):
    def test_validate_data_success(self):
        valid_data = {
            "last_run": "2026-03-16T01:09:00.000000Z",
            "what_changed": "Testing",
            "next_owner": "Mack",
            "blockers": [],
            "hypotheses": ["Test hypothesis"],
            "broadcasts": [],
            "last_updated": "2026-03-16T01:09:00.000000Z",
            "last_updated_by": "Mack"
        }
        is_valid, msg = validate_data(valid_data)
        self.assertTrue(is_valid)
        self.assertIn("SUCCESS", msg)

    def test_validate_data_missing_keys(self):
        invalid_data = {
            "last_run": "2026-03-16T01:09:00.000000Z",
            # what_changed missing
            "next_owner": "Mack",
            "blockers": [],
            "hypotheses": ["Test hypothesis"],
            "broadcasts": [],
            "last_updated": "2026-03-16T01:09:00.000000Z"
            # last_updated_by missing
        }
        is_valid, msg = validate_data(invalid_data)
        self.assertFalse(is_valid)
        self.assertIn("HARD FAIL", msg)
        self.assertIn("what_changed", msg)
        self.assertIn("last_updated_by", msg)

    def test_validate_data_invalid_type(self):
        invalid_data = {
            "last_run": "2026-03-16T01:09:00.000000Z",
            "what_changed": 123,  # Should be str
            "next_owner": "Mack",
            "blockers": "Not a list",  # Should be list
            "hypotheses": ["Test hypothesis"],
            "broadcasts": [],
            "last_updated": "2026-03-16T01:09:00.000000Z",
            "last_updated_by": "Mack"
        }
        is_valid, msg = validate_data(invalid_data)
        self.assertFalse(is_valid)
        self.assertIn("HARD FAIL", msg)
        self.assertIn("what_changed", msg)
        self.assertIn("blockers", msg)

    def test_validate_data_none_allowed(self):
        valid_data_none = {
            "last_run": "2026-03-16T01:09:00.000000Z",
            "what_changed": "Testing",
            "next_owner": "Mack",
            "blockers": None,  # None is allowed
            "hypotheses": None, # None is allowed
            "broadcasts": [],
            "last_updated": "2026-03-16T01:09:00.000000Z",
            "last_updated_by": "Mack"
        }
        is_valid, msg = validate_data(valid_data_none)
        self.assertTrue(is_valid)
        self.assertIn("SUCCESS", msg)

if __name__ == '__main__':
    unittest.main()
