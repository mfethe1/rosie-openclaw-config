#!/opt/homebrew/bin/python3.13
"""Lightweight command performance profiler for SI workflows.

Usage:
  python3.13 performance_profiler.py --name memu-health --cmd "curl -s http://127.0.0.1:12345/health" --runs 5 \
    --json-out /tmp/profile.json --md-out /tmp/profile.md
"""

from __future__ import annotations

import argparse
import json
import shlex
import statistics
import subprocess
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path


@dataclass
class RunResult:
    run: int
    returncode: int
    duration_ms: float
    stdout_preview: str
    stderr_preview: str


def run_once(cmd: str, run: int, timeout: int) -> RunResult:
    start = time.perf_counter()
    proc = subprocess.run(
        cmd,
        shell=True,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    dur_ms = (time.perf_counter() - start) * 1000
    return RunResult(
        run=run,
        returncode=proc.returncode,
        duration_ms=round(dur_ms, 3),
        stdout_preview=(proc.stdout or "")[:200].strip(),
        stderr_preview=(proc.stderr or "")[:200].strip(),
    )


def main() -> int:
    ap = argparse.ArgumentParser(description="Profile command runtime over multiple runs.")
    ap.add_argument("--name", required=True, help="Profile name")
    ap.add_argument("--cmd", required=True, help="Shell command to execute")
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--timeout", type=int, default=120)
    ap.add_argument("--json-out", help="Optional JSON output path")
    ap.add_argument("--md-out", help="Optional markdown output path")
    args = ap.parse_args()

    results: list[RunResult] = []
    for i in range(1, args.runs + 1):
        try:
            results.append(run_once(args.cmd, i, args.timeout))
        except subprocess.TimeoutExpired:
            results.append(
                RunResult(
                    run=i,
                    returncode=124,
                    duration_ms=float(args.timeout * 1000),
                    stdout_preview="",
                    stderr_preview=f"Timeout after {args.timeout}s",
                )
            )

    durations = [r.duration_ms for r in results]
    success_count = sum(1 for r in results if r.returncode == 0)
    summary = {
        "name": args.name,
        "command": args.cmd,
        "runs": args.runs,
        "success_rate": round(success_count / max(args.runs, 1), 3),
        "duration_ms": {
            "min": round(min(durations), 3),
            "max": round(max(durations), 3),
            "avg": round(statistics.mean(durations), 3),
            "p50": round(statistics.median(durations), 3),
        },
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "results": [asdict(r) for r in results],
    }

    if args.json_out:
        p = Path(args.json_out)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    if args.md_out:
        p = Path(args.md_out)
        p.parent.mkdir(parents=True, exist_ok=True)
        lines = [
            f"# Performance Profile: {args.name}",
            "",
            f"- Command: `{args.cmd}`",
            f"- Runs: {args.runs}",
            f"- Success rate: {summary['success_rate']*100:.1f}%",
            f"- Avg: {summary['duration_ms']['avg']} ms | Min: {summary['duration_ms']['min']} ms | Max: {summary['duration_ms']['max']} ms",
            "",
            "## Run Results",
            "",
            "| Run | RC | Duration (ms) | stderr |",
            "|---:|---:|---:|---|",
        ]
        for r in results:
            err = (r.stderr_preview or "").replace("|", "\\|")
            lines.append(f"| {r.run} | {r.returncode} | {r.duration_ms} | {err} |")
        p.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(json.dumps(summary, indent=2))
    return 0 if success_count == args.runs else 1


if __name__ == "__main__":
    raise SystemExit(main())
