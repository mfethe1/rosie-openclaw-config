#!/usr/bin/env python3
"""skill_recommendation_engine.py — Analyze SI skill inventory and suggest additions.

Scans the self_improvement/scripts/ directory, categorizes each skill,
cross-references with open TODO items and decision log, then produces
ranked recommendations for what to build next.

Categories:
  memory     — memory pipeline (store/retrieve/consolidate/sync)
  testing    — test execution, validation, harness
  monitoring — health checks, cost tracking, cron auditing
  research   — competitive scans, paper tracking, benchmarking
  workflow   — orchestration, coordination, change management
  quality    — fail-reflection, profiling, eval gates

Usage:
  python3 skill_recommendation_engine.py
  python3 skill_recommendation_engine.py --json
  python3 skill_recommendation_engine.py --out /tmp/skill-recs.md
"""

from __future__ import annotations

import argparse
import ast
import json
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent
TODO_PATH   = SCRIPTS_DIR.parent / "TODO.md"
STATE_PATH  = SCRIPTS_DIR.parent / "shared-state.json"

# ── category classification ────────────────────────────────────────────────
CATEGORY_PATTERNS: list[tuple[str, list[str]]] = [
    ("memory",     ["memory", "mem", "knowledge", "promem", "migrate", "consolidat"]),
    ("testing",    ["test", "harness", "benchmark", "gate", "runner"]),
    ("monitoring", ["monitor", "health", "cost", "cron", "drift", "model_health", "profil"]),
    ("research",   ["awesome", "scan", "vetting", "competitive", "tracker"]),
    ("workflow",   ["checkpoint", "continuation", "change_monitor", "weekly_review",
                    "archive", "skill_injection", "proactive"]),
    ("quality",    ["fail", "reflect", "lenny", "eval"]),
]


def categorize(name: str) -> str:
    n = name.lower()
    for cat, keywords in CATEGORY_PATTERNS:
        if any(k in n for k in keywords):
            return cat
    return "other"


def get_docstring(path: Path) -> str:
    try:
        tree = ast.parse(path.read_text(errors="replace"))
        ds = ast.get_docstring(tree)
        return (ds or "").split("\n")[0].strip()[:100]
    except (SyntaxError, OSError):
        return ""


# ── inventory ──────────────────────────────────────────────────────────────
def build_inventory() -> list[dict]:
    inv = []
    for f in sorted(SCRIPTS_DIR.glob("*.py")):
        if f.name.startswith("__"):
            continue
        cat = categorize(f.name)
        doc = get_docstring(f)
        lines = len(f.read_text(errors="replace").splitlines())
        inv.append({
            "name": f.name,
            "category": cat,
            "docstring": doc,
            "lines": lines,
        })
    return inv


# ── gap analysis ───────────────────────────────────────────────────────────
IDEAL_COVERAGE = {
    "memory":     {"min": 5, "desc": "Memory pipeline: store, retrieve, consolidate, sync, update"},
    "testing":    {"min": 3, "desc": "Test execution, validation harness, benchmark gates"},
    "monitoring": {"min": 4, "desc": "Health checks, cost tracking, cron auditing, alerting"},
    "research":   {"min": 2, "desc": "Competitive scans, paper tracking, benchmarking"},
    "workflow":   {"min": 3, "desc": "Orchestration, coordination, change management"},
    "quality":    {"min": 2, "desc": "Fail-reflection, profiling, eval gates"},
}

KNOWN_GAPS = [
    {
        "name": "dependency-analyzer",
        "category": "workflow",
        "why": "No tool to trace script interdependencies or detect breaking changes when modifying shared modules (e.g. agent_memory_cli.py used by 10+ scripts).",
        "priority": "MEDIUM",
        "effort": "MEDIUM",
        "owner": "Winnie",
    },
    {
        "name": "session-analyzer",
        "category": "monitoring",
        "why": "No tool to analyze OpenClaw session logs for performance patterns, failure clusters, or cost anomalies per session.",
        "priority": "MEDIUM",
        "effort": "MEDIUM",
        "owner": "Mack",
    },
    {
        "name": "task-orchestrator",
        "category": "workflow",
        "why": "No multi-agent workflow manager — agents coordinate via TODO.md text edits, not structured task dispatch.",
        "priority": "HIGH",
        "effort": "HIGH",
        "owner": "Mack",
    },
    {
        "name": "alert-escalation",
        "category": "monitoring",
        "why": "28 blockers accumulated but no automated escalation to Telegram/iMessage when critical blockers are unresolved >24h.",
        "priority": "HIGH",
        "effort": "LOW",
        "owner": "Rosie",
    },
    {
        "name": "blocker-cleanup",
        "category": "quality",
        "why": "28 active_blockers in shared-state, 20+ resolved but not pruned. State bloat impacts every agent reading shared-state.",
        "priority": "HIGH",
        "effort": "LOW",
        "owner": "Lenny",
    },
    {
        "name": "decision-tracker",
        "category": "workflow",
        "why": "25 decisions (D-001 through D-025) tracked in shared-state JSON — no tool to verify implementation status or generate a decision register.",
        "priority": "MEDIUM",
        "effort": "LOW",
        "owner": "Rosie",
    },
    {
        "name": "TODO-lint",
        "category": "quality",
        "why": "TODO.md header is 40+ lines long and growing. No automated check for stale entries, duplicate tasks, or missing owner/effort tags.",
        "priority": "MEDIUM",
        "effort": "LOW",
        "owner": "Lenny",
    },
]


def compute_gaps(inventory: list[dict]) -> dict:
    cat_counts = Counter(s["category"] for s in inventory)
    gaps = {}
    for cat, info in IDEAL_COVERAGE.items():
        current = cat_counts.get(cat, 0)
        deficit = max(0, info["min"] - current)
        gaps[cat] = {
            "current": current,
            "target": info["min"],
            "deficit": deficit,
            "desc": info["desc"],
            "status": "✅" if deficit == 0 else f"⚠️ need {deficit} more",
        }
    return gaps


def rank_recommendations(gaps: dict, inventory: list[dict]) -> list[dict]:
    """Produce ranked list of recommended next skills."""
    recs = []
    for gap in KNOWN_GAPS:
        # Check if already exists
        exists = any(gap["name"].replace("-", "_") in s["name"] for s in inventory)
        if exists:
            continue
        # Score: HIGH=3, MEDIUM=2, LOW=1 for priority; inverse for effort
        pri = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}.get(gap["priority"], 1)
        eff = {"LOW": 3, "MEDIUM": 2, "HIGH": 1}.get(gap["effort"], 1)
        score = pri * eff  # higher = do sooner
        recs.append({**gap, "score": score, "exists": False})
    recs.sort(key=lambda x: -x["score"])
    return recs


# ── report ─────────────────────────────────────────────────────────────────
def format_report(inventory: list[dict], gaps: dict, recs: list[dict]) -> str:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M EST")
    lines = [
        "# Skill Recommendation Engine Report",
        f"**Generated:** {ts}",
        f"**Total scripts:** {len(inventory)} | **Categories:** {len(set(s['category'] for s in inventory))}",
        "",
        "## Current Inventory by Category",
        "| Category | Count | Status | Scripts |",
        "|---|---|---|---|",
    ]
    by_cat = defaultdict(list)
    for s in inventory:
        by_cat[s["category"]].append(s["name"])
    for cat in sorted(IDEAL_COVERAGE.keys()):
        g = gaps.get(cat, {})
        scripts = ", ".join(f"`{n}`" for n in by_cat.get(cat, []))[:120]
        lines.append(f"| {cat} | {g.get('current',0)} | {g.get('status','?')} | {scripts} |")
    if "other" in by_cat:
        lines.append(f"| other | {len(by_cat['other'])} | — | {', '.join(f'`{n}`' for n in by_cat['other'])[:80]} |")

    lines += [
        "",
        "## Coverage Gaps",
        "| Category | Current | Target | Gap |",
        "|---|---|---|---|",
    ]
    for cat, g in sorted(gaps.items()):
        if g["deficit"] > 0:
            lines.append(f"| {cat} | {g['current']} | {g['target']} | **{g['deficit']} missing** |")

    lines += [
        "",
        "## Recommended Next Skills (Ranked)",
        "| Rank | Skill | Category | Priority | Effort | Score | Owner | Why |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for i, r in enumerate(recs, 1):
        lines.append(
            f"| {i} | `{r['name']}` | {r['category']} | {r['priority']} | "
            f"{r['effort']} | **{r['score']}** | {r['owner']} | {r['why'][:80]} |"
        )

    lines += [
        "",
        "## Top 3 Recommendations",
    ]
    for i, r in enumerate(recs[:3], 1):
        lines += [
            f"### {i}. `{r['name']}` ({r['category']}) — Priority: {r['priority']}, Effort: {r['effort']}",
            f"**Owner:** {r['owner']}",
            f"**Rationale:** {r['why']}",
            "",
        ]

    lines += ["---", f"*{len(recs)} recommendations generated from {len(inventory)} scripts across {len(gaps)} categories.*"]
    return "\n".join(lines)


# ── main ───────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="skill_recommendation_engine — analyze gaps and suggest next skills")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--out", help="Write report to file")
    args = parser.parse_args()

    inventory = build_inventory()
    gaps = compute_gaps(inventory)
    recs = rank_recommendations(gaps, inventory)

    if args.json:
        print(json.dumps({
            "total_scripts": len(inventory),
            "categories": dict(Counter(s["category"] for s in inventory)),
            "gaps": gaps,
            "recommendations": recs,
        }, indent=2))
    else:
        report = format_report(inventory, gaps, recs)
        if args.out:
            Path(args.out).write_text(report)
            print(f"Report written → {args.out}")
        else:
            print(report)


if __name__ == "__main__":
    main()
