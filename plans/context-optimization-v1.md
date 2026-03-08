# Context Optimization Plan v1.1
**Date:** 2026-03-07 (updated)
**Authors:** Rosie (lead), with inputs from Mack, Winnie, Lenny, Michael
**Goal:** Reduce total prompt context to <50K tokens / <30% max context window
**Status:** APPROVED — Ready for execution

---

## Problem Statement

Context rot is degrading agent performance. Current state:
- 8 bootstrap files inject ~6.3K tokens of workspace content per prompt
- The "Autonomy Mandate" block is **duplicated verbatim across 4 files** (AGENTS.md, SOUL.md, IDENTITY.md, BOOTSTRAP.md) — ~3K wasted tokens
- System prompt (tools, skills list, runtime metadata) adds ~15-20K tokens on top
- Total per-prompt context starts at **20-25K tokens before any conversation**
- 76 memory files (4MB) with no structured indexing = poor recall quality
- HEARTBEAT.md (323 tokens) loads on every message but only matters during heartbeat polls
- Skills list includes 30+ entries when each agent uses 7-10

## Token Budget Targets

| Component | Current (est.) | Target | Method |
|-----------|---------------|--------|--------|
| Bootstrap files | ~6,300 tok | <2,000 tok | Dedup + consolidate + slim |
| Skills list | ~3,500 tok | <1,000 tok | Per-agent skill scoping |
| Tool schemas | ~8,000 tok | ~8,000 tok | Not addressable (provider-set) |
| System prompt (other) | ~5,000 tok | ~5,000 tok | Minimal change |
| Memory (in-prompt) | ~341 tok | ~200 tok | Index card format |
| **Total system prompt** | **~23,000 tok** | **<16,000 tok** | |
| Conversation budget | remainder | ≥34K tok | On a 50K window |

---

## Phase 1: Deduplicate + Consolidate (Week 1)

### 1.1 One Concept, One File — Ownership Map

| File | Purpose | Token Budget | Content |
|------|---------|-------------|---------|
| **AGENTS.md** | Policy + rules + autonomy mandate | <1,200 tok | Single source for mandate, security, privacy, git workflow refs, memory protocol |
| **SOUL.md** | Tone/persona only | <300 tok | "Identity: Rosie" personality block (~18 lines). No mandate duplication |
| **TOOLS.md** | Cheat sheet + routing | <250 tok | Channel IDs, workspace path, 10-line tool index pointing to qmd-indexed detail files |
| **USER.md** | User metadata | <100 tok | Name, timezone, contacts (keep as-is) |
| **IDENTITY.md** | DELETE | 0 | Content is 2 lines of nothing after removing mandate dupe |
| **BOOTSTRAP.md** | DELETE | 0 | Content is 1 line after removing mandate dupe |
| **HEARTBEAT.md** | REMOVE from bootstrap | 0 | Keep file, but don't inject — heartbeat prompt already says `Read HEARTBEAT.md` |
| **MEMORY.md** | Index card + routing table | <200 tok | Key facts + keyword→file routing map (see 1.3) |

**Estimated savings: 6,300 → ~2,050 tokens (67% reduction)**

### 1.2 TOOLS.md Slim Format

```markdown
# TOOLS.md
## Channels
- Telegram: `-1003753060481` | Bot: `@RosieFetheBot`
## Workspace
- Path: `/Users/harrisonfethe/.openclaw/workspace`
- Data: `/Volumes/Edrive/`
## Tool References (use qmd or read for details)
- ORATS/options → tools/orats.md
- Massive/market → tools/massive.md  
- Schwab → tools/schwab.md
- Agent CLIs → tools/agent-clis.md
- Oh My OpenCode → tools/opencode.md
```

Detail files go to `workspace/tools/` directory, qmd-indexed.

### 1.3 MEMORY.md → Index Card Format

```markdown
# MEMORY.md — Quick Lookup Index
Loaded: private context only.

## Routing Tags
- trading/options → memory/archive/trading.md | memU tag:trading
- infrastructure → memory/archive/infra.md | qmd collection:tools
- cron/ops → memory/archive/ops-lessons.md
- team/agents → AGENTS.md | qmd collection:agent-coordination
- issueflow → memory/archive/issueflow.md | memU tag:revenue

## Active Blockers
(none)

## Key Facts
- Cost: ~$5.82/day (~$175/mo) as of 2026-03-01
- Dep health: sqlite-vec, sentence-transformers, schwab-py flagged
```

~200 tokens. Agent sees routing map, does targeted lookups.

### 1.4 Prompt CI Gate (prevents drift)

Create `scripts/prompt-lint.sh`:
- Fail if total bootstrap file chars > 8,000 (~2,000 tokens)
- Fail if duplicate text blocks (>100 chars) detected across bootstrap files
- Fail if any single file > 5,000 chars (~1,250 tokens)
- Run as pre-commit hook + cron weekly audit

### 1.5 Per-Agent Skill Scoping

Config change per agent in openclaw config:

```json5
{
  agents: {
    main: { skills: ["github", "coding-agent", "gog", "weather", "session-logs", "summarize", "things-mac"] },
    mack: { skills: ["github", "coding-agent", "openrouter-sonar", "firecrawl-agent"] },
    winnie: { skills: ["github", "coding-agent", "healthcheck", "session-logs"] },
    lenny: { skills: ["healthcheck", "session-logs", "github"] }
  }
}
```

**Estimated savings: ~2,500 tokens from skills list**

---

## Phase 2: QMD + Memory Architecture (Week 2-3)

### 2.1 Enable QMD Memory Backend

```json5
{
  memory: {
    backend: "qmd",
    citations: "auto",
    qmd: {
      paths: [
        "memory/",
        "memory/archive/",
        "tools/",
        "agent-coordination/"
      ],
      searchMode: "query",  // hybrid BM25 + vector + reranking
      update: { interval: "5m" }
    }
  }
}
```

Prerequisites:
- `bun install -g @tobilu/qmd`
- `brew install sqlite` (macOS extension support)
- ~2GB disk for GGUF models (auto-downloaded)

### 2.2 Memory Retrieval — Every Turn, Tiered

**Hard rule added to AGENTS.md:**
> On every non-trivial inbound message: run `memory_search` with the user's intent as query. Pull top 1-3 snippets (max 500 tokens). If confidence < 0.3, proceed without injecting. No exceptions.

**Tiered retrieval flow:**
1. **BM25 keyword pass** (fast, <50ms) — catches exact terms, IDs, error strings
2. **Semantic vector pass** (if BM25 confidence < 0.5) — catches conceptual matches
3. **LLM re-rank** (only on `qmd query` mode) — sorts by actual relevance
4. **Hard token cap**: max 500 tokens injected from memory per turn
5. **Latency budget**: 150ms soft / 400ms hard timeout — skip retrieval on timeout

### 2.3 Memory Indexing Metadata

When writing to memory, include tags:

```markdown
<!-- scope:trading | agent:rosie | confidence:high | fresh_until:2026-04-01 | supersedes:2026-02-15#trading -->
## Decision: Switch to ORATS v3 endpoint
...
```

QMD indexes these as searchable metadata. Retrieval can filter by scope/agent/freshness before semantic search.

### 2.4 Memory Hygiene Cron (weekly)

- Promote durable patterns from daily logs → MEMORY.md categories or archive files
- Archive daily logs older than 30 days → quarterly summary files
- Flag and log conflicting memory entries to `memory/conflicts.md`
- Conflict resolution: prefer newest verified + higher confidence
- Run `qmd embed` after any archive operation

### 2.5 Split TOOLS.md Detail Files

Move to `workspace/tools/`:
- `tools/orats.md` — endpoint inventory, auth, examples
- `tools/agent-clis.md` — auggie, opencode, codex patterns
- `tools/opencode.md` — Oh My OpenCode agent table, delegation patterns
- `tools/schwab.md` — token paths, API reference
- All qmd-indexed via `memory.qmd.paths`

### 2.6 Skill-ify Operational Docs

Create OpenClaw skill `team-ops`:
- Move proactivity rules, execution hooks, checkpoint format from AGENTS.md
- Only loaded when agent reads the skill (on-demand)
- ~2-3K tokens removed from every prompt

---

## Phase 2.7: RLM Principles — Document-as-Variable Pattern

Instead of installing the RLM library or MCP wrapper, we apply the **core RLM principle** as an agent pattern: never load a long document into context — treat it as an external object and use `exec` to search/slice/extract from it programmatically.

No new dependencies. No Docker. Our agents already have `exec` access. We just formalize *when and how* to use it.

### The Rule

> **Any document >5K tokens: do not `read` it into context.** Instead, use `exec` with grep/python/jq to extract only the relevant lines. Return the answer, not the document.

### Pattern Examples

**Searching a large skill file:**
```bash
# BAD: read entire SKILL.md (3K tokens wasted)
# GOOD: extract only the section you need
exec: grep -A 20 "## Configuration" ~/.openclaw/skills/github/SKILL.md
```

**Scanning memory archives for a topic:**
```bash
# BAD: read 5 daily logs into context (15K tokens)
# GOOD: search across files, return only matches
exec: grep -rl "trading" memory/ | xargs grep -h -A 3 "trading" | head -40
```

**Analyzing agent-coordination standards:**
```bash
# BAD: read 4 standards files (8K tokens)
# GOOD: query for specific answer
exec: python3 -c "
import glob
for f in glob.glob('agent-coordination/standards/*.md'):
    with open(f) as fh:
        content = fh.read()
        if 'branch naming' in content.lower():
            # Extract just the relevant section
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if 'branch' in line.lower():
                    print(f'[{f}] ' + '\n'.join(lines[i:i+5]))
"
```

**Processing a large PR diff:**
```bash
# BAD: read full diff (20K tokens)
# GOOD: summarize by file, read only changed functions
exec: git diff main --stat  # see which files changed
exec: git diff main -- src/specific-file.ts  # read only relevant file's diff
```

**Recursive decomposition (manual RLM):**
For complex tasks requiring multiple reference docs (e.g., creating a new skill):
1. First exec: list available examples → `ls ~/.openclaw/skills/*/SKILL.md | head -5`
2. Second exec: extract the pattern from ONE example → `head -30 ~/.openclaw/skills/github/SKILL.md`
3. Third exec: check standards → `grep -A 10 "skill structure" agent-coordination/standards/*.md`
4. Then generate — with only ~500 tokens of extracted context, not 10K of raw files

### QMD + RLM-Pattern Integration

The optimal flow:
1. **QMD** answers "which documents are relevant?" (fast, <200ms, BM25 + semantic)
2. **RLM pattern** answers "what does this document say?" (exec-based extraction, no context loading)

Example: Agent needs a trading decision from 3 weeks ago
- Step 1: `qmd query "trading decision options strategy"` → returns `memory/2026-02-15.md:42` + snippet
- Step 2: `exec: sed -n '40,55p' memory/2026-02-15.md` → extracts just those 15 lines
- Context cost: ~300 tokens total vs ~3,000 tokens for reading the full daily log

### AGENTS.md Rule Addition (Phase 1)

Add to AGENTS.md under document handling:

```markdown
## Document Access Rules
- Files <2K tokens: `read` directly (small enough for context)
- Files 2-5K tokens: `read` with offset/limit to get only relevant sections
- Files >5K tokens: use `exec` (grep/python/jq) to extract answers — never load full file
- Multiple files: use `exec` to search across files, then `read` only the relevant lines
- Memory archives: always use qmd or exec search first, never bulk-read daily logs
```

~100 tokens added to AGENTS.md. Saves thousands per session.

---

## Phase 3: Advanced Optimization (Week 4+)

### 3.1 QMD MCP Server

```bash
qmd mcp --http --daemon  # persistent local server on :8181
```

Wire as MCP tool in openclaw config:
```json5
{
  mcp: {
    servers: {
      qmd: { command: "qmd", args: ["mcp"] }
    }
  }
}
```

Gives agents `qmd_search`, `qmd_deep_search`, `qmd_get` as first-class tools. Lower latency than `exec qmd query`.

### 3.2 Conditional File Loading

- HEARTBEAT.md: remove from bootstrap injection. Heartbeat prompt already includes `Read HEARTBEAT.md`
- MEMORY.md: load only in private/DM contexts (already policy, enforce in config)
- Evaluate OpenClaw tiered bootstrap (issue #22438) when merged

### 3.3 Context SLO Dashboard

Track per-session:
- Total prompt size (tokens)
- Memory retrieval hit-rate (% of queries that return confidence > 0.3)
- Truncation events (files that hit bootstrap cap)
- Stale-memory hit rate (snippets past `fresh_until`)
- Alert when total context > 50K tokens or > 30% window on 3+ consecutive turns

Implementation: cron job that parses session logs + qmd stats, writes to `monitoring/context-slo.md`.

### 3.4 Deterministic Assembly Manifest

Per-turn logging of what got injected:
```json
{
  "turn": 5,
  "bootstrap_tokens": 1842,
  "memory_snippets": [{"id": "trading-2026-03", "tokens": 187, "confidence": 0.82}],
  "skills_loaded": ["github"],
  "dropped_blocks": [],
  "total_context": 28410
}
```

Enables debugging, replay, and drift detection.

### 3.5 Quick Markdown (QMD Format) Evaluation

Test converting injected bootstrap content to QMD syntax (single-char markers):
- `# Heading` → `! Heading`
- `**bold**` → `*bold*`
- Estimated 10-20% token reduction on injected content
- Only if models handle QMD syntax reliably (needs testing)

---

## Execution Ownership

| Task | Owner | Deadline |
|------|-------|----------|
| 1.1 Deduplicate files | Rosie | Week 1 |
| 1.2 Slim TOOLS.md | Rosie | Week 1 |
| 1.3 MEMORY.md index card | Rosie | Week 1 |
| 1.4 Prompt CI gate script | Mack/Lenny | Week 1 |
| 1.5 Skill scoping config | Rosie | Week 1 |
| 2.1 QMD backend setup | Mack | Week 2 |
| 2.2 Memory retrieval rule | Rosie | Week 2 |
| 2.3 Memory tagging standard | Winnie | Week 2 |
| 2.4 Memory hygiene cron | Lenny | Week 2 |
| 2.5 TOOLS.md detail files | Rosie | Week 2 |
| 2.6 team-ops skill | Mack | Week 3 |
| 2.7 RLM pattern rules in AGENTS.md + team training | Rosie | Week 2 |
| 3.1 QMD MCP server | Mack | Week 4 |
| 3.2 Conditional loading | Rosie | Week 4 |
| 3.3 Context SLO dashboard | Lenny | Week 4 |
| 3.4 Assembly manifest | Winnie | Week 4 |
| 3.5 QMD format eval | Mack | Week 5 |
| 3.6 QMD + RLM-pattern integration testing | Lenny | Week 5 |

## Success Criteria

- [ ] Total system prompt < 16K tokens (down from ~23K)
- [ ] Bootstrap workspace files < 2K tokens (down from ~6.3K)
- [ ] Memory recall confidence > 0.5 on 80%+ of queries
- [ ] Zero duplicate text blocks across bootstrap files
- [ ] Prompt CI gate passing on all commits
- [ ] Context SLO: never exceed 50K tokens or 30% window in steady state
- [ ] Memory retrieval runs on every non-trivial turn with <400ms latency
- [ ] Document access rules enforced: files >5K tokens never loaded into context directly
- [ ] All agents use exec-based extraction (grep/python/jq) for large documents
- [ ] Skill/agent creation follows decomposed pattern (list → extract → generate)
- [ ] QMD + RLM-pattern pipeline verified: fast retrieval → targeted extraction working

---

## References

- OpenClaw context docs: https://docs.openclaw.ai/concepts/context
- OpenClaw memory docs: https://docs.openclaw.ai/concepts/memory
- QMD (tobi/qmd): https://github.com/tobi/qmd
- Quick Markdown spec: https://github.com/ajithraghavan/qmd
- RLM paper (MIT): https://arxiv.org/html/2512.24601v1
- Tiered bootstrap PR: https://github.com/openclaw/openclaw/issues/22438
- Token optimizer: https://github.com/openclaw-token-optimizer/openclaw-token-optimizer
