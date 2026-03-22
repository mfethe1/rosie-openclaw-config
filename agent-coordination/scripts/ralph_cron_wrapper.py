#!/usr/bin/env python3
import json
import os
import sys
import time
import subprocess
from datetime import datetime, timedelta

STATE_FILE = "progress.json"
MAX_RUNS_PER_HOUR = 5
MAX_ERRORS = 5

def load_state():
    if not os.path.exists(STATE_FILE):
        return {
            "current_step": "init",
            "completed_steps": [],
            "errors": 0,
            "exit_signal": None,
            "run_history": []
        }
    try:
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {
            "current_step": "init",
            "completed_steps": [],
            "errors": 0,
            "exit_signal": "ERROR_CORRUPT_STATE",
            "run_history": []
        }

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)

def check_budget(state):
    now = datetime.now()
    one_hour_ago = now - timedelta(hours=1)
    
    # Filter history to last hour
    recent_runs = [
        t for t in state.get("run_history", [])
        if datetime.fromisoformat(t) > one_hour_ago
    ]
    
    state["run_history"] = recent_runs
    
    if len(recent_runs) >= MAX_RUNS_PER_HOUR:
        return False
    return True

def main():
    if len(sys.argv) < 2:
        print("Usage: ralph_cron_wrapper.py <agent_command> [args...]")
        sys.exit(1)

    cmd = sys.argv[1:]
    state = load_state()

    if state.get("exit_signal"):
        print(f"Skipping run: Exit signal present -> {state['exit_signal']}")
        sys.exit(0)

    if state.get("errors", 0) >= MAX_ERRORS:
        state["exit_signal"] = "ERROR_CIRCUIT_BROKEN"
        save_state(state)
        print("Circuit breaker tripped: Too many consecutive errors.")
        sys.exit(1)

    if not check_budget(state):
        print("Budget guard active: Max runs per hour reached. Deferring to next hour.")
        save_state(state)
        sys.exit(0)

    # Record this run
    state.setdefault("run_history", []).append(datetime.now().isoformat())
    
    # Execute the agent step
    env = os.environ.copy()
    env["RALPH_LOOP_STATE"] = json.dumps(state)

    print(f"Executing: {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=300)
        
        # Expect the agent to output a new JSON state line prefixed with 'RALPH_STATE:'
        new_state_line = None
        for line in result.stdout.splitlines():
            if line.startswith("RALPH_STATE:"):
                new_state_line = line[len("RALPH_STATE:"):].strip()
        
        if new_state_line:
            try:
                new_state = json.loads(new_state_line)
                new_state["run_history"] = state["run_history"] # Preserve history
                new_state["errors"] = 0 # Reset on success
                save_state(new_state)
                print("Step completed successfully. State updated.")
            except json.JSONDecodeError:
                state["errors"] += 1
                save_state(state)
                print("Failed to parse RALPH_STATE output.")
        else:
            state["errors"] += 1
            save_state(state)
            print("No RALPH_STATE output found in agent response.")
            print("Agent stdout:", result.stdout)
            print("Agent stderr:", result.stderr)

    except subprocess.TimeoutExpired:
        state["errors"] += 1
        save_state(state)
        print("Agent timeout expired (300s).")
    except Exception as e:
        state["errors"] += 1
        save_state(state)
        print(f"Execution error: {e}")

if __name__ == "__main__":
    main()
