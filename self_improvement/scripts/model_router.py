import json

MODEL_ROUTER = {
  'deep_code_synthesis': 'openai-codex/gpt-5.3-codex',
  'fast_verification': 'openai-codex/gpt-5.3-codex-spark',
  'architecture_review': 'anthropic/claude-sonnet-4-6',
  'strategic_decision': 'anthropic/claude-opus-4-6',
  'breadth_exploration': 'google-gemini-cli/gemini-2.5-pro',
  'routine_fix': 'anthropic/claude-haiku-4-5'
}

def route_task(task_type: str, complexity: str) -> str:
  """Route task to optimal model. complexity: 'simple'|'moderate'|'complex'."""
  if complexity == 'simple':
    return MODEL_ROUTER.get(task_type, 'anthropic/claude-haiku-4-5')
  return MODEL_ROUTER.get(task_type, 'openai-codex/gpt-5.3-codex')
