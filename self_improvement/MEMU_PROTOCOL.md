# memU Memory System — Team Protocol (MANDATORY)

**Status:** ✅ DEPLOYED & RUNNING (Feb 18, 2026)
**Server:** `http://127.0.0.1:12345`
**Persistence:** LaunchAgent auto-start (`com.openclaw.memu-server`)

---

## 🔴 HARD REQUIREMENT: Every Agent, Every Handoff

Starting NOW, **every agent** (Rosie, Mack, Winnie, Lenny) MUST:

1. **STORE** context on every handoff/decision point
2. **SEARCH** for prior context before starting any new work
3. **Include proof IDs** in status/inbox updates

No exceptions. No "I'll do it later." No file-only memory.

---

## API Endpoints

### `POST /store` — Write a memory (NO LLM needed)
```bash
curl -s -X POST http://127.0.0.1:12345/store \
  -H "Content-Type: application/json" \
  -d '{
    "key": "handoff:<agent>:<date>",
    "value": "What changed, why, blockers, next steps",
    "agent": "<your-agent-name>",
    "category": "handoff",
    "metadata": {"lane": "trading", "cycle": "3"}
  }'
```
**Response:** `{"status":"success","id":"aea06ef0","message":"Stored entry..."}`

### `POST /search` — Read back context (NO LLM needed)
```bash
curl -s -X POST http://127.0.0.1:12345/search \
  -H "Content-Type: application/json" \
  -d '{"query": "handoff", "agent": "rosie", "limit": 5}'
```
**Response:** `{"status":"success","count":1,"results":[...]}`

### `GET /health` — Verify server is alive
```bash
curl -s http://127.0.0.1:12345/health
```

### `POST /memorize` — Full conversation memorization (REQUIRES OPENAI_API_KEY)
```bash
curl -s -X POST http://127.0.0.1:12345/memorize \
  -H "Content-Type: application/json" \
  -d '{
    "content": [
      {"role": "user", "content": {"text": "..."}, "created_at": "2026-02-18 04:00:00"},
      {"role": "assistant", "content": {"text": "..."}, "created_at": "2026-02-18 04:01:00"}
    ],
    "agent": "rosie"
  }'
```

### `POST /retrieve` — Semantic memory retrieval (REQUIRES OPENAI_API_KEY)
```bash
curl -s -X POST http://127.0.0.1:12345/retrieve \
  -H "Content-Type: application/json" \
  -d '{"query": "what was the last trading decision?"}'
```

---

## Handoff Protocol (MANDATORY per handoff)

### Step 1: Store your work
```bash
curl -s -X POST http://127.0.0.1:12345/store \
  -H "Content-Type: application/json" \
  -d '{
    "key": "handoff:<agent>:<YYYY-MM-DD-HH>",
    "value": "WHAT: <summary>. WHY: <reason>. BLOCKED: <blockers>. NEXT: <action>. OWNER: <next-agent>",
    "agent": "<agent>",
    "category": "handoff"
  }'
```

### Step 2: Include proof in status update
```
✅ memU store: id=<id-from-response>
✅ memU search: count=<N> results for "<query>"
```

### Step 3: Before starting new work, search first
```bash
curl -s -X POST http://127.0.0.1:12345/search \
  -H "Content-Type: application/json" \
  -d '{"query": "<relevant-topic>", "limit": 5}'
```

---

## Verification Command (Run this to prove memU works)
```bash
# 1. Health check
curl -s http://127.0.0.1:12345/health | python3 -m json.tool

# 2. Store test
curl -s -X POST http://127.0.0.1:12345/store \
  -H "Content-Type: application/json" \
  -d '{"key":"verify:<agent>","value":"memU verification test","agent":"<agent>"}' | python3 -m json.tool

# 3. Search test  
curl -s -X POST http://127.0.0.1:12345/search \
  -H "Content-Type: application/json" \
  -d '{"query":"verify"}' | python3 -m json.tool
```

All 3 must return `"status": "success"`. Include the response IDs in your next status update.

---

## Server Management

**Start (if not running):**
```bash
launchctl load ~/Library/LaunchAgents/com.openclaw.memu-server.plist
```

**Stop:**
```bash
launchctl unload ~/Library/LaunchAgents/com.openclaw.memu-server.plist
```

**Logs:**
```bash
tail -f /Users/harrisonfethe/.openclaw/workspace/memu-service/memu-server.log
```

**Manual start (dev):**
```bash
source /Users/harrisonfethe/.openclaw/workspace/memu-venv/bin/activate
cd /Users/harrisonfethe/.openclaw/workspace/memu-service
python3 server.py
```

---

## Architecture
- **Framework:** NevaMind-AI/memU (memu-py v0.1.8)
- **Backend:** In-memory store with JSON file persistence (`data/store.json`)
- **Server:** FastAPI + Uvicorn on port 12345
- **Persistence:** LaunchAgent auto-restart on boot
- **LLM (optional):** Set `OPENAI_API_KEY` env var for full memorize/retrieve

---

**Last verified:** 2026-02-18T04:42Z — Rosie
**Store proof:** id=aea06ef0
**Search proof:** count=1, query="handoff"
