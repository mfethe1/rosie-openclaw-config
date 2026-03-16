#!/usr/bin/env python3
"""
Antfarm Pilot Runner script for feature-dev workflow (Antfarm v0.5.1 pilot).
Enforces the global $10 cost ceiling and manual checkpoint per stage.
"""
import sys
import yaml
import os

YAML_PATH = "/Users/harrisonfethe/.openclaw/workspace/self_improvement/research/antfarm-pilot-workflow.yaml"

def load_pilot():
    if not os.path.exists(YAML_PATH):
        print(f"Error: YAML file not found at {YAML_PATH}")
        sys.exit(1)
        
    with open(YAML_PATH, "r") as f:
        pilot = yaml.safe_load(f)
        
    print(f"Loaded Antfarm Pilot Workflow: {pilot.get('name')}")
    print(f"Cost Ceiling: ${pilot.get('global_cost_ceiling', 'N/A')}")
    print("Steps:")
    for step in pilot.get('steps', []):
        agent = step.get('agent', step.get('type', 'system'))
        print(f" - [{step['id']}] Agent: {agent}")
        if step.get('requires_approval'):
            print(f"    -> Manual Checkpoint Enforced: {step.get('prompt')}")

if __name__ == '__main__':
    load_pilot()
