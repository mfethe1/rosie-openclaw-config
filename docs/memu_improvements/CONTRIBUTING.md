# Contributing to memU Memory System

## Quick start
1. Fork and clone the repo.
2. Install dependencies.
3. Run tests and smoke checks.
4. Open a PR with a clear title and summary.

## Required PR format
- **Summary**: one-sentence problem + one-sentence solution
- **Testing**: commands + outputs
- **Compatibility**: affected API routes and client behavior
- **Rollback**: what to do if regressions show up

## Standards
- Keep docs and code coherent: if behavior changes, update docs in same PR.
- No breaking API defaults without migration note.
- Use deterministic outputs for any benchmark data.

## Review checklist
- Route contract check (`/memories` vs `/api/v1/memu/*`)
- Smoke proof attached
- Idempotency/dedup behavior covered
- Error cases and empty-input responses tested
- Observability/telemetry impact noted

## Community governance
- Encourage external PRs, but require security and stability checks before merge.
- Prefer small incremental changes over large rewrites.
- Reject ad-hoc changes lacking evidence.
