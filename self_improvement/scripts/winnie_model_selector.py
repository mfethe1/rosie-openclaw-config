import json
from typing import Literal

def select_model_for_task(task_type: str, latency_budget_ms: int, evidence_depth: Literal['quick', 'medium', 'deep'], domain: str) -> str:
    """Route task to optimal model based on characteristics. Returns model ID."""
    if latency_budget_ms < 2000 and task_type in ['fact_check', 'quick_lookup']:
        return 'anthropic/claude-haiku-4-6'
    if evidence_depth == 'deep' and task_type in ['synthesis', 'comparison']:
        return 'anthropic/claude-sonnet-4-6'
    if task_type in ['risk_analysis', 'judgment', 'strategic_decision']:
        return 'anthropic/claude-opus-4-6'
    if domain == 'technical_validation':
        return 'openai/gpt-4-turbo'
    if task_type == 'web_research' and domain in ['competitor_tracking', 'ecosystem_breadth']:
        return 'google/gemini-2.0-pro'
    return 'anthropic/claude-sonnet-4-6'  # safe default

def call_llm_with_gating(prompt: str, task_type: str, latency_budget_ms: int = 5000, evidence_depth: str = 'medium', domain: str = 'general') -> str:
    """Enforced gate: select model first, then call. Prevents wrong-model-for-task."""
    model = select_model_for_task(task_type, latency_budget_ms, evidence_depth, domain)
    # Model execution delegated to orchestrator
    return f"Called {model} for {task_type}"
