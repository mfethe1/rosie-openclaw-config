# Context, Memory & Cost Optimization Policy
## All Agents — Strict Enforcement

**Effective:** 2026-03-07
**Source:** OpenClaw docs (memory, compaction, session-pruning, prompt-caching, context) + Tobi's QMD + video analysis

---

## 1. The Core Problem: Compaction Destroys Chat-Based Instructions

Any rule, constraint, or decision given **only in chat** will be lost when compaction triggers.
Compaction summarizes older conversation to stay within token limits — nuance, specific constraints, and safety rules get erased.

**HARD RULE:** If it matters, it goes in a file. Chat instructions are ephemeral. File instructions survive every session.

---

## 2. Memory Architecture (Four Layers)

| Layer | What | Survives Compaction? | Where |
|-------|------|---------------------|-------|
| **L1: Bootstrap files** | SOUL.md, AGENTS.md, USER.md, IDENTITY.md, TOOLS.md, HEARTBEAT.md | YES — reloaded every turn | Workspace root |
| **L2: Session transcript** | Full conversation JSONL on disk | On disk yes, but model can't see compacted parts | `~/.openclaw/sessions/` |
| **L3: Active context window** | What the model actually sees right now | NO — this IS the volatile window | In-memory |
| **L4: Retrieval index** | Searchable memory via memory_search / QMD | YES — queried on demand | SQLite/QMD index |

**Agent discipline:**
- Durable rules → L1 (bootstrap files)
- Daily decisions/findings → `memory/YYYY-MM-DD.md` (L4-indexed)
- Long-term curated knowledge → `MEMORY.md` (L1 in private, L4-indexed)
- Never rely on L3 (active context) for anything that must persist

---

## 3. Pre-Compaction Memory Flush (MUST BE CONFIGURED)

Before compaction erases context, a silent agentic turn saves durable notes to disk.

**Required config:**
```json5
{
  agents: {
    defaults: {
      compaction: {
        reserveTokensFloor: 40000,  // <-- CRITICAL: must have headroom
        memoryFlush: {
          enabled: true,
          softThresholdTokens: 4000
        }
      }
    }
  }
}
```

**Why 40,000 tokens floor:** If too tight, the API overflow bypasses the flush entirely — total context loss. 40k gives the flush turn enough room to execute before the hard limit.

**Current gap:** Our config has `memoryFlush.enabled: true` and `softThresholdTokens: 30000` but `reserveTokensFloor` is NOT SET. This must be fixed immediately.

---

## 4. Mandatory Memory Retrieval Before Action

Every agent MUST search memory before taking non-trivial action:

```
Before answering anything about prior work, decisions, dates, people, preferences, or todos:
run memory_search on MEMORY.md + memory/*.md;
then use memory_get to pull only the needed lines.
```

This is already in our system prompt. Enforcement: if an agent produces output that contradicts stored memory, it's a policy violation.

---

## 5. Bootstrap File Discipline

| File | Purpose | Max Size | Update Policy |
|------|---------|----------|---------------|
| `AGENTS.md` | Operational rules, agent roles, delegation | <100 lines | Rationale-required commits |
| `SOUL.md` | Personality, tone, decision framework | <100 lines | Rationale-required commits |
| `USER.md` | User info, preferences, contacts | <50 lines | As needed |
| `TOOLS.md` | Tool catalog, API locations, paths | <200 lines | On tool changes |
| `IDENTITY.md` | Core identity statement | <30 lines | Rarely |
| `HEARTBEAT.md` | Autonomous work loop | <50 lines | On workflow changes |

**HARD RULE:** Keep bootstrap files lean. Every char counts against context window.
If a file exceeds `bootstrapMaxChars` (default 20,000), it gets truncated and the agent loses the tail.

---

## 6. Session Pruning for Cost Control

Pruning trims old tool results in-memory (doesn't rewrite disk). Reduces cacheWrite costs.

**Required config:**
```json5
{
  agents: {
    defaults: {
      contextPruning: {
        mode: "cache-ttl",
        ttl: "1h"  // prune after 1h idle (align with cacheRetention)
      }
    }
  }
}
```

**Current gap:** Our TTL is set to `24h` — way too long. Tool results accumulate for 24 hours before pruning. Should be `1h` to match long cache retention, or `5m` to match short.

---

## 7. Prompt Caching Optimization

Cache = reuse unchanged prompt prefix. Saves money and speeds up responses.

**Required config:**
```json5
{
  agents: {
    defaults: {
      models: {
        "anthropic/claude-opus-4-6": {
          params: {
            cacheRetention: "long"  // 1h cache window
          }
        },
        "anthropic/claude-sonnet-4-6": {
          params: {
            cacheRetention: "long"
          }
        }
      },
      heartbeat: {
        every: "55m"  // keep cache warm (just under 1h TTL)
      }
    }
  }
}
```

**Current gap:** No `cacheRetention` set on any model. Heartbeat is `5m` (fine for cache-warm but expensive — reconsider if cost is a concern).

---

## 8. QMD Integration (Recommended — Phase 2)

QMD (Tobi's local search engine) combines BM25 + vector + LLM reranking for high-quality retrieval across all memory files.

**Benefits over built-in:**
- Hybrid search (keyword + semantic + reranker)
- Context-aware snippets (returns relevant chunks, not whole files)
- Indexes meeting notes, docs, past sessions — not just memory/*.md
- Fully local (no API calls for search)

**Config to enable:**
```json5
{
  memory: {
    backend: "qmd",
    qmd: {
      searchMode: "query",  // hybrid + reranking (best quality)
      includeDefaultMemory: true,
      paths: [
        { path: "~/Documents/notes", name: "notes" },
        { path: "~/.openclaw/workspace/agent-coordination", name: "coordination" }
      ],
      sessions: {
        enabled: true,
        retentionDays: 30
      }
    }
  }
}
```

**Prerequisites:** Install QMD (`bun install -g @tobilu/qmd`), ensure `brew install sqlite` for extension support.

---

## 9. Memory Hygiene Schedule

| Frequency | Action | Who |
|-----------|--------|-----|
| Per-task | Write learnings to `memory/YYYY-MM-DD.md` | Every agent |
| Pre-compaction | Automated flush saves durable notes | System (configured) |
| Weekly | Promote durable rules from daily logs → `MEMORY.md` | Rosie (orchestrator) |
| Bi-weekly | Prune tactical knowledge >14 days old | Any agent |
| Monthly | Prune observational knowledge >30 days old | Any agent |
| Monthly | Review bootstrap file sizes (`/context list`) | Human or Rosie |

---

## 10. Cost Control Rules

1. **Never let compaction invalidate cache unnecessarily** — use `/compact` proactively with focused instructions rather than waiting for auto-compaction
2. **Set `cacheRetention: "long"` on primary models** — amortizes cache cost over 1h instead of 5m
3. **Set pruning TTL to match cache TTL** — prevents stale tool results from bloating cacheWrite
4. **Monitor with `/usage full`** — track cacheRead vs cacheWrite ratio. High cacheWrite = something is invalidating cache frequently
5. **Keep bootstrap files lean** — every extra char in system prompt is cached AND counted on every turn

---

## 11. Diagnostics Checklist

When debugging memory/context issues:

1. `/context list` — check what's injected, any truncation?
2. `/context detail` — which tools/skills consume the most tokens?
3. `/status` — how full is the context window?
4. `/usage tokens` — per-reply token breakdown
5. Check `~/.openclaw/logs/cache-trace.jsonl` if cache diagnostics enabled

---

## Implementation Priority

### Immediate (config changes)
- [ ] Set `reserveTokensFloor: 40000`
- [ ] Set `cacheRetention: "long"` on Anthropic models
- [ ] Reduce `contextPruning.ttl` from `24h` to `1h`
- [ ] Adjust heartbeat to `55m` for cache-warm (or keep `5m` if autonomy is priority)

### Phase 2
- [ ] Install QMD and enable `memory.backend: "qmd"`
- [ ] Add coordination + notes directories to QMD paths
- [ ] Enable session indexing for cross-session search

### Ongoing
- [ ] Weekly memory hygiene
- [ ] Monthly bootstrap file size audit
- [ ] Expertise TTL pruning (tactical 14d, observational 30d)
