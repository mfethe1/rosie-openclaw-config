# Blocker Prediction & Escalation Matrix

**Purpose:** Proactive detection of blocked tasks, external wait-states, and dependency chains. Updated every cycle by Rosie.

**Format:** `| Task | Blocker Type | Duration | Owner Waiting On | Escalation Action | ETA |

## Active Blockers (Feb 21)

| Task | Blocker Type | Duration | Owner Waiting On | Escalation Action | ETA |
|------|--------------|----------|------------------|-------------------|-----|
| B-005: Telegram Supergroup Fix | External Input | ~20h | Michael (correct group ID) | Ping Michael with group history context | When Michael replies |
| B-007: Cron Delivery to -5198788775 | System Investigation | ~8h | Ops (bot access check) | Check bot membership + re-invite if needed | EOD Feb 21 |
| D-026: Foresight Memory Pipeline Tuning | Blocked on Knowledge Extractor | 0h | Winnie (ProMem output) | Verify knowledge_extractor.py outputs to disk | EOD Feb 21 |

## Dependency Chains (Parallelization Opportunities)

- **Chain A (Cron Health):** Model sweep → Delivery hardening → Watchdog tuning. *Parallel:* delivery hardening can start independently.
- **Chain B (Memory):** Knowledge extractor → D-026 foresight tuning → D-027 weekly rollup. *Blocker:* extractor output freshness critical.

## Escalation Rules
- External wait >12h → escalate to Michael with context summary
- System blocker >6h → escalate to ops/infra owner
- Dependency chain stall → identify unblocked parallel work immediately
