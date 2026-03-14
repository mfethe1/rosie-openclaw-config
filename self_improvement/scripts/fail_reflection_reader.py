#!/opt/homebrew/bin/python3.13
"""fail_reflection_reader.py — D-019 Rosie weekly reader.

Reads memory/fail-reflections.jsonl, groups failures by agent + probable_cause,
and proposes targeted profile patches via shared-state.json broadcasts.

Usage:
  python3.13 fail_reflection_reader.py [--since-days N] [--broadcast] [--dry-run]

Exit codes:
  0 = OK (even if proposals produced)
  1 = error
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path

WORKSPACE = Path("/Users/harrisonfethe/.openclaw/workspace")
REFLECTIONS_PATH = WORKSPACE / "memory/fail-reflections.jsonl"
SHARED_STATE_PATH = WORKSPACE / "self_improvement/shared-state.json"

# Map probable_cause → suggested patch for agent profile
CAUSE_TO_PATCH: dict[str, str] = {
    "output_file_stale": (
        "OUTPUT FRESHNESS: Write output file (outputs/YYYY-MM-DD-HH-<agent>.md) "
        "IMMEDIATELY after task execution — before calling smoke_test.sh. "
        "The file must be written within the current hour."
    ),
    "memu_store_invalid_payload": (
        "MEMU RESILIENCE: Before using memU store/search, verify health with "
        "`curl -s http://localhost:12345/health`. "
        "If unhealthy, wait 5s and retry once before escalating."
    ),
    "model_not_allowed": (
        "MODEL ALLOWLIST: Only use models from the approved rotation list in agents/<name>.md. "
        "claude-sonnet-4-5 is deprecated; use claude-sonnet-4-6."
    ),
    "cron_announce_delivery_failed": (
        "DELIVERY BEST-EFFORT: When cron announce delivery fails, it is a Telegram infrastructure "
        "issue (B-005), not an agent logic failure. Use --best-effort-deliver on cron definitions."
    ),
    "timeout": (
        "TIMEOUT GUARD: Tasks over 300s should use checkpoint_runner.py for resume-safety. "
        "Request timeoutSeconds increase via blocker if 3+ consecutive timeouts."
    ),
    "wrong_output_path": (
        "PATH DISCIPLINE: Output file must use YOUR agent name, not another agent's. "
        "Template: /Users/harrisonfethe/.openclaw/workspace/self_improvement/outputs/YYYY-MM-DD-HH-<your_name>.md"
    ),
}


def load_reflections(path: Path, since: datetime | None = None) -> list[dict]:
    if not path.exists():
        return []
    entries = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            e = json.loads(line)
        except json.JSONDecodeError:
            continue
        if since:
            ts_str = e.get("timestamp", "")
            try:
                ts = datetime.fromisoformat(ts_str)
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
                if ts < since:
                    continue
            except (ValueError, TypeError):
                pass
        entries.append(e)
    return entries


def group_by(entries: list[dict]) -> dict[str, dict[str, list[dict]]]:
    """Returns {agent: {probable_cause: [entries]}}."""
    groups: dict[str, dict[str, list[dict]]] = defaultdict(lambda: defaultdict(list))
    for e in entries:
        agent = e.get("agent", "unknown")
        cause = e.get("probable_cause", "unknown")
        groups[agent][cause].append(e)
    return groups


def build_proposals(groups: dict) -> list[dict]:
    proposals = []
    for agent, causes in groups.items():
        for cause, entries in causes.items():
            count = len(entries)
            patch = CAUSE_TO_PATCH.get(cause, f"Review failures: {cause} ({count}x)")
            hints = list({e.get("profile_hint", "") for e in entries if e.get("profile_hint")})
            proposals.append({
                "agent": agent,
                "probable_cause": cause,
                "occurrences": count,
                "patch_suggestion": patch,
                "profile_hints": hints,
            })
    # Sort: most occurrences first
    proposals.sort(key=lambda p: -p["occurrences"])
    return proposals


def append_broadcast(shared_state_path: Path, message: str, dry_run: bool) -> None:
    if dry_run:
        print(f"[DRY-RUN] Would broadcast: {message[:200]}")
        return
    data = json.loads(shared_state_path.read_text("utf-8"))
    broadcasts = data.setdefault("broadcasts", [])
    item = {
        "id": f"bc-fail-reflect-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
        "created_at": datetime.now().isoformat(),
        "source": "fail_reflection_reader",
        "message": message,
        "ack_by": {},
    }
    broadcasts.append(item)
    data["last_updated"] = datetime.now().isoformat()
    data["last_updated_by"] = "rosie"
    shared_state_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description="D-019: Scan fail-reflections.jsonl and propose profile patches.")
    ap.add_argument("--since-days", type=int, default=7, help="Only look at last N days (default: 7)")
    ap.add_argument("--broadcast", action="store_true", help="Write proposals to shared-state broadcasts")
    ap.add_argument("--dry-run", action="store_true", help="Print proposals without writing")
    ap.add_argument("--reflections", default=str(REFLECTIONS_PATH), help="Path to fail-reflections.jsonl")
    args = ap.parse_args()

    since = datetime.now(tz=timezone.utc) - timedelta(days=args.since_days)
    entries = load_reflections(Path(args.reflections), since=since)

    if not entries:
        print(f"fail_reflection_reader: 0 entries in last {args.since_days} days — nothing to propose.")
        return 0

    groups = group_by(entries)
    proposals = build_proposals(groups)

    print(f"fail_reflection_reader: {len(entries)} failure(s) → {len(proposals)} proposal(s)")
    for p in proposals:
        print(f"\n  Agent: {p['agent']} | Cause: {p['probable_cause']} ({p['occurrences']}x)")
        print(f"  Patch: {p['patch_suggestion'][:120]}")

    if args.broadcast or not args.dry_run:
        # Compose a concise broadcast message
        lines = [f"[D-019 FAIL-REFLECT] {len(entries)} failure(s) in last {args.since_days}d. Proposed profile patches:"]
        for p in proposals[:5]:
            lines.append(
                f"• {p['agent']}/{p['probable_cause']} ({p['occurrences']}x): "
                f"{p['patch_suggestion'][:100]}"
            )
        msg = "\n".join(lines)
        append_broadcast(SHARED_STATE_PATH, msg, dry_run=args.dry_run)
        if not args.dry_run:
            print("\nBroadcast written to shared-state.json.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
