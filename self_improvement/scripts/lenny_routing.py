def route_qa_task(task_type: str) -> tuple[str, str]:
    """Route QA task to primary + fallback model based on type.
    Returns (primary_model, fallback_model)."""
    routing = {
        'risk_triage': ('anthropic/claude-opus-4-6', 'anthropic/claude-sonnet-4-6'),
        'validation_script': ('anthropic/claude-sonnet-4-6', 'openai-codex/gpt-5.3-codex'),
        'log_parsing': ('openai-codex/gpt-5.3-codex', 'openai-codex/gpt-5.3-codex-spark'),
        'health_check': ('anthropic/claude-haiku-4-5', 'anthropic/claude-sonnet-4-6'),
    }
    return routing.get(task_type, ('anthropic/claude-opus-4-6', 'anthropic/claude-sonnet-4-6'))