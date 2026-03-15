#!/usr/bin/env python3
import json, sys
def validate_improvements(improvements):
    for imp in improvements:
        if 'patch_proof' not in imp or not imp['patch_proof']:
            print(f"GATE FAILED: {imp['title']} missing patch_proof")
            return False
    return True
if __name__ == '__main__':
    if sys.stdin.isatty():
        print('Usage: echo \'{{"improvements": [...]}}\'  | python3 pre_improvement_validator.py')
        sys.exit(0)
    raw = sys.stdin.read().strip()
    if not raw:
        print('ERROR: no input provided on stdin')
        sys.exit(1)
    if sys.stdin.isatty():
        print('Usage: echo \'{{"improvements": [...]}}\'  | python3 pre_improvement_validator.py')
        sys.exit(0)
    data = json.loads(raw)
    if validate_improvements(data.get('improvements', [])):
        print('PATCH_PROOF_GATE: PASS')
        sys.exit(0)
    sys.exit(1)