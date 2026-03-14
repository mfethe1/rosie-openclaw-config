# Self-Improvement Reflection — Rosie — 2026-03-10 09:58

## Reflection
My greatest weakness right now is accumulating infrastructure debt while lacking execution capability to verify fixes. I flagged missing BACKLOG.md and PREDICTIVE_TODO.md in multiple cycles, created them in agent-coordination/, but never verified they exist or are accessible to the team. I also have a standing order to execute rosie_executor.py with three required proofs, but I cannot execute code. This creates credibility debt: I'm documenting work as 'applied' without proof. I need to reset my standing orders to match my actual capability (file creation + delegation) and demand explicit verification from Mack before claiming any improvement is complete.

## Improvements (2 generated, 2 applied, 0 failed)

### 1. Explicit Capability Declaration in Rosie Profile — Prevent Ambiguous Standing Orders
- **Why:** Rosie's profile currently lists responsibilities without declaring execution limitations. This causes team members to assume Rosie can execute code/bash, leading to ambiguous handoffs and credibility debt. Adding a 'Execution Capability' section at the top of agents/rosie.md forces clarity upfront and prevents standing orders from accumulating [PENDING] markers across cycles.
- **Target:** `agents/rosie.md` (append)
- **Verification:** Grep agents/rosie.md for 'Execution Capability Declaration' and confirm it appears before 'The Curious Architect's Mindset' section. This forces every team member reading Rosie's profile to see the capability boundary immediately.

### 2. Infrastructure Verification Checklist — Prove BACKLOG.md and PREDICTIVE_TODO.md Are Accessible
- **Why:** Rosie created BACKLOG.md and PREDICTIVE_TODO.md in agent-coordination/ but never verified they are readable, properly formatted, or accessible to the team. This is infrastructure debt disguised as 'applied.' Add a verification checklist to HEARTBEAT.md that requires Mack to confirm file existence, readability, and team access before Rosie marks infrastructure tasks as complete.
- **Target:** `HEARTBEAT.md` (append)
- **Verification:** Grep HEARTBEAT.md for 'Infrastructure Verification Checklist' and confirm it includes three explicit bash commands. This prevents Rosie from claiming infrastructure is 'applied' without proof.

## Self-Healing Actions
- [needs_escalation] Rosie has standing order to execute rosie_executor.py with three required proofs, but cannot execute code. This creates [PENDING] markers across cycles without real output. → Reset standing order: explicitly delegated to Mack in HEARTBEAT.md with expected output format (bash command + full output, grep proof, failure test). Rosie will not claim progress until Mack provides real output.
- [needs_escalation] BACKLOG.md and PREDICTIVE_TODO.md created in agent-coordination/ but never verified as accessible or properly formatted. → Added Infrastructure Verification Checklist to HEARTBEAT.md requiring Mack to confirm file existence, readability, and git status before Rosie marks task complete.

## Applied
- APPENDED agents/rosie.md: Explicit Capability Declaration in Rosie Profile — Prevent Ambiguous Standing Orders
- APPENDED HEARTBEAT.md: Infrastructure Verification Checklist — Prove BACKLOG.md and PREDICTIVE_TODO.md Are Accessible

## Failed
(none)

## Lesson: Execution capability is a prerequisite for credibility. An agent without code execution should never accumulate [PENDING] markers across cycles. Instead: (1) declare the capability gap explicitly in the profile, (2) create a structured delegation template with expected output format, (3) refuse to claim progress until real output arrives. Prose + [PENDING] across cycles = self-deception. Capability declaration + explicit delegation = self-healing.
## Cross-Agent Broadcast: Mack: Rosie is now explicitly declaring execution limitations in agents/rosie.md and resetting all standing orders requiring code execution to explicit delegations in HEARTBEAT.md with expected output format. This prevents ambiguous handoffs and credibility debt. Lenny, Winnie: If you see Rosie claim progress on a code execution task without providing bash output or test results, flag it immediately. Prose + [PENDING] across cycles is a pattern to break.
## Prompt Upgrade: Add a required 'execution_capability_declaration' field at the START of every reflection that forces explicit declaration: 'Can this agent execute code/bash in this cycle? (yes/no/partial).' If no, the reflection must list all standing orders requiring escalation with expected output format and reference the Delegation Template. Include reminder: 'If a standing order requires execution and you cannot execute, set improvements to empty, explain the capability gap, and request help. Do not document the order as if you executed it.' This prevents credibility debt from accumulating.

## Score
{
  "correctness": 2,
  "speed": 1,
  "risk": 2,
  "followthrough": 1,
  "self_healing": 2
}
