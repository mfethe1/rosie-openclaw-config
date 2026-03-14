#!/usr/bin/env python3
"""
predictive_request_deliberation.py — Multi-agent deliberation loop for 
designing the "Predict What Michael Will Ask Next" system.

Publishes proposal via NATS, runs challenge/refine/vote cycles across agents,
converges on a final architecture.

Phases:
1. Publish blended proposal to NATS (events.broadcast.deliberation)
2. Each agent critiques and proposes refinements (via sub-agents)
3. Collect votes + objections
4. Refine based on objections
5. Repeat until alignment (max 3 rounds)
6. Publish final architecture to NATS + write to workspace
"""

import json
import os
import sys
import time
import importlib
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'infra', 'nats'))

_nats_bridge = None
try:
    _nats_bridge = importlib.import_module("nats_bridge")
except ImportError:
    # Optional dependency: continue in degraded mode when NATS tooling is missing.
    _nats_bridge = None

nats_pub = getattr(_nats_bridge, "nats_pub", None) if _nats_bridge is not None else None

if _nats_bridge is not None:
    nats_available = getattr(_nats_bridge, "nats_available", lambda: False)
else:
    def nats_available() -> bool:
        return False

WORKSPACE = os.path.expanduser("~/.openclaw/workspace")
OUTPUT_PATH = os.path.join(WORKSPACE, "self_improvement", "PREDICTIVE_REQUEST_ARCHITECTURE.md")

# ── The Blended Proposal ──────────────────────────────────────────

BLENDED_PROPOSAL = """
# Predictive Request System — Blended Proposal v0.1

## Goal
Infer what Michael will ask next, pre-compute the answer, and serve it instantly 
or proactively surface it before he asks.

## Three Pillars

### Pillar 1: Request Pattern Analyzer
- Tag every inbound Michael request by category: status, build, fix, revenue, research, coordination, review
- Correlate with: time-of-day, day-of-week, recent commits, open PRs, calendar context
- Store as structured events in memU with key `request-pattern:{timestamp}`
- Build a frequency matrix: P(category | context_features)
- Output: top-3 predicted next requests with confidence scores

### Pillar 2: Session Trajectory Analyzer  
- After each Michael message, analyze last 3-5 messages for conversational trajectory
- Detect patterns: "status check → drill-down → action request" or "review → fix → verify"
- Use a lightweight chain-of-thought to infer the next logical follow-up
- Pre-compute the answer for the top prediction
- Output: predicted next message + pre-computed response (cached 5 min)

### Pillar 3: Proactive Pre-fetch Engine
- If prediction confidence > 75%, run the check/query/computation BEFORE Michael asks
- Cache result with TTL=5min in a NATS KV store or local file
- When Michael's actual request arrives, serve from cache (sub-second response)
- Telemetry: log prediction vs actual, compute accuracy over time
- Feedback loop: adjust confidence thresholds based on hit rate

## Data Sources
- Session history (last 24h of Michael conversations)
- Cron health state (if recent failures → predict "what's broken?")
- Git activity (recent pushes → predict "PR status?" or "deploy?")
- Calendar (upcoming meetings → predict prep requests)
- Time patterns (morning → status checks, afternoon → build requests, evening → review)
- NATS event stream (recent agent activity → predict coordination questions)

## Architecture
- `request_tagger.py` — Classifies incoming requests, stores to memU
- `trajectory_analyzer.py` — Analyzes conversation chains, predicts next
- `prefetch_engine.py` — Pre-computes answers for high-confidence predictions
- `prediction_scorer.py` — Compares predictions vs actuals, tunes weights
- NATS subject: `predictions.michael.next_request` — agents can subscribe to pre-fetch triggers
- Cron: runs trajectory analysis every 5 min during active hours (8am-10pm EST)

## Success Metrics
- Prediction accuracy: >60% within first month, >75% by month 3
- Response time improvement: <2s for predicted requests (vs 5-15s normal)
- Pre-fetch hit rate: >40% of cache entries used within TTL
- Michael satisfaction: subjective "that was fast" or "I was just about to ask that" signals
"""

CHALLENGE_PROMPT_TEMPLATE = """You are {agent_name}, an agent on the OpenClaw team. Your role: {role_desc}

A blended proposal has been published for building a "Predict What Michael Will Ask Next" system.

PROPOSAL:
{proposal}

PREVIOUS ROUND CRITIQUES (if any):
{prev_critiques}

Your job in this round:
1. **CHALLENGE**: What's wrong, missing, over-engineered, or naive about this proposal? Be specific and brutal.
2. **PRESSURE TEST**: What failure modes will hit first? What's the #1 reason this will NOT work in practice?
3. **REFINE**: Propose exactly 1-3 specific, actionable improvements. No vague hand-waving.
4. **VOTE**: APPROVE (ship it), APPROVE_WITH_CHANGES (ship after fixes), or BLOCK (fundamental flaw).

Respond in this exact JSON format:
{{
  "agent": "{agent_id}",
  "round": {round_num},
  "challenges": ["challenge 1", "challenge 2"],
  "failure_modes": ["failure mode 1"],
  "refinements": ["specific change 1", "specific change 2"],
  "vote": "APPROVE|APPROVE_WITH_CHANGES|BLOCK",
  "vote_rationale": "one sentence why"
}}
"""

AGENT_ROLES = {
    "rosie": {
        "name": "Rosie",
        "role": "Orchestrator and execution specialist. Focus on: is this buildable with current infra? Are the integration points realistic? Will the cron/NATS architecture actually work?",
    },
    "mack": {
        "name": "Mack (Macklemore)",
        "role": "Implementation specialist and curiosity-driven explorer. Focus on: code architecture quality, novel solution opportunities, what's the simplest thing that could work first? Are we over-engineering?",
    },
    "winnie": {
        "name": "Winnie",
        "role": "Research and evaluation specialist. Focus on: is there prior art we should adopt? What does the research say about user intent prediction? Are the success metrics realistic and measurable?",
    },
    "lenny": {
        "name": "Lenny",
        "role": "QA, health, and resilience specialist. Focus on: what breaks first? Privacy/security implications of tracking request patterns? Data retention risks? What's the testing strategy?",
    },
}


def _publish_event(subject: str, payload: dict, retries: int = 3, delay: float = 0.75) -> bool:
    """Publish one event with bounded retries and optional backoff.

    Returns True when the publish call succeeds, False otherwise.
    This script should continue producing prompts even if NATS is unavailable.
    """
    if not nats_available() or nats_pub is None:
        print(f"⚠️ NATS unavailable, skipping publish to {subject}")
        return False

    last_err: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            nats_pub(subject, payload)
            return True
        except Exception as exc:
            last_err = exc
            if attempt >= retries:
                break
            time.sleep(delay * attempt)

    print(f"WARN: failed to publish {subject} after {retries} attempts: {last_err}")
    return False


def run_deliberation() -> dict:
    """Run the full deliberation loop."""

    published_start = _publish_event(
        "events.broadcast.deliberation",
        {
            "type": "deliberation_start",
            "topic": "predictive_request_system",
            "proposal_version": "0.1",
            "round": 0,
            "proposal": BLENDED_PROPOSAL,
        },
    )

    if published_start:
        print("📡 Published proposal to NATS: events.broadcast.deliberation")
    else:
        print("⚠️  Initial publish to NATS skipped (degraded mode)")

    proposal = BLENDED_PROPOSAL
    all_rounds = []
    output = None

    for round_num in range(1, 4):  # max 3 rounds
        print(f"\n{'=' * 60}")
        print(f"🔄 ROUND {round_num}")
        print(f"{'=' * 60}")

        prev_critiques = json.dumps(all_rounds[-1], indent=2) if all_rounds else "None (first round)"
        round_results = {}

        for agent_id, agent_info in AGENT_ROLES.items():
            prompt = CHALLENGE_PROMPT_TEMPLATE.format(
                agent_name=agent_info["name"],
                role_desc=agent_info["role"],
                proposal=proposal,
                prev_critiques=prev_critiques,
                agent_id=agent_id,
                round_num=round_num,
            )

            # Write prompt to temp file for the sub-agent call
            prompt_file = f"/tmp/deliberation_{agent_id}_r{round_num}.txt"
            with open(prompt_file, 'w', encoding="utf-8") as f:
                f.write(prompt)

            round_results[agent_id] = {
                "prompt_file": prompt_file,
                "prompt": prompt,
            }
            print(f"  📝 Prepared challenge prompt for {agent_info['name']}")

        # Output prompts for orchestrator to run via sub-agents
        output = {
            "round": round_num,
            "agents": list(round_results.keys()),
            "prompt_files": {k: v["prompt_file"] for k, v in round_results.items()},
            "prompts": {k: v["prompt"] for k, v in round_results.items()},
        }

        round_file = os.path.join(WORKSPACE, "self_improvement", f"deliberation_round_{round_num}.json")
        with open(round_file, 'w', encoding="utf-8") as f:
            json.dump(output, f, indent=2)

        published_round = _publish_event(
            "events.broadcast.deliberation",
            {
                "type": "deliberation_round",
                "topic": "predictive_request_system",
                "round": round_num,
                "agents": list(round_results.keys()),
                "status": "prompts_ready",
            },
        )

        if published_round:
            print(f"  📡 Published round {round_num} to NATS")
        else:
            print(f"  ⚠️  Round {round_num} publish skipped/unreliable")

        print(f"  📄 Round data: {round_file}")

    print(f"\n✅ Deliberation prompts prepared for 3 rounds.")
    print("   Orchestrator should now run each agent's prompt as a sub-agent,")
    print("   collect responses, check for alignment, and iterate.")
    return output or {}


if __name__ == "__main__":
    run_deliberation()
