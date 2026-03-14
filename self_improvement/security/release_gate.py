#!/usr/bin/env python3
"""
release_gate.py — Production Release Gate
Runs all security and consensus checks before any code path goes to production.

CLI:
  python3 release_gate.py check <target_dir>  — full gate check
  python3 release_gate.py report              — show last gate result
  python3 release_gate.py --test              — self-test
"""

import sys
import json
import subprocess
import os
import glob
import datetime
import pathlib
import tempfile

SCRIPT_DIR = pathlib.Path(__file__).parent.resolve()
LAST_REPORT_PATH = SCRIPT_DIR / "logs" / "last_gate_report.json"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run(cmd: list[str], cwd: str | None = None) -> tuple[int, str, str]:
    """Run a subprocess and return (returncode, stdout, stderr)."""
    result = subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
    )
    return result.returncode, result.stdout, result.stderr


def _save_report(report: dict) -> None:
    LAST_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(LAST_REPORT_PATH, "w") as f:
        json.dump(report, f, indent=2)


# ---------------------------------------------------------------------------
# Individual checks
# ---------------------------------------------------------------------------

def check_ast_scan(target_dir: str) -> dict:
    """Run skill_auditor.py on the target directory. FAIL on HIGH severity."""
    auditor = SCRIPT_DIR / "skill_auditor.py"
    if not auditor.exists():
        return {"name": "ast_scan", "status": "skip", "details": "skill_auditor.py not found"}

    rc, stdout, stderr = _run(
        [sys.executable, str(auditor), target_dir, "--json"],
    )

    # Try to parse JSON output from auditor
    findings = []
    try:
        data = json.loads(stdout)
        if isinstance(data, list):
            findings = data
        elif isinstance(data, dict):
            findings = data.get("findings", [])
    except (json.JSONDecodeError, ValueError):
        # Fall back to text scan for "HIGH" keyword
        combined = stdout + stderr
        if "HIGH" in combined:
            return {
                "name": "ast_scan",
                "status": "fail",
                "details": f"HIGH severity finding detected (text scan). rc={rc}",
            }
        if rc != 0:
            return {
                "name": "ast_scan",
                "status": "fail",
                "details": f"auditor exited {rc}: {stderr[:300]}",
            }
        return {"name": "ast_scan", "status": "pass", "details": "No HIGH findings (text scan)"}

    high_findings = [f for f in findings if str(f.get("severity", "")).upper() == "HIGH"]
    if high_findings:
        return {
            "name": "ast_scan",
            "status": "fail",
            "details": f"{len(high_findings)} HIGH severity finding(s): {json.dumps(high_findings[:3])}",
        }
    return {
        "name": "ast_scan",
        "status": "pass",
        "details": f"{len(findings)} finding(s), none HIGH",
    }


def check_docker_audit(target_dir: str) -> dict:
    """Run docker_security.py audit on any Dockerfiles found. FAIL if missing USER nonroot or cap-drop."""
    docker_script = SCRIPT_DIR / "docker_security.py"
    dockerfiles = glob.glob(os.path.join(target_dir, "**/Dockerfile*"), recursive=True)

    if not dockerfiles:
        return {"name": "docker_audit", "status": "skip", "details": "No Dockerfiles found"}

    if not docker_script.exists():
        return {"name": "docker_audit", "status": "skip", "details": "docker_security.py not found"}

    failures = []
    for df in dockerfiles:
        rc, stdout, stderr = _run(
            [sys.executable, str(docker_script), "audit", df],
        )
        combined = (stdout + stderr).lower()
        if rc != 0 or "missing user nonroot" in combined or "missing cap-drop" in combined or "fail" in combined:
            failures.append(f"{df}: {(stdout+stderr)[:200]}")

    if failures:
        return {
            "name": "docker_audit",
            "status": "fail",
            "details": "; ".join(failures),
        }
    return {
        "name": "docker_audit",
        "status": "pass",
        "details": f"{len(dockerfiles)} Dockerfile(s) passed",
    }


def check_state_machine(target_dir: str) -> dict:
    """Run state_machine_validator.py on XML state machine files. FAIL on invalid transitions."""
    validator = SCRIPT_DIR / "state_machine_validator.py"
    xml_files = glob.glob(os.path.join(target_dir, "**/*.xml"), recursive=True)

    if not xml_files:
        return {"name": "state_machine", "status": "skip", "details": "No XML files found"}

    if not validator.exists():
        return {"name": "state_machine", "status": "skip", "details": "state_machine_validator.py not found"}

    failures = []
    for xf in xml_files:
        rc, stdout, stderr = _run(
            [sys.executable, str(validator), xf],
        )
        combined = stdout + stderr
        if rc != 0 or "invalid" in combined.lower() or "error" in combined.lower():
            failures.append(f"{xf}: {combined[:200]}")

    if failures:
        return {
            "name": "state_machine",
            "status": "fail",
            "details": "; ".join(failures),
        }
    return {
        "name": "state_machine",
        "status": "pass",
        "details": f"{len(xml_files)} XML file(s) validated",
    }


def check_bccs_consensus(target_dir: str) -> dict:
    """Check BCCS verification result. FAIL if decision != 'commit' or no verification done."""
    # Look for verification result in common locations
    candidate_paths = [
        os.path.join(target_dir, "bccs_result.json"),
        os.path.join(target_dir, "verification_result.json"),
        os.path.join(SCRIPT_DIR, "logs", "bccs_last_result.json"),
    ]

    result_file = None
    for p in candidate_paths:
        if os.path.exists(p):
            result_file = p
            break

    if result_file is None:
        return {
            "name": "bccs_consensus",
            "status": "fail",
            "details": "No BCCS verification result found. Run BCCS verification before release.",
        }

    try:
        with open(result_file) as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        return {"name": "bccs_consensus", "status": "fail", "details": f"Could not read result: {e}"}

    decision = data.get("decision", "").lower()
    mu = data.get("mu", data.get("confidence", 0.0))

    if decision == "reject":
        return {
            "name": "bccs_consensus",
            "status": "fail",
            "details": f"BCCS decision=reject (μ={mu:.3f})",
        }
    if decision != "commit":
        return {
            "name": "bccs_consensus",
            "status": "fail",
            "details": f"BCCS decision='{decision}' (expected 'commit', μ={mu:.3f})",
        }
    if float(mu) < 0.82:
        return {
            "name": "bccs_consensus",
            "status": "fail",
            "details": f"BCCS μ={mu:.3f} below threshold 0.82 (decision={decision})",
        }
    return {
        "name": "bccs_consensus",
        "status": "pass",
        "details": f"decision={decision}, μ={mu:.3f}",
    }


def check_test_suite(target_dir: str) -> dict:
    """Run pytest on target_dir. FAIL if any tests fail."""
    # First try pytest
    rc, stdout, stderr = _run(
        [sys.executable, "-m", "pytest", target_dir, "-q", "--tb=short"],
        cwd=target_dir,
    )

    if rc == 5:
        # pytest exit code 5 = no tests found — run --test on all scripts instead
        py_scripts = glob.glob(os.path.join(target_dir, "*.py"))
        script_failures = []
        script_passes = []

        for script in py_scripts:
            src_rc, src_out, src_err = _run(
                [sys.executable, script, "--test"],
            )
            if src_rc != 0:
                script_failures.append(f"{os.path.basename(script)}: {(src_out+src_err)[:150]}")
            else:
                script_passes.append(os.path.basename(script))

        if script_failures:
            return {
                "name": "test_suite",
                "status": "fail",
                "details": f"--test failures: {'; '.join(script_failures)}",
            }
        if script_passes:
            return {
                "name": "test_suite",
                "status": "pass",
                "details": f"--test passed on: {', '.join(script_passes)}",
            }
        return {"name": "test_suite", "status": "skip", "details": "No tests found"}

    if rc != 0:
        return {
            "name": "test_suite",
            "status": "fail",
            "details": f"pytest exited {rc}: {(stdout+stderr)[:400]}",
        }
    return {
        "name": "test_suite",
        "status": "pass",
        "details": (stdout.strip().splitlines()[-1] if stdout.strip() else "pytest passed"),
    }


# ---------------------------------------------------------------------------
# Gate runner
# ---------------------------------------------------------------------------

def run_gate(target_dir: str) -> dict:
    target_dir = os.path.abspath(target_dir)
    if not os.path.isdir(target_dir):
        report = {
            "gate": "fail",
            "checks": [{"name": "setup", "status": "fail", "details": f"Target directory not found: {target_dir}"}],
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        }
        _save_report(report)
        return report

    checks = [
        check_ast_scan(target_dir),
        check_docker_audit(target_dir),
        check_state_machine(target_dir),
        check_bccs_consensus(target_dir),
        check_test_suite(target_dir),
    ]

    gate = "pass" if all(c["status"] in ("pass", "skip") for c in checks) else "fail"

    report = {
        "gate": gate,
        "checks": checks,
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "target_dir": target_dir,
    }
    _save_report(report)
    return report


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

def _self_test() -> None:
    print("Running release_gate self-tests...")
    errors = []

    # Test 1: nonexistent dir → gate fail
    report = run_gate("/nonexistent_dir_abc123")
    assert report["gate"] == "fail", "Expected fail for missing dir"
    print("  [PASS] Missing dir → gate=fail")

    # Test 2: temp dir with no files → all skip/fail (bccs has no result)
    with tempfile.TemporaryDirectory() as td:
        report = run_gate(td)
        statuses = {c["name"]: c["status"] for c in report["checks"]}
        # ast_scan: skip (no auditor or no findings), docker: skip, state_machine: skip, bccs: fail, test: skip
        assert statuses["docker_audit"] == "skip", f"Expected docker skip, got {statuses['docker_audit']}"
        assert statuses["state_machine"] == "skip", f"Expected sm skip, got {statuses['state_machine']}"
        assert statuses["bccs_consensus"] == "fail", f"Expected bccs fail, got {statuses['bccs_consensus']}"
        print("  [PASS] Empty dir → docker/state_machine skip, bccs fail")

    # Test 3: temp dir with valid bccs result
    with tempfile.TemporaryDirectory() as td:
        bccs = {"decision": "commit", "mu": 0.91}
        with open(os.path.join(td, "bccs_result.json"), "w") as f:
            json.dump(bccs, f)
        report = run_gate(td)
        statuses = {c["name"]: c["status"] for c in report["checks"]}
        assert statuses["bccs_consensus"] == "pass", f"Expected bccs pass, got {statuses['bccs_consensus']}"
        print("  [PASS] Valid bccs result → bccs pass")

    # Test 4: temp dir with reject bccs
    with tempfile.TemporaryDirectory() as td:
        bccs = {"decision": "reject", "mu": 0.65}
        with open(os.path.join(td, "bccs_result.json"), "w") as f:
            json.dump(bccs, f)
        report = run_gate(td)
        statuses = {c["name"]: c["status"] for c in report["checks"]}
        assert statuses["bccs_consensus"] == "fail", f"Expected bccs fail for reject"
        print("  [PASS] Reject bccs → bccs fail")

    # Test 5: report output is valid JSON
    report_str = json.dumps(report)
    parsed = json.loads(report_str)
    assert "gate" in parsed and "checks" in parsed and "timestamp" in parsed
    print("  [PASS] Report structure valid")

    if errors:
        print(f"\nFAILED: {errors}")
        sys.exit(1)
    else:
        print("\nAll release_gate self-tests PASSED.")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    args = sys.argv[1:]

    if not args or "--test" in args:
        _self_test()
        return

    command = args[0]

    if command == "check":
        if len(args) < 2:
            print("Usage: python3 release_gate.py check <target_dir>", file=sys.stderr)
            sys.exit(1)
        target = args[1]
        report = run_gate(target)
        print(json.dumps(report, indent=2))
        sys.exit(0 if report["gate"] == "pass" else 1)

    elif command == "report":
        if not LAST_REPORT_PATH.exists():
            print(json.dumps({"error": "No gate report found. Run: release_gate.py check <dir>"}))
            sys.exit(1)
        with open(LAST_REPORT_PATH) as f:
            print(f.read())

    else:
        print(f"Unknown command: {command}", file=sys.stderr)
        print("Usage: release_gate.py check <dir> | report | --test", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
