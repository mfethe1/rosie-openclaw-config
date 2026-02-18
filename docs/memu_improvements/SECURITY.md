# Security Policy for memU OSS Contributions

## Scope
This guide applies to code, scripts, docs, and CI used in the public memU repository.

## Safe defaults
- **Never store secrets in repo history.** Scrub immediately if accidental.
- **Use env vars** for credentials and tokens.
- **Redact local host details** if they are not part of general architecture.
- **Do not commit logs** containing keys, raw tool output, or credentials.

## Pre-commit checks
1. Run a secret sweep:

```bash
rg -n "(?i)(api[_-]?key|secret|token|password|bearer|oauth|client_secret|private_key)" . \
  --glob "!**/node_modules/**" --glob "!**/.venv/**" --glob "!**/venv/**"
```

2. Validate route compatibility and smoke pass:

```bash
bash memu_server/smoke_test.sh <agent> <task> <output_file>
```

3. Verify no destructive local script side effects in PR description.

## Handling PRs
- Every PR must include:
  - what was changed,
  - why this was needed,
  - test commands + results,
  - rollback plan.
- Security-sensitive changes require dual reviewer acknowledgment before merge.

## Incident handling
- If a secret leaks into repo:
  - rotate exposed credentials,
  - remove/rewrite secret history if feasible,
  - add immediate PR with removal and post-mortem.

## Contact
Report security concerns directly to repo owner channels in first-party chat first.