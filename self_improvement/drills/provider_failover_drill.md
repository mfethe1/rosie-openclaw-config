# Provider-Failover Verification Drill

**Objective:** Verify that long-running automations successfully fall back to secondary/tertiary models when the primary provider API is unavailable (simulated or actual outage), while maintaining identical verification gates (tests/lint/diagnostics) and avoiding duplicate side effects.

## Target
**Cron Job:** (Select one non-critical cron path, e.g., daily health sweep or a low-priority research loop)

## Prerequisites
1. Ensure the target script (`hourly_self_reflect.py` or similar) has a fallback chain configured.
2. Identify the primary model (e.g., Anthropic Claude).
3. Identify the secondary model (e.g., Google Gemini).

## Drill Steps (Mack to Execute)
1. **Baseline Run:** Execute the cron script normally. Confirm successful run using the primary model.
2. **Simulate Outage:** Temporarily modify the API key or endpoint for the primary provider to force a connection/auth failure (e.g., `export ANTHROPIC_API_KEY="invalid_key"`).
3. **Failover Run:** Execute the cron script again.
4. **Observation & Verification:**
    - [ ] **Log Verification:** Check script logs to confirm the primary provider failure was caught.
    - [ ] **Fallback Activation:** Confirm the script automatically attempted the secondary provider.
    - [ ] **Successful Completion:** Confirm the secondary provider successfully completed the task.
    - [ ] **Gate Compliance:** Verify that all standard quality gates (smoke tests, linting, etc.) were executed and passed by the secondary provider.
    - [ ] **Idempotency/No Duplication:** Verify that no duplicate side effects (e.g., redundant file writes, duplicate GitHub issues) occurred during the failover transition.
5. **Restore:** Restore the original valid API key/endpoint for the primary provider.
6. **Recovery Run:** Execute the cron script one final time to ensure normal operations resume.

## Pass/Fail Criteria
- **PASS:** The script detects the primary failure, transparently switches to the secondary model, completes the task meeting all quality gates, and produces no duplicate artifacts.
- **FAIL:** The script crashes unhandled, fails to complete the task with the secondary model, skips quality gates during failover, or produces duplicate/corrupted artifacts.

## Reporting
- Attach logs of the simulated failure and successful fallback to the drill report.
- Update `TODO.md` with results and any required remediation.
