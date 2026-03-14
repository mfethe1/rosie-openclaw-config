# Anticipatory Context Loading (ACL) — v0.2 (Post-Deliberation Round 1)

> Renamed from "Predictive Request System" per team consensus.
> Core insight: **Don't predict the question — warm the likely data.**

## Round 1 Deliberation Summary
| Agent | Vote | Key Contribution |
|-------|------|-----------------|
| Rosie | APPROVE_WITH_CHANGES | SQLite for telemetry, 85% threshold, event-driven not cron |
| Mack | BLOCK → resolved | Simplicity-first: 5 rules + parallel context loading beats statistics |
| Winnie | APPROVE_WITH_CHANGES | Split metrics, cost-aware thresholds, sparse data reality |
| Lenny | APPROVE_WITH_CHANGES | Privacy isolation, kill switch, cost caps, staleness guards |

---

## Goal
When Michael sends a message, have the most likely needed context data **already warm** so responses are faster — without predicting the exact question.

---

## Architecture: Phased Rollout

### Phase 0: Baseline (Week 1) — MEASURE FIRST
**Owner: Rosie**
- Measure current response times for Michael's top-5 request types manually
- Establish baseline: avg time to answer status checks, PR queries, cron health, build requests, research tasks
- Create `acl_baseline.json` with measured values
- **Gate: Phase 1 does not start until baseline is documented**

### Phase 1: Rules + Logging (Week 2-3) — SHIP FAST
**Owner: Mack**

#### 1a. Context Primer (parallel fetch on every message)
When Michael sends ANY message, immediately fire these in parallel WHILE processing:
```
1. cron_health → openclaw status + last 3 cron errors
2. git_status → last 5 commits + open PRs + CI status
3. agent_status → which agents ran in last hour + any failures
```
These run async, results cached for 60s. If the actual response needs any of this data, it's already warm.

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

#### 1c. Request Logger (passive telemetry)
- **Post-message hook** (NOT cron): after every Michael message, append one row to SQLite:
  ```sql
  CREATE TABLE request_log (
      id INTEGER PRIMARY KEY,
      timestamp TEXT,
      category TEXT,  -- status|build|fix|revenue|research|coordination|review
      time_of_day TEXT,  -- morning|afternoon|evening
      day_of_week TEXT,
      context_json TEXT,  -- {has_open_pr, recent_commit, cron_failing, ...}
      response_time_ms INTEGER,
      used_cached_context BOOLEAN
  );
  ```
- SQLite file: `~/.openclaw/workspace/.acl/request_log.db`
- **7-day rolling window**: auto-prune rows older than 7 days on each write
- **No memU writes**: telemetry stays in SQLite, not in knowledge store

#### 1d. Safety Rails (from Lenny)
- **Kill switch**: `/predict off` command halts all ACL activity instantly
- **Non-blocking**: cache miss = fall through to normal handling, zero added latency
- **Cost caps**: max 20 context-prime executions per hour (hard cap)
- **Idle detection**: no Michael message in 15min → stop priming until next message
- **Privacy namespace**: all ACL data in `~/.openclaw/workspace/.acl/` (isolated directory, not in memU)
- **No behavioral profiling**: store request categories only, never store message content

### Phase 2: Data Analysis + Trajectory (Week 4-6) — LEARN FROM DATA
**Owner: Winnie (analysis), Mack (implementation)**
- Requires: ≥50 logged requests from Phase 1
- Analyze request_log.db for patterns beyond the 5 hardcoded rules
- **Category-level analysis only** (not exact-request prediction)
- Rule-based state machine for common conversation flows:
  - `status_check → drill_down → action_request`
  - `review → fix → verify`
  - `research → build → deploy`
- Add new rules to the engine based on discovered patterns
- **Cost-aware threshold**: `confidence × speed_value > compute_cost` before any new priming rule activates
- **Split metrics tracking**:
  - Category accuracy (target: 50%+ by end of Phase 2)
  - Context cache hit rate (target: 30%+ of primed data actually used)
  - Response time delta vs baseline

### Phase 3: Adaptive Prediction (Month 2+) — ONLY IF JUSTIFIED
**Owner: Team decision**
- **Gate: Phase 3 only starts if Phase 2 shows >40% cache hit rate**
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
| `context_primer.py` | Mack | 1 | Parallel context fetcher (3 data sources) |
| `rule_engine.py` | Mack | 1 | 5-rule context priming engine |
| `request_logger.py` | Mack | 1 | SQLite post-message hook logger |
| `acl_safety.py` | Lenny | 1 | Kill switch, cost caps, idle detection |
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
| 1 | Cache hit rate | >20% | Primed data used in actual response |
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
- Phase 2+: Publish `predictions.michael.context_warm` with primed data keys for cross-agent use
- All NATS messages use existing AGENT_EVENTS stream (no new streams needed)
