import unittest
import os
import tempfile
from decision_tracker import track_decisions

class TestDecisionTracker(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.todo_path = os.path.join(self.temp_dir.name, "TODO.md")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_track_decisions_implemented(self):
        with open(self.todo_path, "w") as f:
            f.write("- [x] Handle decision D-001 completely\n")
            f.write("- [x] Resolve D-002 issue\n")
        
        implemented, unimplemented, other = track_decisions(self.todo_path)
        self.assertIn("D-001", implemented)
        self.assertIn("D-002", implemented)
        self.assertEqual(len(unimplemented), 0)
        self.assertEqual(len(other), 0)

    def test_track_decisions_unimplemented(self):
        with open(self.todo_path, "w") as f:
            f.write("- [ ] Handle decision D-003 next\n")
            f.write("- [ ] Draft D-004 logic\n")
        
        implemented, unimplemented, other = track_decisions(self.todo_path)
        self.assertEqual(len(implemented), 0)
        self.assertIn("D-003", unimplemented)
        self.assertIn("D-004", unimplemented)
        self.assertEqual(len(other), 0)

    def test_track_decisions_other(self):
        with open(self.todo_path, "w") as f:
            f.write("Note: D-005 is deprecated.\n")
            f.write("D-006 should be reviewed.\n")
            
        implemented, unimplemented, other = track_decisions(self.todo_path)
        self.assertEqual(len(implemented), 0)
        self.assertEqual(len(unimplemented), 0)
        self.assertIn("D-005", other)
        self.assertIn("D-006", other)

    def test_track_decisions_multiple_states(self):
        with open(self.todo_path, "w") as f:
            f.write("- [ ] Discuss D-007\n")
            f.write("- [x] Finish D-007\n")
        
        implemented, unimplemented, other = track_decisions(self.todo_path)
        # If any is implemented, it counts as implemented and removes from unimplemented
        self.assertIn("D-007", implemented)
        self.assertNotIn("D-007", unimplemented)
        self.assertEqual(len(other), 0)

if __name__ == "__main__":
    unittest.main()
