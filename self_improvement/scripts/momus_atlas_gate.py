#!/usr/bin/env python3
import sys
import json
import re

def verify_momus_plan(plan_text):
    """
    Validates a Momus plan before allowing Atlas to execute it.
    Returns (True, "OK") if valid, (False, reason) if invalid.
    """
    if not plan_text or len(plan_text) < 50:
        return False, "Plan is empty or too short."

    # Must contain explicit ACTIONABLE STEPS or similar headers
    if not re.search(r'(?i)(Actionable Steps|Execution Plan|Steps to Execute)', plan_text):
        return False, "Plan lacks 'Actionable Steps' section."

    # Must have a timeline or order
    if not re.search(r'\d+\.', plan_text):
        return False, "Plan steps are not numbered."

    # Must include context or rationale
    if not re.search(r'(?i)(Why|Context|Rationale|Objective)', plan_text):
        return False, "Plan lacks Context/Objective section."

    # Must not contain unresolved placeholders
    if 'TODO' in plan_text or 'TBD' in plan_text or '[ ]' in plan_text:
        return False, "Plan contains unresolved placeholders (TODO, TBD, etc.)."
        
    return True, "Momus plan validated successfully."

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 momus_atlas_gate.py <path_to_plan>")
        sys.exit(1)
        
    with open(sys.argv[1], 'r') as f:
        plan = f.read()
        
    is_valid, reason = verify_momus_plan(plan)
    
    if is_valid:
        print(f"PASS: {reason}")
        sys.exit(0)
    else:
        print(f"FAIL: {reason}")
        sys.exit(1)
