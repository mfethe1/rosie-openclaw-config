#!/bin/bash
# Dual-condition loop exit gate + hourly budget guard for long cron loops
# Limits execution time and tracks invocation count per hour
set -euo pipefail

CRON_ID=$1
COMMAND="${@:2}"
MAX_MINUTES=55
MAX_CALLS_PER_HOUR=5

LOCK_DIR="/tmp/cron_guard_${CRON_ID}"
mkdir -p "$LOCK_DIR"
HOUR_MARKER="$LOCK_DIR/$(date +%Y%m%d%H)"

COUNT=$(cat "$HOUR_MARKER" 2>/dev/null || echo "0")
if [ "$COUNT" -ge "$MAX_CALLS_PER_HOUR" ]; then
    echo "CRON_GUARD: Hourly limit reached ($MAX_CALLS_PER_HOUR) for cron $CRON_ID" >&2
    exit 1
fi
echo $((COUNT + 1)) > "$HOUR_MARKER"

# Run with timeout
timeout "${MAX_MINUTES}m" $COMMAND
EXIT_CODE=$?

if [ $EXIT_CODE -eq 124 ]; then
    echo "CRON_GUARD: Exit gate triggered (Timeout $MAX_MINUTES min) for cron $CRON_ID" >&2
    exit 124
fi
exit $EXIT_CODE
