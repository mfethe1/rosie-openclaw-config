# Trading Agent Team v1 (Paper-First)

## Objective
Stand up a multi-agent trading stack for autonomous **paper trading** first, then controlled progression to live execution.

## Agent roster and responsibilities

### 1) UW-Flow-Agent
- Source: Unusual Whales API
- Responsibilities:
  - Pull option flow, sweeps, volume/OI anomalies, dark pool context
  - Score directional conviction + unusualness
  - Emit normalized signal records
- Output contract:
  - `symbol`, `contract`, `signal_type`, `confidence`, `timestamp`, `raw_source_ref`

### 2) Firecrawl-FinIntel-Agent
- Source: Firecrawl + web financial sources
- Responsibilities:
  - Pull catalyst/news/earnings/macro context
  - Validate source quality and recency
  - Tag catalysts by expected impact window
- Output contract:
  - `symbol`, `catalyst_type`, `impact_window`, `confidence`, `citations[]`

### 3) Schwab-Data-Agent
- Source: Schwab API (read endpoints)
- Responsibilities:
  - Pull balances, positions, orders, fills, and quote snapshots
  - Maintain canonical account + position state
  - Publish portfolio risk features (exposure, concentration, Greeks where available)
- Output contract:
  - `account_state`, `positions[]`, `open_orders[]`, `risk_snapshot`

### 4) Analytics-Agent
- Source: UW + Firecrawl + Schwab data
- Responsibilities:
  - Fuse all upstream records into ranked ideas
  - Compute signal drift, win-rate by setup, and regime tags
  - Produce candidate trade plans for pre-trade validation
- Output contract:
  - `trade_candidates[]` with expected setup stats and rationale

### 5) PreTrade-Risk-Agent
- Responsibilities:
  - Hard risk gating before any execution intent
  - Define entry, invalidation, target(s), time stop, and position sizing
  - Reject trades that violate policy
- Output contract:
  - `decision: approve|reject|defer`
  - `risk_plan` (entry/exit/sizing/time-stop/max-loss)
  - `approval_token` (required for execution path)

### 6) Schwab-Execution-Agent
- Source: Schwab API (execution endpoints)
- Responsibilities:
  - Place/cancel/replace orders only when valid `approval_token` exists
  - Enforce order policy + kill-switch
  - Log exact order payload and resulting execution events
- Output contract:
  - `execution_receipt` + `order_ids[]` + `status`

## Additional agents to add next (recommended)

### A) Options-Structure-Agent (priority high)
- Convert directional ideas into structure: single-leg vs debit spread vs credit spread/hedge
- Minimize defined risk and improve probability-adjusted returns

### B) Execution-Quality-Agent (priority high)
- Measure slippage, fill quality, and timing efficiency
- Recommend limit-price tactics and session windows

### C) Portfolio-Hedging-Agent (priority high)
- Monitor total portfolio delta/vega/theta and event concentration
- Recommend overlays/hedges when thresholds breach

## Separation-of-duties policy
- Signal agents cannot execute.
- Execution agent cannot self-approve.
- PreTrade-Risk-Agent approval token is mandatory for any order path.
- All actions are logged with deterministic event IDs.

## Core workflow (paper mode)
1. Ingest: UW + Firecrawl + Schwab data
2. Analytics ranks candidates
3. PreTrade-Risk-Agent approves/rejects
4. Execution agent sends to paper endpoint/simulator
5. Schwab-Data-Agent collects fills + updates state
6. Analytics computes attribution and next-cycle adjustments

## Paper-trading guardrails
- Max position risk per trade: 1.0% account notional equivalent
- Max daily loss cap: 2.0%
- Max concurrent positions: 5
- No market orders during first 15 minutes after open
- Auto-stop paper trading if 3 consecutive policy violations occur

## Definition of ready for live (future)
- Minimum 10 trading days paper sample
- Positive expectancy across at least 30 qualified setups
- Slippage within policy threshold
- Zero guardrail bypass incidents
- Manual go-live approval from Michael
