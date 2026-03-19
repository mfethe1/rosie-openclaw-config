#!/usr/bin/env python3
"""
weekly_review.py — SI Weekly Review Automation (Rosie)

Generates a structured weekly review report from:
1. CHANGELOG.md entries from last 7 days
2. TODO.md pending/completed task counts
3. shared-state.json blocker status
4. Output: self_improvement/outputs/YYYY-MM-DD-weekly-review.md

Usage:
    python3 weekly_review.py [--days N] [--output PATH] [--json]

Exit codes:
    0 — report written
    1 — error reading required files
"""

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

WORKSPACE = Path("/Users/harrisonfethe/.openclaw/workspace")
SI = WORKSPACE / "self_improvement"
CHANGELOG = SI / "CHANGELOG.md"
TODO_MD = SI / "TODO.md"
SHARED_STATE = SI / "shared-state.json"
OUTPUTS = SI / "outputs"
COST_TRACKER = SI / "scripts" / "cost_tracker.py"
MEMORY_MD_UPDATER = SI / "scripts" / "memory_md_updater.py"
PYTHON = "/opt/homebrew/bin/python3.13"


def parse_changelog_entries(days: int) -> list[dict]:
    """Extract CHANGELOG entries from the last N days."""
    entries = []
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    try:
        text = CHANGELOG.read_text()
    except FileNotFoundError:
        return entries

    # Match "YYYY-MM-DD HH:MM [Agent] - Description" pattern
    pattern = re.compile(r"^\*?\*?(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2})\s+\[(\w+)\]\s*[-–]\s*(.+)$", re.MULTILINE)
    # Also match "**HH:MM [Agent]**" style (newer format)
    pattern2 = re.compile(r"^\*\*(\d{2}:\d{2})\s+\[(\w+)\]\*\*\s*[-–]\s*(.+)$", re.MULTILINE)

    # For dated entries
    for m in pattern.finditer(text):
        try:
            entry_dt = datetime.strptime(m.group(1), "%Y-%m-%d").replace(tzinfo=timezone.utc)
            if entry_dt >= cutoff:
                entries.append({
                    "date": m.group(1),
                    "time": m.group(2),
                    "agent": m.group(3),
                    "summary": m.group(4).strip("*").strip(),
                })
        except ValueError:
            pass

    # For undated hourly entries (assume today)
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    for m in pattern2.finditer(text):
        entries.append({
            "date": today_str,
            "time": m.group(1),
            "agent": m.group(2),
            "summary": m.group(3).strip("*").strip(),
        })

    return entries


def parse_todo_stats() -> dict:
    """Count tasks in TODO.md by status and agent."""
    try:
        text = TODO_MD.read_text()
    except FileNotFoundError:
        return {"error": "TODO.md not found"}

    agents = ["Rosie", "Mack", "Winnie", "Lenny", "All"]
    stats = {"total_done": 0, "total_pending": 0, "by_agent": {}}

    done_pattern = re.compile(r"^- \[x\].*\[(\w+)\]", re.MULTILINE | re.IGNORECASE)
    pending_pattern = re.compile(r"^- \[ \].*\[(\w+)\]", re.MULTILINE | re.IGNORECASE)

    for m in done_pattern.finditer(text):
        stats["total_done"] += 1
        agent = m.group(1).capitalize()
        if agent not in stats["by_agent"]:
            stats["by_agent"][agent] = {"done": 0, "pending": 0}
        stats["by_agent"][agent]["done"] = stats["by_agent"][agent].get("done", 0) + 1

    for m in pending_pattern.finditer(text):
        stats["total_pending"] += 1
        agent = m.group(1).capitalize()
        if agent not in stats["by_agent"]:
            stats["by_agent"][agent] = {"done": 0, "pending": 0}
        stats["by_agent"][agent]["pending"] = stats["by_agent"][agent].get("pending", 0) + 1

    completion_pct = 0
    total = stats["total_done"] + stats["total_pending"]
    if total > 0:
        completion_pct = round(100 * stats["total_done"] / total, 1)
    stats["completion_pct"] = completion_pct
    stats["total"] = total

    return stats


def parse_blockers() -> dict:
    """Extract blocker counts from shared-state.json."""
    try:
        state = json.loads(SHARED_STATE.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return {"error": "shared-state.json not found or invalid"}

    blockers = state.get("active_blockers", [])
    def is_resolved(b):
        return b.get("priority") == "RESOLVED" or b.get("sla") == "RESOLVED" or bool(b.get("resolved_at"))
    open_blockers = [b for b in blockers if not is_resolved(b)]
    resolved = [b for b in blockers if is_resolved(b)]
    critical = [b for b in open_blockers if b.get("priority") in ("CRITICAL", "HIGH")]

    return {
        "total": len(blockers),
        "open": len(open_blockers),
        "resolved": len(resolved),
        "critical": len(critical),
        "open_list": [{"id": b["id"], "description": b["description"][:80], "priority": b.get("priority")} for b in open_blockers],
    }


def agent_velocity(entries: list[dict]) -> dict:
    """Count changelog entries per agent as a velocity proxy."""
    velocity = {}
    for e in entries:
        agent = e["agent"]
        velocity[agent] = velocity.get(agent, 0) + 1
    return dict(sorted(velocity.items(), key=lambda x: -x[1]))


def generate_recommendations(todo_stats: dict, blockers: dict, entries: list[dict]) -> list[dict]:
    """Generate keep/improve/stop recommendations."""
    recs = []
    completion = todo_stats.get("completion_pct", 0)
    open_blockers = blockers.get("open", 0)
    critical_blockers = blockers.get("critical", 0)

    # KEEP recommendations
    if completion > 50:
        recs.append({"type": "KEEP", "text": f"Task completion at {completion}% — maintain current pace and prioritization."})
    if blockers.get("resolved", 0) > 0:
        recs.append({"type": "KEEP", "text": f"{blockers['resolved']} blockers resolved this cycle — blocker resolution process is working."})

    # IMPROVE recommendations
    if critical_blockers > 0:
        recs.append({"type": "IMPROVE", "text": f"{critical_blockers} CRITICAL/HIGH blocker(s) unresolved. Prioritize these before new features."})
    if completion < 60:
        recs.append({"type": "IMPROVE", "text": f"Completion rate {completion}% is below target (60%). Review if MEDIUM/LOW tasks are crowding URGENT backlog."})
    by_agent = todo_stats.get("by_agent", {})
    high_pending = [(a, v["pending"]) for a, v in by_agent.items() if v.get("pending", 0) > 10]
    for agent, count in high_pending:
        recs.append({"type": "IMPROVE", "text": f"{agent} has {count} pending tasks — consider pruning or redistributing."})

    # STOP recommendations
    if open_blockers > 5:
        recs.append({"type": "STOP", "text": "Blocker count exceeds 5 open items. Stop adding new blocker categories until existing ones are resolved."})

    # Default recommendations if none generated
    if not recs:
        recs.append({"type": "KEEP", "text": "System operating within normal parameters."})
        recs.append({"type": "IMPROVE", "text": "Continue monitoring token usage and cycle health."})

    return recs[:6]  # Cap at 6 recommendations


def fetch_cost_summary(days: int) -> dict:
    """Run cost_tracker.py for weekly cost section (group=model, store enabled)."""
    if not COST_TRACKER.exists():
        return {"error": "cost_tracker.py not found"}

    cycle = f"weekly-review-{datetime.now().strftime('%Y-%m-%d')}"
    cmd = [
        PYTHON,
        str(COST_TRACKER),
        "--days", str(days),
        "--group", "model",
        "--json",
        "--store",
        "--agent", "rosie",
        "--cycle", cycle,
    ]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=40)
        if r.returncode not in (0, 2):
            return {"error": f"cost_tracker failed rc={r.returncode}", "stderr": r.stderr.strip()[:300]}
        data = json.loads(r.stdout)
        data["store_cycle"] = cycle
        return data
    except (subprocess.TimeoutExpired, OSError, json.JSONDecodeError) as e:
        return {"error": f"cost_tracker exception: {e}"}


def fetch_memory_md_summary() -> dict:
    """Run memory_md_updater.py in JSON mode and return summary."""
    if not MEMORY_MD_UPDATER.exists():
        return {"error": "memory_md_updater.py not found"}

    cmd = [PYTHON, str(MEMORY_MD_UPDATER), "--json"]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=40)
        if r.returncode != 0:
            return {"error": f"memory_md_updater failed rc={r.returncode}", "stderr": r.stderr.strip()[:300]}
        return json.loads(r.stdout)
    except (subprocess.SubprocessError, OSError, json.JSONDecodeError) as e:
        return {"error": f"memory_md_updater exception: {e}"}


def build_report(days: int) -> str:
    """Build the full weekly review markdown report."""
    now = datetime.now()
    week_start = (now - timedelta(days=days)).strftime("%Y-%m-%d")
    week_end = now.strftime("%Y-%m-%d")
    timestamp = now.strftime("%Y-%m-%d %H:%M EST")

    entries = parse_changelog_entries(days)
    todo_stats = parse_todo_stats()
    blockers = parse_blockers()
    velocity = agent_velocity(entries)
    recs = generate_recommendations(todo_stats, blockers, entries)
    cost_summary = fetch_cost_summary(days)
    memory_summary = fetch_memory_md_summary()

    lines = [
        f"# Weekly Review — {week_start} to {week_end}",
        f"**Generated:** {timestamp} by Rosie (automated)",
        f"**Period:** {days}-day lookback",
        "",
        "---",
        "",
        "## 1. Task Completion",
        f"- Total tasks: **{todo_stats.get('total', 'N/A')}**",
        f"- Completed: **{todo_stats.get('total_done', 0)}** ({todo_stats.get('completion_pct', 0)}%)",
        f"- Pending: **{todo_stats.get('total_pending', 0)}**",
        "",
        "**By agent:**",
    ]
    by_agent = todo_stats.get("by_agent", {})
    for agent in sorted(by_agent.keys()):
        d = by_agent[agent].get("done", 0)
        p = by_agent[agent].get("pending", 0)
        lines.append(f"  - {agent}: {d} done / {p} pending")

    lines += [
        "",
        "---",
        "",
        "## 2. Changelog Activity (Last {} Days)".format(days),
        f"- Total entries: **{len(entries)}**",
        "",
        "**Velocity by agent:**",
    ]
    if velocity:
        for agent, count in velocity.items():
            lines.append(f"  - {agent}: {count} entries")
    else:
        lines.append("  - (no changelog entries found in period)")

    lines += [
        "",
        "**Recent highlights:**",
    ]
    # Show last 8 entries
    for e in entries[-8:]:
        lines.append(f"  - [{e['date']} {e['time']}] [{e['agent']}] {e['summary'][:100]}")

    lines += [
        "",
        "---",
        "",
        "## 3. Blocker Status",
        f"- Open: **{blockers.get('open', 0)}**",
        f"- Critical/High: **{blockers.get('critical', 0)}**",
        f"- Resolved: **{blockers.get('resolved', 0)}**",
        "",
    ]
    open_list = blockers.get("open_list", [])
    if open_list:
        lines.append("**Open blockers:**")
        for b in open_list:
            lines.append(f"  - [{b['id']}] ({b['priority']}) {b['description']}")
    else:
        lines.append("✅ No open blockers.")

    lines += [
        "",
        "---",
        "",
        "## 4. Cost Summary (7-day model view)",
        "",
    ]
    if cost_summary.get("error"):
        lines.append(f"- ⚠️ Cost tracker unavailable: {cost_summary['error']}")
    else:
        gt = cost_summary.get("grand_total", {})
        lines.append(f"- Estimated total cost: **${gt.get('cost_usd', 0):.4f}**")
        lines.append(f"- Estimated daily cost: **${cost_summary.get('daily_estimate_usd', 0):.4f}**")
        lines.append(f"- Estimated monthly cost: **${cost_summary.get('monthly_estimate_usd', 0):.2f}**")
        lines.append(f"- Total runs counted: **{gt.get('runs', 0)}**")
        top = sorted((cost_summary.get("groups") or {}).items(), key=lambda x: -x[1].get("cost_usd", 0))[:3]
        if top:
            lines.append("- Top model costs:")
            for model, vals in top:
                lines.append(f"  - `{model}`: ${vals.get('cost_usd', 0):.4f} ({vals.get('runs', 0)} runs)")
        lines.append(f"- cost_tracker store cycle: `{cost_summary.get('store_cycle', 'n/a')}`")

    lines += [
        "",
        "---",
        "",
        "## 5. MEMORY.md Updater Summary",
        "",
    ]
    if memory_summary.get("error"):
        lines.append(f"- ⚠️ memory_md_updater unavailable: {memory_summary['error']}")
    else:
        lines.append(f"- New entries fetched: **{memory_summary.get('new_entries_fetched', 0)}**")
        lines.append(f"- Appended to MEMORY.md: **{memory_summary.get('appended', 0)}**")
        lines.append(f"- Skipped duplicate: **{memory_summary.get('skipped_duplicate', 0)}**")
        lines.append(f"- Skipped below threshold: **{memory_summary.get('skipped_threshold', 0)}**")

    lines += [
        "",
        "---",
        "",
        "## 6. Recommendations (Keep / Improve / Stop)",
        "",
    ]
    for r in recs:
        icon = {"KEEP": "✅", "IMPROVE": "⚠️", "STOP": "🛑"}.get(r["type"], "•")
        lines.append(f"- {icon} **{r['type']}:** {r['text']}")

    lines += [
        "",
        "---",
        "",
        "## 7. Next Cycle Focus",
        f"- Resolve {blockers.get('critical', 0)} critical/high blocker(s) first.",
        "- Rosie next: verify weekly review cron is running + monitor output freshness.",
        "- Mack: tackle HIGH-priority pending tasks (see agent task breakdown above).",
        "- Winnie: research + validate any new tooling or proposals.",
        "- Lenny: full eval-gate audit pass + QA of this week's implementations.",
        "",
        "---",
        "",
        f"*Auto-generated by `self_improvement/scripts/weekly_review.py` — {timestamp}*",
    ]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="SI Weekly Review Automation")
    parser.add_argument("--days", type=int, default=7, help="Lookback period in days (default: 7)")
    parser.add_argument("--output", type=str, default="", help="Override output path")
    parser.add_argument("--json", action="store_true", help="Print JSON summary to stdout")
    args = parser.parse_args()

    report = build_report(args.days)

    # Determine output path
    if args.output:
        out_path = Path(args.output)
    else:
        date_str = datetime.now().strftime("%Y-%m-%d")
        out_path = OUTPUTS / f"{date_str}-weekly-review.md"

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(report)
    print(f"Weekly review written to: {out_path}")

    if args.json:
        entries = parse_changelog_entries(args.days)
        todo_stats = parse_todo_stats()
        blockers = parse_blockers()
        summary = {
            "period_days": args.days,
            "generated_at": datetime.now().isoformat(),
            "completion_pct": todo_stats.get("completion_pct", 0),
            "pending_tasks": todo_stats.get("total_pending", 0),
            "open_blockers": blockers.get("open", 0),
            "critical_blockers": blockers.get("critical", 0),
            "changelog_entries": len(entries),
            "output_path": str(out_path),
        }
        print(json.dumps(summary, indent=2))

    return 0


if __name__ == "__main__":
    sys.exit(main())
