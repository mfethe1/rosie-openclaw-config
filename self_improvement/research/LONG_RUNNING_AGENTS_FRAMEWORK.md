# Long-Running Autonomous Agent Framework
**Research Report & Integration Plan**

**Date:** 2026-02-12 17:25 EST
**Researchers:** Rosie (initial), rotating every 4 hours with 1-hour offsets
**Next research:** Winnie @ 18:25, Mack @ 19:25, Rosie @ 20:25

---

## Executive Summary

Discovered 10+ high-value frameworks for persistent, long-running autonomous agents with continuous learning capabilities. Three breakthrough systems stand out:

1. **memU** - 24/7 proactive memory framework (OpenClaw-specific!)
2. **Agno** - Multi-agent system with cross-session learning
3. **Agent Zero** - Persistent memory + self-improving agents

**Key insight:** Most frameworks treat agents as stateless. The future = agents that remember, learn, and improve continuously.

---

## 🏆 Priority 1: memU (MUST INTEGRATE)

**GitHub:** https://github.com/NevaMind-AI/memU

**Why it's perfect for us:**
- **Built explicitly for OpenClaw** (mentions moltbot, clawdbot)
- 24/7 proactive agents (exactly our use case)
- Reduces token costs for always-on agents
- File-system-like memory structure

### Core Innovation: Memory as File System

```
memory/
├── preferences/
│   ├── communication_style.md
│   └── topic_interests.md
├── relationships/
│   ├── contacts/
│   └── interaction_history/
├── knowledge/
│   ├── domain_expertise/
│   └── learned_skills/
└── context/
    ├── recent_conversations/
    └── pending_tasks/
```

### Architecture: 3-Layer Hierarchical Memory

1. **Resource** - Raw data (conversations, documents, images)
2. **Item** - Extracted facts, preferences, skills
3. **Category** - Auto-organized topics

### Proactive Capabilities

**Unlike reactive systems (we read MEMORY.md on demand), memU:**
- Monitors continuously in background
- Predicts user intent before commands
- Auto-extracts insights from interactions
- Surfaces relevant context proactively

### Performance

- 92.09% accuracy on Locomo benchmark
- 26% higher accuracy than OpenAI Memory
- 91% lower latency
- 90% lower token usage

### Integration Plan

```python
# Install memU
pip install memu-py

# Basic integration with OpenClaw
from memu import MemUService

service = MemUService(
    llm_profiles={
        "default": {
            "base_url": "https://api.openai.com/v1",
            "api_key": os.getenv("OPENAI_API_KEY"),
            "chat_model": "gpt-5.2",
        },
        "embedding": {
            "base_url": "https://api.openai.com/v1",
            "api_key": os.getenv("OPENAI_API_KEY"),
            "embed_model": "text-embedding-3-large"
        }
    },
    database_config={
        "metadata_store": {"provider": "postgres"},  # or sqlite
        "vector_store": {"provider": "pgvector"}
    }
)

# Continuous learning pipeline
await service.memorize(
    resource_url="/Users/harrisonfethe/.openclaw/workspace/memory/2026-02-12.md",
    modality="conversation",
    user={"user_id": "rosie"}
)

# Proactive retrieval
context = await service.retrieve(
    queries=[{"role": "user", "content": {"text": "What are our current priorities?"}}],
    where={"user_id": "rosie"},
    method="rag"  # Fast, or "llm" for deep reasoning
)
```

**What we get:**
- Memory survives restarts (vs our MEMORY.md which requires manual updates)
- Auto-categorization (vs manual memory organization)
- Proactive context loading (vs reactive read-on-demand)
- Cross-agent memory sharing (Rosie/Mack/Winnie can share knowledge)

---

## 🏆 Priority 2: Agno (Multi-Agent Learning)

**GitHub:** https://github.com/agno-agi/agno

**Core value proposition:**
- Agents learn from every interaction
- User profiles persist across sessions
- Knowledge transfers across users
- Runs in your environment (privacy-first)

### Learning Modes

1. **Always Learning** - Continuous, automatic
2. **Agentic Learning** - Agent decides when to learn

### What Sets It Apart

```python
from agno.agent import Agent
from agno.db.sqlite import SqliteDb

agent = Agent(
    db=SqliteDb(db_file="tmp/agents.db"),
    learning=True  # One line → learning enabled
)
```

**Features:**
- User profiles that persist
- User memories that accumulate
- Learned knowledge transfers across users
- Async-first (built for long-running tasks)

### Integration with OpenClaw

**Use case:**
1. Rosie learns JiraFlow outreach patterns
2. Knowledge stored in SQLite
3. Mack can query: "How did Rosie handle similar outreach?"
4. System gets smarter over time

**Database options:**
- SQLite (local, simple)
- PostgreSQL (production, shared)

---

## 🏆 Priority 3: Agent Zero (Persistent Self-Improvement)

**GitHub:** https://github.com/agent0ai/agent-zero

**Key innovation:** Organic, learning framework that grows with use

### Core Features

1. **Persistent Memory**
   - Remembers solutions, code, facts
   - Solves tasks faster over time
   - Self-improvement through experience

2. **Multi-Agent Cooperation**
   - Hierarchical structure (superior → subordinate)
   - Subordinates help break down tasks
   - Clean, focused context per agent

3. **SKILL.md Standard**
   - Compatible with Claude Code, Codex, Cursor, Goose
   - Portable, structured capabilities
   - We already use this! (skills folder)

### Real-World Use Cases (Relevant to Us)

**Financial Analysis:**
- Bitcoin price trends
- Correlation with news events
- Annotated charts (like our trading system!)

**API Integration Without Code:**
- "Use this API to X, remember for future"
- Agent learns and stores in memory
- (Perfect for our Schwab/UnusualWhales integrations)

**Automated Monitoring:**
- Check metrics every N minutes
- Alert on thresholds
- (Exactly our trading position monitoring)

### Architecture: Subordinate Agents

```
Agent 0 (You/Michael)
    ↓
Rosie (Coordinator)
    ↓
Mack (Technical) ← Winnie (Implementation)
```

Each agent can spawn subordinates for subtasks, keeping context clean.

---

## 📊 State Management & Tracking Systems

### Database Options (From Research)

**1. SQLite (Local, Embedded)**
- **Best for:** Single-agent systems, prototyping
- **Pros:** Simple, no server, portable
- **Cons:** Single-writer bottleneck
- **Use case:** Each agent has own DB (Rosie.db, Mack.db, Winnie.db)

**2. PostgreSQL (Production, Shared)**
- **Best for:** Multi-agent coordination, high concurrency
- **Pros:** ACID compliance, concurrent writes, vector extensions (pgvector)
- **Cons:** Requires server, more complex
- **Use case:** Shared coordination state, cross-agent memory

**3. PowerSync (Hybrid: Postgres ↔ SQLite)**
- **Innovation:** Real-time sync between Postgres (server) and SQLite (local)
- **Best for:** Offline-first agents that sync when connected
- **Use case:** Agents work offline, sync state when network available

### Workflow Tracking Patterns

**Pattern 1: State Machine (SQLite as State Store)**
- Track task status (pending → running → complete → failed)
- Resume from last checkpoint
- Durable execution (survives crashes)

**Pattern 2: Event Sourcing**
- Store every action as event
- Replay events to rebuild state
- Complete audit trail

**Pattern 3: Vector Store + Metadata**
- pgvector for semantic search
- Metadata tables for structured data
- Best of both worlds

---

## 🔍 Novel & Non-Consensus Ideas

### 1. Memory Consolidation via RL (MemRL)

**Paper:** "Self-Evolving Agents via Runtime Reinforcement Learning on Episodic Memory"

**Idea:** Agents use RL to decide what to remember vs forget
- Not all memories are equal
- Learn which memories improve performance
- Auto-prune low-value memories

**Implementation:**
- Track memory usage → outcome correlation
- Reinforce memories that led to success
- Decay memories that weren't useful

**Non-consensus aspect:** Most systems treat all memories equally. This prioritizes valuable memories.

### 2. Fog Computing for Agents (Autonomous Fog Agents)

**Paper:** Decentralized P2P agent coordination

**Idea:** Agents coordinate via shared memory and P2P, not central orchestrator
- No single point of failure
- Each agent has local policy
- Convergence through consensus

**Implementation for us:**
- Rosie/Mack/Winnie run independently
- shared-state.json = shared memory
- Agents poll and update asynchronously
- Conflicts resolved via timestamp + priority

**Non-consensus aspect:** Most frameworks use centralized orchestrator. This is distributed.

### 3. Agentic Memory (Memory as Action)

**Paper:** "Memory as Action: Autonomous Context Curation for Long-Horizon Tasks"

**Idea:** Memory retrieval is an action the agent chooses, not automatic
- Agent decides when to remember
- When to forget
- When to consolidate

**Implementation:**
- memory_recall(query) is a tool
- memory_store(fact) is a tool
- memory_consolidate() runs periodically
- Agent controls its own memory

**Non-consensus aspect:** Current systems auto-load all memories. This gives agency control.

### 4. Cross-Agent Knowledge Transfer (Non-Obvious)

**Idea:** When Rosie learns something, automatically check if Mack/Winnie should know

**Implementation:**
```python
# Rosie learns: "JiraFlow outreach works best at 9 AM EST"
await memory.store(
    fact="Outreach timing: 9 AM EST optimal for JiraFlow",
    scope="rosie",
    transfer_to=["mack", "winnie"],  # Auto-share
    category="process_learnings"
)
```

**Why non-obvious:** Most systems isolate agent memories. Shared learning is rare.

### 5. Procedural Memory Graphs (Neo4j)

**Idea:** Store workflows as graphs, not linear lists

**Example:**
```
(Task: Deploy JiraFlow) -[:REQUIRES]-> (Task: Test Backend)
(Task: Test Backend) -[:FAILED_DUE_TO]-> (Issue: Stripe Keys)
(Issue: Stripe Keys) -[:SOLVED_BY]-> (Solution: Use env vars)
```

**Benefits:**
- Visualize dependencies
- Identify bottlenecks
- Replay successful paths
- Avoid failed approaches

**Why it matters:** Linear memory (MEMORY.md) loses connections. Graphs preserve them.

---

## 🔧 Recommended Tech Stack

### Immediate (Week 1)

**1. memU Integration**
```bash
pip install memu-py
```
- SQLite for prototyping
- Upgrade to PostgreSQL for production

**2. Shared State Database**
```python
# Replace shared-state.json with SQLite
import sqlite3

conn = sqlite3.connect("/Volumes/EDrive-1/Projects/agent-coordination/agent-state.db")

# Schema
CREATE TABLE agent_state (
    agent_id TEXT PRIMARY KEY,
    current_task TEXT,
    status TEXT,  # active | idle | blocked
    last_update TIMESTAMP,
    context JSON
);

CREATE TABLE task_queue (
    task_id TEXT PRIMARY KEY,
    assigned_to TEXT,
    priority INTEGER,
    status TEXT,
    created_at TIMESTAMP,
    completed_at TIMESTAMP
);

CREATE TABLE learnings (
    id INTEGER PRIMARY KEY,
    agent_id TEXT,
    category TEXT,
    insight TEXT,
    confidence REAL,
    created_at TIMESTAMP
);
```

### Medium-Term (Week 2-4)

**3. Vector Store for Semantic Search**
```bash
# PostgreSQL with pgvector
docker run -d \
  --name agent-postgres \
  -e POSTGRES_PASSWORD=openclaw \
  -p 5432:5432 \
  pgvector/pgvector:pg16
```

**4. Event Log for Audit Trail**
```python
CREATE TABLE agent_events (
    id SERIAL PRIMARY KEY,
    agent_id TEXT,
    event_type TEXT,  # task_started | decision_made | error | success
    payload JSON,
    timestamp TIMESTAMP DEFAULT NOW()
);
```

### Long-Term (Month 2+)

**5. Knowledge Graph (Neo4j)**
```bash
docker run -d \
  --name agent-neo4j \
  -p 7474:7474 -p 7687:7687 \
  neo4j:latest
```

**6. Time-Series Metrics (TimescaleDB)**
```bash
# Track performance over time
CREATE TABLE agent_metrics (
    timestamp TIMESTAMPTZ NOT NULL,
    agent_id TEXT,
    metric_name TEXT,
    value REAL
);

SELECT create_hypertable('agent_metrics', 'timestamp');
```

---

## 🎯 Implementation Roadmap

### Phase 1: Memory Foundation (Week 1)

**Goals:**
- Replace MEMORY.md with memU
- Persist across restarts
- Auto-categorization working

**Tasks:**
1. Install memU-py
2. Set up PostgreSQL with pgvector
3. Migrate existing MEMORY.md → memU
4. Test: Rosie learns fact → Mack retrieves it
5. Measure: Token cost reduction

**Success criteria:**
- All 3 agents sharing memory
- Zero manual MEMORY.md updates
- Memory survives container restarts

### Phase 2: State Tracking (Week 2)

**Goals:**
- Database-backed shared state
- Task queue system
- Event logging

**Tasks:**
1. Create agent-state.db (SQLite)
2. Migrate shared-state.json → database
3. Implement task queue
4. Add event logging
5. Build simple dashboard (query DB)

**Success criteria:**
- All coordination via database
- Complete audit trail
- Can resume work after crash

### Phase 3: Learning Systems (Week 3-4)

**Goals:**
- Cross-agent learning
- Pattern detection
- Self-improvement metrics

**Tasks:**
1. Implement learning pipeline (Agno-style)
2. Add insight extraction
3. Build pattern matcher
4. Create learning dashboard

**Success criteria:**
- System improves week-over-week
- Measurable efficiency gains
- Documented learnings

### Phase 4: Advanced Capabilities (Month 2+)

**Goals:**
- Knowledge graphs
- Predictive context loading
- Multi-agent workflows

**Tasks:**
1. Deploy Neo4j for workflow graphs
2. Implement MemRL (reinforcement learning on memory)
3. Build proactive suggestion system
4. Advanced orchestration

---

## 📋 Continuous Research Schedule

**Every 4 hours, offset by 1 hour per agent:**

### Rosie (17:25, 21:25, 01:25, 05:25...)
**Focus:** Strategic frameworks, orchestration patterns
- Search: "multi-agent coordination 2026"
- Search: "autonomous agent architecture"
- Check: oh-my-opencode updates

### Winnie (18:25, 22:25, 02:25, 06:25...)
**Focus:** Implementation details, databases, tooling
- Search: "agent state persistence sqlite postgres"
- Search: "vector database agent memory"
- Test: New frameworks (memU, Agno)

### Mack (19:25, 23:25, 03:25, 07:25...)
**Focus:** Novel research, non-consensus ideas, papers
- Search arxiv: "agent memory", "self-evolving agents"
- Search: "agentic reasoning papers 2026"
- Identify: Overlooked but valuable approaches

**Document findings in:**
`/Users/harrisonfethe/.openclaw/workspace/self_improvement/research/YYYY-MM-DD-HH-{agent}.md`

---

## 🚀 Quick Wins (Start Today)

1. **Install memU** (15 minutes)
   ```bash
   pip install memu-py
   cd /Users/harrisonfethe/.openclaw/workspace
   mkdir memu-test && cd memu-test
   # Run memU test script
   ```

2. **Create state database** (30 minutes)
   ```bash
   sqlite3 /Volumes/EDrive-1/Projects/agent-coordination/agent-state.db < schema.sql
   ```

3. **Migrate one workflow** (1 hour)
   - Pick: Trading position monitoring
   - Store: Positions in DB vs JSON
   - Query: Live status from DB

---

## 📚 References & Resources

### GitHub Repositories

**High Priority:**
1. [memU](https://github.com/NevaMind-AI/memU) - 24/7 proactive agents (OpenClaw-specific!)
2. [Agno](https://github.com/agno-agi/agno) - Multi-agent learning framework
3. [Agent Zero](https://github.com/agent0ai/agent-zero) - Persistent memory + self-improvement

**Medium Priority:**
4. [CrewAI](https://github.com/crewAIInc/crewAI) - Multi-agent orchestration
5. [AGiXT](https://github.com/Josh-XT/AGiXT) - Adaptive memory + plugin system
6. [AutoGPT](https://github.com/Significant-Gravitas/AutoGPT) - Long-term + short-term memory

**Research Collections:**
7. [Awesome Memory for Agents](https://github.com/TsinghuaC3I/Awesome-Memory-for-Agents)
8. [Agent Memory Paper List](https://github.com/Shichun-Liu/Agent-Memory-Paper-List)
9. [Awesome Agentic Reasoning](https://github.com/weitianxin/Awesome-Agentic-Reasoning)

### Key Papers

1. **MemRL** - Self-Evolving Agents via Runtime RL on Episodic Memory
2. **Memory as Action** - Autonomous Context Curation for Long-Horizon Tasks
3. **Agentic Memory** - Unified Long-Term and Short-Term Memory Management
4. **MemEvolve** - Meta-Evolution of Agent Memory Systems

### Tools & Databases

- **PostgreSQL + pgvector** - Vector search in relational DB
- **PowerSync** - Postgres ↔ SQLite sync
- **Neo4j** - Graph database for workflows
- **TimescaleDB** - Time-series metrics

---

## 💡 Key Takeaways

**What We Learned:**

1. **Memory is the key differentiator** - Stateless agents plateau, learning agents improve
2. **Database > Files** - SQLite/Postgres beats JSON for state management
3. **Proactive > Reactive** - memU predicts needs vs waiting for queries
4. **Cross-agent learning** - Knowledge sharing accelerates improvement
5. **Standards matter** - SKILL.md compatibility unlocks ecosystem

**What We're Building:**

Not just continuous improvement framework (oh-my-opencode style), but **continuously learning agents** (memU + Agno + Agent Zero fusion).

**Competitive advantage:**

Most teams: Agents that work 24/7
Us: Agents that work 24/7 **and get smarter every day**

---

**Next update:** Winnie @ 18:25 EST (research cycle 2)
**Document:** `/Users/harrisonfethe/.openclaw/workspace/self_improvement/research/2026-02-12-17-rosie.md`
