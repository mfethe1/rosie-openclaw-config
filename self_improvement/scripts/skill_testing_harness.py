#!/usr/bin/env python3
"""skill_testing_harness.py — Skill health-check harness (Winnie Cycle #14).

Enumerates and validates skills across two tiers:

  Tier 1 — SI Python scripts (self_improvement/scripts/*.py)
    Tests applied per script:
      T1: Syntax check  (python3 -m py_compile)
      T2: Docstring     (has module-level docstring)
      T3: Help flag     (--help exits 0, if argparse-based)
      T4: Self-test     (run script with no args; checks for __main__ guard)

  Tier 2 — OpenClaw skill directories (skills/<name>/SKILL.md)
    Tests applied per skill:
      S1: SKILL.md exists
      S2: SKILL.md parseable (has name + description)
      S3: Required binaries present (from metadata.openclaw.requires.bins)

Reports:
  - Markdown table + per-skill details
  - JSON structured output (--json)
  - Memory storage via agent_memory_cli.py (one row per failed skill)

Usage:
  python3 skill_testing_harness.py
  python3 skill_testing_harness.py --tier si              # SI scripts only
  python3 skill_testing_harness.py --tier openclaw        # OpenClaw skills only
  python3 skill_testing_harness.py --json                 # JSON output
  python3 skill_testing_harness.py --out report.md        # write to file
  python3 skill_testing_harness.py --agent mack --store   # store failures to memory
  python3 skill_testing_harness.py --filter knowledge     # only skills matching name
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional

# ── paths ──────────────────────────────────────────────────────────────────
SI_SCRIPTS_DIR   = Path(__file__).parent
OPENCLAW_SKILLS  = Path("/opt/homebrew/lib/node_modules/openclaw/skills")
AGENT_MEMORY_CLI = SI_SCRIPTS_DIR / "agent_memory_cli.py"
PYTHON           = "/opt/homebrew/bin/python3.13"

# Scripts to skip (migration / one-shot tools, not ongoing skills)
SKIP_SI_SCRIPTS = {
    "migrate_memory_md_to_sqlite.py",  # one-shot import
    "weekly_competitive_scan.sh",       # shell, not python
}


# ── data types ─────────────────────────────────────────────────────────────
@dataclass
class TestResult:
    test_id: str
    name: str
    passed: bool
    detail: str = ""
    duration_ms: float = 0.0


@dataclass
class SkillReport:
    name: str
    path: str
    tier: str            # "si" | "openclaw"
    tests: list[TestResult] = field(default_factory=list)

    @property
    def passed(self) -> int:
        return sum(1 for t in self.tests if t.passed)

    @property
    def failed(self) -> int:
        return sum(1 for t in self.tests if not t.passed)

    @property
    def status(self) -> str:
        return "PASS" if self.failed == 0 else "FAIL"


# ── helpers ────────────────────────────────────────────────────────────────
def _run(cmd: str, timeout: int = 15) -> tuple[int, str, str, float]:
    t0 = time.time()
    try:
        p = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return p.returncode, p.stdout, p.stderr, (time.time() - t0) * 1000
    except subprocess.TimeoutExpired:
        return -99, "", f"TIMEOUT after {timeout}s", timeout * 1000
    except Exception as e:
        return -1, "", str(e), (time.time() - t0) * 1000


def _has_docstring(path: Path) -> bool:
    try:
        src = path.read_text(errors="replace")
        tree = ast.parse(src)
        return bool(ast.get_docstring(tree))
    except (SyntaxError, OSError):
        return False


def _has_argparse(path: Path) -> bool:
    try:
        src = path.read_text(errors="replace")
        return "argparse" in src or "add_argument" in src
    except OSError:
        return False


def _has_main_guard(path: Path) -> bool:
    try:
        src = path.read_text(errors="replace")
        return '__name__ == "__main__"' in src or "__name__ == '__main__'" in src
    except OSError:
        return False


# ── Tier 1: SI scripts ─────────────────────────────────────────────────────
def test_si_script(path: Path) -> SkillReport:
    report = SkillReport(name=path.name, path=str(path), tier="si")

    # T1: Syntax check
    rc, _, err, ms = _run(f'"{PYTHON}" -m py_compile "{path}"')
    report.tests.append(TestResult(
        "T1:syntax", "Syntax check",
        passed=(rc == 0),
        detail=err.strip()[:120] if rc != 0 else "OK",
        duration_ms=ms
    ))

    # T2: Docstring
    has_doc = _has_docstring(path)
    report.tests.append(TestResult(
        "T2:docstring", "Module docstring",
        passed=has_doc,
        detail="present" if has_doc else "MISSING — add a module-level docstring",
    ))

    # T3: --help (argparse only)
    if _has_argparse(path):
        rc, out, err, ms = _run(f'"{PYTHON}" "{path}" --help', timeout=10)
        # argparse prints help to stdout and exits 0
        report.tests.append(TestResult(
            "T3:help", "--help flag",
            passed=(rc == 0),
            detail=f"exit {rc}" + (f": {err[:80]}" if rc != 0 else ""),
            duration_ms=ms
        ))
    else:
        report.tests.append(TestResult("T3:help", "--help flag", passed=True,
                                       detail="N/A (no argparse)"))

    # T4: Main guard present
    has_guard = _has_main_guard(path)
    report.tests.append(TestResult(
        "T4:main_guard", "main guard",
        passed=has_guard,
        detail="present" if has_guard else "MISSING — script has no __main__ guard",
    ))

    return report


# ── Tier 2: OpenClaw skills ─────────────────────────────────────────────────
def _parse_skill_md(skill_dir: Path) -> dict:
    """Parse SKILL.md YAML frontmatter block.

    Extracts name, description, and requires.bins specifically.
    Handles both multi-line YAML and compact JSON-in-YAML metadata styles.
    """
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        return {}
    content = skill_md.read_text(errors="replace")
    # Extract YAML between first --- delimiters
    m = re.search(r"^---\s*\n(.*?)^---", content, re.DOTALL | re.MULTILINE)
    if not m:
        return {}
    yaml_block = m.group(1)
    result = {}

    # name (top-level field)
    nm = re.search(r"^name:\s*(.+)$", yaml_block, re.MULTILINE)
    if nm:
        result["name"] = nm.group(1).strip().strip('"\'')

    # description (top-level field, may be quoted)
    dm = re.search(r'^description:\s*"?(.+?)"?\s*$', yaml_block, re.MULTILINE)
    if dm:
        result["description"] = dm.group(1).strip().strip('"\'')

    # requires.bins — specifically look for: "bins": ["a", "b"] or bins: [a, b]
    # within a "requires" block. Works for both inline JSON and expanded YAML.
    bins_m = re.search(r'"bins"\s*:\s*\[([^\]]*)\]', yaml_block)
    if not bins_m:
        # Try unquoted YAML style: bins: [rg, git]
        bins_m = re.search(r'\brequires\b.*?\bbins\b\s*:\s*\[([^\]]*)\]',
                            yaml_block, re.DOTALL)
    if bins_m:
        raw = bins_m.group(1)
        bins = [b.strip().strip('"\'') for b in raw.split(",") if b.strip()]
        result["bins"] = [b for b in bins if b and "/" not in b]  # skip paths
    else:
        result["bins"] = []

    return result


def test_openclaw_skill(skill_dir: Path) -> SkillReport:
    report = SkillReport(name=skill_dir.name, path=str(skill_dir), tier="openclaw")

    # S1: SKILL.md exists
    skill_md = skill_dir / "SKILL.md"
    report.tests.append(TestResult(
        "S1:skill_md", "SKILL.md exists",
        passed=skill_md.exists(),
        detail="present" if skill_md.exists() else "MISSING"
    ))

    if not skill_md.exists():
        return report

    # S2: SKILL.md parseable
    meta = _parse_skill_md(skill_dir)
    has_name = bool(meta.get("name"))
    has_desc = bool(meta.get("description"))
    report.tests.append(TestResult(
        "S2:parseable", "SKILL.md parseable",
        passed=(has_name and has_desc),
        detail="OK" if (has_name and has_desc) else f"name={'✓' if has_name else '✗'} desc={'✓' if has_desc else '✗'}"
    ))

    # S3: Required binaries present
    bins = meta.get("bins", [])
    if bins:
        missing = [b for b in bins if not shutil.which(b)]
        report.tests.append(TestResult(
            "S3:bins", "Required binaries",
            passed=(not missing),
            detail=f"all present: {bins}" if not missing else f"MISSING: {missing}"
        ))
    else:
        report.tests.append(TestResult("S3:bins", "Required binaries", passed=True,
                                       detail="N/A (no bins declared)"))
    return report


# ── storage ────────────────────────────────────────────────────────────────
def store_failure(report: SkillReport, agent: str, cycle: str) -> bool:
    if not AGENT_MEMORY_CLI.exists():
        return False
    fails = [t for t in report.tests if not t.passed]
    detail_str = "; ".join(f"{t.test_id}:{t.detail}" for t in fails)
    body = f"skill-harness FAIL: {report.name} ({report.tier}) — {detail_str}"[:400]
    cmd = [
        PYTHON, str(AGENT_MEMORY_CLI), "store",
        "--agent", agent,
        "--cycle", cycle,
        "--topic", f"skill-health:{report.name}",
        "--body", body,
        "--tags", f"skill-harness,{report.tier},fail",
        "--type", "experiential",
        "--context", f"automated skill health check, {report.failed} test(s) failed",
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
    return r.returncode == 0


# ── report formatting ──────────────────────────────────────────────────────
def format_markdown(reports: list[SkillReport], tier_filter: str, elapsed_ms: float) -> str:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M EST")
    passed = sum(1 for r in reports if r.status == "PASS")
    failed = len(reports) - passed

    lines = [
        f"# Skill Testing Harness Report — {ts}",
        f"**Tier:** {tier_filter} | **Skills checked:** {len(reports)} | "
        f"**PASS:** {passed} | **FAIL:** {failed} | **Time:** {elapsed_ms:.0f}ms",
        "",
        "## Summary",
        "| Skill | Tier | Status | Tests |",
        "|---|---|---|---|",
    ]
    for r in reports:
        icon = "✅" if r.status == "PASS" else "❌"
        detail = ", ".join(
            f"{t.test_id}{'✓' if t.passed else '✗'}" for t in r.tests
        )
        lines.append(f"| `{r.name}` | {r.tier} | {icon} {r.status} | {detail} |")

    lines.append("")
    # Detail for failures
    failures = [r for r in reports if r.status == "FAIL"]
    if failures:
        lines.append("## Failures Detail")
        for r in failures:
            lines.append(f"\n### ❌ `{r.name}` ({r.tier})")
            lines.append(f"Path: `{r.path}`")
            for t in r.tests:
                if not t.passed:
                    lines.append(f"- **{t.test_id} {t.name}:** {t.detail}")
    else:
        lines.append("## ✅ All skills healthy")

    lines += ["", "---",
              f"**Overall:** {'ALL PASS ✅' if failed == 0 else f'{failed} skill(s) need attention ❌'}"]
    return "\n".join(lines)


def format_json_report(reports: list[SkillReport], elapsed_ms: float) -> dict:
    return {
        "ran": len(reports),
        "passed": sum(1 for r in reports if r.status == "PASS"),
        "failed": sum(1 for r in reports if r.status == "FAIL"),
        "elapsed_ms": round(elapsed_ms, 1),
        "skills": [
            {
                "name": r.name,
                "tier": r.tier,
                "status": r.status,
                "tests": [asdict(t) for t in r.tests],
            }
            for r in reports
        ],
    }


# ── main ───────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="skill_testing_harness — validate SI scripts + OpenClaw skills")
    parser.add_argument("--tier", choices=["si", "openclaw", "all"], default="all")
    parser.add_argument("--filter", default="", help="Only test skills whose name contains this string")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--out", help="Write report to file")
    parser.add_argument("--store", action="store_true", help="Store failures to agent-memory.db")
    parser.add_argument("--agent", default="winnie")
    parser.add_argument("--cycle", default="")
    args = parser.parse_args()

    t_start = time.time()
    reports: list[SkillReport] = []
    cycle = args.cycle or datetime.now().strftime("%Y-%m-%d-%H")

    # ── Tier 1: SI scripts ─────────────────────────────────────────────────
    if args.tier in ("si", "all"):
        si_files = sorted(
            f for f in SI_SCRIPTS_DIR.glob("*.py")
            if f.name not in SKIP_SI_SCRIPTS
        )
        for sf in si_files:
            if args.filter and args.filter.lower() not in sf.name.lower():
                continue
            print(f"  [SI ] {sf.name}")
            r = test_si_script(sf)
            reports.append(r)
            icon = "✅" if r.status == "PASS" else "❌"
            print(f"        {icon} {r.passed}/{len(r.tests)} tests passed"
                  + (f" — FAIL: {[t.test_id for t in r.tests if not t.passed]}" if r.status == "FAIL" else ""))
            if args.store and r.status == "FAIL":
                store_failure(r, args.agent, cycle)

    # ── Tier 2: OpenClaw skills ─────────────────────────────────────────────
    if args.tier in ("openclaw", "all") and OPENCLAW_SKILLS.exists():
        skill_dirs = sorted(d for d in OPENCLAW_SKILLS.iterdir() if d.is_dir())
        for sd in skill_dirs:
            if args.filter and args.filter.lower() not in sd.name.lower():
                continue
            print(f"  [OC ] {sd.name}")
            r = test_openclaw_skill(sd)
            reports.append(r)
            icon = "✅" if r.status == "PASS" else "❌"
            print(f"        {icon} {r.passed}/{len(r.tests)} tests passed"
                  + (f" — FAIL: {[t.test_id for t in r.tests if not t.passed]}" if r.status == "FAIL" else ""))
            if args.store and r.status == "FAIL":
                store_failure(r, args.agent, cycle)

    elapsed_ms = (time.time() - t_start) * 1000
    passed = sum(1 for r in reports if r.status == "PASS")
    failed = len(reports) - passed

    if args.json:
        output = json.dumps(format_json_report(reports, elapsed_ms), indent=2)
    else:
        output = format_markdown(reports, args.tier, elapsed_ms)

    if args.out:
        Path(args.out).write_text(output)
        print(f"\nReport written → {args.out}")
    else:
        print(f"\n{output}")

    print(f"\n{'✅ ALL PASS' if failed == 0 else f'❌ {failed} FAIL'} "
          f"({passed}/{len(reports)} skills, {elapsed_ms:.0f}ms)")
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
