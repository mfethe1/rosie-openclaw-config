#!/bin/bash
# =============================================================================
# hitl_check.sh — D-020: HITL_REQUIRED Gate
# Scans TODO.md for HITL_REQUIRED tasks and blocks marking DONE without GO.
#
# Usage: bash hitl_check.sh [TODO_path]
# Exit: 0 = all clear, 1 = HITL tasks found without GO
# =============================================================================

TODO_PATH="${1:-/Users/harrisonfethe/.openclaw/workspace/self_improvement/TODO.md}"

if [ ! -f "$TODO_PATH" ]; then
  echo "❌ TODO.md not found: $TODO_PATH"
  exit 1
fi

# Find open HITL_REQUIRED tasks (unchecked)
HITL_OPEN=$(grep -n "^\- \[ \].*HITL_REQUIRED" "$TODO_PATH" 2>/dev/null)
# Find HITL tasks already marked done WITH GO comment
HITL_DONE_WITH_GO=$(grep -n "^\- \[x\].*HITL_REQUIRED.*GO\b" "$TODO_PATH" 2>/dev/null)
# Find HITL tasks marked done WITHOUT GO comment (violation)
HITL_DONE_NO_GO=$(grep -n "^\- \[x\].*HITL_REQUIRED" "$TODO_PATH" 2>/dev/null | grep -v "GO\b")

echo "=== HITL_REQUIRED Gate Check ==="
echo "File: $TODO_PATH"
echo ""

VIOLATIONS=0

if [ -n "$HITL_OPEN" ]; then
  echo "⏳ Open HITL_REQUIRED tasks (awaiting human GO):"
  while IFS= read -r line; do
    echo "   $line"
  done <<< "$HITL_OPEN"
  echo ""
fi

if [ -n "$HITL_DONE_NO_GO" ]; then
  echo "🚨 VIOLATION — HITL tasks marked DONE without GO comment:"
  while IFS= read -r line; do
    echo "   $line"
    VIOLATIONS=$((VIOLATIONS + 1))
  done <<< "$HITL_DONE_NO_GO"
  echo ""
fi

if [ -n "$HITL_DONE_WITH_GO" ]; then
  echo "✅ Properly closed HITL tasks (with GO):"
  while IFS= read -r line; do
    echo "   $line"
  done <<< "$HITL_DONE_WITH_GO"
  echo ""
fi

# Summary
OPEN_COUNT=$(echo "$HITL_OPEN" | grep -c "." 2>/dev/null || echo 0)
[ -z "$HITL_OPEN" ] && OPEN_COUNT=0

echo "Summary: $OPEN_COUNT open HITL tasks, $VIOLATIONS violations"
echo ""

if [ "$VIOLATIONS" -gt 0 ]; then
  echo "❌ HITL GATE FAILED — $VIOLATIONS task(s) marked DONE without human GO"
  echo "   Action: Un-mark these tasks, get explicit GO from Michael, then re-mark DONE."
  exit 1
else
  echo "✅ HITL gate passed"
  exit 0
fi
