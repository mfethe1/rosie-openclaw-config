#!/usr/bin/env python3
import sys
from pathlib import Path

def main():
    loops_file = Path("/Users/harrisonfethe/.openclaw/workspace/self_improvement/LOOPS.md")
    if not loops_file.exists():
        print("FAIL: LOOPS.md not found")
        sys.exit(1)
    
    content = loops_file.read_text()
    
    # Check for at least 3 checklist items in the Cycle Checklist -> Quality gates
    if "gate_compliance_check:" not in content:
        print("FAIL: gate_compliance_check not found in LOOPS.md")
        sys.exit(1)
        
    if "infrastructure_audit:" not in content:
        print("FAIL: infrastructure_audit not found in LOOPS.md")
        sys.exit(1)
        
    if "infrastructure_patch_proof:" not in content:
        print("FAIL: infrastructure_patch_proof not found in LOOPS.md")
        sys.exit(1)

    print("OK: LOOPS.md contains required gate compliance checks.")
    sys.exit(0)

if __name__ == "__main__":
    main()
