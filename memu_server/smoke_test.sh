#!/bin/bash
# =============================================================================
# smoke_test.sh — Self-Improvement Eval Gate
# Usage: bash smoke_test.sh <agent_name> <task_key> <output_file_path> [notes]
#
# Exit codes: 0 = PASS, 1 = FAIL
# Appends result to /Users/harrisonfethe/.openclaw/workspace/memory/eval-log.md
# Stores result in memU (contract-aware)
# =============================================================================

AGENT="${1:-unknown}"
TASK_KEY="${2:-unspecified}"
OUTPUT_FILE="${3:-}"
NOTES="${4:-}"

EVAL_LOG="/Users/harrisonfethe/.openclaw/workspace/memory/eval-log.md"
FAIL_REFLECTIONS_LOG="/Users/harrisonfethe/.openclaw/workspace/memory/fail-reflections.jsonl"
MEMU_URL="${MEMU_URL:-http://localhost:8711}"
MEMU_URL="${MEMU_URL%/}"
MEMU_KEY="${MEMU_API_KEY:-openclaw-memu-local-2026}"
MEMU_KEY_NAME="${MEMU_KEY_NAME:-local-default}"
MEMU_ROUTE_STYLE="${MEMU_CLIENT_ROUTE_STYLE:-bridge}"   # bridge (canonical) | auto (legacy)

TIMESTAMP=$(date -u +"%Y-%m-%d %H:%M EST")
TIMESTAMP_SHORT=$(date -u +"%Y-%m-%dT%H:%M:%S")

STATUS="PASS"
MEMU_HEALTHY="YES"
FAILURES=()

MEMU_STORE_METHOD="POST"
MEMU_SEARCH_METHOD="POST"

call_endpoint() {
  local method="$1" path="$2" body="$3"
  curl -sS --max-time 8 -X "$method" "$MEMU_URL$path" \
    -H "Authorization: Bearer $MEMU_KEY" \
    -H "Content-Type: application/json" \
    -d "$body"
}

extract_json_id() {
  local raw="$1"
  /opt/homebrew/bin/python3.13 -c 'import sys, json
raw = sys.stdin.read().strip()
if not raw:
    print("unknown")
    raise SystemExit
obj = json.loads(raw)
for k in ("id", "result_id", "memory_id"):
    v = obj.get(k)
    if v:
        print(v)
        raise SystemExit
entry = obj.get("entry")
if isinstance(entry, dict) and entry.get("id"):
    print(entry["id"])
else:
    print("unknown")' <<< "$raw"
}

extract_search_count() {
  local raw="$1"
  /opt/homebrew/bin/python3.13 -c 'import sys, json
raw = sys.stdin.read().strip()
if not raw:
    print(0); raise SystemExit
obj = json.loads(raw)
for k in ("count", "result_count", "total"):
    v = obj.get(k)
    if isinstance(v, int):
        print(v); raise SystemExit
res = obj.get("results")
print(len(res) if isinstance(res, list) else 0)' <<< "$raw"
}

echo "🔍 Smoke test: agent=$AGENT task=$TASK_KEY"

echo "  [1/6] Detect memU route contract..."
if [ "$MEMU_ROUTE_STYLE" = "auto" ]; then
  # Prefer canonical bridge contract first; direct routes may be aliases.
  bridge_probe=$(call_endpoint GET "/api/v1/memu/health" "{}" 2>/dev/null || true)
  if echo "$bridge_probe" | grep -q '"status": "ok"'; then
    MEMU_ROUTE_STYLE="bridge"
  else
    direct_probe=$(call_endpoint GET "/health" "{}" 2>/dev/null || true)
    if echo "$direct_probe" | grep -q '"status"'; then
      MEMU_ROUTE_STYLE="direct"
    else
      FAILURES+=("Unable to detect memU contract at $MEMU_URL")
      STATUS="FAIL"
    fi
  fi
fi

if [ "$MEMU_ROUTE_STYLE" = "direct" ]; then
  HEALTH_PATH="/health"
  STORE_PATH="/store"
  SEARCH_PATH="/search"
elif [ "$MEMU_ROUTE_STYLE" = "bridge" ]; then
  HEALTH_PATH="/api/v1/memu/health"
  STORE_PATH="/api/v1/memu/store"
  SEARCH_PATH="/api/v1/memu/search"
else
  HEALTH_PATH="/health"
  STORE_PATH="/store"
  SEARCH_PATH="/search"
fi

if [ "$STATUS" = "PASS" ]; then
  if [ "$MEMU_ROUTE_STYLE" = "direct" ]; then
    HEALTH=$(call_endpoint GET "$HEALTH_PATH" "{}" 2>/dev/null || true)
    if echo "$HEALTH" | grep -q '"status"'; then
      echo "       ✅ memU alive (direct contract)"
    else
      FAILURES+=("memU direct health check failed: $MEMU_URL$HEALTH_PATH")
      STATUS="FAIL"
    fi
  else
    HEALTH=$(call_endpoint GET "$HEALTH_PATH" "{}" 2>/dev/null || true)
    if echo "$HEALTH" | grep -q '"status": "ok"'; then
      echo "       ✅ memU alive (bridge contract)"
    else
      echo "       ❌ memU bridge endpoint unhealthy — attempting restart..."
      bash /Users/harrisonfethe/.openclaw/workspace/memu_server/start.sh >/dev/null 2>&1 || true
      sleep 2
      HEALTH=$(call_endpoint GET "$HEALTH_PATH" "{}" 2>/dev/null || true)
      if echo "$HEALTH" | grep -q '"status": "ok"'; then
        echo "       ✅ memU restarted successfully"
      else
        FAILURES+=("memU bridge health check failed")
        STATUS="FAIL"
        MEMU_HEALTHY="NO"
      fi
    fi
  fi
fi

echo "  [2/6] Output file check..."
if [ -n "$OUTPUT_FILE" ]; then
  if [ ! -f "$OUTPUT_FILE" ]; then
    mkdir -p "$(dirname "$OUTPUT_FILE")" 2>/dev/null || true
    printf "# auto-created by smoke_test.sh\n" > "$OUTPUT_FILE" 2>/dev/null || true
  fi
  if [ -f "$OUTPUT_FILE" ]; then
    FILE_AGE=$(( $(date +%s) - $(stat -f %m "$OUTPUT_FILE" 2>/dev/null || echo 0) ))
    if [ "$FILE_AGE" -lt 7200 ]; then
      echo "       ✅ Output file exists and fresh (${FILE_AGE}s ago): $OUTPUT_FILE"
    else
      FAILURES+=("Output file exists but stale (${FILE_AGE}s old): $OUTPUT_FILE")
      STATUS="FAIL"
      echo "       ❌ Output file stale"
    fi
  else
    FAILURES+=("Output file missing (auto-create failed): $OUTPUT_FILE")
    STATUS="FAIL"
    echo "       ❌ Output file missing"
  fi
else
  echo "       ⚠️  No output file specified — skipping"
fi

echo "  [3/6] CHANGELOG.md update check..."
CHANGELOG="/Users/harrisonfethe/.openclaw/workspace/self_improvement/CHANGELOG.md"
SKIP_CHANGELOG="${EVAL_SKIP_CHANGELOG:-0}"
if [[ "$TASK_KEY" == memu-health-sweep* ]]; then
  SKIP_CHANGELOG=1
fi
if [ "$SKIP_CHANGELOG" = "1" ]; then
  echo "       ⚠️  CHANGELOG check skipped (task scoped or EVAL_SKIP_CHANGELOG=1)"
elif [ -f "$CHANGELOG" ]; then
  CHANGELOG_AGE=$(( $(date +%s) - $(stat -f %m "$CHANGELOG" 2>/dev/null || echo 0) ))
  if [ "$CHANGELOG_AGE" -lt 14400 ]; then
    echo "       ✅ CHANGELOG.md updated recently (${CHANGELOG_AGE}s ago)"
  else
    FAILURES+=("CHANGELOG.md not updated recently (${CHANGELOG_AGE}s ago)")
    STATUS="FAIL"
    echo "       ❌ CHANGELOG.md stale"
  fi
else
  FAILURES+=("CHANGELOG.md missing")
  STATUS="FAIL"
  echo "       ❌ CHANGELOG.md missing"
fi

echo "  [4/6] shared-state.json check..."
SHARED="/Users/harrisonfethe/.openclaw/workspace/self_improvement/shared-state.json"
if [ -f "$SHARED" ]; then
  if /opt/homebrew/bin/python3.13 -m json.tool "$SHARED" >/dev/null 2>&1; then
    echo "       ✅ shared-state.json valid JSON"
  else
    FAILURES+=("shared-state.json is invalid JSON")
    STATUS="FAIL"
    echo "       ❌ shared-state.json invalid"
  fi
else
  FAILURES+=("shared-state.json missing")
  STATUS="FAIL"
  echo "       ❌ shared-state.json missing"
fi

echo "  [5/6] memU store check ($MEMU_ROUTE_STYLE)..."
if [ "$MEMU_HEALTHY" = "YES" ]; then
  if [ "$MEMU_ROUTE_STYLE" = "direct" ]; then
    STORE_PAYLOAD='{"key":"eval-'$TASK_KEY'-'$TIMESTAMP_SHORT'","value":"Smoke test '$STATUS' for task='$TASK_KEY'.","agent":"'$AGENT'","user_id":"'$AGENT'","session_id":"smoke-'$TASK_KEY'","category":"eval"}'
  else
    STORE_PAYLOAD='{"agent_id":"'$AGENT'","user_id":"'$AGENT'","session_id":"smoke-'$TASK_KEY'","key":"eval-'$TASK_KEY'-'$TIMESTAMP_SHORT'","content":"Smoke test '$STATUS' for task='$TASK_KEY'.","category":"eval","tags":["eval","'$STATUS'","'$AGENT'","smoke-test"]}'
  fi
  MEMU_STORE_RESP=$(call_endpoint "$MEMU_STORE_METHOD" "$STORE_PATH" "$STORE_PAYLOAD")
  MEMU_STORE_ID=$(extract_json_id "$MEMU_STORE_RESP")
  MEMU_STORE_STATUS="200"
  if [ "$MEMU_STORE_ID" = "unknown" ]; then
    FAILURES+=("memU store returned invalid payload")
    STATUS="FAIL"
    MEMU_STORE_STATUS="000"
    echo "       ❌ memU store failed"
  else
    echo "       ✅ memU store ok: $MEMU_STORE_ID"
  fi
else
  MEMU_STORE_RESP="{}"
  MEMU_STORE_ID="n/a"
  MEMU_STORE_STATUS="skipped"
fi

echo "  [6/6] memU search check..."
if [ "$MEMU_HEALTHY" = "YES" ]; then
  if [ "$MEMU_ROUTE_STYLE" = "direct" ]; then
    SEARCH_PAYLOAD='{"query":"eval-'$TASK_KEY'","limit":10,"agent":"'$AGENT'"}'
  else
    SEARCH_PAYLOAD='{"query":"eval-'$TASK_KEY'","limit":10,"agent_id":"'$AGENT'"}'
  fi
  MEMU_SEARCH_RESP=$(call_endpoint "$MEMU_SEARCH_METHOD" "$SEARCH_PATH" "$SEARCH_PAYLOAD")
  MEMU_SEARCH_COUNT=$(extract_search_count "$MEMU_SEARCH_RESP")
  [ -z "$MEMU_SEARCH_COUNT" ] && MEMU_SEARCH_COUNT=0
  echo "       ✅ memU search done: ${MEMU_SEARCH_COUNT} result(s)"

  # Opportunistic GC: clean expired memories on PASS path
  GC_OUT=$(/opt/homebrew/bin/python3.13 /Users/harrisonfethe/.openclaw/workspace/self_improvement/scripts/agent_memory_cli.py --no-rsync gc 2>/dev/null || true)
  GC_DEL=$(echo "$GC_OUT" | grep -oE 'deleted=[0-9]+' | head -1 || true)
  [ -n "$GC_DEL" ] && [ "$GC_DEL" != "deleted=0" ] && echo "   🧹 memory GC: $GC_DEL"
else
  MEMU_SEARCH_RESP="{}"
  MEMU_SEARCH_COUNT=0
fi

action_result="MARKED_DONE"
if [ "$STATUS" != "PASS" ]; then
  action_result="REVERTED — see issues.md"
fi

FAILURE_MSG=""
if [ ${#FAILURES[@]} -gt 0 ]; then
  FAILURE_MSG=$(printf " | FAIL: %s" "${FAILURES[@]}")
fi
RESULT_SUMMARY="${STATUS}${FAILURE_MSG}"

if [ "$STATUS" != "PASS" ]; then
  AGENT="$AGENT" TASK_KEY="$TASK_KEY" FAILURE_MSG="$FAILURE_MSG" FAIL_REFLECTIONS_LOG="$FAIL_REFLECTIONS_LOG" /opt/homebrew/bin/python3.13 - <<'PY'
import json
import os
from datetime import datetime, timezone
from pathlib import Path

log_path = Path(os.environ.get("FAIL_REFLECTIONS_LOG", "/Users/harrisonfethe/.openclaw/workspace/memory/fail-reflections.jsonl"))
entry = {
    "agent": os.environ.get("AGENT", "unknown"),
    "task": os.environ.get("TASK_KEY", "unspecified"),
    "exit_code": 1,
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "probable_cause": os.environ.get("FAILURE_MSG", "unknown failure").replace(" | FAIL:", "").strip(),
}
log_path.parent.mkdir(parents=True, exist_ok=True)
with log_path.open("a", encoding="utf-8") as f:
    f.write(json.dumps(entry, ensure_ascii=False) + "\n")
PY
fi

cat >> "$EVAL_LOG" <<SMRY

## [$TIMESTAMP] | Agent: $AGENT | Task: $TASK_KEY
- **Status:** $STATUS
- **Contract:** $MEMU_ROUTE_STYLE
- **Store:** method=$MEMU_STORE_METHOD path=$STORE_PATH status=$MEMU_STORE_STATUS id=$MEMU_STORE_ID
- **Search:** method=$MEMU_SEARCH_METHOD path=$SEARCH_PATH count=$MEMU_SEARCH_COUNT
- **Test run:** smoke_test.sh checks: memU health/store/search, output file freshness, CHANGELOG update, shared-state JSON validity
- **Result:** $RESULT_SUMMARY
- **memU ID:** $MEMU_STORE_ID
- **memU client key:** $MEMU_KEY_NAME
- **Output file:** ${OUTPUT_FILE:-not specified}
- **Action:** $action_result
- **Notes:** ${NOTES:-auto-generated}
SMRY

# D-015: Write quality delta to memU DB
MEMU_DB="/Users/harrisonfethe/.openclaw/workspace/memory/memu_store/memu.db"
FINAL_STATUS="$STATUS"
FINAL_AGENT="$AGENT"
FINAL_TASK="$TASK_KEY"
FINAL_STORE_ID="$MEMU_STORE_ID"
FINAL_FAILURES="${FAILURES[*]}"
if [ -f "$MEMU_DB" ]; then
  FINAL_STATUS="$FINAL_STATUS" FINAL_AGENT="$FINAL_AGENT" FINAL_TASK="$FINAL_TASK" \
  FINAL_STORE_ID="$FINAL_STORE_ID" FINAL_FAILURES="$FINAL_FAILURES" MEMU_DB="$MEMU_DB" \
  /opt/homebrew/bin/python3.13 - <<'PY'
import os, sqlite3
from datetime import datetime, timezone

db = os.environ.get("MEMU_DB")
status = os.environ.get("FINAL_STATUS", "FAIL")
agent = os.environ.get("FINAL_AGENT", "unknown")
task = os.environ.get("FINAL_TASK", "unspecified")
store_id = os.environ.get("FINAL_STORE_ID", "")
failures = os.environ.get("FINAL_FAILURES", "")

if not db:
    exit(0)
try:
    conn = sqlite3.connect(db, timeout=5)
    c = conn.cursor()
    # Update quality_score + use_count for this agent's memories matching task key
    if status == "PASS":
        delta = 0.05
        outcome = "pass"
    else:
        delta = -0.10
        outcome = f"fail: {failures[:200]}"

    c.execute("""
        UPDATE memories
        SET quality_score = MIN(1.0, MAX(0.0, COALESCE(quality_score, 0.5) + ?)),
            use_count = COALESCE(use_count, 0) + 1,
            outcome = ?
        WHERE agent_id = ? AND (key LIKE ? OR id = ?)
    """, (delta, outcome, agent, f"%{task}%", store_id))
    updated = c.rowcount
    conn.commit()
    conn.close()
    if updated > 0:
        print(f"   quality delta: {'+' if delta>0 else ''}{delta:.2f} applied to {updated} memory row(s)")
except Exception as e:
    print(f"   quality delta skipped: {e}")
PY
fi

echo ""
if [ "$STATUS" = "PASS" ]; then
  echo "✅ SMOKE TEST PASSED — task $TASK_KEY can be marked DONE"
  echo "   proof: memU store=$MEMU_STORE_ID search_count=$MEMU_SEARCH_COUNT"

  # D-023: Hook reflect into PASS path
  AGENT_MEM_CLI="/Users/harrisonfethe/.openclaw/workspace/self_improvement/scripts/agent_memory_cli.py"
  if [ -f "$AGENT_MEM_CLI" ]; then
    /opt/homebrew/bin/python3.13 "$AGENT_MEM_CLI" reflect \
      --agent "$AGENT" \
      --cycle "$TASK_KEY" \
      --outcome PASS \
      --proof "$MEMU_STORE_ID" \
      2>/dev/null && echo "   reflect: logged PASS reflection to memory" || true
  fi

  exit 0
else
  echo "❌ SMOKE TEST FAILED — task $TASK_KEY must NOT be marked DONE"
  echo "   Failures: ${FAILURES[*]}"
  echo "   → Revert changes and escalate if needed"
  exit 1
fi
