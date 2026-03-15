#!/usr/bin/env python3
import sys
import re
import os
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
SI_DIR = SCRIPT_DIR.parent
import re
import os

def check_orphans(todo_path):
    if not os.path.exists(todo_path):
        print(f"Error: {todo_path} not found.")
        sys.exit(1)

    with open(todo_path, "r") as f:
        lines = f.readlines()

    valid_agents = {"Rosie", "Winnie", "Mack", "Lenny", "Oracle", "All", "Atlas", "Hephaestus", "Sisyphus", "Librarian", "Explore", "Michael"}
    
    orphans = []
    in_active_section = False
    
    for i, line in enumerate(lines):
        line = line.strip()
        
        # Track sections
        if line.startswith("## P1") or line.startswith("## P2") or line.startswith("## P3") or line.startswith("## P4"):
            in_active_section = True
            continue
        elif line.startswith("## Closed") or line.startswith("## Archived"):
            in_active_section = False
            continue
            
        if not in_active_section:
            continue
            
        if not line.startswith("- "):
            continue
        if line.startswith("- ~~"):
            continue # Skip completed
        if line.startswith("- [x]"):
            continue # Skip completed
            
        # Only process actual task definitions (they usually start with bolding like - **[Mack]**)
        match = re.search(r"-\s*(?:\*\*)?\[(.*?)\]", line)
        if not match:
            # Maybe it's not a task but a sub-bullet. Usually tasks are at the top level and have an assignment.
            # Only complain if the line looks like a top-level task bullet (no indent before dash, not a sub-bullet)
            continue
            
        assigned_str = match.group(1)
        # Handle "Winnie/Oracle" -> ["Winnie", "Oracle"]
        assigned_list = [a.strip() for a in assigned_str.split("/")]
        
        # Check if the text inside bracket is actually a status rather than an agent
        if assigned_str in [" ", "x", "Priority: Medium"]:
            # This happens for `- [ ]` or `- [x]`. Look for the NEXT bracket
            match2 = re.search(r"\]\s*(?:\*\*)?\[(.*?)\]", line)
            if match2:
                assigned_str = match2.group(1)
                assigned_list = [a.strip() for a in assigned_str.split("/")]
            else:
                continue
                
        valid = False
        for a in assigned_list:
            if a in valid_agents:
                valid = True
                break
                
        if not valid:
            orphans.append((i+1, line, f"Unknown agent(s) in bracket: {assigned_str}"))

    return orphans

if __name__ == "__main__":
    todo_path = sys.argv[1] if len(sys.argv) > 1 else str(SI_DIR / 'TODO.md')
    orphans = check_orphans(todo_path)
    if orphans:
        print(f"TODO.md Orphan Check FAILED: Found {len(orphans)} unassigned or misassigned active tasks.")
        for line_num, text, reason in orphans:
            print(f"  Line {line_num}: {reason} -> {text[:60]}...")
        sys.exit(1)
        
    print("PASS: TODO.md Orphan Check. All active tasks have valid assignees.")
    sys.exit(0)
