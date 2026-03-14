#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_TIMEOUT_SECONDS = 300
VALID_TOOLS = ("auggie", "opencode", "gemini", "codex")
SCRIPT_DIR = Path(__file__).resolve().parent
LOG_PATH = (
    Path.home()
    / ".openclaw"
    / "workspace"
    / "self_improvement"
    / "logs"
    / "cli_dispatches.jsonl"
)
WRAPPERS = {
    "auggie": SCRIPT_DIR / "dispatch_auggie.sh",
    "opencode": SCRIPT_DIR / "dispatch_opencode.sh",
    "gemini": SCRIPT_DIR / "dispatch_gemini.sh",
    "codex": SCRIPT_DIR / "dispatch_codex.sh",
}


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Dispatch a coding task to an external CLI tool.",
    )
    parser.add_argument(
        "--tool",
        required=True,
        choices=VALID_TOOLS,
        help="Target tool.",
    )
    parser.add_argument(
        "--task",
        required=True,
        help="Natural language task prompt.",
    )
    parser.add_argument(
        "--workspace",
        required=True,
        help="Workspace path to run the CLI tool in.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT_SECONDS,
        help=f"Timeout in seconds (default: {DEFAULT_TIMEOUT_SECONDS}).",
    )
    parser.add_argument(
        "--reasoning-effort",
        type=str,
        choices=["low", "medium", "high"],
        help="Reasoning effort level (low/medium/high) for supported tools (e.g. opencode).",
    )
    return parser.parse_args()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_parse_json(text: str) -> dict[str, Any] | None:
    if not text:
        return None
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None


def _run_dispatch(
    tool: str, task: str, workspace: Path, timeout: int, reasoning_effort: str | None = None
) -> dict[str, Any]:
    wrapper = WRAPPERS[tool]
    if not wrapper.exists():
        return {
            "exit_code": 127,
            "stdout": "",
            "stderr": f"Wrapper not found: {wrapper}",
            "timed_out": False,
            "wrapper_output": None,
        }

    command = [str(wrapper), str(workspace), task, str(timeout)]
    if reasoning_effort and tool == "opencode":
        command.append(reasoning_effort)
    start = time.time()
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        parsed = _safe_parse_json(completed.stdout.strip())
        result: dict[str, Any] = {
            "exit_code": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
            "timed_out": False,
            "wrapper_output": parsed,
        }
        if parsed and {"exit_code", "stdout", "stderr"}.issubset(parsed):
            result["exit_code"] = parsed["exit_code"]
            result["stdout"] = parsed["stdout"]
            result["stderr"] = parsed["stderr"]
            result["timed_out"] = bool(parsed.get("timed_out", False))
        result["duration_seconds"] = round(time.time() - start, 3)
        return result
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout if isinstance(exc.stdout, str) else ""
        stderr = exc.stderr if isinstance(exc.stderr, str) else ""
        return {
            "exit_code": 124,
            "stdout": stdout,
            "stderr": stderr or f"Dispatcher timeout after {timeout} seconds",
            "timed_out": True,
            "wrapper_output": None,
            "duration_seconds": round(time.time() - start, 3),
        }


def _append_log(record: dict[str, Any]) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=True) + "\n")


def main() -> int:
    args = _parse_args()
    workspace = Path(args.workspace).expanduser().resolve()

    if not workspace.exists() or not workspace.is_dir():
        output = {
            "tool": args.tool,
            "task": args.task,
            "workspace": str(workspace),
            "timeout_seconds": args.timeout,
            "exit_code": 2,
            "stdout": "",
            "stderr": f"Workspace is not a directory: {workspace}",
            "timed_out": False,
            "timestamp": _now_iso(),
        }
        print(json.dumps(output, ensure_ascii=True))
        _append_log(output)
        return 2

    result = _run_dispatch(args.tool, args.task, workspace, args.timeout, args.reasoning_effort)
    response = {
        "tool": args.tool,
        "task": args.task,
        "workspace": str(workspace),
        "timeout_seconds": args.timeout,
        "reasoning_effort": args.reasoning_effort,
        "timestamp": _now_iso(),
        "exit_code": result["exit_code"],
        "stdout": result["stdout"],
        "stderr": result["stderr"],
        "timed_out": result["timed_out"],
        "duration_seconds": result.get("duration_seconds"),
    }
    if result.get("wrapper_output") is not None:
        response["wrapper_output"] = result["wrapper_output"]

    print(json.dumps(response, ensure_ascii=True))
    _append_log(response)
    return int(result["exit_code"])


if __name__ == "__main__":
    sys.exit(main())
