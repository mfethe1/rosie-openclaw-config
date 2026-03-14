# PM Framework v2.0 — Enterprise Adaptive Team Simulation

## Overview

A multi-persona AI-powered project management system that simulates a full enterprise team. It implements:
- **25+ specialized personas** across 5 tiers: leadership, craft specialists, GTM, customer simulation, and red/blue team
- **Dynamic team composition** via `TeamBuilder` — auto-selects the right team for any project context
- **Synthetic customer personas** via `CustomerPersonaGenerator` — generates realistic users for any industry/role
- **Phased memory-stream sessions** — each phase passes its output to the next (MetaGPT aggregation pattern)
- **Domain-adaptive Technical Lead** — shifts expertise to construction, biotech, finance, or marketing context

---

## Files

| File | Purpose |
|------|---------|
| `personas.py` | Enterprise persona library — 25+ roles + CustomerPersonaGenerator + TeamBuilder |
| `pm_session.py` | Session runner — linear (backward compat) and phased (enterprise) modes |
| `marketing_voice.py` | Brand voice social media response generator |
| `continuous_review.py` | Cron-driven scheduled review loop |
| `team_presets.json` | Pre-built team compositions for 12 common project types |
| `project_configs/*.json` | Per-project configuration files |
| `logs/` | All session and review outputs |

---

## Persona Tiers

### Tier 0 — Legacy Core (always available)

| Role | Name | Temp | Function |
|------|------|------|----------|
| `pm` | Project Manager | 0.3 | Sprint planning, user stories, risk register |
| `red` | Red Team Critic | 0.7 | Adversarial attack on the plan |
| `blue` | Blue Team Defender | 0.4 | Defense + mitigations |
| `interviewer` | User Story Interviewer | 0.6 | User personas + latent requirements |
| `qa` | QA Reviewer | 0.2 | Testability review + test scenarios |
| `marketing` | Marketing Strategist | 0.7 | Campaign planning + content calendar |

### Tier 1 — Core Leadership

| Role | Name | Temp | Function |
|------|------|------|----------|
| `cpo` | Chief Product Officer | 0.4 | Strategic vision, ROI, go/no-go decisions, final arbitration |
| `tech_lead` | Technical Lead / CTO | 0.35 | Architecture, technical risks, build/buy decisions — **domain-adaptive** |
| `engineering_manager` | Engineering Manager | 0.3 | Capacity planning, sprint commitment, dependency mapping |

### Tier 2 — Craft Specialists

| Role | Name | Temp | Function |
|------|------|------|----------|
| `ux_designer` | UX/UI Designer | 0.5 | User flows, accessibility, design systems |
| `data_scientist` | Data Scientist / ML Engineer | 0.35 | ML feasibility, data readiness, model risk |
| `devops` | DevOps / SRE | 0.3 | Infrastructure, CI/CD, observability, deployment |
| `security` | Security Engineer | 0.25 | OWASP, threat modeling, HIPAA/SOC2/GDPR |
| `tech_writer` | Technical Writer | 0.3 | Documentation gaps, API docs, changelogs |
| `solutions_architect` | Solutions Architect | 0.35 | Integration architecture, API design, vendor evaluation |
| `performance_engineer` | Performance Engineer | 0.3 | Latency budgets, load testing, caching |

### Tier 3 — Business & Go-to-Market

| Role | Name | Temp | Function |
|------|------|------|----------|
| `product_marketing` | Product Marketing Manager | 0.6 | Positioning, messaging, competitive battlecards, launch |
| `sales_engineer` | Sales Engineer | 0.55 | Demo scripts, objection handling, POC criteria |
| `customer_success` | Customer Success Manager | 0.45 | Onboarding, adoption playbooks, churn risk |
| `business_analyst` | Business Analyst | 0.3 | Requirements traceability, ROI models, process maps |
| `legal` | Legal / Compliance Advisor | 0.2 | Data privacy, regulatory requirements, IP risk |

### Tier 4 — Synthetic Customer Personas (dynamic)

Generated dynamically by `CustomerPersonaGenerator`. Each persona has:
- Name, title, company_size, years_experience, tech_savviness (1-10)
- Pain points (industry + role specific)
- Evaluation criteria (what they look for in the product)
- Objections (by expertise level: novice/intermediate/expert)
- Budget sensitivity (low/medium/high)
- Full system_prompt (200-400 words, stays fully in character)

### Tier 5 — Red/Blue Team Enhanced

| Role | Name | Temp | Function |
|------|------|------|----------|
| `chaos_engineer` | Chaos Engineer | 0.6 | Failure scenario catalog (8-12 experiments, ranked by impact) |
| `ethical_ai` | Ethical AI Reviewer | 0.4 | Bias detection, fairness metrics, human oversight requirements |
| `competitive_intel` | Competitive Intelligence Analyst | 0.55 | Competitor tracking, battlecard updates, market positioning |
| `accessibility` | Accessibility Auditor | 0.25 | WCAG 2.1 AA compliance, AT testing, debt classification |

---

## Domain Adaptation

The `tech_lead` persona dynamically adjusts based on `domain`:

| Domain | Focus Areas |
|--------|-------------|
| `software` (default) | Architecture, scalability, API design, CI/CD, code quality |
| `construction` | Building codes (IBC/ACI/AISC), material specs, estimation accuracy, BIM workflows |
| `biotech` | Research methodology, FDA regulatory pathway, clinical trial phases, GMP |
| `marketing` | Campaign metrics, funnel optimization, attribution modeling, A/B testing |
| `finance` | Risk models, SOX/Basel/GAAP compliance, audit trails, PCI-DSS |

```python
from personas import get_tech_lead_for_domain
tech_lead = get_tech_lead_for_domain("construction")
```

---

## CustomerPersonaGenerator

```python
from personas import CustomerPersonaGenerator

generator = CustomerPersonaGenerator()

# Generate for BuildBid
customers = generator.generate(
    product="BuildBid",
    industry="construction",
    count=5,
    expertise_distribution={"novice": 2, "intermediate": 2, "expert": 1},
    roles=["general_contractor", "estimator", "project_owner", "subcontractor", "architect"]
)

# Each customer:
c = customers[0]
print(c["name"])               # "Alex Johnson"
print(c["title"])              # "General Contractor / Owner"
print(c["tech_savviness"])     # 3 (out of 10)
print(c["pain_points"])        # ["Bid estimates take 2-3 days...", ...]
print(c["objections"])         # ["This looks complicated...", ...]
print(c["budget_sensitivity"]) # "high"
print(c["system_prompt"])      # Full 300-word prompt to simulate this customer
```

Supported industries with specific pain points: `construction`, `healthcare`, `saas`
Generic pain points used for any other industry.

---

## TeamBuilder

```python
from personas import TeamBuilder

builder = TeamBuilder()

# Auto-selects appropriate team for a construction SaaS project
team = builder.for_project(
    project_type="saas",
    industry="construction",
    stage="growth",         # startup | growth | enterprise | maintenance
    focus="feature_development",  # feature_development | bug_fix | security_audit | launch | pivot | data_ml | accessibility
    include_customers=True,
    customer_count=2
)
# Returns: list of persona dicts with domain-adapted prompts

# Manual composition
team = builder.custom([
    "cpo", "tech_lead", "ux_designer", "security",
    "customer_novice", "customer_expert"
], domain="construction")

# Describe the team
print(builder.describe_team(team))
# Team (6 members):
#   [cpo] Chief Product Officer / Executive Sponsor — Tier 1
#   [tech_lead] Technical Lead / CTO [construction] — Tier 1
#   ...
```

### Auto-selection logic

The team is built from four layers:
1. **Always included**: `pm`, `red`, `blue`, `qa`
2. **Stage additions**: e.g. `growth` adds `cpo`, `tech_lead`, `engineering_manager`, `product_marketing`, `customer_success`
3. **Focus additions**: e.g. `feature_development` adds `interviewer`, `ux_designer`, `tech_writer`
4. **Industry additions**: e.g. `construction` adds `solutions_architect`, `business_analyst`

---

## Running a Session

### Linear mode (backward compatible)
```bash
# Standard multi-persona review
python3 pm_session.py run \
  --project "BuildBid" \
  --context "Estimating module complete, lot model persistence needed" \
  --personas pm,red,blue,qa

# From project config
python3 pm_session.py run --config project_configs/buildbid.json --personas pm,red,blue,qa,cpo

# With verbose output
python3 pm_session.py run --project "BuildBid" --context "..." --personas pm,red --verbose
```

### Phased mode (enterprise)
```bash
# Full enterprise session — auto-selects team
python3 pm_session.py run \
  --project "BuildBid" \
  --config project_configs/buildbid.json \
  --mode phased \
  --industry construction \
  --stage growth \
  --focus feature_development

# Skip expensive phases
python3 pm_session.py run \
  --project "BuildBid" --context "..." \
  --mode phased --industry construction \
  --skip-phases "Go-to-Market"

# Without customer personas
python3 pm_session.py run \
  --project "BuildBid" --context "..." \
  --mode phased --no-customers
```

### Using presets from team_presets.json
```bash
# construction_saas preset
python3 pm_session.py run \
  --project "BuildBid" \
  --config project_configs/buildbid.json \
  --personas cpo,pm,tech_lead,ux_designer,solutions_architect,business_analyst,red,blue,security,qa,tech_writer,product_marketing,sales_engineer,customer_success,competitive_intel

# security_audit preset
python3 pm_session.py run \
  --project "BuildBid" --context "..." \
  --personas pm,tech_lead,security,legal,red,chaos_engineer,blue,devops,qa
```

### Scheduled continuous review
```bash
python3 continuous_review.py --project buildbid
python3 continuous_review.py --all
python3 continuous_review.py --list
python3 continuous_review.py --project buildbid --dry-run
```

---

## Phased Session Flow

```
Context Input + Project Config
         │
         ▼
┌─────────────────────────────────────────────────────────┐
│ Phase 1: DISCOVERY                                       │
│ Interviewer + Customer Personas → requirements          │
└─────────────────────────────────────────────────────────┘
         │ outputs passed to →
         ▼
┌─────────────────────────────────────────────────────────┐
│ Phase 2: PLANNING                                        │
│ PM + Tech Lead + Architect → sprint plan + architecture │
│ Engineering Manager → capacity + dependencies           │
│ Business Analyst → requirements traceability + ROI      │
│ [PM synthesizes phase]                                  │
└─────────────────────────────────────────────────────────┘
         │ outputs passed to →
         ▼
┌─────────────────────────────────────────────────────────┐
│ Phase 3: REVIEW (adversarial)                           │
│ Red Team + Chaos Engineer → failure scenarios           │
│ Security → OWASP + compliance                          │
│ Competitive Intel → market position gaps               │
│ Ethical AI → bias + fairness (if ML involved)          │
└─────────────────────────────────────────────────────────┘
         │ outputs passed to →
         ▼
┌─────────────────────────────────────────────────────────┐
│ Phase 4: DEFENSE                                        │
│ Blue Team → mitigations for all Review findings        │
│ Engineering Manager → sprint re-commitment             │
│ [Blue Team synthesizes phase]                          │
└─────────────────────────────────────────────────────────┘
         │ outputs passed to →
         ▼
┌─────────────────────────────────────────────────────────┐
│ Phase 5: QUALITY                                        │
│ QA → test scenarios + completeness score               │
│ Accessibility → WCAG 2.1 AA audit                      │
│ Technical Writer → documentation gap analysis          │
│ [QA synthesizes phase]                                 │
└─────────────────────────────────────────────────────────┘
         │ outputs passed to →
         ▼
┌─────────────────────────────────────────────────────────┐
│ Phase 6: GO-TO-MARKET                                   │
│ Product Marketing → positioning + launch brief         │
│ Sales Engineer → demo script + objection handling      │
│ Customer Success → onboarding + adoption playbook      │
│ [Product Marketing synthesizes phase]                  │
└─────────────────────────────────────────────────────────┘
         │ ALL outputs passed to →
         ▼
┌─────────────────────────────────────────────────────────┐
│ Phase 7: SYNTHESIS                                      │
│ CPO arbitrates ALL prior input                         │
│ → Final go/no-go decision                              │
│ → Top 3 business bets                                  │
│ → Resolved risk register                               │
│ → Success metrics                                      │
└─────────────────────────────────────────────────────────┘
         │
         ▼
  JSON Report saved to logs/
```

Each phase's outputs are accumulated in a global memory stream (dict).
Later phases receive all prior outputs via `build_user_message()`.
This is the MetaGPT memory-stream aggregation pattern.

---

## Team Presets (team_presets.json)

| Preset | Personas | Recommended For |
|--------|----------|-----------------|
| `minimal` | 4 | Quick decisions, daily reviews |
| `sprint_planning` | 6 | Weekly sprint planning |
| `feature_launch` | 18 | Major feature releases |
| `security_audit` | 9 | SOC 2 prep, HIPAA review |
| `construction_saas` | 15 | BuildBid, estimating tools |
| `healthcare_saas` | 15 | EHR integrations, health platforms |
| `fintech` | 15 | Payments, trading, lending |
| `startup_mvp` | 8 | Pre-PMF, first sprints |
| `data_ml_platform` | 13 | ML pipelines, feature stores |
| `api_platform` | 13 | Developer APIs, SDKs |
| `accessibility_remediation` | 6 | WCAG compliance sprints |
| `enterprise_sales` | 9 | Fortune 500 deals, RFPs |
| `post_incident` | 9 | Post-mortems, SRE sprints |

---

## Self-Tests

```bash
# Test personas.py (TeamBuilder, CustomerPersonaGenerator, domain adaptation)
python3 personas.py --test

# Test pm_session.py (message builders, team assembly, phase structure)
python3 pm_session.py --test
```

Both tests run without API calls and validate all new functionality.

---

## Adding a New Persona

1. Add to `PERSONAS` dict in `personas.py`:
```python
PERSONAS["my_role"] = {
    "name": "My Role Name",
    "role": "my_role",
    "tier": 2,  # 0=legacy, 1=leadership, 2=craft, 3=gtm, 5=red/blue enhanced
    "system_prompt": """200-400 word prompt defining expertise, approach, and output format...""",
    "evaluation_criteria": ["Criterion 1", "Criterion 2"],
    "output_format": "my_format",
    "temperature": 0.4
}
```

2. Add to `PERSONA_FLOW` in `pm_session.py`:
```python
PERSONA_FLOW["my_role"] = {
    "label": "My Role Review",
    "depends_on": ["pm", "red"]
}
```

3. Add message-building logic in `build_user_message()`:
```python
elif role == "my_role":
    prior_context = prior_outputs.get("pm", "")
    msg += f"\n## PM Sprint Plan\n{prior_context}\n\nYour instructions..."
```

4. Add to relevant PHASES in the PHASES list.

---

## Adding a New Project

```bash
cat > project_configs/myproject.json << 'EOF'
{
  "name": "MyProject",
  "description": "What it does and who it's for",
  "current_state": "What's done, what's in progress",
  "industry": "construction",
  "stage": "growth",
  "key_features": ["Feature 1", "Feature 2"],
  "target_users": ["User type 1", "User type 2"],
  "known_issues": ["Issue 1", "Issue 2"],
  "next_priorities": ["Priority 1", "Priority 2"],
  "tech_stack": ["Python", "React", "PostgreSQL"],
  "business_stage": "Beta",
  "target_market": "Market description"
}
EOF

# Run session
python3 pm_session.py run --config project_configs/myproject.json --mode phased --industry construction
```

---

## Programmatic Usage

```python
from pm_session import run_session, run_phased_session
from personas import TeamBuilder, CustomerPersonaGenerator, get_tech_lead_for_domain

# Linear session (backward compat)
report = run_session("BuildBid", context, ["pm", "red", "blue", "qa"])
print(report["outputs"]["synthesis"])

# Phased session
report = run_phased_session(
    project="BuildBid",
    context=context,
    industry="construction",
    stage="growth",
    focus="feature_development",
    include_customers=True,
    customer_count=3
)
print(report["phases"]["Synthesis"]["cpo"])

# Build a custom team
builder = TeamBuilder()
team = builder.for_project("saas", "construction", "growth", "launch")

# Generate customer personas
gen = CustomerPersonaGenerator()
customers = gen.generate(
    product="BuildBid", industry="construction", count=5,
    expertise_distribution={"novice": 2, "intermediate": 2, "expert": 1},
    roles=["general_contractor", "estimator", "project_owner", "subcontractor", "architect"]
)
```

---

## Model Configuration

Default model: `claude-haiku-4-5` (fast, cost-effective for multi-turn persona sessions)

```python
MODEL = "claude-haiku-4-5"    # default — fast, cheap
MODEL = "claude-sonnet-4-5"   # better quality, higher cost
MODEL = "claude-opus-4-5"     # highest quality (use for synthesis phases only)
```

Per-persona temperature guide:
| Persona | Temperature | Reason |
|---------|-------------|--------|
| PM, QA, Security, Legal | 0.2-0.3 | Structured, precise output |
| Blue Team, Tech Lead, Engineering Manager | 0.3-0.4 | Balanced evidence + reasoning |
| CPO, Ethical AI | 0.4 | Strategic with grounded reasoning |
| UX Designer, Solutions Architect | 0.35-0.5 | Creative but structured |
| Customer Success, Sales Engineer | 0.45-0.55 | Empathetic and persuasive |
| Competitive Intel, Product Marketing | 0.55-0.6 | Market-creative |
| Red Team, Marketing, Chaos Engineer | 0.6-0.7 | Adversarial / creative |

---

## Cron Setup

```cron
# Run PM review for all projects every Monday at 8am
0 8 * * 1 cd /Users/harrisonfethe/.openclaw/workspace/self_improvement/pm_framework && python3 continuous_review.py --all >> logs/cron.log 2>&1

# BuildBid phased review weekly
0 7 * * 1 cd /Users/harrisonfethe/.openclaw/workspace/self_improvement/pm_framework && python3 pm_session.py run --config project_configs/buildbid.json --mode phased --industry construction --stage growth --focus feature_development >> logs/cron.log 2>&1
```

---

## Integration with Self-Improvement Loop

```python
from pm_framework.pm_session import run_phased_session
report = run_phased_session("MyProject", context, industry="construction", stage="growth")
# report["outputs"] — full memory stream (all persona outputs)
# report["phases"] — phase-by-phase breakdown
# report["phases"]["Synthesis"]["cpo"] — final CPO decision
```
