#!/bin/bash
# Enforce cron patch verification gate
# Called by smoke_test.sh to verify any cron edits were validated

set -euo pipefail

OUTPUT_FILE="$1"

if [[ ! -f "$OUTPUT_FILE" ]]; then
  echo "❌ GATE FAILURE: Output file missing, cannot verify cron patch compliance"
  exit 1
fi

# Check if output mentions cron editing
if grep -qiE "cron (edit|patch|update)" "$OUTPUT_FILE"; then
  # Cron was edited, verification proof must exist
  if grep -q "cron_patch_verifier.sh" "$OUTPUT_FILE" || grep -q "no crons edited this cycle" "$OUTPUT_FILE"; then
    echo "✅ Cron patch verification gate: PASS (proof found)"
    exit 0
  else
    echo "❌ GATE FAILURE: Cron edited but no cron_patch_verifier.sh proof in output"
    echo "Required: Run 'self_improvement/scripts/cron_patch_verifier.sh <cron_id>' and include output"
    exit 1
  fi
else
  # No cron edits mentioned, gate not applicable
  echo "✅ Cron patch verification gate: PASS (not applicable - no cron edits)"
  exit 0
fi