#!/usr/bin/env python3
"""DGM-style benchmark gate for self-improvement loops.

Checks (minimum required):
1) memU health endpoint reachable and status=ok
2) Latest SI output freshness within threshold
3) CHANGELOG.md freshness within threshold

Exit codes:
0 = PASS
1 = FAIL (one or more checks failed)
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import sys
import time
import urllib.request
from pathlib import Path

DEFAULT_MEMU = "http://localhost:8711/api/v1/memu/health"


def iso_from_epoch(ts: float) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime(ts))


def check_memu(url: str, timeout_s: float) -> dict:
    started = time.time()
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            data = json.loads(body)
        ok = (resp.status == 200) and (data.get("status") == "ok")
        return {
            "name": "memu_health",
            "ok": ok,
            "http_status": resp.status,
            "status_field": data.get("status"),
            "latency_ms": round((time.time() - started) * 1000, 2),
        }
    except Exception as e:
        return {
            "name": "memu_health",
            "ok": False,
            "error": str(e),
            "latency_ms": round((time.time() - started) * 1000, 2),
        }


def newest_output(outputs_dir: Path) -> tuple[Path | None, float | None]:
    files = [Path(p) for p in glob.glob(str(outputs_dir / "*-*.md"))]
    if not files:
        return None, None
    newest = max(files, key=lambda p: p.stat().st_mtime)
    return newest, newest.stat().st_mtime


def freshness_check(name: str, ts: float | None, max_age_hours: float, source: str) -> dict:
    if ts is None:
        return {"name": name, "ok": False, "source": source, "error": "missing"}
    age_s = time.time() - ts
    max_age_s = max_age_hours * 3600
    return {
        "name": name,
        "ok": age_s <= max_age_s,
        "source": source,
        "age_hours": round(age_s / 3600, 3),
        "max_age_hours": max_age_hours,
        "timestamp": iso_from_epoch(ts),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run SI benchmark gate checks")
    parser.add_argument("--workspace", default="/Users/harrisonfethe/.openclaw/workspace")
    parser.add_argument("--max-output-age-hours", type=float, default=6.0)
    parser.add_argument("--max-changelog-age-hours", type=float, default=6.0)
    parser.add_argument("--memu-health-url", default=DEFAULT_MEMU)
    parser.add_argument("--timeout-seconds", type=float, default=4.0)
    parser.add_argument("--json", action="store_true", help="print machine-readable JSON")
    args = parser.parse_args()

    workspace = Path(args.workspace)
    outputs_dir = workspace / "self_improvement" / "outputs"
    changelog = workspace / "self_improvement" / "CHANGELOG.md"

    checks = []
    checks.append(check_memu(args.memu_health_url, args.timeout_seconds))

    newest, newest_ts = newest_output(outputs_dir)
    checks.append(
        freshness_check(
            "output_freshness",
            newest_ts,
            args.max_output_age_hours,
            str(newest) if newest else str(outputs_dir),
        )
    )

    cl_ts = changelog.stat().st_mtime if changelog.exists() else None
    checks.append(
        freshness_check(
            "changelog_freshness",
            cl_ts,
            args.max_changelog_age_hours,
            str(changelog),
        )
    )

    passed = all(c.get("ok") for c in checks)
    result = {
        "ok": passed,
        "checked_at": iso_from_epoch(time.time()),
        "checks": checks,
    }

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print("SI Benchmark Gate:", "PASS" if passed else "FAIL")
        for c in checks:
            status = "PASS" if c.get("ok") else "FAIL"
            print(f"- {c['name']}: {status}")
            if c.get("source"):
                print(f"  source: {c['source']}")
            if "age_hours" in c:
                print(f"  age: {c['age_hours']}h (max {c['max_age_hours']}h)")
            if "timestamp" in c:
                print(f"  ts: {c['timestamp']}")
            if "latency_ms" in c:
                print(f"  latency_ms: {c['latency_ms']}")
            if c.get("error"):
                print(f"  error: {c['error']}")

    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
