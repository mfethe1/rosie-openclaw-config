#!/usr/bin/env bash
# Rosie OpenClaw Config & Memory Nightly Backup
# Runs at midnight EST — commits and pushes to mfethe1/rosie-openclaw-config
set -euo pipefail

BACKUP_REPO="$HOME/rosie-openclaw-config"
OPENCLAW_DIR="$HOME/.openclaw"
WORKSPACE="$OPENCLAW_DIR/workspace"
LOG_FILE="$BACKUP_REPO/backup.log"
DATE=$(date +"%Y-%m-%d_%H%M%S")

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >> "$LOG_FILE"; }

# Sanitize a file in-place: strip known secret patterns
sanitize_file() {
    local f="$1"
    [ -f "$f" ] || return 0
    sed -i '' -E \
        -e 's/sk-ant-api[a-zA-Z0-9_-]{20,}/<REDACTED>/g' \
        -e 's/sk-[a-zA-Z0-9_-]{20,}/<REDACTED>/g' \
        -e 's/GOCSPX-[a-zA-Z0-9_-]+/<REDACTED>/g' \
        -e 's/[0-9]+-[a-zA-Z0-9_]+\.apps\.googleusercontent\.com/<REDACTED>/g' \
        -e 's/ghp_[a-zA-Z0-9]{36,}/<REDACTED>/g' \
        -e 's/gho_[a-zA-Z0-9]{36,}/<REDACTED>/g' \
        -e 's/AIza[a-zA-Z0-9_-]{35,}/<REDACTED>/g' \
        -e 's/xoxb-[a-zA-Z0-9-]+/<REDACTED>/g' \
        -e 's/Bearer [a-zA-Z0-9._-]{20,}/Bearer <REDACTED>/g' \
        -e 's/ya29\.[a-zA-Z0-9._-]+/<REDACTED>/g' \
        -e 's/AKIA[A-Z0-9]{16}/<REDACTED>/g' \
        -e 's/whsec_[a-zA-Z0-9]+/<REDACTED>/g' \
        -e 's/AC[a-f0-9]{32}/<REDACTED>/g' \
        "$f" 2>/dev/null || true
}

log "=== Nightly backup started ==="

cd "$BACKUP_REPO"

# Pull latest to avoid conflicts
git fetch origin && git rebase origin/main 2>/dev/null || {
    log "WARN: rebase failed, resetting to origin/main"
    git reset --hard origin/main
}

# --- 1) Config file (sanitized via python) ---
if [ -f "$OPENCLAW_DIR/openclaw.json" ]; then
    python3 -c "
import json
with open('$OPENCLAW_DIR/openclaw.json') as f:
    cfg = json.load(f)
def redact(obj):
    if isinstance(obj, dict):
        return {k: '<REDACTED>' if any(s in k.lower() for s in ['token','secret','key','password','credential','apikey','api_key']) else redact(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [redact(i) for i in obj]
    return obj
with open('$BACKUP_REPO/openclaw.sanitized.json', 'w') as f:
    json.dump(redact(cfg), f, indent=2)
" 2>/dev/null && log "Config sanitized and copied" || log "WARN: Config sanitization failed"
fi

# --- 2) Workspace bootstrap/config files ---
mkdir -p "$BACKUP_REPO/workspace"
for f in AGENTS.md SOUL.md TOOLS.md IDENTITY.md USER.md HEARTBEAT.md BOOTSTRAP.md MEMORY.md BACKLOG.md GUARDRAILS.md BOOT.md CHANGELOG.md; do
    if [ -f "$WORKSPACE/$f" ]; then
        cp "$WORKSPACE/$f" "$BACKUP_REPO/workspace/$f"
        sanitize_file "$BACKUP_REPO/workspace/$f"
    fi
done
log "Workspace bootstrap files copied and sanitized"

# --- 3) Memory daily logs (sanitized) ---
mkdir -p "$BACKUP_REPO/workspace/memory"
if [ -d "$WORKSPACE/memory" ]; then
    find "$WORKSPACE/memory" -name "*.md" -exec cp {} "$BACKUP_REPO/workspace/memory/" \; 2>/dev/null
    for mf in "$BACKUP_REPO/workspace/memory/"*.md; do
        sanitize_file "$mf"
    done
    log "Memory daily logs copied and sanitized"
fi

# --- 4) Agent-memory databases (compressed SQL dumps) ---
mkdir -p "$BACKUP_REPO/databases"
if [ -f "$OPENCLAW_DIR/memory/main.sqlite" ] && command -v sqlite3 &>/dev/null; then
    sqlite3 "$OPENCLAW_DIR/memory/main.sqlite" .dump 2>/dev/null | \
        sed -E \
            -e 's/sk-ant-api[a-zA-Z0-9_-]{20,}/<REDACTED>/g' \
            -e 's/sk-[a-zA-Z0-9_-]{20,}/<REDACTED>/g' \
            -e 's/GOCSPX-[a-zA-Z0-9_-]+/<REDACTED>/g' \
            -e 's/[0-9]+-[a-zA-Z0-9_]+\.apps\.googleusercontent\.com/<REDACTED>/g' \
            -e 's/AIza[a-zA-Z0-9_-]{35,}/<REDACTED>/g' \
            -e 's/ya29\.[a-zA-Z0-9._-]+/<REDACTED>/g' \
        | gzip > "$BACKUP_REPO/databases/agent-memory-main.sql.gz" \
        && log "Memory SQLite dumped, sanitized, and compressed" \
        || log "WARN: Memory SQLite dump failed"
fi

if [ -f "$OPENCLAW_DIR/agent-memory.db" ] && command -v sqlite3 &>/dev/null; then
    sqlite3 "$OPENCLAW_DIR/agent-memory.db" .dump 2>/dev/null | \
        sed -E \
            -e 's/sk-ant-api[a-zA-Z0-9_-]{20,}/<REDACTED>/g' \
            -e 's/sk-[a-zA-Z0-9_-]{20,}/<REDACTED>/g' \
            -e 's/GOCSPX-[a-zA-Z0-9_-]+/<REDACTED>/g' \
            -e 's/AIza[a-zA-Z0-9_-]{35,}/<REDACTED>/g' \
        | gzip > "$BACKUP_REPO/databases/agent-memory.sql.gz" \
        && log "agent-memory.db dumped, sanitized, and compressed" \
        || log "WARN: agent-memory.db dump failed"
fi

# --- 5) Cron config (jobs only, skip large run logs) ---
mkdir -p "$BACKUP_REPO/cron"
if [ -f "$OPENCLAW_DIR/cron/jobs.json" ]; then
    cp "$OPENCLAW_DIR/cron/jobs.json" "$BACKUP_REPO/cron/jobs.json"
    log "Cron jobs config copied"
fi

# --- 6) Skills manifest ---
if [ -d "$OPENCLAW_DIR/skills" ]; then
    ls -1 "$OPENCLAW_DIR/skills/" > "$BACKUP_REPO/skills-manifest.txt" 2>/dev/null || true
fi

# --- 7) System crontab snapshot ---
crontab -l > "$BACKUP_REPO/crontab-snapshot.txt" 2>/dev/null || echo "# No crontab" > "$BACKUP_REPO/crontab-snapshot.txt"
log "Crontab snapshot saved"

# --- 8) Commit and push ---
cd "$BACKUP_REPO"
git add -A
if git diff --cached --quiet; then
    log "No changes to commit"
else
    git commit -m "nightly backup ${DATE}" --no-verify
    if git push origin main 2>&1 | tee -a "$LOG_FILE" | tail -3; then
        log "Backup committed and pushed successfully"
    else
        log "ERROR: Push failed — check backup.log"
    fi
fi

log "=== Nightly backup complete ==="
