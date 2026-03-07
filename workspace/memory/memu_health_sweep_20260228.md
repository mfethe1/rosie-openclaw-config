# memU Health Sweep — 2026-02-28 05:08 EST

## Route Contract & Architecture
- **Split Brain Detected**: Two competing servers running.
  - **Local (New)**: `localhost:12345` (v1.2.0). Routes: `/store`, `/search`, `/health`.
  - **Bridge (Legacy)**: `localhost:8711` (v2.2.0). Routes: `/api/v1/memu/health`, `/store`, etc.
- **Contract Drift**: Clients (logs) hitting `12345` with `/api/v1/memu/*` get **404s**.
- **Docs Conflict**: `memu-service/data/store.json` claims 8711 is "DEAD", but it is active and healthy.

## Smoke Checks
- **Store (12345)**: PASS. Proof ID: `671edb98` (key=`sweep-2026-02-28-0508`).
- **Search (12345)**: PASS. Retrieved recent sweep entries.
- **Health (12345)**: PASS. Status: `healthy`, 58 entries.
- **Legacy Store (8711)**: FAIL (401 Unauthorized) - requires strict auth, unlike 12345.

## Comparison (Canonical / Competitors)
- **12345 (New)**: Minimalist (mem0-lite). Good for local sidecars.
  - **Risk**: No auth enforcement on write (unlike Zep/mem0).
- **8711 (Bridge)**: Closer to Zep API (prefixed routes, auth).
- **Competitor Gap**: Missing atomic `/delete` and bulk operations standard in Zep/Mem0.

## Findings & Fixes
1. **Ambiguous Routing**: Clients are confusing 12345 and 8711 contracts (404 logs).
   - **Fix**: Standardize on **one** port/contract. If 12345 is canonical, add `/api/v1/memu` aliases or update all clients.
2. **Zombie Service**: 8711 ("DEAD") is consuming resources and claiming "v2.2.0" (higher than new "v1.2.0").
   - **Fix**: Verify if 8711 is truly obsolete. If so, `kill` and remove `memu_server` folder.
3. **Security Regression**: 12345 accepts unauthenticated writes.
   - **Fix**: Enforce `Authorization` header check on 12345.

## Status: DEGRADED (Architecture Split)
Functionality works, but architecture is split and confusing.
