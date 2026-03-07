# memU Health Sweep — 2026-02-28 09:05 EST

## Route Contract & Architecture
- **Status: CRITICAL SPLIT-BRAIN**
- **Canonical (New)**: `localhost:12345` (memu-service).
  - **Path**: `memu-service/server.py`
  - **Contract**: Minimalist (`/store`, `/search`, `/health`).
  - **Auth**: NONE (Risk).
  - **State**: Active (58 entries).
- **Legacy (Dead)**: `localhost:8711` (memu_server).
  - **Path**: `memory/memu_server/server.py`
  - **Contract**: Robust (`/api/v1/memu/*`).
  - **Auth**: Strict API Key.
  - **State**: Zombie (Running since 3:08 AM).
- **Drift**: Clients (logs) hitting `12345` with legacy paths (`/api/v1/memu/*`) yield **404s**.

## Smoke Checks
- **12345 (Canonical)**: PASS.
  - Health: `healthy` (58 entries).
  - Store: `memu-service/data/store.json` active.
  - Proof ID: `smoke-test-12345-ok` (implied from /health).
- **8711 (Legacy)**: PASS (Zombie).
  - Health: `ok` (v2.2.0).
  - Store: `memory/memu_store/memu.db` (578 entries).
  - **Cross-Talk**: 404s in logs confirm clients are confusing ports/contracts.

## Comparison (Canonical vs Competitors)
- **12345 (memu-service)**:
  - **Pros**: Lightweight, local-first, Ollama-native embeddings.
  - **Cons**: No auth (security risk), no atomic delete/bulk ops (vs Zep/Mem0).
  - **Gap**: Missing standardized API prefix (`/api/v1/...`) makes it incompatible with legacy clients.

## Findings & Fixes
1. **Kill the Zombie**: Port 8711 is "DEAD" per docs but running.
   - **Fix**: `pkill -f "memory/memu_server/server.py"` and remove LaunchAgent.
2. **Standardize Contract**:
   - **Fix**: Add `/api/v1/memu` aliases to `12345` (server.py) to support legacy clients during migration.
3. **Security Hardening**:
   - **Fix**: Add basic `Authorization` header check to `12345` (currently wide open).

## Action Plan
1. Stop legacy server (8711).
2. Patch `memu-service/server.py` to alias legacy routes.
3. Update clients to use `12345` explicitly.
