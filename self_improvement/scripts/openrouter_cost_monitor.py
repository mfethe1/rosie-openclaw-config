#!/usr/bin/env python3
"""OpenRouter API usage and cost monitor.

Reads API key from ~/.openclaw/secrets/openrouter.env, queries
https://openrouter.ai/api/v1/auth/key, prints usage summaries, and logs
timestamped snapshots to JSONL.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib import error, request


API_URL = "https://openrouter.ai/api/v1/auth/key"
DEFAULT_ENV_PATH = Path("~/.openclaw/secrets/openrouter.env").expanduser()
DEFAULT_LOG_PATH = Path(
    "~/.openclaw/workspace/self_improvement/logs/openrouter_costs.jsonl"
).expanduser()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Query OpenRouter key usage and log cost snapshots."
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output machine-readable JSON",
    )
    parser.add_argument(
        "--alert",
        action="store_true",
        help="Print warning if daily spend exceeds threshold",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=5.0,
        help="Daily spend alert threshold in dollars (default: 5.0)",
    )
    parser.add_argument(
        "--env-file",
        default=str(DEFAULT_ENV_PATH),
        help=f"Path to env file (default: {DEFAULT_ENV_PATH})",
    )
    parser.add_argument(
        "--log-file",
        default=str(DEFAULT_LOG_PATH),
        help=f"Path to JSONL snapshot log (default: {DEFAULT_LOG_PATH})",
    )
    return parser.parse_args()


def load_api_key(env_file: Path) -> str:
    if not env_file.exists():
        raise RuntimeError(f"API key file not found: {env_file}")

    try:
        content = env_file.read_text(encoding="utf-8")
    except OSError as exc:
        raise RuntimeError(f"Could not read API key file {env_file}: {exc}") from exc

    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        if "=" not in line:
            continue

        key, value = line.split("=", 1)
        if key.strip() != "OPENROUTER_API_KEY":
            continue

        api_key = value.strip().strip('"').strip("'")
        if not api_key:
            raise RuntimeError(f"OPENROUTER_API_KEY is empty in env file: {env_file}")
        return api_key

    raise RuntimeError(f"OPENROUTER_API_KEY not found in env file: {env_file}")


def request_usage(api_key: str) -> dict[str, Any]:
    req = request.Request(
        API_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json",
        },
        method="GET",
    )

    try:
        with request.urlopen(req, timeout=20) as resp:
            body = resp.read().decode("utf-8")
            payload = json.loads(body)
    except error.HTTPError as exc:
        details = ""
        try:
            details = exc.read().decode("utf-8", errors="replace")
        except (OSError, ValueError):
            details = ""
        message = f"OpenRouter API HTTP error {exc.code}: {exc.reason}"
        if details:
            message = f"{message}. Response: {details}"
        raise RuntimeError(message) from exc
    except error.URLError as exc:
        reason = getattr(exc, "reason", exc)
        raise RuntimeError(f"OpenRouter API connection error: {reason}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Invalid JSON from OpenRouter API: {exc}") from exc

    if not isinstance(payload, dict):
        raise RuntimeError(
            "Unexpected API response format: top-level JSON is not an object"
        )

    data = payload.get("data")
    if not isinstance(data, dict):
        raise RuntimeError("Unexpected API response format: missing 'data' object")

    return data


def coerce_float(data: dict[str, Any], field: str) -> float:
    value = data.get(field)
    if value is None:
        raise RuntimeError(f"Missing '{field}' in API response")
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise RuntimeError(
            f"Invalid '{field}' value in API response: {value!r}"
        ) from exc


def build_snapshot(data: dict[str, Any]) -> dict[str, Any]:
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "usage_total": coerce_float(data, "usage"),
        "usage_daily": coerce_float(data, "usage_daily"),
        "usage_weekly": coerce_float(data, "usage_weekly"),
        "usage_monthly": coerce_float(data, "usage_monthly"),
    }


def append_jsonl(log_file: Path, entry: dict[str, Any]) -> None:
    try:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        with log_file.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, separators=(",", ":")) + "\n")
    except OSError as exc:
        raise RuntimeError(f"Could not write log file {log_file}: {exc}") from exc


def format_human(snapshot: dict[str, Any]) -> str:
    return "\n".join(
        [
            "OpenRouter Cost Snapshot",
            f"timestamp_utc: {snapshot['timestamp']}",
            f"daily_usd: {snapshot['usage_daily']:.6f}",
            f"weekly_usd: {snapshot['usage_weekly']:.6f}",
            f"monthly_usd: {snapshot['usage_monthly']:.6f}",
            f"total_usd: {snapshot['usage_total']:.6f}",
        ]
    )


def main() -> int:
    args = parse_args()

    if args.threshold < 0:
        print("ERROR: --threshold must be non-negative", file=sys.stderr)
        return 2

    env_file = Path(os.path.expanduser(args.env_file))
    log_file = Path(os.path.expanduser(args.log_file))

    try:
        api_key = load_api_key(env_file)
        data = request_usage(api_key)
        snapshot = build_snapshot(data)
        append_jsonl(log_file, snapshot)
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(snapshot, separators=(",", ":")))
    else:
        print(format_human(snapshot))

    if args.alert and snapshot["usage_daily"] > args.threshold:
        warning = (
            "WARNING: OpenRouter daily spend "
            f"${snapshot['usage_daily']:.2f} exceeded threshold ${args.threshold:.2f}"
        )
        print(warning, file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
