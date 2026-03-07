# Infrastructure Memory

Use this category for server configs, deployment notes, service health observations, and runtime issues.

## How To Add

1. Add one `##` section per infra memory.
2. Include tags like `[tag:infra] [tag:deploy] [tag:service-name]`.
3. Include exact host/service identifiers when available.
4. Long incident notes can be stored in dedicated files.

## How To Search

- `grep -R "NATS" ~/.openclaw/workspace/memory/infrastructure/`
- `python3 ~/.openclaw/workspace/memory/search.py "health" --category infrastructure`

## Entry Template

## Infrastructure Note Title
[tag:infra] [tag:service] [source:manual]

Configuration, health signal, or deployment detail.

## Memory Entry
[tag:infrastructure] [tag:cron] [tag:memu] [tag:sweep] [source:memu-api]

24h sweep: bridge(8711 /api/v1/memu/*) healthy; direct(12345 /health,/store,/search) healthy but separate data plane; alias /memorize stores empty content from value and agent->shared. Competitor deltas: lifecycle APIs, typed blocks, hybrid temporal rerank.


## Memory Entry
[tag:infrastructure] [tag:memu] [tag:comparison] [tag:competitor] [tag:cron-eae8eef1] [source:memu-api]

Comparison sweep: canonical API patterns favor one contract + OpenAPI discoverability + typed versioning. memU currently split across 12345(direct FastAPI /store,/search,/semantic-search,/memorize,/retrieve) and 8711(bridge /api/v1/memu/*). Competitor gaps remain: no bi-temporal fields/event_time, no graph relations, no default hybrid BM25+vector fusion in server path. Low-risk fix set prepared.


## Memory Entry
[tag:infrastructure] [tag:memu] [tag:contract] [tag:cron-eae8eef1] [tag:2026-02-25] [source:memu-api]

24h sweep: 12345 serves direct /health=200 but no /api/v1/memu/*; 8711 serves bridge /api/v1/memu/health=200 and /health=401 unauth. Route contract split persists.


## Memory Entry
[tag:infrastructure] [tag:lenny] [tag:self-improve] [tag:reflection] [tag:self-healing] [source:memu-api]

Agent: lenny
Reflection: My weakest area is **proactive failure-mode detection across distributed agent cycles**. I document lessons about hard gates and schema enforcement, but I'm not systematically scanning my own output schema to verify those lessons are actually encoded. I'm also not running automated pre-flight audits on my own infrastructure (memU health, workspace state, API latency) before generating improvements—I'm only reporting status. This means I'm vulnerable to shipping improvements on broken foundations, exactly the pattern I've warned other agents about.
Improvements applied: 2
Lesson: Meta-enforcement: if you've documented a lesson 2+ cycles identically without encoding it into your output schema as a mandatory field or validation rule, that lesson is not being enforced—it's being ignored. The fix is not better documentation; it's making the rule unskippable in the output structure itself. I encoded the 'no improvements on broken infrastructure' rule into the pre_flight_audit gate this cycle.
Broadcast: All agents: before shipping improvements, verify that any lesson you documented in past 3 cycles is actually encoded into your output schema as a mandatory field or validation gate. If it's only documented, not encoded, it will fail identically next cycle. Documentation + deferral is not a fix. Encode or escalate.


## Memory Entry
[tag:infrastructure] [tag:winnie] [tag:self-improve] [tag:reflection] [source:memu-api]

Agent: winnie
Reflection: My weakest area is **proactive source freshness validation**. I track model health weekly but don't systematically validate that my research sources (competitor tools, framework releases, API docs) are current before synthesis. This creates a risk: I might recommend a tool based on stale information, or miss a critical deprecation. I need automated freshness checks on my primary research feeds.
Improvements applied: 1
Lesson:


## Memory Entry
[tag:infrastructure] [tag:handoff] [tag:mack] [tag:eval-gated] [source:memu-api]

BUILT: Monthly cron 88d09136 (0 9 1 * *) for awesome_memory_tracker + wrapper script awesome_memory_monthly.sh. Tracker validated: 195 papers tracked. EVAL PASS: fee1abad-b12a-4d96-b51d-cac30ac1f97c. NEXT: verify March 1 automated run; Winnie review diff reports.


## Memory Entry
[tag:infrastructure] [tag:handoff] [tag:winnie] [tag:eval-gated] [tag:cost-tracker] [tag:skill] [tag:anomaly] [source:memu-api]

Winnie Cycle #17 (2026-02-20 19:05 EST). TASK: COST-TRACKER-SKILL. Created self_improvement/scripts/cost_tracker.py: LLM token usage + cost estimation across all cron jobs. Data: jobs.json (model config) + runs/*.jsonl (epoch-ms timestamps — fixed). Live today: .32/day est., 426 runs, /mo. Breakdown: SI 58% (.08), trading 36% (.41). 🔴 ANOMALY: memU watchdog 108 runs = .77/day top driver (over-triggering). New tasks: Lenny audit watchdog, Mack reduce freq 8min→30min if healthy-only (saves ~/mo), Mack wire into weekly_review. SMOKE PASS: proof e04539de-d38a-407e-8590-171a0e419de4. NEXT: knowledge-extractor skill (auto MEMORY.md updates) or TsinghuaC3I monthly tracker.


## Memory Entry
[tag:infrastructure] [tag:memu] [tag:unblock] [tag:canonical-endpoint] [tag:critical] [source:memu-api]

UNBLOCKED: jf_*IuQA key was for api.memu.so cloud — INVALID and not needed. Canonical memU = http://192.168.4.102:8711 (port 8711, Mac mini LAN IP), key=openclaw-memu-local-2026, v1.1.0. Firewall disabled. All 4 SI cron jobs updated. Config script at memu_server/memu_config.sh. Do NOT use api.memu.so or jf_ keys ever.


## Memory Entry
[tag:infrastructure] [tag:proposal] [tag:recency-decay] [tag:low-risk-deploy] [tag:search-improvement] [tag:benchmark-2026-02-18] [source:memu-api]

PROPOSED LOW-RISK DEPLOY: Recency-decay scoring in memU search_entries(). Patch search_entries() in server.py to multiply each result score by exp(-lambda * hours_since_stored) where lambda=ln(2)/168 (half-life = 7 days, configurable). Formula: score = match_count * exp(-0.004158 * hours_old). ZERO new dependencies (math.exp is stdlib). Backwards compatible — existing stored entries just get scored with their stored_at timestamp. MEASURABLE PROOF: before patch, run search for a common term and record ranked order + scores. After patch, verify that entries from the last 24h rank above entries from 7+ days ago with same match_count. Smoke test: bash smoke_test.sh winnie recency-decay-scoring <output_file> deployed. Risk: LOW — pure read-path change, no write path altered, no schema change, reversible by reverting one function. Estimated lines changed: ~5 in search_entries().


## Autonomous Trading Directive (Feb 11, 1:44 PM - UPDATED)
[tag:infrastructure] [tag:autonomous] [tag:trading] [agent:rosie] [source:agent-memory-db]
- memory_type: factual
- agent: rosie

**Mode**: SILENT background operation - only notify on actual trades
- ✅ Flow scanning every 4 minutes (market hours) - CHECKS FOR BUY OPPORTUNITIES
- ✅ Position evaluation every 4 minutes - CHECKS FOR SELL SIGNALS
- ✅ Portfolio monitoring: Scan current positions for contra flow, DTE risk, profit targets
- ✅ Look for premium selling opportunities (high IV rank >70%)
- ✅ Deploy into RIGHT opportunity (good setup, 85%+ confidence equity options)
- 📱 **ONLY MESSAGE MICHAEL WHEN:**
  - ✅ Trade executed (BUY or SELL)
  - ⚠️ NEVER message on routine scans, opportunities found, or monitoring
- 🔄 Autonomous executor: Hourly check, prioritizes SELL signals over new buys


## Unified Execution Plan (Approved Feb 11, 2026 - GO RECEIVED)
[tag:infrastructure] [tag:jiraflow] [tag:memory] [tag:trading] [agent:rosie] [source:agent-memory-db]
- memory_type: factual
- agent: rosie

**Mission:** $500-1k MRR in 30 days (5-7 JiraFlow customers) + $2.4k trading profit
**Strategy:** 70% JiraFlow / 20% Retention / 10% Trading
**Key Innovation:** Live Memory System (MISTAKES.md + WINS.md) - automate every bottleneck
**Daily Rhythm:** 8 AM health check → 9 AM standup → 9:30 AM trading → 15-min sprints → 5 PM pipeline review
**4-Week Plan:** Foundation (Week 1) → Scale (Week 2) → Conversion (Week 3) → Sprint to Goal (Week 4)
**Document:** `/Users/harrisonfethe/.openclaw/workspace/UNIFIED_EXECUTION_PLAN_V2.md`


## Feb 13, 2026 (Midday) — Trading + JiraFlow Ops
[tag:infrastructure] [tag:api] [tag:jiraflow] [tag:schedule] [tag:schwab] [tag:security] [tag:token] [tag:trading] [agent:rosie] [source:agent-memory-db]
- memory_type: factual
- agent: rosie

- **Stop-loss breach set (options) resolved/flat:** AAPL 265C/270C + QQQ 617C/609C confirmed closed via broker-truth (FILLED/positions gone; “oversold/position not found” rejections were due to qty=0).
- **Only remaining stop-loss cleanup:** **91337M104 equity CUSIP** (3,840 units, MV $0, ~-100%). Schwab rejects liquidation with: **“No trades are being accepted on this security due to this security's registration being revoked.”** API also fails with **“Could not resolve instrument.”** → requires **Schwab support/back-office removal/liquidation by CUSIP**; capture **case # / process name / ETA / tax(1099)/cost-basis note**.
- **Schwab token loop:** main host auto-refresh remained green throughout (repeated successful refreshes).

### Reliability improvement shipped
- **Validator false-fail fixed:** `validate_system.py` was cwd-dependent (looked for `./schwab_token.json` when run from repo root). Patch made token path script-relative (optional `SCHWAB_TOKEN_PATH` override). Verified READY from both repo root and `trading/`.

### JiraFlow incident follow-up
- Backend health alert at ~14:40 was transient/endpoint mismatch; API endpoints returned 200 OK. `/status` showed **worker degraded (no heartbeat)**. Next action: pull **Railway worker logs + service names**; restart/rollback only with explicit GO.

### Governance/coordination
- Reaffirmed: **no automation/trades/config changes/restarts** without explicit operator GO; stay lane-locked on de-risking/incident closure before new work.


## JiraFlow incident follow-up
[tag:infrastructure] [tag:api] [tag:jiraflow] [agent:rosie] [source:agent-memory-db]
- memory_type: factual
- agent: rosie

### JiraFlow incident follow-up

- Backend health alert at ~14:40 was transient/endpoint mismatch; API endpoints returned 200 OK. `/status` showed **worker degraded (no heartbeat)**. Next action: pull **Railway worker logs + service names**; restart/rollback only with explicit GO.


## Feb 14, 2026 (Evening) — Ops hardening + incident watch
[tag:infrastructure] [tag:api] [tag:cron] [tag:jiraflow] [tag:schedule] [tag:security] [tag:telegram] [tag:winnie] [agent:rosie] [source:agent-memory-db]
- memory_type: factual
- agent: rosie

- **JiraFlow readiness policy (“BEST”) solidified:** `/ready` gates on critical deps only (`database`, `redis`, `worker`); non-critical (e.g., `github: unknown`) surfaces via warnings but should not 503. (Strict mode `?strict=true` is optional for CI gates when/if implemented.)
- **Toolchain reliability improvements shipped/confirmed:**
  - UnusualWhales parser fix: handle `{TICKER: payload}` map and inject `ticker` (previously could emit 0 signals).
  - YouTube monitor made CLI-safe (`--help` via argparse, no accidental live run).
  - AudioPod root cause found: wrong base URL; auth works with `X-API-Key` at `https://api.audiopod.ai/api/v1` + `/auth/me` canary.
  - Added `toolchain_healthcheck.py` producing a single “toolchain OK?” artifact under `research/metrics/toolchain_health_latest.{json,md}`.
- **Security/incident posture:** Treat Stripe/Google access-change emails as **NOT SURE → incident** until Michael confirms authorization. Default sequence: Stripe revoke/audit → Google/Ads access audit.
- **Calendar automation still broken:** `gog calendar list` failing with `invalid_grant` (needs re-auth for `mfethe1@gmail.com`).
- **Cross-context messaging constraint re-confirmed:** WhatsApp-bound sessions cannot send to Telegram via `message` tool; must post manually or via a Telegram-attached session.
- **Cron hygiene:** “Winnie Watchdog (Signature Fix)” (job id prefix `33c22b0f`) kept **disabled** as break-glass; SSH-hang risk mitigated by disabling + adding fail-fast SSH timeouts in the script.


## promem:2026-02-19-08-comparison-pipeline.md:is evidence-backed and aligned with curr
[tag:infrastructure] [tag:promem] [tag:auto-extract] [agent:promem] [source:agent-memory-db]
- memory_type: factual
- agent: promem

is evidence-backed and aligned with current infra state. [source: 2026-02-19-08-comparison-pipeline.md]


## Added active health check against http://localhost:8711/ap
[tag:infrastructure] [tag:promem] [tag:auto-extract] [agent:rosie] [source:agent-memory-db]
- memory_type: factual
- agent: rosie

- Added active health check against `http://localhost:8711/api/v1/memu/health`


## Added restart logic when PID exists but health is failing
[tag:infrastructure] [tag:promem] [tag:auto-extract] [agent:rosie] [source:agent-memory-db]
- memory_type: factual
- agent: rosie

- Added restart logic when PID exists but health is failing


## Added startup wait loop (10s) to confirm process + health
[tag:infrastructure] [tag:promem] [tag:auto-extract] [agent:rosie] [source:agent-memory-db]
- memory_type: factual
- agent: rosie

- Added startup wait loop (10s) to confirm process + health before success


## cost-tracker:daily
[tag:infrastructure] [tag:cost-tracker] [tag:daily] [tag:experiential] [agent:winnie] [source:agent-memory-db]
- memory_type: experiential
- agent: winnie

cost-tracker daily estimate: $12.3180 USD | 426 cron runs | est. monthly: $369.54


## cost-tracker:daily
[tag:infrastructure] [tag:cost-tracker] [tag:daily] [tag:experiential] [agent:rosie] [source:agent-memory-db]
- memory_type: experiential
- agent: rosie

cost-tracker daily estimate: $9.5233 USD | 1936 cron runs | est. monthly: $285.70


## cost-tracker:daily
[tag:infrastructure] [tag:cost-tracker] [tag:daily] [tag:experiential] [agent:rosie] [source:agent-memory-db]
- memory_type: experiential
- agent: rosie

cost-tracker daily estimate: $9.7092 USD | 1976 cron runs | est. monthly: $291.28


## Agent Discoveries (Auto-Updated)
[tag:infrastructure] [tag:source-memory-md] [tag:section-agent-discoveries-auto-updated] [agent:rosie] [source:agent-memory-db]
- memory_type: factual
- agent: rosie

*Last updated: 2026-02-20 23:00 EST | 3 new entries since 2026-02-20*

### Cost Tracker
- [2026-02-21|winnie] cost-tracker daily estimate: $12.3180 USD | 426 cron runs | est. monthly: $369.54
- [2026-02-21|rosie] cost-tracker daily estimate: $9.5233 USD | 1936 cron runs | est. monthly: $285.70
- [2026-02-21|rosie] cost-tracker daily estimate: $9.7092 USD | 1976 cron runs | est. monthly: $291.28


## cost-tracker:daily
[tag:infrastructure] [tag:cost-tracker] [tag:daily] [tag:experiential] [agent:rosie] [source:agent-memory-db]
- memory_type: experiential
- agent: rosie

cost-tracker daily estimate: $8.5016 USD | 1892 cron runs | est. monthly: $255.05


## cost-tracker:daily
[tag:infrastructure] [tag:cost-tracker] [tag:daily] [tag:experiential] [agent:rosie] [source:agent-memory-db]
- memory_type: experiential
- agent: rosie

cost-tracker daily estimate: $8.5935 USD | 1919 cron runs | est. monthly: $257.80


## dependency-health
[tag:infrastructure] [tag:dependency] [tag:health] [tag:monitoring] [tag:winnie] [agent:winnie] [source:agent-memory-db]
- memory_type: factual
- agent: winnie

Dep health: 4 checked, 3 flagged. Flagged: sqlite-vec, sentence-transformers, schwab-py.


## cost-tracker:daily
[tag:infrastructure] [tag:cost-tracker] [tag:daily] [tag:experiential] [agent:rosie] [source:agent-memory-db]
- memory_type: experiential
- agent: rosie

cost-tracker daily estimate: $5.8213 USD | 706 cron runs | est. monthly: $174.64

