import json
from typing import Literal

TASK_ROUTING = {
    'deep_technical_synthesis': 'openai-codex/gpt-5.3-codex',
    'fast_implementation': 'openai-codex/gpt-5.3-codex-spark',
    'architecture_review': 'anthropic/claude-sonnet-4-6',
    'strategic_decision': 'anthropic/claude-opus-4-6',
    'broad_alternatives': 'google-gemini-cli/gemini-2.5-pro',
    'routine_fix': 'anthropic/claude-haiku-4-5'
}

def route_task(task_type: str) -> str:
    if task_type not in TASK_ROUTING:
        raise ValueError(f'Unknown task_type: {task_type}. Valid: {list(TASK_ROUTING.keys())}')
    return TASK_ROUTING[task_type]

def validate_routing_decision(task_type: str, model_chosen: str) -> bool:
    expected = route_task(task_type)
    return model_chosen == expected
