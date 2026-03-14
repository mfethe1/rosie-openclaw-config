#!/bin/bash
# awesome_memory_monthly.sh — Monthly Awesome-Memory-for-Agents tracker
# Designed to be called by a cron job on the 1st of each month at 09:00 EST.
# Runs awesome_memory_tracker.py and writes report to SI outputs.
set -euo pipefail

PYTHON="/opt/homebrew/bin/python3.13"
SCRIPT="/Users/harrisonfethe/.openclaw/workspace/self_improvement/scripts/awesome_memory_tracker.py"
OUTPUT_DIR="/Users/harrisonfethe/.openclaw/workspace/self_improvement/outputs"
DATE=$(date +%Y-%m-%d)
REPORT="${OUTPUT_DIR}/${DATE}-awesome-memory-report.md"

echo "Running awesome_memory_tracker at $(date)..."
"$PYTHON" "$SCRIPT" --out "$REPORT"
echo "✅ Report written to: $REPORT"
