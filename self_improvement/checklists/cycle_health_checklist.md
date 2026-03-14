# Cycle Health Checklist (EXECUTABLE_TEMPLATE)

## Pre-Execution Gates (BLOCKING)
- [ ] memU bridge responding to health check (timeout: 2s)
- [ ] workspace directories exist: self_improvement/, outputs/, scripts/
- [ ] shared-state.json is readable and valid JSON
- [ ] API keys present in environment (OPENAI_API_KEY, MEMU_AUTH_TOKEN)
- [ ] Previous cycle output exists and is parseable

## Failure Mode
If ANY gate fails, raise exception and block improvement generation. Log failure reason to outputs/YYYY-MM-DD-HH-rosie.md with 'HEALTH_CHECK_FAILED' prefix.