# Git Workflow & Agent Isolation Policy
## STRICT ENFORCEMENT — All Agents (Rosie, Mack, Lenny, Winnie)

**Effective:** 2026-03-06
**Status:** MANDATORY — violations are build-breaking

---

## 1. Git Worktree Isolation (HARD RULE)

Every agent MUST work in its own git worktree. No two agents touch the same working directory simultaneously.

**Before starting any task:**
```bash
# Create worktree for your task
git worktree add ../workspace-<agent>-<task-slug> -b <agent>/<task-slug>

# Example
git worktree add ../workspace-rosie-fix-auth -b rosie/fix-auth
```

**On completion:**
```bash
# From your worktree: stage, commit, push
git add -A
git commit -m "<agent>/<task>: <description>"
git push origin <agent>/<task-slug>

# Clean up worktree after merge
git worktree remove ../workspace-<agent>-<task-slug>
```

**Branch naming convention:**
- `<agent>/<descriptive-slug>` — e.g. `rosie/add-retry-logic`, `mack/refactor-db-layer`
- Never commit directly to `main` or `master`

---

## 2. Pull Before Work (HARD RULE)

Every agent MUST pull the latest canonical branch before creating a worktree or starting any work.

```bash
git fetch origin
git rebase origin/main  # or merge, but rebase preferred for clean history
```

No exceptions. Stale branches cause merge conflicts that waste everyone's time.

---

## 3. Atomic Commits (HARD RULE)

- One logical change per commit
- Commit message format: `<agent>/<area>: <what changed>`
- Never commit generated files, secrets, or node_modules
- Every commit must leave the project in a buildable/testable state

---

## 4. Never Manually Fix Agent Slop (HARD RULE)

From Jaymin West's agentic engineering philosophy:

> If an agent produces bad output, that is an engineering problem — not an LLM problem.

**The rule:** Do NOT manually patch bad agent output. Instead:
1. Diagnose WHY the output was bad (missing context? bad prompt? wrong constraints?)
2. Fix the underlying cause (update the spec, add constraints, improve the prompt)
3. Reset and rerun the agent from scratch

This ensures the system stays reliable. Manual patches hide systemic failures.

---

## 5. One Agent, One Task, One Prompt (HARD RULE)

- Each agent gets a single, focused task per session
- Task must be decomposed small enough to one-shot
- If a task requires multiple agents, use explicit handoff via git (PR or branch merge), not shared state

> "A focused agent is a correct agent."

---

## 6. Quality Gates Before Handoff (HARD RULE)

No work moves to another agent or to main without passing ALL gates:

1. **Tests pass** — 100% pass rate, no skipped tests
2. **Lint clean** — zero warnings, zero errors
3. **Type check clean** — no type errors
4. **No manual mocks** — test against real logic, never mock what you can use for real
5. **Commit is atomic** — one logical change, buildable state

```bash
# Minimum gate check before any PR/merge
bun test        # or npm test / pytest / etc.
bun run lint    # or eslint / biome
bun run typecheck  # or tsc --noEmit
```

If ANY gate fails, the agent must fix it before proceeding. No passing broken work downstream.

---

## 7. Hard Tool Blocks (HARD RULE)

Agents are restricted from certain operations to prevent unauthorized changes:

| Blocked Action | Why |
|---|---|
| `git push --force` on shared branches | Destroys history |
| Direct commits to `main`/`master` | Bypasses review |
| `git merge` into main without PR | Bypasses quality gates |
| Deleting other agents' branches | Not your branch |
| Modifying other agents' worktrees | Isolation violation |
| Running `rm -rf` on shared directories | Catastrophic |

**Read-only agents** (Oracle, Librarian, Explore) must NEVER write, edit, or commit.

---

## 8. Specification-Driven Work (HARD RULE)

Every non-trivial task must have a spec before an agent starts work. The spec includes:

- Exact files to create/modify (with paths)
- Expected behavior (with test cases)
- Constraints and non-goals
- Acceptance criteria

Ambiguity is the #1 source of agent slop. Kill it with specificity.

---

## 9. Anti-Mocking Testing Philosophy (HARD RULE)

From the video: "Never mock what you can use for real."

- Use real database connections (SQLite in-memory is fine)
- Use real HTTP calls against test servers, not mocked responses
- Use real file system operations in temp directories
- Only mock external paid APIs or truly unreachable services
- Integration tests > unit tests with mocks

---

## 10. Expertise Accumulation (RECOMMENDED)

Adopt Mulch-style expertise recording:
- After completing a task, record what was learned (conventions, failures, patterns)
- Store in `.mulch/` or equivalent structured format
- Next agent session starts with accumulated project knowledge
- Git-tracked so all agents benefit from shared learnings

```bash
# After task completion
ml record <domain> --type convention "Discovered: always use WAL mode for concurrent SQLite"
ml record <domain> --type failure --description "X broke because Y" --resolution "Do Z instead"
```

---

## 11. Merge Strategy

- Use `merge=union` for JSONL files (issues, expertise, logs)
- Prefer rebase for feature branches to keep linear history
- Squash merge into main for clean history
- Run `ml doctor --fix` after merges to deduplicate if needed

---

## 12. Agent Coordination Protocol

1. Check inbox before starting work
2. Claim task in BACKLOG.md (set owner = your agent name)
3. Create worktree + branch
4. Do the work
5. Run quality gates
6. Commit + push
7. Open PR or notify coordinator
8. Record learnings
9. Clean up worktree

No freelancing. No overlapping work. No shared mutable state.

---

## Enforcement

Violations of HARD RULE items are treated as build failures. The offending agent must:
1. Revert the violation
2. Record the failure as a learning (Mulch-style)
3. Rerun from a clean state

This policy is loaded by all agents at session start via AGENTS.md reference.
