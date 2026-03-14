#!/opt/homebrew/bin/python3.13
"""
checkpoint_runner.py

Small checkpoint helper for long-running tasks (>300s).
- Persists step completion state to a JSON checkpoint file.
- Skips already-completed steps (resume-safe).
- Tracks retries, duration, and last error.

Example:
  /opt/homebrew/bin/python3.13 self_improvement/scripts/checkpoint_runner.py \
    --checkpoint-file /tmp/si-checkpoint.json \
    --step fetch_data \
    --timeout 600 \
    --command "python3 heavy_script.py --phase fetch"
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict


@dataclass
class Result:
    ok: bool
    code: int
    message: str


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_state(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {"schema_version": "1.0", "created_at": now_iso(), "steps": {}}
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        # Corrupted checkpoint should not hard-block execution.
        return {
            "schema_version": "1.0",
            "created_at": now_iso(),
            "recovered_from_corruption": True,
            "steps": {},
        }


def save_state(path: Path, state: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    state["updated_at"] = now_iso()
    path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n")


def run_step(
    checkpoint_file: Path,
    step: str,
    command: str,
    timeout: int,
    max_retries: int,
    shell: str,
) -> Result:
    state = load_state(checkpoint_file)
    steps = state.setdefault("steps", {})
    record = steps.get(step, {})

    if record.get("status") == "completed":
        return Result(True, 0, f"skip: step '{step}' already completed")

    attempts = int(record.get("attempts", 0))

    while attempts < max_retries:
        attempts += 1
        start_ts = time.time()
        record.update(
            {
                "status": "running",
                "attempts": attempts,
                "last_started_at": now_iso(),
                "command": command,
                "timeout_seconds": timeout,
            }
        )
        steps[step] = record
        save_state(checkpoint_file, state)

        try:
            proc = subprocess.run(
                [shell, "-lc", command],
                text=True,
                capture_output=True,
                timeout=timeout,
            )
            elapsed = round(time.time() - start_ts, 3)
            record["last_duration_seconds"] = elapsed
            record["last_exit_code"] = proc.returncode
            record["last_stdout_tail"] = (proc.stdout or "")[-2000:]
            record["last_stderr_tail"] = (proc.stderr or "")[-2000:]

            if proc.returncode == 0:
                record["status"] = "completed"
                record["completed_at"] = now_iso()
                steps[step] = record
                save_state(checkpoint_file, state)
                return Result(True, 0, f"ok: step '{step}' completed in {elapsed}s")

            record["status"] = "failed"
            record["last_error"] = f"non-zero exit: {proc.returncode}"
            steps[step] = record
            save_state(checkpoint_file, state)

        except subprocess.TimeoutExpired as exc:
            elapsed = round(time.time() - start_ts, 3)
            record["status"] = "failed"
            record["last_duration_seconds"] = elapsed
            record["last_error"] = f"timeout after {timeout}s"
            record["last_stdout_tail"] = (exc.stdout or "")[-2000:]
            record["last_stderr_tail"] = (exc.stderr or "")[-2000:]
            steps[step] = record
            save_state(checkpoint_file, state)

    return Result(False, 1, f"fail: step '{step}' exhausted retries ({max_retries})")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Resume-safe checkpoint wrapper for long-running shell steps")
    p.add_argument("--checkpoint-file", required=True, help="Absolute path to checkpoint JSON file")
    p.add_argument("--step", required=True, help="Unique step key")
    p.add_argument("--command", required=True, help="Shell command to execute")
    p.add_argument("--timeout", type=int, default=600, help="Per-attempt timeout (seconds)")
    p.add_argument("--max-retries", type=int, default=2, help="Max attempts before hard fail")
    p.add_argument("--shell", default="/bin/zsh", help="Shell binary for command execution")
    return p


def main() -> int:
    args = build_parser().parse_args()
    checkpoint_file = Path(args.checkpoint_file).expanduser()

    result = run_step(
        checkpoint_file=checkpoint_file,
        step=args.step,
        command=args.command,
        timeout=args.timeout,
        max_retries=args.max_retries,
        shell=args.shell,
    )
    print(result.message)
    return result.code


if __name__ == "__main__":
    sys.exit(main())
