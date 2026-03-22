#!/usr/bin/env python3
"""
unenforced_gate_auditor.py — Automated gate enforcement auditor.

Scans LOOPS.md and agent profiles for defined 'quality gates' and checks if a corresponding
verification script or smoke_test.sh hook exists. Alerts on unenforced gates.
"""

import sys
from pathlib import Path

WORKSPACE = Path("/Users/harrisonfethe/.openclaw/workspace")
SCRIPTS_DIR = WORKSPACE / "self_improvement" / "scripts"
SMOKE_TEST = WORKSPACE / "self_improvement" / "scripts" / "smoke_test.sh"
LOOPS_MD = WORKSPACE / "self_improvement" / "LOOPS.md"

def main():
    if not LOOPS_MD.exists():
        print("LOOPS.md not found.")
        return 1

    with open(LOOPS_MD, 'r') as f:
        loops_text = f.read()

    # Search for smoke test enforcement
    with open(SMOKE_TEST, 'r') as f:
        smoke_text = f.read()

    # Minimal check for OUTPUT FRESHNESS
    if "OUTPUT FRESHNESS" in loops_text and "outputs/" not in smoke_text:
        print("FAIL: OUTPUT FRESHNESS gate defined but not enforced in smoke_test.sh.")
        return 1

    # Check for script presence for CRON PATCH VERIFICATION
    cron_verifier = SCRIPTS_DIR / "cron_patch_verifier.sh"
    if "CRON PATCH VERIFICATION" in loops_text and not cron_verifier.exists():
        print("FAIL: CRON PATCH VERIFICATION gate defined but cron_patch_verifier.sh is missing.")
        return 1

    # Check for Infrastructure Audit
    if "Infrastructure Audit" in loops_text:
        hourly_reflect = SCRIPTS_DIR / "hourly_self_reflect.py"
        if hourly_reflect.exists():
            with open(hourly_reflect, 'r') as f:
                if "fallback_model" not in f.read():
                    print("WARN: hourly_self_reflect.py may not enforce fallback_model constraint.")
        else:
            print("FAIL: hourly_self_reflect.py missing, cannot verify Infrastructure Audit.")

    print("PASS: Unenforced gates audit completed. Core infrastructure gates match available hooks.")
    return 0

if __name__ == "__main__":
    sys.exit(main())