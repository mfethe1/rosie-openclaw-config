import os
import tempfile
import unittest
from todo_orphan_check import check_orphans

class TestTodoOrphanCheck(unittest.TestCase):
    def setUp(self):
        self.fd, self.path = tempfile.mkstemp()

    def tearDown(self):
        os.close(self.fd)
        if os.path.exists(self.path):
            os.remove(self.path)

    def write_todo(self, content: str):
        with open(self.path, "w") as f:
            f.write(content)

    def test_valid_agents(self):
        content = """## P2
- **[Mack]** Task 1
- [Winnie/Oracle] Task 2
- [ ] **[Lenny]** Task 3
"""
        self.write_todo(content)
        orphans = check_orphans(self.path)
        self.assertEqual(len(orphans), 0)

    def test_invalid_agent(self):
        content = """## P2
- [InvalidAgent] Task 1
"""
        self.write_todo(content)
        orphans = check_orphans(self.path)
        self.assertEqual(len(orphans), 1)
        self.assertEqual(orphans[0][2], "Unknown agent(s) in bracket: InvalidAgent")

    def test_ignore_closed_archived(self):
        content = """## Closed
- [InvalidAgent] Task 1
## Archived
- [Unknown] Task 2
"""
        self.write_todo(content)
        orphans = check_orphans(self.path)
        self.assertEqual(len(orphans), 0)

    def test_ignore_completed_tasks(self):
        content = """## P2
- ~~[InvalidAgent] Task 1~~
- [x] [Unknown] Task 2
"""
        self.write_todo(content)
        orphans = check_orphans(self.path)
        self.assertEqual(len(orphans), 0)

    def test_malformed_bracket(self):
        content = """## P2
- [ ] Task missing agent bracket
"""
        self.write_todo(content)
        orphans = check_orphans(self.path)
        # Should be ignored because it doesn't match the inner bracket or is missing assignment
        # It's not the goal of this specific check to catch ALL malformed tasks, just unknown agents in brackets.
        # But wait, does it catch missing assignment? The current logic skips if there's no bracket match or if match is " ".
        self.assertEqual(len(orphans), 0)

    def test_sub_bullets(self):
        content = """## P3
- **[Mack]** Parent task
  - Subtask without agent
"""
        self.write_todo(content)
        orphans = check_orphans(self.path)
        self.assertEqual(len(orphans), 0)

if __name__ == "__main__":
    unittest.main()
