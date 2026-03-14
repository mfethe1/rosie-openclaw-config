# PM Framework — Agent Onboarding Guide

> Version: 2026-03-02  
> Framework: PM Framework v2.0 (Enterprise Adaptive Team Simulation)  
> Location: `/Users/harrisonfethe/.openclaw/workspace/self_improvement/pm_framework`

---

## What This Framework Does

Runs multi-persona AI review sessions for any project. Each session passes a project context through a chain of 7–25 specialized personas (PM, Red Team, Blue Team, CPO, etc.) and produces a structured JSON + Markdown report covering sprint planning, risk analysis, mitigations, QA strategy, and go-to-market.

**When to use it:**
- Sprint planning for a new feature
- Pre-launch risk review
- Reviewing a ticket before dev starts
- Weekly continuous review (automated via LaunchAgents)
- Generating CPO-level go/no-go decisions

---

## Quick Start (Any Agent)

```bash
# Navigate to framework
cd /Users/harrisonfethe/.openclaw/workspace/self_improvement/pm_framework

# Set API key (uses OpenRouter)
export OPENROUTER_API_KEY=$(grep OPENROUTER_API_KEY ~/.openclaw/secrets/openrouter.env | cut -d= -f2)

# Dry-run any project (no API calls)
python3 continuous_review.py --project buildbid --dry-run

# Run a live review (minimal persona set: fast, ~30s)
python3 pm_session.py run --config project_configs/buildbid.json --personas pm,red,blue,qa

# Run full live test for a ticket
python3 run_live_test.py --project buildbid --ticket H8

# List all configured projects
python3 continuous_review.py --list

# Self-test all modules (no API calls)
python3 personas.py --test
python3 pm_session.py --test
python3 continuous_review.py --test
python3 gen_marketing_replies.py --test
```

---

## Per-Agent Lane Guide

### 🔵 Lenny — Product & Sprint Planning

**Your primary use:** Run pre-sprint reviews to generate user stories, acceptance criteria, and risk registers before committing to sprint scope.

```bash
# Full sprint planning review for BuildBid
cd /Users/harrisonfethe/.openclaw/workspace/self_improvement/pm_framework
export OPENROUTER_API_KEY=$(grep OPENROUTER_API_KEY ~/.openclaw/secrets/openrouter.env | cut -d= -f2)

# Standard sprint review (PM + red/blue + QA)
python3 pm_session.py run \
  --config project_configs/buildbid.json \
  --personas pm,red,blue,qa,cpo \
  --verbose

# Phased enterprise session (full team, ~10-15 min)
python3 pm_session.py run \
  --config project_configs/buildbid.json \
  --mode phased \
  --industry construction \
  --stage growth \
  --focus feature_development

# Review a specific ticket
python3 run_live_test.py --project buildbid --ticket H9 --personas pm,red,blue,qa,cpo
```

**Output location:** `logs/session-buildbid-*.json`  
**Key outputs to read:** `outputs.pm` (sprint plan), `outputs.cpo` (go/no-go decision)

---

### 🟠 Mack — Engineering & Technical Review

**Your primary use:** Run architecture and security reviews before dev starts. Focus on tech_lead, devops, security, and solutions_architect personas.

```bash
# Technical review (construction domain)
cd /Users/harrisonfethe/.openclaw/workspace/self_improvement/pm_framework
export OPENROUTER_API_KEY=$(grep OPENROUTER_API_KEY ~/.openclaw/secrets/openrouter.env | cut -d= -f2)

# Security + architecture review
python3 pm_session.py run \
  --config project_configs/buildbid.json \
  --personas tech_lead,solutions_architect,security,devops,red,blue,qa

# Live ticket test with tech focus
python3 run_live_test.py \
  --project buildbid --ticket H8 \
  --personas tech_lead,security,red,blue,qa

# For JiraFlow (Node.js stack)
python3 pm_session.py run \
  --config project_configs/jiraflow.json \
  --personas tech_lead,devops,security,qa \
  --verbose

# Security audit preset
python3 pm_session.py run \
  --config project_configs/sanger.json \
  --personas pm,tech_lead,security,legal,red,chaos_engineer,blue,devops,qa
```

**Output location:** `logs/session-*.json`  
**Key outputs to read:** `outputs.tech_lead` (architecture), `outputs.security` (threats), `outputs.chaos_engineer` (failure modes)

---

### 🦞 Rosie — Orchestration & Continuous Review

**Your primary use:** Trigger scheduled reviews, monitor project health across all four products, escalate anomalies.

```bash
# Check all LaunchAgent jobs (cron health)
launchctl list | grep "ai.protelynx.pm"

# Manually trigger a review
launchctl kickstart gui/$(id -u)/ai.protelynx.pm-review-buildbid

# Run all projects in one pass
cd /Users/harrisonfethe/.openclaw/workspace/self_improvement/pm_framework
export OPENROUTER_API_KEY=$(grep OPENROUTER_API_KEY ~/.openclaw/secrets/openrouter.env | cut -d= -f2)
python3 continuous_review.py --all

# Check latest review logs
ls -lt logs/review-*.json | head -8

# Run a specific project review
python3 continuous_review.py --project contentpilot

# Live test a ticket (full persona chain)
python3 run_live_test.py --project buildbid --ticket H8
```

**Cron registry:** `CRON_REGISTRY.md`  
**All log output:** `logs/cron-*.log`, `logs/review-*.json`

---

### 🟣 Winnie — Marketing & Brand Voice

**Your primary use:** Generate and refresh social media reply templates in Michael's voice. Run ContentPilot reviews.

```bash
# Generate/refresh marketing replies kit
cd /Users/harrisonfethe/.openclaw/workspace/self_improvement/pm_framework
export OPENROUTER_API_KEY=$(grep OPENROUTER_API_KEY ~/.openclaw/secrets/openrouter.env | cut -d= -f2)
python3 gen_marketing_replies.py

# Single ad-hoc reply (LinkedIn)
python3 marketing_voice.py respond \
  --post "Your actual comment text here" \
  --platform linkedin \
  --tone empathetic

# Twitter reply
python3 marketing_voice.py respond \
  --post "AI will replace estimators" \
  --platform twitter \
  --tone advocate

# ContentPilot project review
python3 pm_session.py run \
  --config project_configs/contentpilot.json \
  --personas pm,product_marketing,sales_engineer,customer_success,red,blue,qa \
  --verbose

# ContentPilot continuous review
python3 continuous_review.py --project contentpilot
```

**Output location:** `marketing_replies_kit.md` (refresh weekly)  
**Key script:** `gen_marketing_replies.py` (9 scenarios, 3 categories)  
**Tone options:** `default`, `advocate`, `empathetic`, `educational`, `direct`, `community`

---

## Project Config Reference

| Config File | Project | Domain | Stage |
|-------------|---------|--------|-------|
| `project_configs/buildbid.json` | BuildBid | construction | growth |
| `project_configs/jiraflow.json` | JiraFlow | saas | mvp |
| `project_configs/sanger.json` | Sanger | biotech | alpha |
| `project_configs/contentpilot.json` | ContentPilot | marketing | beta |

---

## Persona Quick Reference

| Role | When to include |
|------|----------------|
| `pm` | Always — generates sprint plan |
| `red` | Always — adversarial critique |
| `blue` | Always — mitigations |
| `qa` | Always — test strategy |
| `cpo` | Go/no-go decisions |
| `tech_lead` | Architecture decisions |
| `security` | Pre-launch, HIPAA/SOC2 reviews |
| `ux_designer` | User flow changes |
| `product_marketing` | Launch readiness |
| `chaos_engineer` | Reliability reviews |
| `legal` | Compliance/data privacy |

**Minimal fast set (30s):** `pm,red,blue,qa`  
**Standard (2min):** `pm,red,blue,qa,cpo,tech_lead`  
**Full enterprise (10-15min):** `--mode phased`

---

## Output Files

```
logs/
├── live-test-buildbid-h8-YYYY-MM-DD.json    # Live test JSON report
├── live-test-buildbid-h8-YYYY-MM-DD.md      # Human-readable summary
├── review-buildbid-YYYY-MM-DD.json          # Continuous review log
├── session-*.json                            # pm_session.py outputs
├── cron-buildbid.log                        # Daily buildbid cron log
├── cron-jiraflow.log                        # Daily jiraflow cron log
├── cron-sanger.log                          # Daily sanger cron log
└── cron-contentpilot.log                    # Daily contentpilot cron log
```

---

## Adding a New Project

```bash
# Create config
cat > project_configs/myproject.json << 'EOF'
{
  "name": "MyProject",
  "description": "...",
  "current_state": "...",
  "industry": "construction",
  "stage": "growth",
  "key_features": [],
  "target_users": [],
  "known_issues": [],
  "next_priorities": [],
  "tech_stack": [],
  "business_stage": "Beta",
  "target_market": "..."
}
EOF

# Test it
python3 continuous_review.py --project myproject --dry-run

# Register a daily cron (LaunchAgent)
# Copy an existing plist and update Label + project name
cp ~/Library/LaunchAgents/ai.protelynx.pm-review-buildbid.plist \
   ~/Library/LaunchAgents/ai.protelynx.pm-review-myproject.plist
# Edit: Label, command --project value, log paths
launchctl load ~/Library/LaunchAgents/ai.protelynx.pm-review-myproject.plist
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `RuntimeError: No API key` | `export OPENROUTER_API_KEY=$(grep OPENROUTER_API_KEY ~/.openclaw/secrets/openrouter.env | cut -d= -f2)` |
| Config not found | Check `python3 continuous_review.py --list` |
| crontab hangs | Use LaunchAgents (macOS FDA restriction); see `CRON_REGISTRY.md` |
| JSON parse error in marketing_voice | Rerun — model occasionally outputs markdown-wrapped JSON |
| Persona import error | Run `python3 personas.py --test` to diagnose |

---

_For framework questions, check `FRAMEWORK.md` (full reference) or ask Rosie._
