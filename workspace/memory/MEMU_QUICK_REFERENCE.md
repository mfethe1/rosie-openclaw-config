# memU Quick Reference — DEFINITIVE (2026-02-22)

**Status: ✅ WORKING** — Server running, PID active, all endpoints verified.

## Connection
- **URL:** `http://localhost:8711`
- **API Key:** `openclaw-memu-local-2026`
- **Config file:** `source /Users/harrisonfethe/.openclaw/workspace/memu_server/memu_config.sh`

## Endpoints

### Health (no auth required)
```bash
curl -s http://localhost:8711/api/v1/memu/health
```

### Store (POST, auth required)
```bash
curl -s -X POST http://localhost:8711/api/v1/memu/store \
  -H "Authorization: Bearer <REDACTED>" \
  -H "Content-Type: application/json" \
  -d '{"agent_id":"AGENT","key":"unique-key","content":"text","category":"cat","tags":["t1"]}'
```

### Search (POST, auth required)
```bash
curl -s -X POST http://localhost:8711/api/v1/memu/search \
  -H "Authorization: Bearer <REDACTED>" \
  -H "Content-Type: application/json" \
  -d '{"query":"search terms","limit":5}'
```

### List Recent (GET, auth via query param)
```bash
curl -s "http://localhost:8711/api/v1/memu/list?limit=10&api_key=openclaw-memu-local-2026"
```

## Common Mistakes (DO NOT REPEAT)
- ❌ `GET /api/v1/memu/search` → 404. Search is **POST**.
- ❌ Missing `Authorization: Bearer` header → 401.
- ❌ Using `/health` instead of `/api/v1/memu/health` on bridge checks → 401 Unauthorized (protected route), not a health failure.
- ❌ Using old/wrong API key → 401. Key is `openclaw-memu-local-2026`.
- ❌ Reporting "memU is broken" without testing with correct auth → not broken, you're calling it wrong.

## Self-Healing
If memU is actually down (health endpoint returns connection refused):
```bash
bash /Users/harrisonfethe/.openclaw/workspace/memu_server/start.sh
```
Wait 2 seconds, then re-test health endpoint.
