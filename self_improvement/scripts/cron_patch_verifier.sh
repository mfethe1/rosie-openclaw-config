#!/bin/bash
# Cron Patch Verifier — enforces CRON PATCH VERIFICATION gate
# Usage: ./cron_patch_verifier.sh <cron_id_1> [cron_id_2] ...

set -euo pipefail

if [ $# -eq 0 ]; then
  echo "Usage: $0 <cron_id_1> [cron_id_2] ..."
  exit 1
fi

OUTPUT_FILE="verification_$(date +%Y-%m-%d-%H-%M).txt"
echo "Cron Patch Verification — $(date)" > "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"

echo "Waiting 2 minutes for cron execution window..."
sleep 120

FAILURES=0

for CRON_ID in "$@"; do
  echo "Checking cron $CRON_ID..." | tee -a "$OUTPUT_FILE"
  
  LOGS=$(openclaw cron logs "$CRON_ID" --limit 3 2>&1 || true)
  echo "$LOGS" >> "$OUTPUT_FILE"
  
  if echo "$LOGS" | grep -qE "(status.*ok|delivered|success)"; then
    echo "✓ $CRON_ID: VERIFIED" | tee -a "$OUTPUT_FILE"
  elif echo "$LOGS" | grep -qE "(error|failed|chat not found|model.*not found)"; then
    echo "✗ $CRON_ID: DELIVERY FAILURE DETECTED" | tee -a "$OUTPUT_FILE"
    FAILURES=$((FAILURES + 1))
  else
    echo "⚠ $CRON_ID: NO RECENT EXECUTION (may be scheduled later)" | tee -a "$OUTPUT_FILE"
  fi
  
  echo "" >> "$OUTPUT_FILE"
done

echo "" >> "$OUTPUT_FILE"
echo "Summary: $FAILURES failure(s) detected out of $# cron(s) checked" | tee -a "$OUTPUT_FILE"

if [ $FAILURES -gt 0 ]; then
  echo "" >> "$OUTPUT_FILE"
  echo "ACTION REQUIRED: Add failed crons to blockers board with proof artifacts from this file" >> "$OUTPUT_FILE"
  exit 1
fi

echo "Verification complete. Results saved to $OUTPUT_FILE"
exit 0