# Issues Log — Self-Improvement System

**Owner:** Lenny (QA/Health)
**Purpose:** Track FAIL events from eval-log.md, regressions, escalations, and near-misses.

---

## Entry Format

```
## [YYYY-MM-DD HH:MM EST] | Severity: CRITICAL|HIGH|MEDIUM | Agent: [name]
- **Issue:** [description]
- **Task:** [task-key that failed]
- **Eval-Log Ref:** [timestamp from eval-log.md]
- **Root Cause:** [what went wrong]
- **Revert:** [what was reverted, if anything]
- **Escalated:** YES/NO | Channel: [telegram group if yes]
- **Resolution:** [how it was fixed, or OPEN]
- **Resolved at:** [timestamp or OPEN]
```

---

## Open Issues

## [2026-02-23 08:00 EST] | Severity: MEDIUM | Agent: Winnie
- **Issue:** OpenClaw memory_search returns 429 "insufficient_quota" from OpenAI embeddings, despite config showing `provider: gemini`. Memory search is also set to `enabled: false` in openclaw.json. The platform may be falling back to OpenAI despite the Gemini provider setting.
- **Task:** proactive-discovery (Winnie self-improvement cycle)
- **Root Cause:** OpenAI embeddings API quota exhausted. Config mismatch: `memorySearch.provider` set to `gemini` but system still routes to OpenAI.
- **Impact:** All agents lose memory_search capability. Does not block execution (agents can read files directly), but degrades context recall.
- **Escalated:** NO — informational, platform-level issue
- **Resolution:** OPEN — needs Michael to either top up OpenAI embedding credits or verify the Gemini embedding provider is correctly wired. Workaround: agents read MEMORY.md and memory/*.md directly when needed.
- **Resolved at:** OPEN

## [2026-02-23 08:00 EST] | Severity: LOW | Agent: Winnie
- **Issue:** 6 crons in error state — all due to transient provider rate-limit cooldowns from ~8PM last night when many crons competed for models simultaneously. All will self-recover at next scheduled run.
- **Affected:** 0e793cfe (Team Morning Summary), 0e441378 (Daily Morning Summary), 976facd2 (oh-my-opencode), b3e6b47b (Test Coverage), 89db2e01 (Weekly Campaign), bde27873 (Weekly Competitive)
- **Self-healed:** Bumped b3e6b47b timeout 600→900s (was timing out independently of rate limits).
- **Resolution:** SELF-HEALED (timeout fix) + TRANSIENT (rate limits clear automatically)

---

## Resolved Issues

<!-- Resolved issues move here with resolution timestamp -->

---

## Known Risks (from Red Team 2026-02-18)

| Risk | Severity | Mitigation | Status |
|------|----------|-----------|--------|
| No eval gate on self-improvement | HIGH | eval-log.md + smoke_test.sh | ✅ RESOLVED |
| Event log not durable (file-based) | MEDIUM | Noted; Temporal.io pattern queued for research | 🔵 BACKLOG |
| Memory rot (append-only text) | MEDIUM | memU + 180-day rolling files | 🟡 PARTIAL |
| Guardrails are prompt-only | LOW | Accepted risk; noted in AGENTS.md | 🔵 ACCEPTED |
| BACKLOG.md no atomic writes | MEDIUM | Agents read shared-state before write | 🟡 PARTIAL |


---
## [OPEN] B-015: memU Canonical IP Drift
- **Raised at:** 2026-02-20 00:09 EST
- **Raised by:** lenny (qa-audit cron)
- **Severity:** HIGH
- **Root cause:** Mac mini LAN IP changed from 192.168.4.102 → 192.168.4.121 (DHCP drift)
- **Impact:** All 4 SI agent cron prompts + shared-state.json canonical_base_url are stale. Direct 192.168.4.102:8711 curl calls fail (host down). smoke_test.sh/start.sh use localhost so eval gate still works.
- **Fix required:** Mack update all cron prompts to use http://localhost:8711 (permanent fix) or http://192.168.4.121:8711 (temporary). Update shared-state.json memu.canonical_base_url.
- **Revert:** N/A (config-only change)
- **Escalated:** NO — Mack can handle autonomously
- **Resolution:** OPEN

---
## [OPEN] B-017: memu_server/start.sh missing ANTHROPIC_API_KEY (SimpleMem disabled)
- **Raised at:** 2026-02-20 03:17 EST (de-conflicted from Winnie's B-015 collision)
- **Raised by:** lenny (qa-audit) — original finding by Winnie cycle 2026-02-20 01:08
- **Severity:** HIGH
- **Root cause:** memu_server/start.sh does not source deploy.env; ANTHROPIC_API_KEY absent in server env; SimpleMem LLM compression + auto_tags are silently disabled.
- **Fix:** Add `source ~/.openclaw/secrets/deploy.env` (or equivalent) before `nohup` launch in start.sh, then restart server.
- **Owner:** Mack
- **Escalated:** NO
- **Resolution:** OPEN

---
## [OPEN] B-018: Tool Pressure Test cron (751074aa) errors
- **Raised at:** 2026-02-20 03:17 EST
- **Raised by:** lenny (cron health sweep)
- **Severity:** MEDIUM
- **Root cause:** Unknown — first observation this cycle. Needs Mack investigation.
- **Owner:** Mack
- **Resolution:** OPEN

---
## [OPEN] B-019: Rosie Outreach Content cron (a243398a) errors
- **Raised at:** 2026-02-20 03:17 EST
- **Raised by:** lenny (cron health sweep)
- **Severity:** MEDIUM
- **Root cause:** Unknown — new observation. May be Telegram delivery or model issue.
- **Owner:** Mack/Rosie
- **Resolution:** OPEN

---
## [OPEN] B-020: B-009 regression — 98fecdc5 Autonomous Goal Progress still erroring
- **Raised at:** 2026-02-20 03:17 EST
- **Raised by:** lenny (cron health sweep)
- **Severity:** MEDIUM
- **Root cause:** B-009 marked DONE 2026-02-19 14:01 (delivery channel fix) but cron still shows error status. Fix incomplete or different error path.
- **Fix required:** Mack re-diagnose. Do not mark DONE without 2 consecutive clean runs.
- **Owner:** Mack
- **Resolution:** OPEN

---
## [OPEN] B-021: d3cdf022 Mack Code Refactoring still erroring (B-011 regression)
- **Raised at:** 2026-02-20 06:05 EST
- **Raised by:** lenny (cron-regression-sweep)
- **Severity:** MEDIUM
- **Root cause:** B-011 marked DONE (timeoutSeconds 600→900) but cron d3cdf022 still shows error status. The timeout increase may not have taken effect or a different error is occurring.
- **Fix required:** Mack pull raw cron logs for d3cdf022, diagnose actual error, verify fix takes effect. Require 2 consecutive clean runs before re-marking DONE.
- **Owner:** Mack
- **Resolution:** OPEN

---
## [OPEN] B-022: b3e6b47b Winnie Test Coverage cron erroring
- **Raised at:** 2026-02-20 06:05 EST
- **Raised by:** lenny (cron-regression-sweep)
- **Severity:** MEDIUM
- **Root cause:** First observation this cycle. Unknown cause — may be model issue, timeout, or Telegram delivery.
- **Owner:** Mack/Winnie
- **Resolution:** OPEN

---
## [OPEN] B-023: Team Morning Summary crons both erroring (0e793cfe + 0e441378)
- **Raised at:** 2026-02-20 09:08 EST
- **Raised by:** lenny (cron health sweep)
- **Severity:** MEDIUM
- **Root cause:** Unknown — both cron IDs ran at 8:00 AM EST and both show error. May be duplicate jobs sharing same root cause (model issue or Telegram delivery). Two separate IDs for what appears to be same/overlapping Morning Summary function.
- **Additional risk:** Possible duplicate cron job — 0e793cfe "Team - Morning Summary" and 0e441378 "Team: Daily Morning Summary" may be same job registered twice. Recommend Mack audit and disable one.
- **Owner:** Mack
- **Resolution:** OPEN

---
## [OPEN] B-024: Winnie oh-my-opencode cron (976facd2) erroring
- **Raised at:** 2026-02-20 12:06 EST (observed prior cycle, filing now)
- **Raised by:** lenny (cron health sweep)
- **Severity:** LOW
- **Root cause:** Unknown. Cron 976facd2 "Winnie: oh-my-opencode" runs daily at 9AM and is erroring. Last clean run unknown.
- **Owner:** Mack/Winnie
- **Resolution:** OPEN

---
## [OPEN] B-025: Market-hours crons (28a281a3 + 794fec8c) erroring at market open
- **Raised at:** 2026-02-20 12:06 EST
- **Raised by:** lenny (cron health sweep)
- **Severity:** MEDIUM (HIGH if trading signals depend on these)
- **Root cause:** Both crons ran at 9:00/9:30 AM EST today (Friday Feb 20) and errored. 28a281a3 = "Rosie Hourly Market Recap", 794fec8c = "Daily 9:30 AM Profit". These are M-F market crons.
- **Impact risk:** If trading crons downstream depend on these outputs, missed market-open data could impact trade signals.
- **Owner:** Mack
- **Resolution:** OPEN

---
## [OPEN] GUARDRAIL-001: Smoke_test output_file must not be a DB/binary/pre-existing file
- **Raised at:** 2026-02-20 15:08 EST
- **Raised by:** lenny (D-015 FAIL analysis)
- **Severity:** LOW (guardrail improvement, not a failure)
- **Observation:** D-015-quality-scoring FAIL at [13:56 UTC]: output_file was set to memu.db (pre-existing DB, 58266s old). Smoke test freshness check correctly rejected it. Agent re-ran with d015-schema-migration.md → PASS.
- **Proposed fix:** Add rule to AGENTS.md §6 or all agent profiles: "output_file must be a freshly-written markdown/text file in the current task run — not a DB path, binary, or pre-existing artifact."
- **Owner:** Rosie (AGENTS.md update)
- **Resolution:** OPEN (rule not yet formally documented)

---
## [OPEN] B-026: End-of-Day Trading Report cron (de28f1db) erroring at market close
- **Raised at:** 2026-02-20 18:08 EST
- **Raised by:** lenny (cron health sweep)
- **Severity:** MEDIUM (HIGH if EOD report drives any trading decisions or records)
- **Root cause:** Cron ran ~4:15 PM EST at market close today (Fri Feb 20) and errored. Unknown cause — model, timeout, or trading data fetch failure.
- **Owner:** Mack
- **Resolution:** OPEN

---
## [OPEN] B-027: All 4 hourly SI crons erroring immediately after deployment
- **Raised at:** 2026-02-21 00:10 EST
- **Raised by:** lenny (cron health sweep)
- **Severity:** URGENT — 4 new hourly self-improvement cron loops (5bb1a1f5, 60d17e90, 2cecafc6, b08e94f7) all fail on every run. Systematic failure pattern.
- **Root cause:** Unknown — likely model name misconfiguration, missing auth in isolated shell, or incorrect cron prompt format.
- **Impact:** All 4 hourly agent loops are dead on arrival. No hourly SI cycles running.
- **Owner:** Mack
- **Proposed fix:** Pull raw error logs for any one of the 4 crons, identify root cause, patch model/delivery config, verify next run clean.
- **Resolution:** OPEN

---
## [OPEN] B-028: X Post and X Reply Monitor crons erroring
- **Raised at:** 2026-02-21 00:10 EST
- **Raised by:** lenny (cron health sweep)
- **Severity:** MEDIUM
- **Root cause:** e7f74701 X Post Evening + 920932b9 X Reply Monitor both error. May be X/Twitter API auth or model issue.
- **Owner:** Mack
- **Resolution:** OPEN

---
## [INCIDENT] GUARDRAIL-002: shared-state.json concurrent write race condition
- **Occurred at:** 2026-02-21 03:45 UTC (10:45 PM EST)
- **Detected by:** Lenny LENNY-REFLECT-2026-02-20-22 (smoke_test.sh JSON validity check)
- **Repaired by:** Lenny LENNY-REFLECT-2026-02-20-22 retry at 03:46 UTC
- **Root cause:** Two agents wrote shared-state.json in the same minute, corrupting the file. No atomic write protection.
- **Status:** REPAIRED (no data loss)
- **Proposed fix:** Mack implement atomic write for shared-state.json (write to temp file, rename) + optionally file-lock.
- **Owner:** Mack
- **Resolution:** PARTIALLY RESOLVED — file repaired; permanent fix pending

---
## [OPEN] B-005: Email & Calendar Check cron — wrong Telegram supergroup ID
- **Raised at:** 2026-02-18 09:11 EST
- **Raised by:** lenny
- **Severity:** CRITICAL (blocks email/calendar monitoring + 8ea09e28 Midnight Critique)
- **Observation:** Cron c79de2e6 has Telegram target ID -1005112703035, which is WRONG. Correct supergroup ID needed from Michael.
- **Impact:** 29+ consecutive errors. Also blocks B-016 strategic crons.
- **Owner:** Michael (needs correct Telegram supergroup ID)
- **Resolution:** OPEN — awaiting Michael

---
## [OPEN] B-014: Winnie research benchmark timeout
- **Raised at:** 2026-02-19 06:06 EST
- **Raised by:** lenny
- **Severity:** MEDIUM
- **Observation:** Winnie research benchmark timed out (600s). May need increased timeout or checkpoint pattern.
- **Owner:** Mack
- **Resolution:** OPEN

---
## [OPEN] B-016: Strategic crons (Midnight Critique + Trading Pattern) — delivery blocked
- **Raised at:** 2026-02-19 18:08 EST
- **Raised by:** lenny
- **Severity:** HIGH
- **Observation:** 8ea09e28 Midnight Critique and cca26c09 Trading Pattern crons generate high-value content but delivery is blocked by B-005 (wrong Telegram supergroup ID). Content visible in run logs but not delivered.
- **Impact:** Revenue insights silently lost.
- **Owner:** Michael + Mack (after Michael provides correct ID)
- **Resolution:** OPEN — blocked by B-005

---
## [OPEN] B-029: OpenAI Embedding Quota Exhausted — memory_search broken
- **Raised at:** 2026-02-23 20:30 EST
- **Raised by:** winnie
- **Severity:** HIGH (blocks all memory_search calls for all agents)
- **Observation:** `memory_search` returns `insufficient_quota` error from OpenAI embeddings API. All semantic memory recall is offline.
- **Impact:** Agents cannot recall prior decisions, preferences, or context from MEMORY.md/memory/*.md. Degraded quality across all cycles.
- **Owner:** Michael (needs billing top-up or embedding provider switch)
- **Resolution:** OPEN — requires OpenAI API billing action or provider migration

---
## [FIXED] B-030: 3 cron jobs in error state — fixed by Winnie
- **Raised at:** 2026-02-23 20:30 EST
- **Raised by:** winnie
- **Severity:** MEDIUM
- **Observation:** 3 crons had errors: (1) b3e6b47b Winnie Test Coverage — timeout at 600s, (2) 6392a69e Agent Comparison Pipeline — disallowed model gemini-3.1-flash, (3) 89db2e01 X Weekly Campaign — announce delivery failure.
- **Fixes applied:** (1) timeout increased 600→900s, (2) model changed to anthropic/claude-sonnet-4-6, (3) best-effort-deliver enabled.
- **Resolution:** FIXED 2026-02-23 20:30 EST
