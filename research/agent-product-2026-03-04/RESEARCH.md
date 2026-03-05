# RESEARCH.md — Agent Product Sprint (2026-03-04)

## Scope
Deep research completed for:
1. Low-code AI agent setup for beginners
2. Multi-agent framework architecture and implementation patterns
3. Empirical evaluation/reproducibility standards for premium publication
4. Monetization strategy for PDF product ladder

## Method
- **Perplexity Deep Research via OpenRouter** (`sonar-deep-research`) only
- **Firecrawl Agent** structured extraction across best-practices, framework comparison, architecture, and monetization

## Raw Research Files
- `sonar_market_demand.json`
- `sonar_empirical_methods.json`
- `sonar_curriculum_ladder.json`
- `firecrawl_lowcode_best_practices.json`
- `firecrawl_framework_comparison.json`
- `firecrawl_multiagent_architecture.json`
- `firecrawl_monetization_packaging.json`

## Synthesis

### A) Market Demand (2025–2026)
- Demand is high for implementation-focused AI guides due to deployment gaps and skills shortages.
- Low-code adoption continues accelerating; non-technical operators need practical playbooks.
- Premium willingness-to-pay increases when content includes reproducible steps, templates, and measurable outcomes.

### B) Beginner Product Direction (Low-Code)
- Best onboarding pattern: narrow use-case + prebuilt template + incremental testing.
- Most effective framing: “agent as employee” (role, tools, SOP).
- Key anti-patterns to avoid in public guide:
  - broad “general assistant” builds
  - jargon-heavy instructions
  - no troubleshooting/failure-state section

### C) Framework Positioning (Intermediate to Advanced)
- **Zapier AI**: fastest onboarding, expensive at scale.
- **Make**: strong visual control/debugging, good for ops teams.
- **n8n**: best cost/privacy flexibility with more technical overhead.
- **CrewAI**: role-based collaboration abstraction.
- **LangGraph**: strongest deterministic control for production-critical systems.
- **AutoGen**: strong for code-centric multi-agent patterns.

### D) Empirical Standards for Premium Publication
- Outcome-only metrics are insufficient; include trajectory/process evaluation.
- Use LLM-as-judge with calibration and periodic human checks.
- Require reproducibility package:
  - prompts/configs/versions
  - environment details
  - multi-run stats with confidence intervals
- Portfolio benchmarking recommended:
  - general benchmark
  - domain benchmark
  - tool-use benchmark
  - adversarial/robustness benchmark

### E) Monetization Strategy
- Product ladder:
  1. Entry PDF (low-ticket)
  2. Bundle/toolkit package (mid-tier)
  3. Premium empirical report / implementation program
- Conversion funnel:
  - lead magnet → paid starter PDF → premium upsell
- Highest-performing packaging combines PDF + templates/checklists + implementation assets.

## Built Package Drafts
- `Agent_Setup_in_60_Minutes_Package.md`
- `From_Single_Agent_to_Multi_Agent_Package.md`
- `Agent_Architecture_Empirical_Research_Package.md`

## Recommended Immediate Next Steps
1. Lenny QA: verify empirical claims + remove unverified source assertions where needed.
2. Mack: produce executable reference setups and screenshots for each package.
3. Winnie: convert markdown packages to branded PDFs + publish landing pages.
4. Final pass: add Evidence Appendix to each PDF (test env, exact steps, expected outputs, known limits).
