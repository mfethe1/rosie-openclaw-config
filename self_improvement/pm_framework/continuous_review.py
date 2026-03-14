#!/usr/bin/env python3
"""
continuous_review.py — Scheduled PM Review Loop
Designed to run as a cron job. Loads project config, runs PM session,
diffs against previous review, and logs action items.

Usage:
    python3 continuous_review.py --project buildbid
    python3 continuous_review.py --all
    python3 continuous_review.py --test
"""

import os
import sys
import json
import argparse
import datetime
from pathlib import Path
from typing import Optional

# Graceful event_logger import
try:
    sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
    from event_logger import log_event
except ImportError:
    def log_event(event_type, data=None, **kwargs):
        pass

FRAMEWORK_DIR = Path(__file__).parent
CONFIGS_DIR = FRAMEWORK_DIR / "project_configs"
LOGS_DIR = FRAMEWORK_DIR / "logs"
DEFAULT_PERSONAS = ["pm", "red", "blue", "qa"]


def load_config(project_name: str) -> dict:
    """Load project config by name (matches filename without .json)."""
    config_path = CONFIGS_DIR / f"{project_name.lower()}.json"
    if not config_path.exists():
        available = [f.stem for f in CONFIGS_DIR.glob("*.json")]
        raise FileNotFoundError(
            f"Config '{project_name}' not found. Available: {available}"
        )
    with open(config_path) as f:
        return json.load(f)


def get_previous_review(project_name: str) -> Optional[dict]:
    """Get the most recent review log for a project."""
    pattern = f"review-{project_name.lower()}-*.json"
    review_files = sorted(LOGS_DIR.glob(pattern), reverse=True)
    if not review_files:
        return None
    with open(review_files[0]) as f:
        return json.load(f)


def diff_reviews(prev: dict, curr: dict) -> dict:
    """Simple diff between two review outputs."""
    if not prev:
        return {"status": "first_review", "changes": [], "new_items": []}

    changes = []
    prev_outputs = prev.get("outputs", {})
    curr_outputs = curr.get("outputs", {})

    # Check for new personas run
    prev_personas = set(prev.get("personas_run", []))
    curr_personas = set(curr.get("personas_run", []))
    new_personas = curr_personas - prev_personas
    if new_personas:
        changes.append(f"New personas added: {', '.join(new_personas)}")

    # Rough content diff by synthesis length change
    prev_synth = prev_outputs.get("synthesis", "")
    curr_synth = curr_outputs.get("synthesis", "")
    len_diff = len(curr_synth) - len(prev_synth)
    if abs(len_diff) > 200:
        direction = "expanded" if len_diff > 0 else "condensed"
        changes.append(f"Synthesis {direction} by {abs(len_diff)} chars")

    # Date diff
    prev_date = prev.get("timestamp", "unknown")[:10]
    curr_date = curr.get("timestamp", "unknown")[:10]
    changes.append(f"Previous review: {prev_date}, Current: {curr_date}")

    return {
        "status": "updated",
        "days_since_last": (
            datetime.datetime.now() -
            datetime.datetime.fromisoformat(prev.get("timestamp", datetime.datetime.now().isoformat()))
        ).days,
        "changes": changes,
        "synthesis_preview": curr_synth[:500] if curr_synth else ""
    }


def extract_action_items(report: dict) -> list:
    """Extract action items from PM synthesis output."""
    synthesis = report.get("outputs", {}).get("synthesis", "")
    if not synthesis:
        return []

    # Simple heuristic: lines containing action verbs or bullet points
    action_lines = []
    for line in synthesis.split("\n"):
        line = line.strip()
        if not line:
            continue
        # Lines that look like action items
        if any(line.startswith(prefix) for prefix in ["- ", "* ", "1.", "2.", "3.", "4.", "5.", "•"]):
            action_lines.append(line.lstrip("-*•1234567890. ").strip())
        elif any(kw in line.lower() for kw in ["must", "should", "need to", "priority:", "action:"]):
            action_lines.append(line)

    return action_lines[:20]  # Cap at 20 items


def build_team_summary(project_name: str, report: dict, diff: dict, action_items: list) -> str:
    """Build a human-readable summary suitable for posting to a team channel."""
    timestamp = report.get("timestamp", "")[:10]
    synthesis = report.get("outputs", {}).get("synthesis", "No synthesis available.")
    red_preview = report.get("outputs", {}).get("red", "")[:300] if report.get("outputs", {}).get("red") else ""
    blue_preview = report.get("outputs", {}).get("blue", "")[:300] if report.get("outputs", {}).get("blue") else ""

    lines = [
        f"📋 **PM Review: {project_name}** — {timestamp}",
        f"Personas: {', '.join(report.get('personas_run', []))}",
        "",
        "**Sprint Synthesis:**",
        synthesis[:600] + ("..." if len(synthesis) > 600 else ""),
        "",
    ]

    if red_preview:
        lines += ["**Top Risks (Red Team):**", red_preview[:300] + "...", ""]

    if action_items:
        lines += ["**Action Items:**"] + [f"  • {item}" for item in action_items[:8]] + [""]

    if diff.get("status") == "updated":
        lines.append(f"_(Last review: {diff.get('days_since_last', '?')} days ago)_")
    elif diff.get("status") == "first_review":
        lines.append("_(First review for this project)_")

    return "\n".join(lines)


def run_review(project_name: str, dry_run: bool = False) -> dict:
    """Run a full review for one project."""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*50}")
    print(f"CONTINUOUS REVIEW: {project_name}")
    print(f"{'='*50}")

    # Load config
    try:
        config = load_config(project_name)
    except FileNotFoundError as e:
        print(f"Error: {e}")
        return {}

    # Build context from config
    context = json.dumps({
        "description": config.get("description", ""),
        "current_state": config.get("current_state", ""),
        "known_issues": config.get("known_issues", []),
        "next_priorities": config.get("next_priorities", [])
    }, indent=2)

    # Get previous review for diff
    prev_review = get_previous_review(project_name)

    if dry_run:
        print(f"[DRY RUN] Would run PM session for {project_name}")
        print(f"Config: {config.get('name')} — {config.get('business_stage')}")
        print(f"Previous review: {'found' if prev_review else 'none'}")
        return {"dry_run": True, "project": project_name}

    # Run PM session
    from pm_session import run_session
    report = run_session(config.get("name", project_name), context, DEFAULT_PERSONAS)

    # Diff analysis
    diff = diff_reviews(prev_review, report)
    action_items = extract_action_items(report)
    summary = build_team_summary(project_name, report, diff, action_items)

    # Save review log
    date_str = datetime.datetime.now().strftime("%Y-%m-%d")
    log_path = LOGS_DIR / f"review-{project_name.lower()}-{date_str}.json"
    review_log = {
        "project": project_name,
        "timestamp": report.get("timestamp"),
        "personas_run": report.get("personas_run", []),
        "outputs": report.get("outputs", {}),
        "diff": diff,
        "action_items": action_items,
        "team_summary": summary
    }

    with open(log_path, "w") as f:
        json.dump(review_log, f, indent=2)

    print(f"\n{summary}")
    print(f"\n✅ Review logged: {log_path}")

    log_event("continuous_review_complete", {
        "project": project_name,
        "action_items": len(action_items),
        "diff_status": diff.get("status"),
        "log_path": str(log_path)
    })

    return review_log


def main():
    parser = argparse.ArgumentParser(description="Continuous PM Review Loop")
    parser.add_argument("--project", help="Project name (matches config filename)")
    parser.add_argument("--all", action="store_true", help="Run for all configured projects")
    parser.add_argument("--test", action="store_true", help="Self-test without API calls")
    parser.add_argument("--dry-run", action="store_true", help="Show what would run, no API calls")
    parser.add_argument("--list", action="store_true", help="List available project configs")

    args = parser.parse_args()

    if args.test:
        print("=== continuous_review.py SELF-TEST ===")
        configs = list(CONFIGS_DIR.glob("*.json")) if CONFIGS_DIR.exists() else []
        print(f"Config directory: {CONFIGS_DIR}")
        print(f"Found configs: {[f.stem for f in configs]}")
        print(f"Logs directory: {LOGS_DIR}")

        # Test load
        for cfg in configs[:1]:
            data = json.loads(cfg.read_text())
            print(f"Loaded '{cfg.stem}': {data.get('name')} — {data.get('business_stage')}")

        # Test diff
        diff = diff_reviews(None, {"timestamp": datetime.datetime.now().isoformat(), "outputs": {}, "personas_run": []})
        print(f"Diff (no prev): {diff['status']}")
        print("✅ Self-test passed")
        return

    if args.list:
        configs = list(CONFIGS_DIR.glob("*.json"))
        print("Available projects:")
        for f in configs:
            data = json.loads(f.read_text())
            print(f"  {f.stem}: {data.get('name')} — {data.get('business_stage', 'unknown')}")
        return

    if args.all:
        configs = list(CONFIGS_DIR.glob("*.json"))
        results = {}
        for cfg in configs:
            result = run_review(cfg.stem, dry_run=args.dry_run)
            results[cfg.stem] = "ok" if result else "failed"
        print(f"\n{'='*50}")
        print("ALL REVIEWS COMPLETE")
        for proj, status in results.items():
            print(f"  {proj}: {status}")
        return

    if args.project:
        run_review(args.project, dry_run=args.dry_run)
        return

    parser.print_help()


if __name__ == "__main__":
    if "--test" in sys.argv:
        print("=== continuous_review.py SELF-TEST ===")
        configs = list(CONFIGS_DIR.glob("*.json")) if CONFIGS_DIR.exists() else []
        print(f"Found configs: {[f.stem for f in configs]}")
        print("✅ Self-test passed")
        sys.exit(0)
    main()
