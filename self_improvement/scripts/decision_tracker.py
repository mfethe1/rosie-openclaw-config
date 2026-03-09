import re
import json
import os
import argparse

def track_decisions(todo_path):
    implemented = {}
    unimplemented = {}
    other = {}

    decision_pattern = re.compile(r'D-(\d{3})')
    task_pattern = re.compile(r'^\s*-\s*\[([ x])\]')

    with open(todo_path, 'r') as f:
        for line in f:
            matches = decision_pattern.findall(line)
            if not matches:
                continue
            
            task_match = task_pattern.match(line)
            status = 'unknown'
            if task_match:
                status = 'implemented' if task_match.group(1).lower() == 'x' else 'unimplemented'

            for d in matches:
                d_id = f"D-{d}"
                # If a decision is mentioned multiple times, we mark it implemented if ANY of its tasks are implemented
                if status == 'implemented':
                    implemented[d_id] = implemented.get(d_id, []) + [line.strip()]
                    if d_id in unimplemented:
                        del unimplemented[d_id]
                elif status == 'unimplemented':
                    if d_id not in implemented:
                        unimplemented[d_id] = unimplemented.get(d_id, []) + [line.strip()]
                else:
                    if d_id not in implemented and d_id not in unimplemented:
                        other[d_id] = other.get(d_id, []) + [line.strip()]

    return implemented, unimplemented, other

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true", help="Output in JSON format")
    args = parser.parse_args()

    todo_path = os.path.join(os.path.dirname(__file__), "..", "TODO.md")
    implemented, unimplemented, other = track_decisions(todo_path)

    all_d = set(implemented.keys()) | set(unimplemented.keys()) | set(other.keys())
    
    # We want to check D-001 to D-032
    # Find missing
    max_d = max([int(d.split('-')[1]) for d in all_d]) if all_d else 0
    
    report = {
        "summary": {
            "total_found": len(all_d),
            "implemented": len(implemented),
            "unimplemented": len(unimplemented),
            "unknown_status": len(other)
        },
        "unimplemented": {k: v for k, v in unimplemented.items()},
        "implemented": {k: v for k, v in implemented.items()},
        "other": {k: v for k, v in other.items()}
    }

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"Decision Tracker Report")
        print(f"=======================")
        print(f"Total Decisions Found: {len(all_d)}")
        print(f"Implemented: {len(implemented)}")
        print(f"Unimplemented: {len(unimplemented)}")
        print(f"Unknown Status: {len(other)}\n")
        
        print("Unimplemented Decisions:")
        for k in sorted(unimplemented.keys()):
            print(f"- {k}")
            for line in unimplemented[k]:
                print(f"  {line}")
        print("\nUnknown Status Decisions:")
        for k in sorted(other.keys()):
            print(f"- {k}")
            for line in other[k]:
                print(f"  {line}")
