# ERRORS.md — Error Pattern Log
_Track recurring errors to prevent repeat failures. Format: date, agent, error, root cause, fix._

## Known Patterns
- **MLE stored_count=0**: Dedup threshold too aggressive. Extracts memories but blocks all new writes. Fix: adjust threshold in MLE config. (Owner: Mack)
- **B-019/B-021/B-022**: Multiple crons with 3+ consecutive errors. Root cause: model rotation issues or stale endpoints. (Owner: Lenny)
- **JSON parse failures in self-reflect**: max_tokens too low causes truncation. Fixed 2026-02-22 by Winnie (restored to 4096).
