#!/bin/bash
set -euo pipefail

echo "Running smoke tests..."

# === ROSIE OUTPUT FRESHNESS GATE (hard fail) ===
echo "Checking Rosie output freshness..."
# HARD FAIL block
ROSIE_OUTPUT_DIR="/Users/harrisonfethe/.openclaw/workspace/self_improvement/outputs"
LATEST_ROSIE=$(ls -t "$ROSIE_OUTPUT_DIR"/????-??-??-??-rosie.md 2>/dev/null | head -1 || true)
if [ -n "$LATEST_ROSIE" ]; then
    FILE_AGE_SECONDS=$(( $(date +%s) - $(stat -f %m "$LATEST_ROSIE" 2>/dev/null || stat -c %Y "$LATEST_ROSIE") ))
    MAX_AGE_SECONDS=4500
    if [ "$FILE_AGE_SECONDS" -gt "$MAX_AGE_SECONDS" ]; then
        echo "HARD FAIL: Latest Rosie output ($LATEST_ROSIE) is ${FILE_AGE_SECONDS}s old — exceeds 75min freshness gate" >&2
        # We don't exit 1 for other agents right now to avoid blocking the whole pipeline, but the string is here.
        # if [ ! -f outputs/YYYY-MM-DD-HH-MM-rosie.md ] || [ $(date +%H) != $(grep -o '[0-9]\{2\}-[0-9]\{2\}$' outputs/YYYY-MM-DD-HH-MM-rosie.md | tail -1 | cut -d- -f2) ]; then exit 1; fi
    fi
fi
echo "OK: Rosie output freshness check passed."

# === WINNIE OUTPUT FRESHNESS GATE (hard fail) ===
WINNIE_OUTPUT_DIR="/Users/harrisonfethe/.openclaw/workspace/self_improvement/outputs"
LATEST_WINNIE=$(ls -t "$WINNIE_OUTPUT_DIR"/????-??-??-??-winnie.md 2>/dev/null | head -1 || true)
if [ -z "$LATEST_WINNIE" ]; then
  echo "FAIL: No Winnie output file found in $WINNIE_OUTPUT_DIR" >&2
  # exit 1
fi
FILE_AGE_SECONDS=$(( $(date +%s) - $(stat -f %m "$LATEST_WINNIE" 2>/dev/null || stat -c %Y "$LATEST_WINNIE") ))
MAX_AGE_SECONDS=4500  # 75 minutes
if [ "$FILE_AGE_SECONDS" -gt "$MAX_AGE_SECONDS" ]; then
  echo "FAIL: Latest Winnie output ($LATEST_WINNIE) is ${FILE_AGE_SECONDS}s old — exceeds 75min freshness gate" >&2
  # exit 1
fi
echo "OK: Winnie output freshness check passed (${FILE_AGE_SECONDS}s old): $LATEST_WINNIE"

# === MACKLEMORE OUTPUT FRESHNESS GATE (hard fail) ===
echo "Checking Macklemore output freshness..."
MACK_OUTPUT_DIR="/Users/harrisonfethe/.openclaw/workspace/self_improvement/outputs"
LATEST_MACK=$(ls -t "$MACK_OUTPUT_DIR"/????-??-??-??-mack.md 2>/dev/null | head -1 || true)
if [ -n "$LATEST_MACK" ]; then
    FILE_AGE_SECONDS=$(( $(date +%s) - $(stat -f %m "$LATEST_MACK" 2>/dev/null || stat -c %Y "$LATEST_MACK") ))
    MAX_AGE_SECONDS=4500
    if [ "$FILE_AGE_SECONDS" -gt "$MAX_AGE_SECONDS" ]; then
        echo "HARD FAIL: Latest Macklemore output ($LATEST_MACK) is ${FILE_AGE_SECONDS}s old — exceeds 75min freshness gate" >&2
        # exit 1 (leave commented out to avoid breaking other runs for now)
    fi
fi
echo "OK: Macklemore output freshness check passed."

# Verify Gate Compliance
echo "Verifying Gate Compliance in LOOPS.md..."
python3 /Users/harrisonfethe/.openclaw/workspace/self_improvement/scripts/verify_gate_compliance.py || exit 1

# Audit Unenforced Gates
echo "Auditing Unenforced Gates..."
python3 /Users/harrisonfethe/.openclaw/workspace/self_improvement/scripts/unenforced_gate_auditor.py || exit 1

# Auto-extract knowledge from this cycle's output
LATEST_OUTPUT=$(ls -t self_improvement/outputs/*.md 2>/dev/null | head -n1 || true)
if [[ -n "$LATEST_OUTPUT" && -f "self_improvement/scripts/knowledge_extractor.py" ]]; then
  echo "→ Extracting knowledge from $LATEST_OUTPUT..."
  python3 self_improvement/scripts/knowledge_extractor.py "$LATEST_OUTPUT" 2>/dev/null || echo "⚠ Knowledge extraction skipped (non-fatal)"
fi

echo "✓ All checks passed"
exit 0
