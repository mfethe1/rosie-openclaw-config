# Vetting Report Template
**Report ID:** YYYY-MM-DD-HH-[TOOL/FEATURE]
**Evaluator:** Winnie | **Status:** [ADOPT_NOW | SANDBOX_TEST | SKIP]

## Executive Summary
- **What:** [1-line description]
- **Why discovered:** [Signal source + date]
- **Recommendation:** [ADOPT_NOW | SANDBOX_TEST | SKIP]

## Evidence & Analysis
### Pros (with sources)
- [Feature/benefit] — [URL/release note]
- [Feature/benefit] — [URL/release note]

### Cons (with sources)
- [Limitation] — [URL/Github issue]
- [Limitation] — [URL/Github issue]

## Integration Cost & Risk
| Dimension | Assessment | Impact |
|-----------|-----------|--------|
| **Setup burden** | [Low/Med/High] | [Days/weeks to integrate] |
| **Dependency surface** | [# new deps] | [Maintenance risk: Low/Med/High] |
| **API stability** | [Stable/Beta/Experimental] | [Risk of breaking changes] |
| **Estimated cost (12mo)** | [$/month] | [vs current solution] |
| **Lock-in risk** | [Low/Med/High] | [Switching cost if deprecated] |

## Migration Path (if adopted)
1. [Step 1]
2. [Step 2]
3. [Rollback plan]

## Decision Checkpoints
- [ ] ≥2 independent sources confirm value proposition
- [ ] Cost/risk ratio favorable vs status quo
- [ ] No vendor lock-in misalignment with workspace strategy
- [ ] Sandbox test success (if required) before rollout

## Next Action
[Specific next step: "Request Stripe creds for live test", "Allocate sandbox environment", etc.]
