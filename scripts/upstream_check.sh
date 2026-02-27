#!/bin/bash
# upstream_check.sh — runs every 3h
# Checks openclaw/openclaw for new commits, evaluates what to adopt,
# preserves our critical agent settings.

set -euo pipefail

AGENT="${AGENT_NAME:-rosie}"
UPSTREAM="openclaw/openclaw"
BASE_DIR="$HOME/.openclaw/workspace/infra/openclaw-sync"
STATE_FILE="$BASE_DIR/.upstream_state.json"
PINNED_FILE="$BASE_DIR/.pinned_sha"
REPORT_DIR="$BASE_DIR/reports"
mkdir -p "$REPORT_DIR"

REPORT_FILE="$REPORT_DIR/diff_$(date +%Y%m%dT%H%M%S)_${AGENT}.md"
LOG="$BASE_DIR/upstream_check.log"

log() { echo "[$(date -u +%FT%TZ)] [$AGENT] $*" | tee -a "$LOG"; }

log "Starting upstream check..."

# Fetch latest commits
COMMITS=$(gh api "repos/$UPSTREAM/commits?per_page=20" \
  --jq '[.[] | {sha: .sha[0:12], message: (.commit.message | split("\n")[0]), date: .commit.author.date}]' 2>/dev/null) || {
  log "ERROR: Could not fetch upstream commits"
  exit 1
}

LATEST_SHA=$(echo "$COMMITS" | python3 -c "import sys,json; print(json.load(sys.stdin)[0]['sha'])")
PINNED_SHA=$(cat "$PINNED_FILE" 2>/dev/null || echo "")

NEW_COUNT=0
if [ -n "$PINNED_SHA" ] && [ "$PINNED_SHA" != "$LATEST_SHA" ]; then
  NEW_COUNT=$(echo "$COMMITS" | python3 -c "
import sys,json
d=json.load(sys.stdin)
pinned='$PINNED_SHA'
count=0
for c in d:
    if c['sha'][:len(pinned)]==pinned or pinned[:len(c['sha'])]==c['sha']:
        break
    count+=1
print(count)
")
fi

log "Latest SHA: $LATEST_SHA | Pinned: ${PINNED_SHA:-first_run} | New: $NEW_COUNT commits"

# Generate report
python3 << PYEOF
import json, sys

commits = json.loads("""$COMMITS""")
pinned = "$PINNED_SHA"

# Filter new commits
new = []
for c in commits:
    if c['sha'][:len(pinned)] == pinned or pinned[:len(c['sha'])] == c['sha']:
        break
    new.append(c)

# Categorize
adopt, watch, skip = [], [], []
adopt_kw = ['fix','bug','security','perf','memory','agent','model','cron','crash','error']
skip_kw  = ['i18n','locale','typo','readme','docs']

for c in new:
    msg = c['message'].lower()
    if any(k in msg for k in skip_kw):
        skip.append(c)
    elif any(k in msg for k in adopt_kw):
        adopt.append(c)
    else:
        watch.append(c)

report = f"""# OpenClaw Upstream Diff — {json.loads(open('/dev/null','r').read() or '""')}

**Agent:** $AGENT  
**Run:** $(date -u +%FT%TZ)  
**Latest upstream:** {commits[0]['sha']} ({commits[0]['date'][:10]})  
**Pinned:** {pinned or '(first run)'}  
**New commits:** {len(new)}

## Recent Upstream Commits (latest 10)
"""
for c in commits[:10]:
    marker = " ← NEW" if c in new else ""
    report += f"- \`{c['sha']}\` {c['date'][:10]} — {c['message']}{marker}\n"

report += "\n## Evaluation\n"
if not new:
    report += "✅ Already up to date. No action required.\n"
else:
    if adopt:
        report += "\n### ✅ Recommend Adopt\n"
        for c in adopt:
            report += f"- \`{c['sha']}\` — {c['message']}\n"
    if watch:
        report += "\n### 👀 Watch / Evaluate\n"
        for c in watch:
            report += f"- \`{c['sha']}\` — {c['message']}\n"
    if skip:
        report += "\n### ⏭️ Skip (i18n/docs)\n"
        for c in skip:
            report += f"- \`{c['sha']}\` — {c['message']}\n"

report += """
## Protected Settings (never auto-overwritten)
- SOUL.md, AGENTS.md, IDENTITY.md, USER.md, WORKFLOW_AUTO.md, HEARTBEAT.md
- memU endpoint: localhost:12345 (+ Railway backup)
- NATS: gondola.proxy.rlwy.net:22393
- Model: anthropic/claude-sonnet-4-6
- All agent crons, skills, and custom scripts

## How to Apply Recommended Commits
\`\`\`bash
openclaw update   # pulls latest openclaw version
# then verify: openclaw doctor
\`\`\`
"""

with open("$REPORT_FILE", "w") as f:
    f.write(report)

state = {
    "agent": "$AGENT",
    "last_check": "$(date -u +%FT%TZ)",
    "latest_sha": "$LATEST_SHA",
    "new_commits": len(new),
    "adopt": len(adopt),
    "watch": len(watch),
    "skip": len(skip),
    "report": "$REPORT_FILE"
}
with open("$STATE_FILE", "w") as f:
    json.dump(state, f, indent=2)

print(f"Report: $REPORT_FILE")
print(f"Adopt: {len(adopt)} | Watch: {len(watch)} | Skip: {len(skip)}")
PYEOF

# Update pinned SHA
echo "$LATEST_SHA" > "$PINNED_FILE"

# Push report to GitHub repo
cd "$BASE_DIR"
git add -A 2>/dev/null
git diff --cached --quiet 2>/dev/null || git commit -m "chore($AGENT): upstream diff $(date +%Y-%m-%dT%H:%M) [$NEW_COUNT new]" 2>/dev/null
git push origin main 2>/dev/null || true

log "Done. Report: $REPORT_FILE"
