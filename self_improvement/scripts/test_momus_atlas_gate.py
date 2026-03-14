import os
import unittest
from momus_atlas_gate import verify_momus_plan

class TestMomusAtlasGate(unittest.TestCase):
    def test_empty_plan(self):
        is_valid, reason = verify_momus_plan("")
        self.assertFalse(is_valid)
        self.assertEqual(reason, "Plan is empty or too short.")

    def test_missing_actionable_steps(self):
        plan = "Objective: Do something.\n1. Step 1\n" * 10
        is_valid, reason = verify_momus_plan(plan)
        self.assertFalse(is_valid)
        self.assertEqual(reason, "Plan lacks 'Actionable Steps' section.")

    def test_missing_numbering(self):
        plan = "Objective: Do something.\nActionable Steps:\n- Step A\n- Step B\n" * 5
        is_valid, reason = verify_momus_plan(plan)
        self.assertFalse(is_valid)
        self.assertEqual(reason, "Plan steps are not numbered.")

    def test_missing_objective(self):
        plan = "Actionable Steps:\n1. Step A\n2. Step B\n" * 5
        is_valid, reason = verify_momus_plan(plan)
        self.assertFalse(is_valid)
        self.assertEqual(reason, "Plan lacks Context/Objective section.")

    def test_unresolved_placeholder(self):
        plan = "Objective: Do something.\nActionable Steps:\n1. Step A TODO\n2. Step B\n" * 5
        is_valid, reason = verify_momus_plan(plan)
        self.assertFalse(is_valid)
        self.assertEqual(reason, "Plan contains unresolved placeholders (TODO, TBD, etc.).")

    def test_valid_plan(self):
        plan = "Objective: Do something great.\nActionable Steps:\n1. Prepare environment.\n2. Execute task.\n" * 5
        is_valid, reason = verify_momus_plan(plan)
        self.assertTrue(is_valid)
        self.assertEqual(reason, "Momus plan validated successfully.")

if __name__ == '__main__':
    unittest.main()
