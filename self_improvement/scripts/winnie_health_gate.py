#!/usr/bin/env python3
import json, subprocess, sys
from pathlib import Path

def enforce_model_health():
    """BLOCKING: Fail loudly if model health check does not pass."""
    try:
        result = subprocess.run(
            ['python3', 'self_improvement/scripts/health_check_models.py'],
            capture_output=True, timeout=30, text=True
        )
        if result.returncode != 0:
            print(f'HARD_GATE_VIOLATION: Model health check failed.\n{result.stderr}')
            sys.exit(1)
        health = json.loads(result.stdout)
        failures = sum(1 for m in health.get('models', []) if m.get('consecutive_failures', 0) >= 2)
        if failures > 0:
            print(f'HARD_GATE_VIOLATION: {failures} model(s) failed 2+ consecutive calls. Fallback required.')
            sys.exit(1)
        return True
    except Exception as e:
        print(f'HARD_GATE_ERROR: {e}')
        sys.exit(1)

if __name__ == '__main__':
    enforce_model_health()
    print('GATE_PASS: Model health validated. Proceeding.')
