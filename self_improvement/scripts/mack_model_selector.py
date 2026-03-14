#!/usr/bin/env python3
import sys, json

task_to_model = {
  'deep_synthesis': 'openai-codex/gpt-5.3-codex',
  'fast_impl': 'openai-codex/gpt-5.3-codex-spark',
  'architecture': 'anthropic/claude-sonnet-4-6',
  'strategic': 'anthropic/claude-opus-4-6',
  'breadth': 'google-gemini-cli/gemini-2.5-pro',
  'simple_fix': 'anthropic/claude-haiku-4-5'
}

if len(sys.argv) < 2:
  print(json.dumps({'error': 'usage: mack_model_selector.py <task_type>', 'valid_types': list(task_to_model.keys())}))
  sys.exit(1)

task = sys.argv[1]
if task not in task_to_model:
  print(json.dumps({'error': f'unknown task type: {task}', 'valid_types': list(task_to_model.keys())}))
  sys.exit(1)

print(json.dumps({'task': task, 'model': task_to_model[task]}))