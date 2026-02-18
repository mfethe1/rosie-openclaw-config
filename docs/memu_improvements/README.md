# memU Memory System — Open Source Roadmap & Setup Guide

## Public repo goal
This repository is designed to be the canonical, externally auditable source for our memory-system work.

- Public repo target: **mfethe1/fumemory**
- Scope: memU service/client upgrades, schemas, scripts, tests, runbooks, and comparison notes.

## What should be committed
Commit only **non-sensitive** items:
- Server and client code changes
- Test scripts, CI workflows, and smoke checks
- Documentation, architecture docs, and design docs
- Benchmarking/competition analysis and accepted RFCs
- Runbooks and operational procedures

## What should **never** be committed
- API keys / secrets / tokens / credentials
- Passwords, private endpoints, session logs with real tokens
- PII, raw broker/account details, or internal device identifiers

Before every PR and before every push, run:

```bash
# quick secret-scoped audit
rg -n "(?i)(api[_-]?key|secret|token|password|bearer|AKIA|xox[bap]-|oauth|sk- |AIza|FC-|BSA-)" . \
  --glob "!**/node_modules/**" --glob "!**/.venv/**" --glob "!**/venv/**"
```

## Setup (local)
1. Clone the public repo

```bash
git clone https://github.com/mfethe1/fumemory.git
cd fumemory
```

2. (Optional) add a local upstream for private refs used in our workspace

```bash
git remote add private "git@github.com:mfethe1/fumemory.git"
```

3. Install and run local memU service stack as documented in this repo docs.
4. Run the smoke suite from repo root:

```bash
bash memu_server/smoke_test.sh <agent> <task> <output_file>
```

## PR review policy (non-negotiable)
- Any PR must pass the smoke checks before merge.
- At least one reviewer validates:
  - route-contract consistency (`/memories` vs `/api/v1/memu/*`),
  - backward compatibility behavior,
  - durability and idempotency behavior,
  - error handling for malformed inputs.
- Any changes touching auth/keys must include a red-team threat note and be reviewed by at least one extra owner.

## Community contribution flow
- Issues and PRs are expected from external contributors.
- Contributors should:
  - summarize change intent and rollback plan,
  - include local verification commands,
  - include any benchmark or compatibility evidence,
  - include `memU` proof IDs where possible.
- Security review has priority over feature speed.

## Publication and marketing checklist
- Post monthly memory-system update highlights in marketing channels:
  - what improved,
  - what broke and fixed,
  - what changed for reliability,
  - where collaborators can test.

## Release tags
Use version-style tags per significant memory-system capability milestone.

Examples:
- `memu-v1.3-route-contract`
- `memu-v1.4-dedup-hardened`
- `memu-v1.5-graph-ready`

## Governance for rollout
- If a memU-related bug is reported and validated, no merge until rollback plan is available.
- Every rollout must include:
  - a smoke proof,
  - a security scan summary,
  - a compatibility note (expected client impact).
