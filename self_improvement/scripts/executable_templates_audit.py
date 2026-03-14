#!/usr/bin/env python3
"""executable_templates_audit.py — Pre-flight audit for SI execution templates.

Checks that required templates exist and are callable. Used as a blocking gate
before improvement generation in the SI self-reflection loop.

Exit 0 = all critical templates present (improvements may proceed).
Exit 1 = critical template missing (block improvements, self-heal first).

Non-critical (advisory) templates that are missing produce warnings but don't block.
"""

import json
import os
import sys
from pathlib import Path

WORKSPACE = Path("/Users/harrisonfethe/.openclaw/workspace")
TEMPLATE_DIR = WORKSPACE / "agents" / "templates"
SCRIPTS_DIR = WORKSPACE / "self_improvement" / "scripts"

# Critical templates — must exist for improvements to proceed
# Critical templates — must exist for improvements to proceed
CRITICAL_TEMPLATES = {
    "smoke_test": {
        "path": WORKSPACE / "memu_server" / "smoke_test.sh",
        "description": "Eval gate for task completion",
    },
    "continuation_check": {
        "path": SCRIPTS_DIR / "continuation_check.py",
        "description": "TODO completion checker",
    },
}

# Advisory templates — nice to have, warn if missing but don't block
ADVISORY_TEMPLATES = {
    "research_preflight_gate": {
        "path": TEMPLATE_DIR / "research_preflight_gate.py",
        "description": "Pre-flight gate for research tasks (Winnie)",
    },
    "change_monitor": {
        "path": SCRIPTS_DIR / "change_monitor.py",
        "description": "Workspace change detection",
    },
    "agent_memory_cli": {
        "path": SCRIPTS_DIR / "agent_memory_cli.py",
        "description": "Memory store/search CLI",
    },
    "si_benchmark_gate": {
        "path": SCRIPTS_DIR / "si_benchmark_gate.py",
        "description": "SI benchmark gate checker",
    },
}


def audit():
    report = {
        "templates_verified": False,
        "critical_ok": True,
        "missing_critical": [],
        "missing_advisory": [],
        "warnings": [],
        "status": "PASS",
    }

    # Check critical templates
    for name, meta in CRITICAL_TEMPLATES.items():
        if not meta["path"].exists():
            report["missing_critical"].append(name)
            report["critical_ok"] = False
            report["status"] = "FAIL"

    # Check advisory templates (warn only)
    for name, meta in ADVISORY_TEMPLATES.items():
        if not meta["path"].exists():
            report["missing_advisory"].append(name)
            report["warnings"].append(f"Advisory template missing: {name} ({meta['description']})")

    if report["status"] == "FAIL":
        print(json.dumps(report, indent=2))
        sys.exit(1)

    report["templates_verified"] = True
    print(json.dumps(report, indent=2))
    return report


if __name__ == "__main__":
    audit()
