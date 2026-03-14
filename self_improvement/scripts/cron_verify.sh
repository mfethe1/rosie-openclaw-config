#!/bin/bash
# cron_verify.sh — Post-patch validation loop for SI crons
# Usage: ./cron_verify.sh <cron_id> [expected_model]
# Waits 2 min, checks last 3 logs for errors, reports status

set -e
CRON_ID="${1:-}"
EXPECTED_MODEL="${2:-anthropic/claude-sonnet-4-6}"

if [ -z "$CRON_ID" ]; then
  echo "Usage: $0 <cron_id> [expected_model]"
  exit 1
fi

echo "[$(date)] Verifying cron $CRON_ID after patch..."
sleep 120

echo "[$(date)] Fetching last 3 logs..."
LOGS=$(openclaw cron logs "$CRON_ID" --limit 3 2>&1)

if echo "$LOGS" | grep -q "error\|Error\|failed\|Failed"; then
  echo "❌ FAIL: Cron $CRON_ID has errors in recent logs:"
  echo "$LOGS"
  exit 1
fi

if echo "$LOGS" | grep -q "$EXPECTED_MODEL"; then
  echo "✅ PASS: Cron $CRON_ID running model $EXPECTED_MODEL"
  exit 0
else
  echo "⚠️  WARNING: Expected model $EXPECTED_MODEL not found in recent logs (may not have run yet)."
  echo "$LOGS"
  exit 0
fi
