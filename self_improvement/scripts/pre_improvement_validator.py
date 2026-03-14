#!/usr/bin/env python3
import json, sys
def validate_improvements(improvements):
    for imp in improvements:
        if 'patch_proof' not in imp or not imp['patch_proof']:
            print(f"GATE FAILED: {imp['title']} missing patch_proof")
            return False
    return True
if __name__ == '__main__':
    data = json.load(sys.stdin)
    if validate_improvements(data.get('improvements', [])):
        print('PATCH_PROOF_GATE: PASS')
        sys.exit(0)
    sys.exit(1)