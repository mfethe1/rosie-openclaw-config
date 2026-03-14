#!/usr/bin/env python3
"""
cost_tracker.py — Track API costs per agent per model per cycle.

Records token usage and estimated cost for each API call.
Stored as JSONL in self_improvement/logs/costs-YYYY-MM-DD.jsonl
"""

import json
from datetime import datetime, timezone
from pathlib import Path

LOGS_DIR = Path(__file__).parent / "logs"

# Cost per 1M tokens (input/output) — approximate
COSTS = {
    "anthropic/claude-opus-4-6": {"input": 15.0, "output": 75.0},
    "anthropic/claude-sonnet-4-6": {"input": 3.0, "output": 15.0},
    "google/gemini-3.1-pro-preview": {"input": 1.25, "output": 10.0},
    "google/gemini-3.1-flash": {"input": 0.15, "output": 0.60},
    "openai-codex/gpt-5.3-codex": {"input": 2.0, "output": 8.0},
    "openai-codex/gpt-5.3-codex-spark": {"input": 0.5, "output": 2.0},
    "perplexity/sonar": {"input": 1.0, "output": 1.0},
    "perplexity/sonar-pro": {"input": 3.0, "output": 15.0},
    "perplexity/sonar-reasoning-pro": {"input": 2.0, "output": 8.0},
    "perplexity/sonar-deep-research": {"input": 2.0, "output": 8.0},
}


def log_cost(agent: str, model: str, input_tokens: int, output_tokens: int,
             context: str = ""):
    """Log a cost entry."""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    cost_rates = COSTS.get(model, {"input": 5.0, "output": 15.0})
    cost_usd = (input_tokens * cost_rates["input"] + output_tokens * cost_rates["output"]) / 1_000_000

    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "agent": agent,
        "model": model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cost_usd": round(cost_usd, 6),
        "context": context,
    }

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    cost_file = LOGS_DIR / f"costs-{today}.jsonl"
    with open(cost_file, "a") as f:
        f.write(json.dumps(entry, separators=(",", ":")) + "\n")

    return entry


def daily_summary(date: str = None) -> dict:
    """Summarize costs for a given date (YYYY-MM-DD)."""
    if not date:
        date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    cost_file = LOGS_DIR / f"costs-{date}.jsonl"
    if not cost_file.exists():
        return {"date": date, "total_usd": 0, "by_agent": {}, "by_model": {}}

    total = 0
    by_agent = {}
    by_model = {}
    for line in cost_file.read_text().strip().splitlines():
        try:
            e = json.loads(line)
            cost = e.get("cost_usd", 0)
            total += cost
            agent = e.get("agent", "unknown")
            model = e.get("model", "unknown")
            by_agent[agent] = by_agent.get(agent, 0) + cost
            by_model[model] = by_model.get(model, 0) + cost
        except json.JSONDecodeError:
            continue

    return {
        "date": date,
        "total_usd": round(total, 4),
        "by_agent": {k: round(v, 4) for k, v in sorted(by_agent.items(), key=lambda x: -x[1])},
        "by_model": {k: round(v, 4) for k, v in sorted(by_model.items(), key=lambda x: -x[1])},
    }


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "summary":
        date = sys.argv[2] if len(sys.argv) > 2 else None
        s = daily_summary(date)
        print(f"Cost summary for {s['date']}: ${s['total_usd']:.4f}")
        for agent, cost in s["by_agent"].items():
            print(f"  {agent}: ${cost:.4f}")
        for model, cost in s["by_model"].items():
            print(f"  {model}: ${cost:.4f}")
    else:
        print("Usage: cost_tracker.py summary [YYYY-MM-DD]")
