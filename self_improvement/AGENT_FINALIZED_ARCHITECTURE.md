# Finalized Agent System Version (Consolidated)

## Decision summary
Based on all current research inputs (Ralph-loop style, Antfarm, Oh-My-OpenCode, and existing self-improvement workflow), the production default is:

1. **No unlimited Ralph-style outer loop as primary orchestrator.**
2. **Use a deterministic multi-agent workflow skeleton (Antfarm-style)** with explicit step outputs, verification, and escalation.
3. **Adopt Oh-My-OpenCode strengths where useful**: specialized model roles, background execution lanes, and richer tooling ergonomics.
4. **Keep per-agent operational profiles (`agents/<name>.md`)** for local optimization.
5. **Run continuous comparison and hardening cycles every 2 days.**

## Canonical operating pattern
- **Coordinator (Rosie):** defines task, acceptance criteria, sequencing, ownership.
- **Execution lanes:**
  - Research lane (Winnie)
  - Implementation lane (Mack)
  - Resilience/QA lane (Lenny)
- **Workflow style:** plan → do → verify → handoff → approve/iterate.
- **Stop conditions:** deterministic success criteria, retry budget, then escalate.

## Why this beats alternatives
- **vs Ralph loop only:** avoids unbounded repeat loops and noisy loops without hard checks.
- **vs pure Oh-My-OpenCode:** avoids over-complex harness coupling while borrowing its strong role/tool model and task decomposition.
- **vs ad-hoc manual coordination:** adds traceability, no-silent-duplication, and explicit state handoffs.

## Hard rules (global)
- Minimum 2 strong models per workflow.
- Every cycle must read and update **all three**: `TODO`, `LOOPS`, and `shared-state.json`.
- Every active cycle must also load its per-agent file:
  - `agents/rosie.md`
  - `agents/mack.md`
  - `agents/winnie.md`
  - `agents/lenny.md`
- No run is complete without:
  - proof artifact (outputs file or changelog update),
  - explicit blocker list,
  - next owner.

## Comparison scorecard for next cycles
For every competitor or tool update review, record:
- deterministic execution guarantees
- verification gates
- failure/retry model
- cost + maintenance burden
- fit with per-agent profiles

---

## Next immediate action
- **Mack:** formalize minimal profile-loader into loop job entry templates.
- **Winnie:** keep capturing competitor diffs in `self_improvement/outputs/*-winnie.md` against this matrix.
- **Lenny:** enforce repeated-failure rule + alert when checks fail 3x.
- **Rosie:** ensure every cycle cites this architecture file in handoff notes.
