#!/usr/bin/env python3
"""cost_tracker.py — Token usage & cost estimation skill (Winnie Cycle #17).

Tracks estimated LLM token usage and cost across all OpenClaw cron jobs.

Data sources:
  - /Users/harrisonfethe/.openclaw/cron/jobs.json        — job config (model, name, schedule)
  - /Users/harrisonfethe/.openclaw/cron/runs/<id>.jsonl  — per-job run history (ts, durationMs, status)

Cost estimation model:
  - Input tokens estimated from known prompt sizes (per-category baseline) + context multiplier
  - Output tokens estimated from run duration (empirical: ~50 tokens/second for typical agent work)
  - Prices loaded from MODEL_PRICING table (updated Feb 2026)

Outputs:
  - Markdown cost report (default) or JSON (--json)
  - Optional memory store to agent-memory.db (--store)
  - Optional CSV export (--csv)

Usage:
  python3 cost_tracker.py                        # today's estimate, markdown report
  python3 cost_tracker.py --days 7               # last 7 days
  python3 cost_tracker.py --group agent          # group by agent role
  python3 cost_tracker.py --group model          # group by model
  python3 cost_tracker.py --json                 # JSON output
  python3 cost_tracker.py --store --agent winnie # store daily total to agent-memory.db
  python3 cost_tracker.py --out /tmp/cost.md     # write report to file
  python3 cost_tracker.py --alert 5.00           # print warning if today's cost > $5
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional
import subprocess

# ── paths ──────────────────────────────────────────────────────────────────
OPENCLAW_DIR = Path.home() / ".openclaw"
JOBS_FILE    = OPENCLAW_DIR / "cron" / "jobs.json"
RUNS_DIR     = OPENCLAW_DIR / "cron" / "runs"
AGENT_CLI    = Path(__file__).parent / "agent_memory_cli.py"
PYTHON       = "/opt/homebrew/bin/python3.13"

# ── model pricing: (input $/1M tokens, output $/1M tokens) ────────────────
# Sources: Anthropic/OpenAI pricing pages, Feb 2026 estimates
MODEL_PRICING: dict[str, tuple[float, float]] = {
    "anthropic/claude-opus-4-6":           (15.00, 75.00),
    "anthropic/claude-sonnet-4-6":         ( 3.00, 15.00),
    "anthropic/claude-haiku-4-5":          ( 0.80,  4.00),
    "openai-codex/gpt-5.3-codex":          (10.00, 30.00),
    "openai-codex/gpt-5.3-codex-spark":    ( 1.50,  6.00),
    "google-antigravity/gemini-3-pro-high": ( 3.50, 10.50),
    "google-antigravity/claude-opus-4-6-thinking": (15.00, 75.00),
    "google-gemini-cli/gemini-2.5-pro":    ( 3.50, 10.50),
    "google-gemini-cli/gemini-2.5-flash":  ( 0.30,  1.20),
    # Aliases
    "opus":                                (15.00, 75.00),
    "sonnet":                              ( 3.00, 15.00),
    "haiku":                               ( 0.80,  4.00),
}

# ── token estimation baselines (per run) ──────────────────────────────────
# Categories based on job name patterns → estimated input prompt size (tokens)
CATEGORY_INPUT_TOKENS: dict[str, int] = {
    "self-improvement":  4500,   # SI agents: large cron prompt + context
    "trading":           2500,   # Trading agents: market data context
    "monitoring":        1500,   # Monitoring/health checks: lightweight
    "memory":            2000,   # Memory review/sync jobs
    "social":            1200,   # X posts, outreach
    "email":             1800,   # Email checks
    "default":           2000,   # Fallback
}
OUTPUT_TOKENS_PER_SECOND = 45   # ~45 output tokens/second for agent work
MIN_OUTPUT_TOKENS        = 200
MAX_OUTPUT_TOKENS        = 3000


def _categorise(name: str) -> str:
    n = name.lower()
    if any(k in n for k in ["self-improvement", "winnie", "rosie", "mack", "lenny", "memu", "refactor"]):
        return "self-improvement"
    if any(k in n for k in ["trade", "trading", "market", "scanner", "position", "portfolio", "schwab"]):
        return "trading"
    if any(k in n for k in ["monitor", "health", "watchdog", "version", "check", "restart"]):
        return "monitoring"
    if any(k in n for k in ["memory", "mem"]):
        return "memory"
    if any(k in n for k in ["x post", "x —", "tweet", "social", "outreach"]):
        return "social"
    if any(k in n for k in ["email", "calendar"]):
        return "email"
    return "default"


def _resolve_model(raw: Optional[str]) -> str:
    if not raw:
        return "anthropic/claude-sonnet-4-6"   # OpenClaw default
    raw = raw.strip()
    for key in MODEL_PRICING:
        if key == raw or raw in key or key.endswith(raw):
            return key
    return raw   # unknown model


def _price(model: str) -> tuple[float, float]:
    return MODEL_PRICING.get(model, (3.00, 15.00))  # default to sonnet pricing


def _estimate_tokens(duration_ms: int, category: str) -> tuple[int, int]:
    """Return (input_tokens, output_tokens) estimate for a single run."""
    input_t  = CATEGORY_INPUT_TOKENS.get(category, 2000)
    output_t = max(MIN_OUTPUT_TOKENS,
                   min(MAX_OUTPUT_TOKENS, int((duration_ms / 1000) * OUTPUT_TOKENS_PER_SECOND)))
    return input_t, output_t


# ── data classes ───────────────────────────────────────────────────────────
@dataclass
class RunRecord:
    ts: str      # raw value (epoch-ms int or ISO string)
    job_id: str
    status: str
    duration_ms: int
    date: str = ""   # YYYY-MM-DD, derived in __post_init__

    def __post_init__(self):
        """Parse ts to YYYY-MM-DD. Handles epoch-ms int or ISO string."""
        try:
            ts_val = str(self.ts).strip()
            # Epoch milliseconds — long digit string (>= 10 digits = seconds since 2001+)
            if ts_val.isdigit() and len(ts_val) >= 10:
                self.date = datetime.fromtimestamp(int(ts_val) / 1000).strftime("%Y-%m-%d")
            elif ts_val:
                # ISO string like "2026-02-20T..." or "2026-02-20"
                self.date = ts_val[:10]
            else:
                self.date = "unknown"
        except (ValueError, TypeError):
            self.date = "unknown"


@dataclass
class JobSummary:
    job_id: str
    name: str
    model: str
    category: str
    runs: list[RunRecord] = field(default_factory=list)

    def cost_for_date_range(self, since: datetime, until: datetime) -> dict:
        in_range = [r for r in self.runs
                    if since.date().isoformat() <= r.date <= until.date().isoformat()
                    and r.status != "skipped"]
        if not in_range:
            return {"runs": 0, "input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0}

        total_in = total_out = 0
        for r in in_range:
            it, ot = _estimate_tokens(r.duration_ms, self.category)
            total_in  += it
            total_out += ot

        p_in, p_out = _price(self.model)
        cost = (total_in * p_in + total_out * p_out) / 1_000_000

        return {
            "runs": len(in_range),
            "input_tokens": total_in,
            "output_tokens": total_out,
            "cost_usd": round(cost, 4),
        }


# ── loaders ────────────────────────────────────────────────────────────────
def load_jobs() -> list[JobSummary]:
    if not JOBS_FILE.exists():
        return []
    data = json.loads(JOBS_FILE.read_text())
    raw_jobs = data if isinstance(data, list) else data.get('jobs', [])
    jobs = []
    for j in raw_jobs:
        jid  = j.get('id', '')
        name = j.get('name', 'Unknown')
        payload = j.get('payload', {})
        model_raw = (payload.get('model')
                     or j.get('model')
                     or payload.get('agentConfig', {}).get('model'))
        model = _resolve_model(model_raw)
        cat   = _categorise(name)
        jobs.append(JobSummary(job_id=jid, name=name, model=model, category=cat))
    return jobs


def load_runs(jobs: list[JobSummary]) -> None:
    job_map = {j.job_id: j for j in jobs}
    if not RUNS_DIR.exists():
        return
    for run_file in RUNS_DIR.glob("*.jsonl"):
        jid = run_file.stem
        job = job_map.get(jid)
        if not job:
            # Unknown job — create a placeholder
            job = JobSummary(job_id=jid, name=f"[unknown:{jid[:8]}]",
                             model="anthropic/claude-sonnet-4-6", category="default")
            job_map[jid] = job
            jobs.append(job)
        for line in run_file.read_text().splitlines():
            if not line.strip():
                continue
            try:
                r = json.loads(line)
                job.runs.append(RunRecord(
                    ts=str(r.get('ts', '')),
                    job_id=jid,
                    status=r.get('status', 'unknown'),
                    duration_ms=int(r.get('durationMs', 0)),
                ))
            except (json.JSONDecodeError, ValueError, TypeError):
                continue


# ── report formatters ──────────────────────────────────────────────────────
def _group_report(jobs: list[JobSummary], since: datetime, until: datetime,
                  group_by: str = "category") -> dict:
    groups: dict[str, dict] = defaultdict(lambda: {
        "runs": 0, "input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0, "jobs": 0
    })
    grand = {"runs": 0, "input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0}

    for job in jobs:
        stats = job.cost_for_date_range(since, until)
        if stats["runs"] == 0:
            continue
        key = job.category if group_by == "category" else \
              job.model    if group_by == "model"    else \
              job.name[:35]
        g = groups[key]
        g["runs"]         += stats["runs"]
        g["input_tokens"] += stats["input_tokens"]
        g["output_tokens"]+= stats["output_tokens"]
        g["cost_usd"]     += stats["cost_usd"]
        g["jobs"]         += 1
        for k in ("runs", "input_tokens", "output_tokens", "cost_usd"):
            grand[k] = grand.get(k, 0) + stats[k]

    return {"groups": dict(groups), "grand_total": grand}


def format_markdown(jobs: list[JobSummary], since: datetime, until: datetime,
                    group_by: str = "category") -> str:
    days = max(1, (until - since).days + 1)
    report = _group_report(jobs, since, until, group_by)
    grand  = report["grand_total"]

    lines = [
        f"# Cost Tracker Report",
        f"**Period:** {since.date()} → {until.date()} ({days}d) | "
        f"**Group by:** {group_by} | **Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M EST')}",
        "",
        "## Summary by " + group_by.capitalize(),
        f"| {group_by.capitalize()} | Runs | Input Tok | Output Tok | Est. Cost |",
        "|---|---|---|---|---|",
    ]

    for key, g in sorted(report["groups"].items(), key=lambda x: -x[1]["cost_usd"]):
        lines.append(
            f"| `{key[:38]}` | {g['runs']} | "
            f"{g['input_tokens']:,} | {g['output_tokens']:,} | "
            f"**${g['cost_usd']:.4f}** |"
        )

    lines += [
        f"| **TOTAL** | **{grand['runs']}** | "
        f"**{grand['input_tokens']:,}** | **{grand['output_tokens']:,}** | "
        f"**${grand['cost_usd']:.4f}** |",
        "",
        "## Daily Rate Estimate",
        f"- **Est. daily cost:** ${grand['cost_usd'] / days:.4f}",
        f"- **Est. monthly cost:** ${grand['cost_usd'] / days * 30:.2f}",
        f"- **Total runs in period:** {grand['runs']}",
        f"- **Total tokens (in+out):** {(grand['input_tokens'] + grand['output_tokens']):,}",
        "",
        "## Top 10 Jobs by Cost",
        "| Job | Model | Cat | Runs | Est. Cost |",
        "|---|---|---|---|---|",
    ]

    all_jobs_stats = []
    for job in jobs:
        stats = job.cost_for_date_range(since, until)
        if stats["runs"] > 0:
            all_jobs_stats.append((job, stats))
    all_jobs_stats.sort(key=lambda x: -x[1]["cost_usd"])

    for job, stats in all_jobs_stats[:10]:
        model_short = job.model.split("/")[-1][:20]
        lines.append(
            f"| `{job.name[:35]}` | `{model_short}` | {job.category} | "
            f"{stats['runs']} | ${stats['cost_usd']:.4f} |"
        )

    lines += [
        "",
        "---",
        f"*Estimates based on: input tokens from category baseline, "
        f"output tokens from duration × {OUTPUT_TOKENS_PER_SECOND} tok/s. "
        f"Actual costs may vary ±30%.*",
    ]
    return "\n".join(lines)


def format_json_out(jobs: list[JobSummary], since: datetime, until: datetime,
                    group_by: str = "category") -> dict:
    days  = max(1, (until - since).days + 1)
    report= _group_report(jobs, since, until, group_by)
    grand = report["grand_total"]
    return {
        "period_days": days,
        "since": since.date().isoformat(),
        "until": until.date().isoformat(),
        "group_by": group_by,
        "groups": report["groups"],
        "grand_total": grand,
        "daily_estimate_usd": round(grand["cost_usd"] / days, 4),
        "monthly_estimate_usd": round(grand["cost_usd"] / days * 30, 2),
    }


# ── memory store ───────────────────────────────────────────────────────────
def store_daily_total(total_cost: float, total_runs: int, agent: str, cycle: str) -> bool:
    if not AGENT_CLI.exists():
        return False
    body = (f"cost-tracker daily estimate: ${total_cost:.4f} USD | "
            f"{total_runs} cron runs | "
            f"est. monthly: ${total_cost * 30:.2f}")
    cmd = [PYTHON, str(AGENT_CLI), "store",
           "--agent", agent, "--cycle", cycle,
           "--topic", "cost-tracker:daily",
           "--body", body,
           "--tags", "cost-tracker,daily,experiential",
           "--type", "experiential",
           "--context", f"automated cost estimation, {total_runs} runs"]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
    return r.returncode == 0


# ── main ───────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="cost_tracker — LLM token usage & cost estimation")
    parser.add_argument("--days",   type=int, default=1, help="Number of days back to analyse (default 1)")
    parser.add_argument("--since",  help="Start date YYYY-MM-DD (overrides --days)")
    parser.add_argument("--until",  help="End date YYYY-MM-DD (default today)")
    parser.add_argument("--group",  choices=["category", "model", "job"], default="category")
    parser.add_argument("--json",   action="store_true")
    parser.add_argument("--out",    help="Write report to file path")
    parser.add_argument("--store",  action="store_true", help="Store daily total to agent-memory.db")
    parser.add_argument("--agent",  default="winnie")
    parser.add_argument("--cycle",  default="")
    parser.add_argument("--alert",  type=float, help="Exit 2 if today's cost exceeds this USD threshold")
    args = parser.parse_args()

    now   = datetime.now()
    until = datetime.strptime(args.until, "%Y-%m-%d") if args.until else now
    since = (datetime.strptime(args.since, "%Y-%m-%d") if args.since
             else until - timedelta(days=args.days - 1))

    jobs = load_jobs()
    load_runs(jobs)

    if not jobs:
        print("ERROR: No jobs found in", JOBS_FILE, file=sys.stderr)
        sys.exit(1)

    if args.json:
        output = json.dumps(format_json_out(jobs, since, until, args.group), indent=2)
    else:
        output = format_markdown(jobs, since, until, args.group)

    if args.out:
        Path(args.out).write_text(output)
        print(f"Report written → {args.out}")
    else:
        print(output)

    # Summary to stderr for pipeline use
    report  = _group_report(jobs, since, until, args.group)
    grand   = report["grand_total"]
    days    = max(1, (until - since).days + 1)
    daily   = grand["cost_usd"] / days
    print(f"\n💰 Est. daily: ${daily:.4f} | Est. monthly: ${daily*30:.2f} "
          f"| Total runs: {grand['runs']}", file=sys.stderr)

    if args.store:
        cycle = args.cycle or now.strftime("%Y-%m-%d-%H")
        stored = store_daily_total(daily, grand["runs"], args.agent, cycle)
        print(f"Memory store: {'✅' if stored else '❌'}", file=sys.stderr)

    if args.alert is not None and daily > args.alert:
        print(f"⚠️  ALERT: Daily cost ${daily:.4f} exceeds threshold ${args.alert:.2f}", file=sys.stderr)
        sys.exit(2)

    sys.exit(0)


if __name__ == "__main__":
    main()
