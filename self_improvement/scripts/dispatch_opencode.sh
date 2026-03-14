#!/usr/bin/env bash

set -u -o pipefail

WORKSPACE="${1:-}"
PROMPT="${2:-}"
TIMEOUT="${3:-300}"
REASONING_EFFORT="${4:-}"
TOOL_BIN="/opt/homebrew/bin/opencode"

if [[ -f "$HOME/.profile" ]]; then
  source "$HOME/.profile" >/dev/null 2>&1 || true
fi
if [[ -f "$HOME/.zshrc" ]]; then
  source "$HOME/.zshrc" >/dev/null 2>&1 || true
fi
if [[ -f "$HOME/.bashrc" ]]; then
  source "$HOME/.bashrc" >/dev/null 2>&1 || true
fi

if [[ -z "$WORKSPACE" || -z "$PROMPT" ]]; then
  python3 -c 'import json; print(json.dumps({"exit_code": 2, "stdout": "", "stderr": "usage: dispatch_opencode.sh <workspace> <prompt> [timeout]", "timed_out": False}))'
  exit 2
fi

if [[ ! -d "$WORKSPACE" ]]; then
  python3 -c 'import json,sys; print(json.dumps({"exit_code": 2, "stdout": "", "stderr": f"workspace not found: {sys.argv[1]}", "timed_out": False}))' "$WORKSPACE"
  exit 2
fi

STDOUT_FILE="$(mktemp)"
STDERR_FILE="$(mktemp)"

CMD=("$TOOL_BIN" "run" "$PROMPT")
if [[ -n "$REASONING_EFFORT" ]]; then
  CMD+=("--reasoning-effort" "$REASONING_EFFORT")
fi

(
  cd "$WORKSPACE" || exit 1
  "${CMD[@]}" >"$STDOUT_FILE" 2>"$STDERR_FILE"
)
EXIT_CODE=$?

python3 -c 'import json,sys,pathlib; out=pathlib.Path(sys.argv[1]).read_text(encoding="utf-8", errors="replace"); err=pathlib.Path(sys.argv[2]).read_text(encoding="utf-8", errors="replace"); print(json.dumps({"exit_code": int(sys.argv[3]), "stdout": out, "stderr": err, "timed_out": False, "timeout_seconds": int(sys.argv[4])}, ensure_ascii=True))' "$STDOUT_FILE" "$STDERR_FILE" "$EXIT_CODE" "$TIMEOUT"

rm -f "$STDOUT_FILE" "$STDERR_FILE"
exit "$EXIT_CODE"
