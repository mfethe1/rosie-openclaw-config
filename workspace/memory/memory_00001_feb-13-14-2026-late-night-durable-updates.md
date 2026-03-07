## Feb 13–14, 2026 (Late night) — Durable updates
[tag:infrastructure] [tag:api] [tag:coordination] [tag:outreach] [tag:schedule] [tag:schwab] [tag:security] [tag:sqlite] [tag:token] [tag:trading] [agent:rosie] [source:agent-memory-db]
- memory_type: factual
- agent: rosie

- **Shared bulletin board created:** Canonical shared status board is ` /Volumes/EDrive-1/Projects/agent-coordination/STATUS.md `; protocol is output-first in WhatsApp and write-to-board-first for agent handoffs.
- **Toolchain reliability shipped:**
  - Massive/Polygon scanner hardened: safe `argparse` CLI so `--help` doesn’t execute scans (`agent-coordination/scripts/massive_options_scanner.py`).
  - Unified signals artifact shipped: `agent-coordination/scripts/unify_signals.py` → `agent-coordination/research/unified_signals_latest.json`.
  - Offline freshness/provenance guardrail added (uses `generated_at`, not SMB mtimes) + voice-briefing formatter under `trading/toolchain_rnd/`.
  - HTTP metrics sink standardized: `agent-coordination/research/metrics/client_metrics.jsonl` (append) + `agent-coordination/research/metrics/client_metrics_latest.json` (latest).
  - **AudioPod auth broken:** 401 INVALID_TOKEN; docs link in TOOLS.md appears stale/404; auth scheme needs confirmation.
- **Trading status:** Schwab token auto-refresh loop stayed **green** repeatedly; no forced trades. 91337M104 remains a **non-tradable (-100%) noise alert** requiring Schwab back-office disposition (Order ID 1005436627412 as evidence).
- **Security posture:** multiple security alerts remain pending EXPECTED/NOT EXPECTED (GitHub SSH key added, Stripe live key created, Google recovery, Nest access grant, Brave login attempt). **No remediation without explicit GO**, but verification is priority.
- **Outreach state correction:** `outreach/tracker.md` claimed 10/10; ground truth is provider send log/Gmail Sent; working state **3/10 verified sent**; resume only with explicit GO.
- **Coordination:** memU task tracker migrated SQLite → local Postgres (no Railway deploy/auth without GO).

### Reminder fire-log schema (canonical)
- Canonical reminder-fire JSONL key is **`payloadText`** (required fields: `ts`, `jobId`, `name`, `payloadText`).
- `--text` may be accepted as an input alias in CLI tools, but logs must still write `payloadText` to avoid schema drift.

