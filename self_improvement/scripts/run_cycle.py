#!/usr/bin/env python3
import sys
import subprocess
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent

def main():
    args = sys.argv[1:]
    target = SCRIPT_DIR / "hourly_self_reflect.py"
    if not target.exists():
        print(f"Error: {target} not found")
        return 1
    
    cmd = [sys.executable, str(target)] + args
    result = subprocess.run(cmd)
    return result.returncode

if __name__ == "__main__":
    sys.exit(main())
