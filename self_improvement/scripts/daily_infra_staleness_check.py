#!/usr/bin/env python3
"""daily_infra_staleness_check.py — Quick infrastructure health check.

Checks:
- memU server reachable (localhost:12345)
- Workspace writable
- Cron health (via cron_health_fixer --dry-run)
- Memory GC needed
- Output file count (warn if >200)

Usage:
  python3 daily_infra_staleness_check.py          # human output
  python3 daily_infra_staleness_check.py --json    # machine output
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

WORKSPACE = Path("/Users/harrisonfethe/.openclaw/workspace")
SCRIPTS = WORKSPACE / "self_improvement/scripts"
OUTPUTS = WORKSPACE / "self_improvement/outputs"


def check_memu() -> tuple[str, str]:
    try:
        out = subprocess.check_output(
            ["curl", "-s", "http://localhost:8711/api/v1/memu/health"],
            timeout=5
        ).decode()
        d = json.loads(out)
        return ("PASS", d.get("status", "unknown"))
    except (subprocess.SubprocessError, OSError, json.JSONDecodeError) as e:
        return ("FAIL", str(e)[:60])


def check_workspace() -> tuple[str, str]:
    test = WORKSPACE / ".write_test"
    try:
        test.write_text("ok")
        test.unlink()
        return ("PASS", "writable")
    except OSError as e:
        return ("FAIL", str(e)[:60])


def check_cron_health() -> tuple[str, str]:
    try:
        out = subprocess.check_output(
            [sys.executable, str(SCRIPTS / "cron_health_fixer.py"), "--json"],
            timeout=10
        ).decode()
        d = json.loads(out)
        n = d.get("fixed", 0)
        if n == 0:
            return ("PASS", "0 fixes needed")
        return ("WARN", f"{n} cron jobs need repair")
    except (subprocess.SubprocessError, json.JSONDecodeError) as e:
        return ("FAIL", str(e)[:60])


def check_memory_gc() -> tuple[str, str]:
    try:
        out = subprocess.check_output(
            [sys.executable, str(SCRIPTS / "agent_memory_cli.py"), "--no-rsync", "gc"],
            timeout=10
        ).decode().strip()
        return ("PASS", out)
    except subprocess.SubprocessError as e:
        return ("FAIL", str(e)[:60])


def check_output_count() -> tuple[str, str]:
    count = len(list(OUTPUTS.glob("*.md")))
    if count > 200:
        return ("WARN", f"{count} files (run archive)")
    return ("PASS", f"{count} files")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    checks = {
        "memU": check_memu(),
        "workspace": check_workspace(),
        "cron_health": check_cron_health(),
        "memory_gc": check_memory_gc(),
        "output_count": check_output_count(),
    }

    results = {k: {"status": v[0], "detail": v[1]} for k, v in checks.items()}
    overall = "FAIL" if any(v[0] == "FAIL" for v in checks.values()) else \
              "WARN" if any(v[0] == "WARN" for v in checks.values()) else "PASS"

    if args.json:
        print(json.dumps({"timestamp": datetime.now().isoformat(), "overall": overall, "checks": results}))
    else:
        icons = {"PASS": "✅", "WARN": "⚠️", "FAIL": "🔴"}
        print(f"Infrastructure Check: {icons.get(overall, '?')} {overall}")
        for name, (status, detail) in checks.items():
            print(f"  {icons.get(status, '?')} {name}: {detail}")

    return 0 if overall != "FAIL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
