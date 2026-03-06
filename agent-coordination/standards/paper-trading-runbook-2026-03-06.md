# Paper Trading Runbook — 2026-03-06

## Goal
Run a full autonomous paper-trading day with strict pre-trade gating and post-trade attribution.

## Session windows
- Pre-market prep: 08:00–09:25 ET
- Active execution window: 09:35–15:30 ET
- End-of-day review: 15:45–16:30 ET

## Startup checklist
1. Verify Schwab read connectivity (account + positions + orders endpoint health)
2. Verify UW ingestion heartbeat (fresh data within expected interval)
3. Verify Firecrawl catalyst feed freshness
4. Verify risk policy loaded in PreTrade-Risk-Agent
5. Verify Execution-Agent in **PAPER_MODE=true**
6. Verify kill-switch command path available

## Decision pipeline
1. UW-Flow-Agent publishes candidate options flow
2. Firecrawl-FinIntel-Agent adds catalyst context
3. Analytics-Agent scores and ranks setups
4. PreTrade-Risk-Agent computes:
   - entry trigger
   - invalidation
   - target(s)
   - time stop
   - sizing bucket
5. If approved, issue signed `approval_token`
6. Execution-Agent submits paper order
7. Schwab-Data-Agent captures order/fill updates
8. Analytics-Agent logs setup outcomes and quality metrics

## Mandatory reject conditions
- Missing or stale source data
- Spread/liquidity outside policy
- Required catalysts contradict flow thesis
- Risk exceeds per-trade or daily cap
- Missing approval token

## Intraday controls
- Recompute portfolio risk every 5 minutes
- Pause new entries if daily drawdown exceeds soft threshold
- Hard stop (no new orders) if daily loss cap reached

## End-of-day deliverables
- Trade ledger (all attempted + executed + rejected)
- Attribution by strategy archetype
- Slippage and execution-quality report
- Top 3 policy improvements for next session

## Tomorrow success criteria
- 100% of paper orders passed pre-trade token gate
- 0 guardrail bypasses
- Complete audit trail for every decision
- Actionable EOD report generated before 16:30 ET
