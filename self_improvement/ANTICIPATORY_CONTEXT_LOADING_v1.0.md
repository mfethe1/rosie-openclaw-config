# Anticipatory Context Loading (ACL) — v1.0 FINAL
## Deliberation Consensus: 4/4 APPROVE_WITH_CHANGES → ALIGNED

> **Core insight: Don't predict the question — warm the likely data.**
> 2 rounds of multi-agent deliberation via NATS. Zero blocks remaining.

---

## Deliberation Record

### Round 1
| Agent | Vote | Key Contribution |
|-------|------|-----------------|
| Rosie | APPROVE_WITH_CHANGES | SQLite for telemetry, event-driven not cron, staleness guards |
| Mack | **BLOCK** | Over-engineered → simplify to 5 rules + parallel context loading |
| Winnie | APPROVE_WITH_CHANGES | Split metrics, cost-aware thresholds, sparse data reality |
| Lenny | APPROVE_WITH_CHANGES | Privacy isolation, kill switch, cost caps, auto-disable |

### Round 2 (post-refinement)
| Agent | Vote | Remaining Concerns (non-blocking) |
|-------|------|----------------------------------|
| Rosie | ✅ APPROVE | Debounce primer <30s, clarify cost cap unit, min sample size for gates |
| Mack | ✅ APPROVE | Phase 0 max 72h, kill switch via env var, define "cache hit" precisely |
| Winnie | ✅ APPROVE | 30-day rule review date, default speed_value=1.0, time-cap on Phase 2 gate |
| Lenny | ✅ APPROVE | SQLite WAL mode, circuit breaker on 3 failures, `acl status` diagnostic |

---

## Goal
When Michael sends a message, have the most likely needed context data **already warm** so responses are faster — without predicting the exact question.

---

## Architecture: Phased Rollout

### Phase 0: Baseline (Max 72 hours) — MEASURE FIRST
**Owner: Rosie**
- Measure current response times for Michael's top-5 request types
- Establish baseline: avg time for status checks, PR queries, cron health, build requests, research tasks
- Create `acl_baseline.json` with measured values
- **Gate: Phase 1 does not start until baseline is documented**
- **Time cap: 72 hours max — go/no-go decision by then**

### Phase 1: Rules + Logging (Week 2-3) — SHIP FAST
**Owner: Mack**

#### 1a. Context Primer (parallel fetch on every message)
When Michael sends ANY message, immediately fire these in parallel WHILE processing:
```
1. cron_health → openclaw status + last 3 cron errors
2. git_status → last 5 commits + open PRs + CI status
3. agent_status → which agents ran in last hour + any failures
```
Results cached for 60s. If the actual response needs any of this data, it's already warm.

**Debounce**: skip if last fetch was <30s ago (prevents hammering during rapid exchanges).

**Definition of "cache hit"**: primed data was referenced in the response generated within 60s of the fetch.

#### 1b. Rule Engine (5 rules, no ML)
```python
RULES = {
    "morning_weekday": {
        "condition": "8am-10am EST + Mon-Fri",
        "prime": ["cron_health", "overnight_summary", "inbox_count"],
    },
    "post_commit": {
        "condition": "git push detected in last 15min",
        "prime": ["ci_status", "test_results", "pr_diff"],
    },
    "pr_open": {
        "condition": "open PR with Michael's commits",
        "prime": ["pr_review_status", "ci_checks", "merge_conflicts"],
    },
    "after_deploy": {
        "condition": "deploy event in last 30min",
        "prime": ["health_checks", "error_rates", "rollback_status"],
    },
    "evening_wind_down": {
        "condition": "7pm-10pm EST",
        "prime": ["daily_summary", "tomorrow_calendar", "open_blockers"],
    },
}
```
**30-day review gate**: rules must be reviewed/updated within 30 days of activation. If not reviewed, emit a NATS alert.

#### 1c. Request Logger (passive telemetry)
- **Post-message hook** (NOT cron): after every Michael message, append one row to SQLite:
  ```sql
  CREATE TABLE request_log (
      id INTEGER PRIMARY KEY,
      timestamp TEXT NOT NULL,
      category TEXT NOT NULL,
      time_of_day TEXT,
      day_of_week TEXT,
      context_json TEXT,
      response_time_ms INTEGER,
      used_cached_context BOOLEAN DEFAULT 0
  );
  ```
- SQLite file: `~/.openclaw/workspace/.acl/request_log.db`
- **SQLite WAL mode** enabled for concurrent read/write safety
- **7-day rolling window**: auto-prune rows older than 7 days on each write
- **No memU writes**: telemetry stays in SQLite, not in knowledge store
- Exclude `~/.openclaw/workspace/.acl/` from backup/snapshot lists

#### 1d. Safety Rails
- **Kill switch**: `ACL_ENABLED=0` env var halts all ACL activity instantly. Also responds to `/predict off` command.
- **Non-blocking**: cache miss = fall through to normal handling, zero added latency
- **Cost caps**: max 20 context-prime API calls per hour (hard cap, counted per execution)
- **Circuit breaker**: 3 consecutive primer failures → pause ACL for 1 hour, emit NATS alert, auto-retry
- **Idle detection**: no Michael message in 15min → stop priming until next message
- **Privacy namespace**: all ACL data in `~/.openclaw/workspace/.acl/` (isolated directory, not in memU)
- **No behavioral profiling**: store request categories only, never store message content
- **Auto-disable**: if cache hit rate <40% after 2 weeks of data (min 100 messages), auto-disable pre-fetch and alert

#### 1e. Diagnostics
- `acl status` command outputs: cache hit rate, cache size, last prune timestamp, rules active, cost budget remaining, circuit breaker state

### Phase 2: Data Analysis + Trajectory (Week 4-6) — LEARN FROM DATA
**Owner: Winnie (analysis), Mack (implementation)**
- **Gate: ≥50 logged requests OR 14 days elapsed** (whichever comes first — prevents indefinite stall)
- Analyze request_log.db for patterns beyond the 5 hardcoded rules
- **Category-level analysis only** (not exact-request prediction)
- Rule-based state machine for common conversation flows:
  - `status_check → drill_down → action_request`
  - `review → fix → verify`
  - `research → build → deploy`
- Add new rules to the engine based on discovered patterns
- **Cost-aware threshold**: `confidence × speed_value > compute_cost` — default `speed_value=1.0` until calibrated from baseline data
- **Split metrics tracking**:
  - Category accuracy (target: 50%+ by end of Phase 2)
  - Context cache hit rate (target: 30%+ of primed data actually used)
  - Response time delta vs baseline

### Phase 3: Adaptive Prediction (Month 2+) — ONLY IF JUSTIFIED
**Owner: Team decision**
- **Gate: Phase 2 shows >40% cache hit rate over ≥100 messages across ≥7 days**
- Lightweight embedding-based category clustering (detect new request types)
- Frequency matrix P(category | context_features) from SQLite data
- Adaptive rule generation: auto-propose new rules, require human approval before activation
- NATS integration: publish `predictions.michael.context_warm` for other agents to subscribe
- Auto-disable if accuracy <40% for 2 consecutive weeks

---

## Files to Create
| File | Owner | Phase | Purpose |
|------|-------|-------|---------|
| `acl_baseline.json` | Rosie | 0 | Baseline response time measurements |
| `context_primer.py` | Mack | 1 | Parallel context fetcher (3 sources, debounced) |
| `rule_engine.py` | Mack | 1 | 5-rule context priming engine |
| `request_logger.py` | Mack | 1 | SQLite post-message hook logger (WAL mode) |
| `acl_safety.py` | Lenny | 1 | Kill switch, cost caps, circuit breaker, idle detection |
| `acl_status.py` | Lenny | 1 | Diagnostic command (`acl status`) |
| `pattern_analyzer.py` | Winnie | 2 | SQLite analysis + new rule discovery |
| `trajectory_fsm.py` | Mack | 2 | Rule-based conversation flow state machine |
| `adaptive_predictor.py` | Mack | 3 | Embedding-based category prediction |

All files live in `~/.openclaw/workspace/self_improvement/acl/`

---

## Success Metrics (Phased)
| Phase | Metric | Target | Measurement |
|-------|--------|--------|-------------|
| 0 | Baseline documented | 100% | acl_baseline.json exists with 5+ request types |
| 1 | Context primer operational | Working | 3 parallel fetches complete in <2s |
| 1 | Request logger capturing | >90% | SQLite rows match inbound message count |
| 1 | Cache hit rate | >20% | Primed data referenced in response within 60s |
| 2 | Category accuracy | >50% | Correct category predicted for >50% of requests |
| 2 | Response time improvement | >25% | vs Phase 0 baseline for top-3 request types |
| 3 | Adaptive rule quality | >40% hit | Auto-generated rules have >40% cache hit rate |

---

## What This Is NOT
- ❌ Not a mind-reading system that predicts exact questions
- ❌ Not an LLM-on-every-message cost center
- ❌ Not a behavioral surveillance profile
- ✅ A context warming system that makes the agent faster by having data ready
- ✅ 5 simple rules + parallel fetch that ships in a day
- ✅ A learning system that gets smarter with data, gated by proof at each phase

---

## NATS Integration
- Phase 1: Publish `events.broadcast.acl_status` on rule engine activation/deactivation
- Phase 1: Publish `events.report.acl.cache_hit` / `events.report.acl.cache_miss` for telemetry
- Phase 1: Publish `events.broadcast.acl_circuit_breaker` on circuit breaker trigger/recovery
- Phase 2+: Publish `predictions.michael.context_warm` with primed data keys for cross-agent use
- All NATS messages use existing AGENT_EVENTS stream (no new streams needed)

---

## Appendix: Round 2 Minor Items (folded into v1.0)
| Source | Concern | Resolution |
|--------|---------|------------|
| Rosie | Debounce primer on rapid messages | 30s cooldown between primer runs |
| Rosie | Clarify cost cap unit | 20 API calls/hour (not 20 executions) |
| Rosie | Min sample size for phase gates | 100 messages + 7 days for Phase 2→3 |
| Mack | Phase 0 duration cap | 72h max |
| Mack | Kill switch as env var | `ACL_ENABLED=0` |
| Mack | Define "cache hit" | Primed data referenced in response within 60s |
| Winnie | Rule review sunset date | 30-day review gate on rules |
| Winnie | Default speed_value | 1.0 until calibrated |
| Winnie | Time-cap on Phase 2 gate | 14 days OR 50 requests |
| Lenny | SQLite WAL mode | Enabled in schema |
| Lenny | Circuit breaker | 3 failures → 1hr pause + alert |
| Lenny | Backup exclusion | .acl/ excluded from snapshots |
| Lenny | `acl status` diagnostic | Added as acl_status.py |
