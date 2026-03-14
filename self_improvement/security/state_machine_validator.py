#!/usr/bin/env python3
"""
Gateway XML State Machine Validator
Sits between LLM output and tool execution.
Validates state machines emitted by the SOP compiler.
"""
import sys
import json
import re
import xml.etree.ElementTree as ET
from typing import Optional


def extract_xml_block(text: str) -> Optional[str]:
    """Extract first <StateMachine> or <State ...> block from text."""
    # Try full StateMachine wrapper first
    m = re.search(r'(<StateMachine[\s\S]*?</StateMachine>)', text)
    if m:
        return m.group(1)
    # Fallback: wrap bare State elements
    states = re.findall(r'<State[\s\S]*?</State>', text)
    if states:
        return '<StateMachine>' + ''.join(states) + '</StateMachine>'
    return None


def parse_state_machine(xml_str: str) -> dict:
    """Parse XML into states dict. Returns {state_id: [transition_targets]}."""
    root = ET.fromstring(xml_str)
    states = {}
    for state in root.iter('State'):
        sid = state.get('id') or state.get('current') or state.get('name')
        if not sid:
            continue
        transitions = [t.get('target') for t in state.iter('Transition') if t.get('target')]
        states[sid] = transitions
    return states


def find_reachable(states: dict, start: str) -> set:
    """BFS reachability from start state."""
    visited = set()
    queue = [start]
    while queue:
        s = queue.pop(0)
        if s in visited:
            continue
        visited.add(s)
        for t in states.get(s, []):
            if t not in visited:
                queue.append(t)
    return visited


def detect_cycles(states: dict) -> list:
    """DFS cycle detection. Returns list of cycle descriptions."""
    cycles = []
    visited = set()
    rec_stack = set()

    def dfs(node, path):
        visited.add(node)
        rec_stack.add(node)
        for neighbor in states.get(node, []):
            if neighbor not in visited:
                if neighbor in states:
                    dfs(neighbor, path + [neighbor])
            elif neighbor in rec_stack:
                cycle_start = path.index(neighbor) if neighbor in path else 0
                cycle_path = path[cycle_start:] + [neighbor]
                cycles.append(' -> '.join(cycle_path))
        rec_stack.discard(node)

    for state in states:
        if state not in visited:
            dfs(state, [state])
    return cycles


def validate(xml_input: str) -> dict:
    """
    Main validation function.
    Returns: {valid: bool, errors: [], current_state: str, next_valid_transitions: []}
    """
    errors = []
    current_state = None
    next_valid_transitions = []

    # Extract XML if embedded in larger text
    xml_block = extract_xml_block(xml_input)
    if not xml_block:
        return {
            "valid": False,
            "errors": ["No valid StateMachine XML found in input"],
            "current_state": None,
            "next_valid_transitions": []
        }

    # Parse
    try:
        states = parse_state_machine(xml_block)
    except ET.ParseError as e:
        return {
            "valid": False,
            "errors": [f"XML parse error: {e}"],
            "current_state": None,
            "next_valid_transitions": []
        }

    if not states:
        return {
            "valid": False,
            "errors": ["No State elements found in XML"],
            "current_state": None,
            "next_valid_transitions": []
        }

    state_ids = set(states.keys())

    # Find current state (State with current="true" or first INIT state)
    try:
        root = ET.fromstring(xml_block)
        for state in root.iter('State'):
            if state.get('current', '').lower() in ('true', '1', 'yes'):
                current_state = state.get('id') or state.get('name')
                break
        if not current_state:
            # Try INIT
            for sid in state_ids:
                if sid.upper() in ('INIT', 'START', 'BEGIN'):
                    current_state = sid
                    break
        if not current_state and state_ids:
            current_state = next(iter(state_ids))
    except Exception:
        pass

    # Validate transitions reference valid state ids
    for sid, targets in states.items():
        for target in targets:
            if target not in state_ids:
                errors.append(f"State '{sid}': transition target '{target}' does not exist")

    # Validate no orphan states (unreachable from INIT)
    init_state = None
    for sid in state_ids:
        if sid.upper() in ('INIT', 'START', 'BEGIN'):
            init_state = sid
            break
    if not init_state and state_ids:
        init_state = next(iter(state_ids))

    if init_state:
        reachable = find_reachable(states, init_state)
        orphans = state_ids - reachable
        for orphan in sorted(orphans):
            errors.append(f"Orphan state (unreachable from '{init_state}'): '{orphan}'")

    # Cycle detection
    cycles = detect_cycles(states)
    for cycle in cycles:
        errors.append(f"Cycle detected: {cycle}")

    # Compute next valid transitions from current state
    if current_state and current_state in states:
        next_valid_transitions = [t for t in states[current_state] if t in state_ids]

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "current_state": current_state,
        "next_valid_transitions": next_valid_transitions
    }


def run_tests():
    print("Running state_machine_validator tests...")
    passed = 0
    failed = 0

    def check(name, result, expect_valid, expect_error_fragment=None):
        nonlocal passed, failed
        ok = result["valid"] == expect_valid
        if expect_error_fragment:
            ok = ok and any(expect_error_fragment in e for e in result["errors"])
        status = "PASS" if ok else "FAIL"
        if status == "FAIL":
            failed += 1
            print(f"  [{status}] {name}: {result}")
        else:
            passed += 1
            print(f"  [{status}] {name}")

    # Test 1: Valid simple machine
    xml1 = """<StateMachine>
      <State id="INIT"><Transition target="RUNNING"/></State>
      <State id="RUNNING"><Transition target="DONE"/></State>
      <State id="DONE"/>
    </StateMachine>"""
    check("Valid simple machine", validate(xml1), True)

    # Test 2: Invalid transition target
    xml2 = """<StateMachine>
      <State id="INIT"><Transition target="NONEXISTENT"/></State>
    </StateMachine>"""
    check("Invalid transition target", validate(xml2), False, "NONEXISTENT")

    # Test 3: Orphan state
    xml3 = """<StateMachine>
      <State id="INIT"><Transition target="RUNNING"/></State>
      <State id="RUNNING"/>
      <State id="ORPHAN"/>
    </StateMachine>"""
    check("Orphan state detected", validate(xml3), False, "ORPHAN")

    # Test 4: Cycle detection
    xml4 = """<StateMachine>
      <State id="INIT"><Transition target="A"/></State>
      <State id="A"><Transition target="B"/></State>
      <State id="B"><Transition target="A"/></State>
    </StateMachine>"""
    check("Cycle detected", validate(xml4), False, "Cycle")

    # Test 5: No XML found
    check("No XML", validate("some plain text with no xml"), False, "No valid")

    # Test 6: Current state detection
    xml6 = """<StateMachine>
      <State id="INIT" current="true"><Transition target="DONE"/></State>
      <State id="DONE"/>
    </StateMachine>"""
    r = validate(xml6)
    ok = r["valid"] and r["current_state"] == "INIT" and "DONE" in r["next_valid_transitions"]
    status = "PASS" if ok else "FAIL"
    print(f"  [{status}] Current state + transitions: {r}")
    if ok:
        passed += 1
    else:
        failed += 1

    print(f"\nResults: {passed} passed, {failed} failed")
    return failed == 0


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 state_machine_validator.py validate <xml_file_or_string>")
        print("       python3 state_machine_validator.py --test")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "--test":
        success = run_tests()
        sys.exit(0 if success else 1)

    if cmd == "validate":
        if len(sys.argv) < 3:
            print("Error: provide xml_file or xml_string", file=sys.stderr)
            sys.exit(1)
        arg = sys.argv[2]
        # Try as file first
        try:
            with open(arg) as f:
                content = f.read()
        except (FileNotFoundError, OSError):
            content = arg

        result = validate(content)
        print(json.dumps(result, indent=2))
        sys.exit(0 if result["valid"] else 2)

    print(f"Unknown command: {cmd}", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()
