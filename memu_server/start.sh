#!/bin/bash
# Start (or restart) memU bridge server with PID + health checks
set -euo pipefail

# Force canonical local API key so inherited shell/test env vars cannot poison health checks.
export MEMU_API_KEY="openclaw-memu-local-2026"
export MEMU_LOG_LEVEL="${MEMU_LOG_LEVEL:-INFO}"
export MEMU_STRICT_SCHEMA_MODE="${MEMU_STRICT_SCHEMA_MODE:-1}"

DEPLOY_ENV="$HOME/.openclaw/secrets/deploy.env"
if [ -f "$DEPLOY_ENV" ]; then
  # Load deploy-time secrets (e.g., ANTHROPIC_API_KEY for SimpleMem compression)
  set -a
  # shellcheck disable=SC1090
  . "$DEPLOY_ENV"
  set +a
fi

PYTHON_BIN="/opt/homebrew/bin/python3.13"
SERVER_SCRIPT="/Users/harrisonfethe/.openclaw/workspace/memu_server/server.py"
PID_FILE="/tmp/memu_server.pid"
LOG_FILE="/Users/harrisonfethe/.openclaw/workspace/memory/memu_server.log"
HEALTH_URL="http://localhost:8711/api/v1/memu/health"

is_healthy() {
  curl -fsS --max-time 2 -H "Authorization: Bearer $MEMU_API_KEY" "$HEALTH_URL" >/dev/null 2>&1
}

cleanup_stale_pid() {
  if [ -f "$PID_FILE" ]; then
    local old_pid
    old_pid="$(cat "$PID_FILE" 2>/dev/null || true)"
    if [ -n "${old_pid:-}" ] && ! kill -0 "$old_pid" 2>/dev/null; then
      rm -f "$PID_FILE"
    fi
  fi
}

start_server() {
  # server.py already writes structured logs to $LOG_FILE via FileHandler.
  # Avoid duplicating every line by not redirecting stdout/stderr into same file.
  nohup "$PYTHON_BIN" "$SERVER_SCRIPT" >/dev/null 2>&1 &
  echo $! > "$PID_FILE"
}

cleanup_stale_pid

# If process exists but health endpoint fails, restart it.
if [ -f "$PID_FILE" ]; then
  PID="$(cat "$PID_FILE")"
  if kill -0 "$PID" 2>/dev/null; then
    if is_healthy; then
      echo "memU server already running and healthy (PID $PID)"
      exit 0
    fi

    echo "memU server process exists but is unhealthy (PID $PID). Restarting..."
    kill "$PID" 2>/dev/null || true
    sleep 1
    kill -9 "$PID" 2>/dev/null || true
    rm -f "$PID_FILE"
  fi
fi

echo "Starting memU bridge server..."
start_server

# Wait up to ~10s for healthy startup
for _ in {1..10}; do
  PID="$(cat "$PID_FILE" 2>/dev/null || true)"
  if [ -n "${PID:-}" ] && kill -0 "$PID" 2>/dev/null && is_healthy; then
    echo "✅ memU server started (PID $PID) on port 8711"
    echo "   Health: curl $HEALTH_URL"
    exit 0
  fi
  sleep 1
done

echo "❌ memU server failed health check after start. Check $LOG_FILE"
exit 1
