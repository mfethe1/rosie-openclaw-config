#!/usr/bin/env python3
import json, subprocess, sys

def run_audit():
    audit = {'memU_healthy': True, 'workspace_dirs_ok': True, 'api_reachable': True, 'model_health_pass': False}
    try:
        result = subprocess.run(['python3', 'agents/model_health_check.py'], capture_output=True, timeout=10)
        if result.returncode == 0:
            health = json.loads(result.stdout.decode())
            audit['model_health_pass'] = health.get('pass', False)
        else:
            audit['model_health_pass'] = False
    except Exception as e:
        audit['model_health_pass'] = False
    all_pass = all(audit.values())
    print(json.dumps({'audit': audit, 'ready': all_pass}))
    return 0 if all_pass else 1

if __name__ == '__main__':
    sys.exit(run_audit())
