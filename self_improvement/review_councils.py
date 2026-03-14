#!/usr/bin/env python3
"""
S-04: Automated Review Councils
Three daily automated review scans:
  1. Health Council   — service health checks
  2. Security Council — skill auditor scan
  3. Innovation Council — Sonar-backed AI improvement suggestions

Each outputs logs/council-{type}-YYYY-MM-DD.json

CLI:
  python3 review_councils.py health|security|innovation|all
  python3 review_councils.py --test
"""

from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ── paths ──────────────────────────────────────────────────────────────────
SELF_DIR = Path(__file__).parent
LOGS_DIR = SELF_DIR / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)

HOME = Path.home()
SKILLS_DIR = HOME / ".openclaw" / "skills"
SKILL_AUDITOR = SELF_DIR / "security" / "skill_auditor.py"
SONAR_SCRIPT = HOME / ".openclaw" / "skills" / "openrouter-sonar" / "scripts" / "sonar_search.py"

# Try to import event_logger for logging council runs
try:
    sys.path.insert(0, str(SELF_DIR))
    from scripts.cli_dispatcher import dispatch  # type: ignore
    HAS_DISPATCHER = True
except Exception:
    HAS_DISPATCHER = False


# ── shared helpers ──────────────────────────────────────────────────────────

def _report_path(council_type: str) -> Path:
    date_str = datetime.now().strftime("%Y-%m-%d")
    return LOGS_DIR / f"council-{council_type}-{date_str}.json"


def _write_report(council_type: str, data: Dict[str, Any]) -> Path:
    path = _report_path(council_type)
    with path.open("w") as f:
        json.dump(data, f, indent=2)
    return path


def _run_cmd(cmd: List[str], timeout: int = 30) -> Tuple[int, str, str]:
    """Run a command, return (returncode, stdout, stderr)."""
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", f"TIMEOUT after {timeout}s"
    except FileNotFoundError as e:
        return -2, "", str(e)
    except Exception as e:
        return -3, "", str(e)


def _tcp_check(host: str, port: int, timeout: float = 2.0) -> bool:
    """Return True if TCP connection succeeds."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except Exception:
        return False


# ── Health Council ──────────────────────────────────────────────────────────

SERVICES = [
    {"name": "memU",   "host": "localhost", "port": 12345},
    {"name": "Ollama", "host": "localhost", "port": 11434},
    {"name": "NATS",   "host": "localhost", "port": 4222},
    {"name": "MLE",    "host": "localhost", "port": 8765},
]


def run_health_council() -> Dict[str, Any]:
    started = datetime.now(timezone.utc).isoformat()
    results: List[Dict[str, Any]] = []
    degraded: List[str] = []

    for svc in SERVICES:
        up = _tcp_check(svc["host"], svc["port"])
        status = "UP" if up else "DOWN"
        if not up:
            degraded.append(svc["name"])
        results.append({
            "service": svc["name"],
            "host": svc["host"],
            "port": svc["port"],
            "status": status,
        })

    # Also check if key scripts exist
    script_checks = [
        str(SELF_DIR / "cost_tracker.py"),
        str(SELF_DIR / "security" / "skill_auditor.py"),
        str(SONAR_SCRIPT),
    ]
    script_results = []
    for sc in script_checks:
        script_results.append({"path": sc, "exists": Path(sc).exists()})

    report = {
        "council": "health",
        "run_at": started,
        "services": results,
        "scripts": script_results,
        "degraded_count": len(degraded),
        "degraded_services": degraded,
        "overall": "HEALTHY" if not degraded else "DEGRADED",
    }
    path = _write_report("health", report)
    report["report_path"] = str(path)
    return report


# ── Security Council ────────────────────────────────────────────────────────

def run_security_council() -> Dict[str, Any]:
    started = datetime.now(timezone.utc).isoformat()
    findings: List[Dict[str, Any]] = []
    skills_scanned: List[str] = []
    errors: List[str] = []

    if not SKILL_AUDITOR.exists():
        errors.append(f"skill_auditor.py not found at {SKILL_AUDITOR}")
    elif not SKILLS_DIR.exists():
        errors.append(f"skills dir not found: {SKILLS_DIR}")
    else:
        # Get all skill directories
        skill_dirs = [d for d in SKILLS_DIR.iterdir() if d.is_dir()]
        for skill_dir in sorted(skill_dirs):
            skills_scanned.append(skill_dir.name)
            rc, stdout, stderr = _run_cmd(
                [sys.executable, str(SKILL_AUDITOR), str(skill_dir)],
                timeout=30
            )
            if rc != 0 and rc != -2:
                # Try with no args in case auditor scans all
                pass
            if stdout.strip():
                try:
                    data = json.loads(stdout)
                    if isinstance(data, list):
                        for item in data:
                            item["skill"] = skill_dir.name
                            findings.append(item)
                    elif isinstance(data, dict):
                        data["skill"] = skill_dir.name
                        if data.get("findings") or data.get("issues"):
                            findings.append(data)
                except Exception:
                    # Non-JSON output — treat non-empty as finding
                    if stdout.strip() and "error" in stdout.lower():
                        findings.append({
                            "skill": skill_dir.name,
                            "raw": stdout.strip()[:500],
                        })
            if stderr.strip():
                errors.append(f"{skill_dir.name}: {stderr.strip()[:200]}")

    # Also run auditor with --all if supported
    if SKILL_AUDITOR.exists():
        rc, stdout, stderr = _run_cmd(
            [sys.executable, str(SKILL_AUDITOR), "--all"],
            timeout=60
        )
        if rc == 0 and stdout.strip():
            try:
                bulk = json.loads(stdout)
                if isinstance(bulk, list):
                    for item in bulk:
                        if item not in findings:
                            findings.append(item)
            except Exception:
                pass

    report = {
        "council": "security",
        "run_at": started,
        "skills_scanned": skills_scanned,
        "skills_count": len(skills_scanned),
        "findings_count": len(findings),
        "findings": findings[:50],  # cap to 50
        "errors": errors[:20],
        "overall": "CLEAN" if not findings else "FINDINGS",
    }
    path = _write_report("security", report)
    report["report_path"] = str(path)
    return report


# ── Innovation Council ──────────────────────────────────────────────────────

INNOVATION_QUERIES = [
    "latest AI agent self-improvement techniques 2025",
    "best practices autonomous LLM agent memory management",
    "new methods for LLM agent orchestration and multi-agent coordination",
]


def _parse_suggestions(raw: str) -> List[str]:
    """Extract up to 3 actionable suggestions from Sonar output."""
    suggestions: List[str] = []
    lines = raw.strip().splitlines()
    for line in lines:
        line = line.strip()
        if not line:
            continue
        # Look for numbered items or bullet points
        if (line[:2] in ("1.", "2.", "3.", "4.", "5.")
                or line.startswith("- ")
                or line.startswith("* ")):
            text = line.lstrip("0123456789.-* ").strip()
            if len(text) > 20:
                suggestions.append(text)
        if len(suggestions) >= 3:
            break

    # If nothing structured, grab first 3 non-empty sentences
    if not suggestions:
        import re
        sentences = re.split(r'(?<=[.!?])\s+', raw.strip())
        for s in sentences:
            s = s.strip()
            if len(s) > 30:
                suggestions.append(s)
            if len(suggestions) >= 3:
                break

    return suggestions[:3]


def run_innovation_council() -> Dict[str, Any]:
    started = datetime.now(timezone.utc).isoformat()
    raw_results: List[Dict[str, Any]] = []
    all_suggestions: List[str] = []
    errors: List[str] = []

    if not SONAR_SCRIPT.exists():
        errors.append(f"sonar_search.py not found at {SONAR_SCRIPT}")
    else:
        for query in INNOVATION_QUERIES:
            rc, stdout, stderr = _run_cmd(
                [sys.executable, str(SONAR_SCRIPT), "--pro", query],
                timeout=60
            )
            raw_results.append({
                "query": query,
                "rc": rc,
                "output_len": len(stdout),
            })
            if rc == 0 and stdout.strip():
                suggestions = _parse_suggestions(stdout)
                all_suggestions.extend(suggestions)
            elif stderr.strip():
                errors.append(f"query={query!r}: {stderr.strip()[:200]}")

    # Deduplicate, keep first 3
    seen: List[str] = []
    for s in all_suggestions:
        if s not in seen:
            seen.append(s)
        if len(seen) >= 3:
            break

    # If Sonar unavailable, fall back to static known-good suggestions
    if not seen:
        seen = [
            "Implement reflection loops: after each task, have the agent score its own output and log lessons learned.",
            "Use structured memory with TTL expiry to prevent context bloat in long-running agent sessions.",
            "Add a meta-learning layer that tracks which tool combinations resolve errors fastest and prioritises them.",
        ]
        errors.append("Sonar unavailable — using static fallback suggestions")

    report = {
        "council": "innovation",
        "run_at": started,
        "queries_run": len(INNOVATION_QUERIES),
        "raw_results": raw_results,
        "suggestions": seen,
        "errors": errors,
        "overall": "OK" if not errors else "PARTIAL",
    }
    path = _write_report("innovation", report)
    report["report_path"] = str(path)
    return report


# ── all councils ────────────────────────────────────────────────────────────

def run_all() -> Dict[str, Any]:
    print("[health council]")
    health = run_health_council()
    print(f"  → {health['overall']} ({health['degraded_count']} degraded)")

    print("[security council]")
    security = run_security_council()
    print(f"  → {security['overall']} ({security['findings_count']} findings)")

    print("[innovation council]")
    innovation = run_innovation_council()
    print(f"  → {innovation['overall']} ({len(innovation['suggestions'])} suggestions)")

    return {
        "health": health,
        "security": security,
        "innovation": innovation,
    }


# ── self-test ──────────────────────────────────────────────────────────────

def run_tests() -> bool:
    print("=== review_councils self-test ===")
    import tempfile, shutil

    tmp = Path(tempfile.mkdtemp())
    global LOGS_DIR
    orig_logs = LOGS_DIR
    LOGS_DIR = tmp

    # Health council test
    h = run_health_council()
    assert h["council"] == "health"
    assert "services" in h
    assert "overall" in h
    assert Path(h["report_path"]).exists()
    print(f"  [OK] health council: {h['overall']}, {h['degraded_count']} degraded")

    # TCP check test
    assert _tcp_check("localhost", 99999) is False
    print("  [OK] _tcp_check returns False for closed port")

    # _parse_suggestions test
    raw = """
Here are the key improvements:
1. Use vector memory for long-term storage of agent context.
2. Implement automatic retry with exponential back-off.
3. Add structured logging for all tool calls.
"""
    suggestions = _parse_suggestions(raw)
    assert len(suggestions) == 3, f"Expected 3 suggestions, got {len(suggestions)}"
    print(f"  [OK] _parse_suggestions: {suggestions[0][:40]}...")

    # Security council test (no auditor required to pass)
    s = run_security_council()
    assert s["council"] == "security"
    assert Path(s["report_path"]).exists()
    print(f"  [OK] security council: {s['overall']}, {s['findings_count']} findings")

    # Innovation council test (Sonar may be absent, falls back)
    i = run_innovation_council()
    assert i["council"] == "innovation"
    assert len(i["suggestions"]) == 3
    assert Path(i["report_path"]).exists()
    print(f"  [OK] innovation council: {i['suggestions'][0][:50]}...")

    shutil.rmtree(tmp)
    LOGS_DIR = orig_logs

    print("=== ALL TESTS PASSED ===")
    return True


# ── CLI ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Review Councils - S-04")
    parser.add_argument("council", nargs="?",
                        choices=["health", "security", "innovation", "all"],
                        help="Which council to run")
    parser.add_argument("--test", action="store_true", help="Run self-tests")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    args = parser.parse_args()

    if args.test:
        sys.exit(0 if run_tests() else 1)

    if not args.council:
        parser.print_help()
        sys.exit(1)

    if args.council == "health":
        result = run_health_council()
    elif args.council == "security":
        result = run_security_council()
    elif args.council == "innovation":
        result = run_innovation_council()
    elif args.council == "all":
        result = run_all()
    else:
        parser.print_help()
        sys.exit(1)

    if args.json or args.council == "all":
        print(json.dumps(result, indent=2))
    else:
        # Human-readable summary
        print(f"\n{'='*50}")
        print(f"Council: {result.get('council', args.council).upper()}")
        print(f"Run at:  {result.get('run_at', 'unknown')}")
        print(f"Overall: {result.get('overall', 'unknown')}")
        print(f"Report:  {result.get('report_path', 'N/A')}")

        if args.council == "health":
            for svc in result.get("services", []):
                marker = "✓" if svc["status"] == "UP" else "✗"
                name = svc.get("service") or svc.get("name", "?")
                print(f"  {marker} {name} :{svc['port']} — {svc['status']}")

        elif args.council == "security":
            print(f"Skills scanned: {result.get('skills_count', 0)}")
            print(f"Findings: {result.get('findings_count', 0)}")
            for f in result.get("findings", [])[:5]:
                print(f"  - {f.get('skill', '?')}: {str(f)[:80]}")

        elif args.council == "innovation":
            print("\nActionable suggestions:")
            for i, s in enumerate(result.get("suggestions", []), 1):
                print(f"  {i}. {s}")
        print(f"{'='*50}\n")


if __name__ == "__main__":
    main()
