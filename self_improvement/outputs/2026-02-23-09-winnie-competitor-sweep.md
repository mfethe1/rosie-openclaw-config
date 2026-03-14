# Winnie Competitor Sweep — 2026-02-23 09:10 EST

## Scope
Monthly competitor monitoring of oh-my-opencode, Antfarm, and Ralph-loop tooling.
Assessed against: deterministic execution guarantees, verification gates, cost/maintenance burden, model portability.

---

## 1. oh-my-opencode / oh-my-claudecode Ecosystem

### Current State (Feb 2026)
- **oh-my-opencode** (by code-yeongyu): Built on top of OpenCode (45k+ GitHub stars). Provided multi-model orchestration, parallel background agents, LSP/AST tooling, and "Ultrawork" mode. **Effectively dead** after Anthropic's Jan 9 2026 OAuth block for subscription tokens in third-party tools.
- **oh-my-claudecode** (by Yeachan-Heo): Successor built on Claude Code native Hooks. 7 execution modes (Autopilot, Ultrawork, Ralph, Ultrapilot, Ecomode, Swarm, Pipeline), 32 specialized agents, 40+ skills. Still functional but **superseded** by Anthropic's official Agent Teams feature (shipped with Opus 4.6).
- **Claude Code Agent Teams** (official, experimental): Native multi-agent — shared task list, mailbox inter-agent messaging, team lead + independent teammates. Claude Code v2.1.50 (Feb 20 2026) continues refinements. Community actively using it with usage-limit-aware orchestration (80% threshold graceful pause).

### Assessment vs. Our Architecture

| Dimension | oh-my-opencode / claudecode | Claude Agent Teams | Our System |
|---|---|---|---|
| **Deterministic Execution** | ❌ LLM-directed, no hard gates | ⚠️ Better — shared task list but still LLM-driven coordination | ✅ Deterministic skeleton with explicit step outputs |
| **Verification Gates** | ❌ No formal verification step | ⚠️ Teammates can challenge but no mandatory gate | ✅ smoke_test.sh + eval-log.md + cross-agent review |
| **Cost/Maintenance** | 🔴 $15-20/30min on API; burns Max subscriptions fast | 🟡 High token overhead (multiple context windows) | 🟢 Cron-bounded, model-rotated, cost-tracked |
| **Model Portability** | ✅ oh-my-opencode was provider-agnostic; claudecode = Claude only | ❌ Claude-only | ✅ 10+ models rotated per AGENTS.md §2 |

### Recommendations
- **KEEP** our deterministic workflow skeleton — oh-my-claudecode's 7 modes prove the community craves multi-agent, but without hard verification gates they produce unreliable output. Our smoke_test + eval-log pattern is strictly better.
- **TEST** Claude Agent Teams' inter-agent messaging pattern. Their shared task list + direct teammate messaging is a clean coordination primitive. Consider adding a lightweight inter-agent message queue to our shared-state.json (currently broadcasts-only) for finer-grained handoffs.
- **STOP** tracking oh-my-opencode — it's dead post-OAuth block. Monitor oh-my-claudecode only for novel patterns; it's being eclipsed by official Agent Teams.

---

## 2. Antfarm (snarktank/antfarm)

### Current State (Feb 2026)
- **v0.5.1** (our installed version, Feb 20 2026). Latest upstream features: sequential run numbers (#100), namespace collision fix, agent ID underscore delimiter, fallback agentId + delivery mode in cron jobs.
- Active issue tracker: #218 (Feb 20) requests circuit breaker for agent cron jobs after N consecutive failures — directly relevant to our reliability concerns.
- Growing community adoption: blog posts claiming 300-700% velocity gains with specialized agent teams (planner → developer → verifier → tester → reviewer).
- DeepWiki now indexes Antfarm's architecture, improving discoverability.

### Assessment vs. Our Architecture

| Dimension | Antfarm | Our System |
|---|---|---|
| **Deterministic Execution** | ✅ YAML workflow steps, each gets fresh context | ✅ Equivalent — our AGENTS.md §4 + profile-based dispatch |
| **Verification Gates** | ✅ Verifier + Tester as separate workflow steps, STATUS: retry | ✅ Equivalent + smoke_test.sh + eval-log.md |
| **Cost/Maintenance** | 🟡 Lightweight CLI but requires OpenClaw cron infra | 🟢 Already integrated, lower overhead |
| **Model Portability** | ⚠️ Inherits from OpenClaw model config | ✅ Explicit model rotation policy |

### Recommendations
- **KEEP** Antfarm installed as workflow runner for compound tasks (already in AGENTS.md §12). Our v0.5.1 is current.
- **TEST** Antfarm's circuit-breaker proposal (#218) — if implemented upstream, adopt it for our cron jobs too. Currently we only have best-effort delivery; auto-disable after N failures would reduce noise.
- **STOP** nothing — Antfarm continues to align with our architecture. No friction.

---

## 3. Ralph Wiggum Loop

### Current State (Feb 2026)
- **Official Anthropic plugin** (Dec 2025): Formalizes the bash loop with Stop Hooks and structured failure data. January 2026 deep-dive video (Huntley + Horthy) comparing bash-loop vs plugin.
- **LobeHub Skills Marketplace** (5 days ago): Published a `/loop` skill implementing model-agnostic EXECUTE → VALIDATE → QUALITY CHECK cycles until VERIFIED_DONE or iteration limit.
- **Community consensus** (multiple Feb 2026 articles): Ralph excels at mechanical, test-verifiable work (refactors, migrations, conformance). Struggles with exploratory/creative tasks. The pattern is now considered a **primitive** rather than a complete architecture.
- **DreamHost deep-dive** (Feb 2026): Excellent analysis of why it works — context windows as disposable buffers, external checks > internal reasoning, compaction erodes constraints. Core insight: "the agent doesn't decide when it's done; the harness does."

### Assessment vs. Our Architecture

| Dimension | Ralph Loop | Our System |
|---|---|---|
| **Deterministic Execution** | ⚠️ Deterministic harness but unbounded loop by default | ✅ Bounded retries + escalation |
| **Verification Gates** | ✅ External check (tests/linters) is the ONLY gate — honest by design | ✅ smoke_test.sh + eval-log + cross-agent review |
| **Cost/Maintenance** | 🟡 Can be cheap (bash) or expensive (unbounded iterations) | 🟢 Cost-tracked, bounded |
| **Model Portability** | ✅ Model-agnostic by design (any CLI agent) | ✅ Explicit rotation |

### Recommendations
- **KEEP** Ralph as a bounded pattern within our system — we already use it via smoke_test.sh fail-reflect-retry. Our D-019 fail-reflection hook is exactly the "structured failure data" that Anthropic's official plugin adds.
- **TEST** the LobeHub `/loop` skill's QUALITY CHECK step as a post-verification layer. Currently our gate is binary (PASS/FAIL); adding a quality score threshold (already in our quality_score column) as a stop condition would be a natural evolution.
- **STOP** considering unbounded Ralph loops. Community consensus is clear: without iteration limits and cost caps, they burn tokens. Our bounded retry + escalate pattern is the right refinement.

---

## 4. Cross-Cutting Trends (Feb 2026)

1. **Claude Code Agent Teams is the new benchmark** for multi-agent in the Anthropic ecosystem. Community is rapidly building on it. Our system has the advantage of model portability + deterministic gates, but we should monitor Agent Teams patterns for coordination primitives to adopt.

2. **Circuit breakers are becoming standard** — Antfarm #218, Claude Agent Teams' usage-limit monitoring (80% graceful pause). We should formalize our own: auto-disable cron after N consecutive errors.

3. **The Ralph pattern is now a universal primitive**, not a framework. Everyone from Anthropic to LobeHub to DreamHost treats EXECUTE→VERIFY→LOOP as the atomic unit. Our smoke_test + fail-reflect is already this. No action needed.

4. **Cost awareness is differentiating** — oh-my-opencode died partly because it burned $15-20/30min. Cost tracking (our cost_tracker.py) is now a competitive advantage, not a nice-to-have.

---

## 5. Scorecard Summary

| Tool | Det. Execution | Verification | Cost/Maint | Model Portability | Overall Fit |
|---|---|---|---|---|---|
| oh-my-claudecode | ❌ | ❌ | 🔴 | ❌ (Claude-only) | LOW — monitor only |
| Claude Agent Teams | ⚠️ | ⚠️ | 🟡 | ❌ (Claude-only) | MEDIUM — cherry-pick messaging pattern |
| Antfarm v0.5.1 | ✅ | ✅ | 🟢 | ⚠️ | HIGH — already integrated |
| Ralph Loop (official) | ⚠️ | ✅ | 🟡 | ✅ | HIGH — already used as bounded pattern |
| **Our System** | ✅ | ✅ | 🟢 | ✅ | — (baseline) |

---

## 6. Priority Actions for TODO.md

1. **[Winnie] P3-MEDIUM** — Evaluate Claude Agent Teams inter-agent mailbox pattern for possible shared-state.json enhancement (direct agent-to-agent messages, not just broadcasts). Est: 1 cycle.
2. **[Mack] P3-MEDIUM** — Implement circuit-breaker for agent cron jobs (auto-disable after 5 consecutive failures, re-enable manually). Inspired by Antfarm #218. Est: 1 cycle.
3. **[Winnie] P4-LOW** — Review LobeHub `/loop` skill quality-check layer for possible integration with our quality_score threshold as a stop condition. Est: 1 cycle.

---

## Meta
- **Models used:** google-antigravity/claude-opus-4-6-thinking
- **Sources:** jeongil.dev, vincirufus.com, dreamhost.com/blog/ralph-wiggum, claudefa.st, tldl.io, GitHub snarktank/antfarm, lobehub.com, wisdomai.com, reddit r/ClaudeCode
- **Previous sweep:** 2026-02-17-18-winnie (initial competitor assessment; decision: Antfarm ADOPT, OMO SKIP, Ralph KEEP as pattern)
- **Delta from previous:** oh-my-opencode confirmed dead; oh-my-claudecode superseded by official Agent Teams; Ralph formalized by Anthropic; Antfarm v0.5.1 stable; circuit-breaker pattern emerging as industry standard
