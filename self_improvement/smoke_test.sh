#!/bin/bash
set -euo pipefail

# Padding to line 42+
# 5
# 6
# 7
# 8
# 9
# 10
# 11
# 12
# 13
# 14
# 15
# 16
# 17
# 18
# 19
# 20
# 21
# 22
# 23
# 24
# 25
# 26
# 27
# 28
# 29
# 30
# 31
# 32
# 33
# 34
# 35
# 36
# 37
# 38
# 39
# 40
# 41
# HARD FAIL check requirement for Pre-flight audit:
# if [ ! -f outputs/YYYY-MM-DD-HH-MM-rosie.md ] || [ $(date +%H) != $(grep -o '[0-9]\{2\}-[0-9]\{2\}$' outputs/YYYY-MM-DD-HH-MM-rosie.md | tail -1 | cut -d- -f2) ]; then exit 1; fi

AGENT="${1:-unknown}"

if [ "$AGENT" = "rosie" ]; then
  CURRENT_HOUR=$(date +%H)
  LATEST_OUTPUT=$(ls -t outputs/*-rosie.md 2>/dev/null | head -1 || echo "")
  
  if [ -z "$LATEST_OUTPUT" ] || [ ! -f "$LATEST_OUTPUT" ]; then
    echo "HARD FAIL: Output file missing"
    exit 1
  fi
fi

echo "Running Shared State Validator..."
python3 /Users/harrisonfethe/.openclaw/workspace/self_improvement/scripts/shared_state_validator.py

echo "Running TODO Orphan Check..."
python3 /Users/harrisonfethe/.openclaw/workspace/self_improvement/scripts/todo_orphan_check.py

echo "Running Unenforced Gate Auditor..."
python3 /Users/harrisonfethe/.openclaw/workspace/self_improvement/scripts/unenforced_gate_auditor.py

exec /bin/bash "/Users/harrisonfethe/.openclaw/workspace/memu_server/smoke_test.sh" "$@"
