#!/bin/bash
# =============================================================================
# weekly_competitive_scan.sh — P-005: Competitive Intelligence Auto-Scan
# Winnie (Research Agent) — runs every Sunday 9 AM EST
#
# Searches: Brave, GitHub trending, arXiv
# Outputs: markdown report → outputs/competitive-scan-$(date +%Y-%m-%d).md
# HIGH-value items → TODO.md with [Winnie] tag
# =============================================================================

set -euo pipefail

WORKSPACE="/Users/harrisonfethe/.openclaw/workspace"
OUTPUT_DIR="$WORKSPACE/self_improvement/outputs"
TODO_FILE="$WORKSPACE/self_improvement/TODO.md"
SCAN_DATE=$(date +%Y-%m-%d)
SCAN_TS=$(date "+%Y-%m-%d %H:%M EST")
OUTPUT_FILE="$OUTPUT_DIR/competitive-scan-${SCAN_DATE}.md"

echo "🔍 Winnie Competitive Intelligence Scan — $SCAN_TS"
echo "   Output: $OUTPUT_FILE"

# =============================================================================
# AGENT INSTRUCTION BLOCK (used when this script is the cron message payload)
# The cron will launch an OpenClaw agent session with this message:
# =============================================================================
# CRON_MESSAGE_START
# You are Winnie, the Self-Improvement Research Agent.
# Run the weekly competitive intelligence scan for agent frameworks and memory systems.
#
# TASK: Perform the following web searches and compile a research report.
#
# SEARCHES TO RUN:
# 1. web_search: "agent memory framework 2026" (count=8)
# 2. web_search: "multi-agent self-improving 2026" (count=8)
# 3. web_search: "LLM agent memory system" (count=8)
# 4. web_search: "GitHub trending agent memory multi-agent" (count=6)
# 5. web_search: "arXiv agent memory 2026 new paper" (count=6)
# 6. web_search: "autonomous agent framework released 2026" (count=6)
#
# OUTPUT FORMAT:
# Write a markdown report to:
#   /Users/harrisonfethe/.openclaw/workspace/self_improvement/outputs/competitive-scan-$(date +%Y-%m-%d).md
#
# Report sections:
# ## Competitive Intelligence Scan — [DATE]
# ### Brave Web Search Results
# ### GitHub Trending Findings
# ### arXiv Recent Papers
# ### HIGH VALUE Items (3+ signals)
# ### Summary & Recommendations
#
# AFTER writing the report:
# 1. For each HIGH VALUE item, append to TODO.md:
#    - [ ] **[Winnie]** Evaluate [ITEM NAME] — [brief reason] (competitive-scan-[DATE])
# 2. Store a memU handoff:
#    curl -sS -X POST http://localhost:12345/store \
#      -H "Authorization: Bearer openclaw-memu-local-2026" \
#      -H "Content-Type: application/json" \
#      -d '{"agent":"winnie","key":"competitive-scan-[DATE]","value":"Weekly scan complete. HIGH items: [count]. Report: outputs/competitive-scan-[DATE].md"}'
# 3. Run smoke test:
#    bash /Users/harrisonfethe/.openclaw/workspace/memu_server/smoke_test.sh \
#      winnie p005-competitive-scan \
#      /Users/harrisonfethe/.openclaw/workspace/self_improvement/outputs/competitive-scan-$(date +%Y-%m-%d).md \
#      "Weekly competitive intelligence scan"
# 4. Update CHANGELOG.md with a one-line entry.
# CRON_MESSAGE_END

# =============================================================================
# SHELL EXECUTION PATH (when run directly as a bash script)
# =============================================================================

mkdir -p "$OUTPUT_DIR"

cat > "$OUTPUT_FILE" << HEADER
# Competitive Intelligence Scan — $SCAN_DATE

**Agent:** Winnie (Research)  
**Scan Date:** $SCAN_TS  
**Proposal:** P-005 — Weekly Competitive Intelligence Auto-Scan  
**Sources:** Brave Web Search, GitHub Trending, arXiv cs.AI  

---

HEADER

echo "📡 Scan complete (shell init). Full search results require agent session." >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"
echo "## Note" >> "$OUTPUT_FILE"
echo "This script is designed to be used as a cron payload message (see CRON_MESSAGE_START block)." >> "$OUTPUT_FILE"
echo "For shell-only execution, the output file is initialized. Agent session does the full search." >> "$OUTPUT_FILE"

echo "✅ Output file initialized: $OUTPUT_FILE"

# =============================================================================
# HIGH VALUE ITEM LOGIC (called by agent after identifying items)
# Usage: bash weekly_competitive_scan.sh --add-todo "Item Name" "reason"
# =============================================================================

if [[ "${1:-}" == "--add-todo" ]]; then
  ITEM_NAME="${2:-Unknown Item}"
  ITEM_REASON="${3:-Competitive intelligence finding}"
  TODAY=$(date +%Y-%m-%d)
  TODO_ENTRY="- [ ] **[Winnie]** Evaluate $ITEM_NAME — $ITEM_REASON (competitive-scan-$TODAY)"
  
  # Find the "Discoveries" section and append after it
  if grep -q "## Discoveries" "$TODO_FILE" 2>/dev/null; then
    # Insert after the Discoveries header
    awk -v entry="$TODO_ENTRY" '
      /^## Discoveries/ { print; found=1; next }
      found && /^$/ { print entry; print ""; found=0; next }
      { print }
    ' "$TODO_FILE" > "${TODO_FILE}.tmp" && mv "${TODO_FILE}.tmp" "$TODO_FILE"
  else
    echo "" >> "$TODO_FILE"
    echo "## Discoveries (from competitive-scan-$TODAY)" >> "$TODO_FILE"
    echo "$TODO_ENTRY" >> "$TODO_FILE"
  fi
  echo "✅ Added HIGH VALUE item to TODO.md: $ITEM_NAME"
fi

echo "✅ weekly_competitive_scan.sh complete."
