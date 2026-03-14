# Tools and Skills Inventory

**Purpose:** Track installed skills, candidates, and rationale.

---

## Installed Skills (Available Now)

### Core Infrastructure
- **1password** - Secrets management via `op` CLI
- **github** - GitHub CLI (`gh`) integration
- **skill-creator** - Build new skills with SKILL.md templates

### Communication
- **himalaya** - Email via IMAP/SMTP
- **gog** - Google Workspace (Gmail, Calendar, Drive, Docs)
- **imsg** - iMessage/SMS on macOS
- **wacli** - WhatsApp messaging

### Productivity
- **things-mac** - Things 3 task management
- **apple-notes** - Apple Notes via `memo` CLI
- **obsidian** - Obsidian vault management

### Data & Research
- **weather** - Weather forecasts
- **summarize** - Text/video/podcast transcription
- **healthcheck** - Security hardening and audits

### Media & Automation
- **video-frames** - Extract frames/clips from video
- **camsnap** - RTSP/ONVIF camera capture
- **peekaboo** - macOS UI automation
- **openai-whisper-api** - Audio transcription

### AI & Generation
- **gemini** - Gemini CLI for Q&A
- **nano-banana-pro** - Gemini image generation
- **nano-pdf** - PDF editing with natural language
- **openai-image-gen** - Batch image generation

### Development
- **coding-agent** - Run Codex/Claude Code via CLI
- **mcporter** - MCP server management

### Specialized
- **blucli** - BluOS audio system control
- **gifgrep** - GIF search and download

---

## Skills to Build (From oh-my-opencode)

### P0 - Critical (This Week)
1. **code-search** - Fast codebase exploration
   - Why: Lean context by delegating grep to cheap models
   - Risk: None (read-only operations)
   - Rollback: Just remove skill

2. **pattern-matcher** - Find existing code patterns
   - Why: Indistinguishable code (match project style)
   - Risk: None (read-only)
   - Rollback: Remove skill

3. **test-runner** - Automated testing workflows
   - Why: Autonomous quality verification
   - Risk: Low (runs in sandbox)
   - Rollback: Remove skill

4. **doc-fetch** - Official documentation retrieval
   - Why: Research before coding (avoid reinventing)
   - Risk: None (web fetch only)
   - Rollback: Remove skill

### P1 - High Priority (Next 2 Weeks)
5. **task-orchestrator** - Multi-agent workflow manager
   - Why: Break complex tasks into coordinated work
   - Risk: Medium (spawns sub-agents, uses sessions_spawn)
   - Rollback: Remove skill, manual coordination

6. **git-master** - Atomic commits, conventional commits
   - Why: Professional git workflow
   - Risk: Low (can review before push)
   - Rollback: Git reset if needed

7. **knowledge-extractor** - Auto MEMORY.md updates
   - Why: Continuous learning automation
   - Risk: Low (edits MEMORY.md)
   - Rollback: Git revert MEMORY.md

8. **cost-tracker** - Token usage monitoring
   - Why: Optimize spending across agents
   - Risk: None (read-only)
   - Rollback: Remove skill

### P2 - Medium Priority (Month 2)
9. **session-analyzer** - Conversation history insights
10. **codebase-digest** - Large repo summarization
11. **deployment-validator** - Pre-deploy safety checks
12. **ultrawork-trigger** - Magic "ulw" keyword orchestration

---

## Skill Candidates (ClawHub Research)

### From ClawHub (Need Evaluation)
- **elite-longterm-memory** - Cross-session recall improvements
  - Status: Winnie to evaluate
  - Why: Better than current MEMORY.md?
  - Risk: Unknown

- **claude-code-plugin-compat** - Import Claude Code plugins
  - Status: Winnie to evaluate
  - Why: Access to Claude Code ecosystem
  - Risk: Compatibility issues?

### From oh-my-opencode Ecosystem
- **context7 MCP** - Official docs search
- **grep.app MCP** - GitHub code search
- **openapi-to-mcp** - Convert APIs to MCP servers
- **mcp-builder** - Auto-generate MCP servers

---

## Skills We Don't Need (Already Have)

❌ **Email automation** - Have himalaya + gog
❌ **Calendar integration** - Have gog
❌ **GitHub integration** - Have github skill
❌ **Task management** - Have things-mac
❌ **Note-taking** - Have apple-notes + obsidian
❌ **Weather data** - Have weather skill
❌ **Transcription** - Have summarize + openai-whisper-api

---

## Missing Categories (Gaps to Fill)

### Email/CRM Outreach Ops
- **Need:** Bulk email campaigns (JiraFlow outreach)
- **Options:** Build on himalaya, or dedicated skill

### Research Ingestion
- **Need:** RSS/news/release monitoring
- **Options:** Custom skill or MCP server

### Journaling / Habit Tracking
- **Need:** Automated retros, habit tracking
- **Options:** Extend apple-notes or custom skill

### Multi-Repo Coordination
- **Need:** Coordinate FermWare/JiraFlow/Sanger/OptionsFlow
- **Options:** multi-repo-coordinator skill (P2)

---

## Evaluation Criteria (Before Installing)

**Every skill candidate must answer:**
1. **Why do we need it?** (Specific use case, clear value)
2. **What's the risk?** (What could break? Security implications?)
3. **How do we rollback?** (If it breaks, how do we recover?)
4. **Who maintains it?** (Internal vs external, update frequency)
5. **Token cost?** (How expensive to use regularly?)

**Approval process:**
1. Winnie researches and documents (using above criteria)
2. Add to this file with risk assessment
3. Rosie reviews for coordination impact
4. Mack implements and tests
5. Winnie validates before production use

---

## Skill Maintenance Log

**Format:** YYYY-MM-DD | Skill | Action | Agent | Notes

- 2026-02-12 | code-search | Planned | Rosie | P0 priority, Mack to build
- 2026-02-12 | pattern-matcher | Planned | Rosie | P0 priority, Mack to build
- 2026-02-12 | test-runner | Planned | Rosie | P0 priority, Winnie to build
- 2026-02-12 | doc-fetch | Planned | Rosie | P0 priority, Mack to build

---

**Keep this document current. Every skill addition/removal gets logged here.**
