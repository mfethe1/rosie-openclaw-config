#!/usr/bin/env python3
"""
Daily research + NATS voting consensus loop.

- Runs Firecrawl-agent research for agent/LLM/tool optimization topics
- Creates a daily ballot of implementation candidates
- Broadcasts lane-lock + vote requests over NATS
- Tallies votes using BCCS engine and emits consensus decision

Python 3.9 stdlib only.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import pathlib
import subprocess
import sys
from typing import Dict, List, Optional

ROOT = pathlib.Path(__file__).resolve().parents[2]
WORKSPACE = ROOT
BASE = WORKSPACE / "self_improvement" / "agentic_research"
LOGS = BASE / "logs"
LOGS.mkdir(parents=True, exist_ok=True)

FIRECRAWL = pathlib.Path.home() / ".openclaw" / "skills" / "firecrawl-agent" / "scripts" / "firecrawl_agent.py"
NATS_BRIDGE = WORKSPACE / "infra" / "nats" / "nats_bridge.py"
BCCS = WORKSPACE / "self_improvement" / "consensus" / "bccs_engine.py"

VOTES_FILE = LOGS / "votes.jsonl"

AGENTS = ["rosie", "mack", "winnie", "lenny"]

QUERIES = [
    # 5 daily Firecrawl searches (use full quota)
    "latest 2025 2026 research on LLM agent optimization and reliable tool use",
    "recent papers on agentic workflows, planning, and multi-agent coordination",
    "elegant systems approaches for AI tool routing, safety, and evaluation loops",
    "new research on autonomous software engineering agents, code review agents, and CI/CD agent reliability",
    "latest methods for multi-agent memory systems, retrieval quality, and consensus-based decision making",
]


def _now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def _run(cmd: List[str], timeout: int = 60) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def nats_call(command: str, agent: str, *args: str) -> None:
    try:
        _run(["python3", str(NATS_BRIDGE), command, agent, *args], timeout=10)
    except Exception:
        pass


def run_firecrawl(query: str) -> Dict:
    if not FIRECRAWL.exists():
        return {"ok": False, "query": query, "error": "firecrawl_agent script not found"}

    cmd = [
        "python3",
        str(FIRECRAWL),
        "--json",
        "--template",
        "research",
        query,
    ]
    res = _run(cmd, timeout=180)
    if res.returncode != 0:
        return {"ok": False, "query": query, "error": res.stderr.strip()[:600]}

    try:
        data = json.loads(res.stdout)
    except Exception:
        data = {"raw": res.stdout[:4000]}
    return {"ok": True, "query": query, "data": data}


def _to_text(data: Dict) -> str:
    if isinstance(data, dict):
        for key in ("summary", "answer", "result", "content", "raw"):
            val = data.get(key)
            if isinstance(val, str) and val.strip():
                return val.strip()
        return json.dumps(data)[:1200]
    return str(data)[:1200]


def create_ballot(research_results: List[Dict], date_key: str) -> pathlib.Path:
    options = []
    for idx, item in enumerate(research_results, start=1):
        if not item.get("ok"):
            continue
        text = _to_text(item.get("data", {}))
        first = text.split(". ")[0][:220]
        options.append({
            "id": f"opt{idx}",
            "title": f"Implement research track {idx}",
            "query": item.get("query"),
            "proposal": first,
        })

    if not options:
        options = [
            {"id": "opt1", "title": "Stability Track", "query": "fallback", "proposal": "Improve tool reliability and retry control."},
            {"id": "opt2", "title": "Cost Track", "query": "fallback", "proposal": "Improve budget guardrails and reduce failed retries."},
            {"id": "opt3", "title": "Workflow Track", "query": "fallback", "proposal": "Improve task decomposition and intent packet quality."},
            {"id": "opt4", "title": "Automation Track", "query": "fallback", "proposal": "Improve autonomous loops and exception handling."},
            {"id": "opt5", "title": "Memory Track", "query": "fallback", "proposal": "Improve memory retrieval quality and consistency."},
        ]

    ballot = {
        "ballot_id": f"research-{date_key}",
        "created_at": _now().isoformat(),
        "options": options[:5],
        "threshold": 0.82,
        "status": "open",
    }
    out = LOGS / f"ballot-{date_key}.json"
    out.write_text(json.dumps(ballot, indent=2))
    return out


def publish_vote_requests(ballot_path: pathlib.Path) -> None:
    ballot = json.loads(ballot_path.read_text())
    option_ids = "|".join([o.get("id", "") for o in ballot.get("options", []) if o.get("id")])
    payload = {
        "type": "vote_request",
        "ballot_id": ballot["ballot_id"],
        "options": ballot["options"],
        "deadline_utc": (_now() + dt.timedelta(hours=6)).isoformat(),
        "how_to_vote": f"python3 {BASE}/daily_research_consensus.py vote --agent <agent> --ballot {ballot['ballot_id']} --option <{option_ids}>",
    }

    nats_call("report", "rosie", "lane_lock", f"research_consensus_open:{ballot['ballot_id']}")
    nats_call("broadcast", "rosie", f"Lane lock: opened research vote {ballot['ballot_id']}")

    for agent in AGENTS:
        nats_call("assign", "rosie", agent, json.dumps(payload))


def append_vote(agent: str, ballot_id: str, option: str, rationale: str = "") -> None:
    record = {
        "ts": _now().isoformat(),
        "agent": agent,
        "ballot_id": ballot_id,
        "option": option,
        "rationale": rationale[:400],
    }
    with VOTES_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")


def tally(ballot_id: str) -> Dict:
    if not VOTES_FILE.exists():
        return {"ok": False, "error": "no votes yet", "ballot_id": ballot_id}

    votes = []
    for line in VOTES_FILE.read_text().splitlines():
        try:
            row = json.loads(line)
        except Exception:
            continue
        if row.get("ballot_id") == ballot_id:
            votes.append(row)

    latest_by_agent: Dict[str, Dict] = {}
    for v in votes:
        latest_by_agent[v.get("agent", "")] = v

    if len(latest_by_agent) < 3:
        return {
            "ok": False,
            "ballot_id": ballot_id,
            "error": "insufficient votes",
            "votes_received": len(latest_by_agent),
        }

    cumulative: Dict[str, Dict[str, int]] = {}
    for agent, v in latest_by_agent.items():
        opt = v.get("option")
        if not opt:
            continue
        cumulative[agent] = {opt: 1}

    res = _run(["python3", str(BCCS), "--cumulative", json.dumps(cumulative)], timeout=20)
    if res.returncode != 0:
        return {"ok": False, "ballot_id": ballot_id, "error": res.stderr.strip()[:300]}

    out = json.loads(res.stdout)
    winner = out.get("winner")
    nscore = float(out.get("normalised_scores", {}).get(winner, 0.0))
    decided = nscore >= 0.82

    final = {
        "ok": True,
        "ballot_id": ballot_id,
        "winner": winner,
        "normalised_score": round(nscore, 4),
        "decided": decided,
        "votes_received": len(latest_by_agent),
        "result": out,
        "ts": _now().isoformat(),
    }

    decision_file = LOGS / f"decision-{ballot_id}.json"
    decision_file.write_text(json.dumps(final, indent=2))

    nats_call("report", "rosie", "consensus", json.dumps(final)[:600])
    if decided:
        nats_call("broadcast", "rosie", f"Consensus reached {ballot_id}: {winner} ({nscore:.3f})")
    else:
        nats_call("broadcast", "rosie", f"Consensus pending {ballot_id}: {winner} ({nscore:.3f}) below threshold")

    return final


def cmd_run(date_key: Optional[str]) -> int:
    if not date_key:
        date_key = _now().strftime("%Y-%m-%d")

    nats_call("heartbeat", "rosie", "research_loop_start")

    results = [run_firecrawl(q) for q in QUERIES]
    research_file = LOGS / f"research-{date_key}.json"
    research_file.write_text(json.dumps({"ts": _now().isoformat(), "results": results}, indent=2))

    ballot_path = create_ballot(results, date_key)
    publish_vote_requests(ballot_path)

    # Also attempt to close yesterday's ballot for daily consensus continuity.
    prev_date = (dt.datetime.strptime(date_key, "%Y-%m-%d") - dt.timedelta(days=1)).strftime("%Y-%m-%d")
    prev_ballot_id = f"research-{prev_date}"
    prev_tally = tally(prev_ballot_id)

    nats_call("heartbeat", "rosie", "research_loop_complete")
    print(json.dumps({
        "ok": True,
        "research": str(research_file),
        "ballot": str(ballot_path),
        "previous_tally": prev_tally,
    }))
    return 0


def run_tests() -> int:
    test_ballot = create_ballot(
        [{"ok": True, "query": "q", "data": {"summary": "Test summary for option one."}}],
        "2099-01-01",
    )
    ballot = json.loads(test_ballot.read_text())
    assert ballot["options"], "ballot options missing"

    append_vote("rosie", "research-2099-01-01", "opt1", "r1")
    append_vote("mack", "research-2099-01-01", "opt1", "r2")
    append_vote("winnie", "research-2099-01-01", "opt1", "r3")
    t = tally("research-2099-01-01")
    assert t.get("ok") is True
    assert t.get("winner") == "opt1"
    print("All tests passed.")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="Daily research consensus loop")
    sub = p.add_subparsers(dest="cmd")

    r = sub.add_parser("run", help="Run daily research + open ballot")
    r.add_argument("--date", default=None)

    v = sub.add_parser("vote", help="Cast a vote")
    v.add_argument("--agent", required=True)
    v.add_argument("--ballot", required=True)
    v.add_argument("--option", required=True)
    v.add_argument("--rationale", default="")

    t = sub.add_parser("tally", help="Tally votes for a ballot")
    t.add_argument("--ballot", required=True)

    p.add_argument("--test", action="store_true")

    args = p.parse_args()
    if args.test:
        return run_tests()

    if args.cmd == "run":
        return cmd_run(args.date)
    if args.cmd == "vote":
        append_vote(args.agent, args.ballot, args.option, args.rationale)
        print(json.dumps({"ok": True}))
        return 0
    if args.cmd == "tally":
        print(json.dumps(tally(args.ballot), indent=2))
        return 0

    p.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
