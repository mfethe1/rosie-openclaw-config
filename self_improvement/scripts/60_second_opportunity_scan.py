#!/usr/bin/env python3
import sys
import subprocess
from pathlib import Path

def scan_opportunities():
    print("Running 60-second opportunity scan...")
    opportunities = []

    # 1. Look for unresolved FIXME or TODO comments in scripts
    scripts_dir = Path("self_improvement/scripts")
    try:
        result = subprocess.run(
            ['grep', '-rn', '--include=*.py', '-E', '(FIXME|TODO)\\s*:', str(scripts_dir)],
            capture_output=True, text=True
        )
        if result.returncode == 0 and result.stdout:
            lines = result.stdout.strip().split('\n')
            opportunities.append(f"Found {len(lines)} FIXME/TODO markers in {scripts_dir}")
    except (subprocess.SubprocessError, OSError) as e:
        print(f"Error scanning for FIXMEs: {e}")

    # 2. Check for missing error handling or overly broad excepts
    try:
        cmd = f"grep -rn --include=*.py 'except Exception:' {scripts_dir} | grep -v '60_second_opportunity_scan.py'"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0 and result.stdout:
            lines = result.stdout.strip().split('\n')
            opportunities.append(f"Found {len(lines)} broad 'except Exception:' clauses that could be refined.")
    except (subprocess.SubprocessError, OSError) as e:
        print(f"Error scanning for broad excepts: {e}")

    # 3. Look for recent failing tests (mock check here, assuming we check a log)
    smoke_test_log = Path("self_improvement/smoke_test.log")
    if smoke_test_log.exists():
        with open(smoke_test_log) as f:
            if 'FAIL' in f.read():
                opportunities.append("Recent smoke test logged a FAIL. Needs investigation.")

    return opportunities

if __name__ == "__main__":
    ops = scan_opportunities()
    if not ops:
        print("No immediate 60-second opportunities found.")
        sys.exit(0)
    else:
        print("\n=== OPPORTUNITIES DETECTED ===")
        for op in ops:
            print(f"  * {op}")
        sys.exit(3)
