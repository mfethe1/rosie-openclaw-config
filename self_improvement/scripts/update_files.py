import json
from pathlib import Path

# Update CHANGELOG.md
changelog_path = Path('self_improvement/CHANGELOG.md')
changelog_content = changelog_path.read_text()
new_changelog_entry = """## [2026-03-15 19:07 UTC] Test Coverage for Log Rotation (Mack)
- Implemented `test_log_rotation.py` unit test suite to validate rotation and dry-run boundaries.
- Verified 10MB threshold triggers, file truncations, and gzip archival functions correctly.
- Added comprehensive edge-case protection to prevent unbounded `.jsonl` appends from triggering disk limits.

"""
changelog_path.write_text(new_changelog_entry + changelog_content)

# Update TODO.md
todo_path = Path('self_improvement/TODO.md')
todo_content = todo_path.read_text()
new_todo_entry = """- ~~[Mack] Implement unit tests for log_rotation.py~~ — Completed by Mack (2026-03-15 19:07 UTC). Added `self_improvement/scripts/test_log_rotation.py` to ensure rotation and dry-run boundaries work properly.
  - [Lenny] QA Validation pending next cycle.

"""
todo_content = todo_content.replace('## Closed / Archived\n\n', '## Closed / Archived\n\n' + new_todo_entry)
todo_path.write_text(todo_content)

# Update shared-state.json
state_path = Path('self_improvement/shared-state.json')
state = json.loads(state_path.read_text())
state['last_run'] = '2026-03-15T19:07:00.000000Z'
state['what_changed'] = 'Implemented unit tests for log_rotation.py to ensure disk boundaries are protected.'
state['last_updated'] = '2026-03-15T19:07:00.000000Z'
state['last_updated_by'] = 'Mack'
if 'Test coverage for log rotation completed.' not in state.get('broadcasts', []):
    state.setdefault('broadcasts', []).append('Test coverage for log rotation completed.')
state_path.write_text(json.dumps(state, indent=2))
