#!/usr/bin/env python3
"""
Ralph Loop Cron Wrapper for Long-Running Agentic Jobs.
Maintains state across cron executions, tracks iteration counts, and circuit-breaks
if runaway or consecutive failures occur.
"""
import sys, json, os, datetime, subprocess, re
from pathlib import Path

WORKSPACE = Path("/Users/harrisonfethe/.openclaw/workspace")
STATE_DIR = WORKSPACE / "infra" / "state" / "ralph_loops"

def load_state(job_id):
    state_file = STATE_DIR / f"{job_id}_progress.json"
    if state_file.exists():
        try:
            return json.loads(state_file.read_text())
        except:
            pass
    return {
        "job_id": job_id,
        "current_step": 1,
        "completed_steps": [],
        "errors": 0,
        "exit_signal": None,
        "hourly_count": 0,
        "hourly_reset_time": datetime.datetime.now().isoformat()
    }

def save_state(job_id, state):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    state_file = STATE_DIR / f"{job_id}_progress.json"
    state_file.write_text(json.dumps(state, indent=2))

BASE_PROMPT = """You are Macklemore (Mack), execution and implementation specialist for the OpenClaw self-improvement system. 
This is a Ralph Loop iteration. You must advance the task by exactly ONE step, updating files directly using your tools.
Task: Fix the top issues in self_improvement scripts.
1. Run dependency_analyzer.py to find top 5 scripts with issues.
2. Pick the highest priority script and fix it.
3. Validate fix with smoke_test.sh.
4. Update CHANGELOG.md.

CURRENT STATE:
{state_json}

INSTRUCTIONS:
- Review the current state.
- Decide the NEXT logical step and EXECUTE it using tools.
- Once finished executing, return ONLY a JSON block indicating the new state.
- If you encounter unrecoverable errors, output: {{"exit_signal": "ERROR_CIRCUIT_BROKEN"}}
- If the entire task is complete, output: {{"exit_signal": "COMPLETE"}}
- Otherwise, output: {{"completed_steps": ["what you just accomplished"], "current_step": <next_step_num>}}

You MUST execute the action (e.g. edit files, run tests) before returning the JSON.
ONLY return the JSON at the end of your response.
"""

def extract_json(text):
    text = re.sub(r"```(?:json)?\s*\n?", "", text)
    text = re.sub(r"\n?```\s*$", "", text)
    try:
        return json.loads(text.strip())
    except:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1:
            try:
                return json.loads(text[start:end+1])
            except:
                pass
    return None

def main():
    if len(sys.argv) < 2:
        print("Usage: ralph_cron_wrapper.py <job_id>")
        sys.exit(1)
        
    job_id = sys.argv[1]
    state = load_state(job_id)
    
    if state.get("exit_signal") in ["ERROR_CIRCUIT_BROKEN", "COMPLETE"]:
        print(f"[{job_id}] Halting: Exit signal is {state['exit_signal']}")
        # Optionally, reset the signal to run again
        if state["exit_signal"] == "COMPLETE":
             print(f"[{job_id}] Resetting job for new run.")
             state = load_state("dummy") # resets to fresh
             state["job_id"] = job_id
        else:
             sys.exit(0)
        
    now = datetime.datetime.now()
    reset_time = datetime.datetime.fromisoformat(state["hourly_reset_time"]) if state.get("hourly_reset_time") else now
    
    if (now - reset_time).total_seconds() > 3600:
        state["hourly_count"] = 0
        state["hourly_reset_time"] = now.isoformat()
        
    if state["hourly_count"] >= 5:
        print(f"[{job_id}] Hourly budget exceeded (5/hour). Postponing until next window.")
        save_state(job_id, state)
        sys.exit(0)
        
    state["hourly_count"] += 1
    save_state(job_id, state)
    
    prompt = BASE_PROMPT.format(state_json=json.dumps(state, indent=2))
    print(f"[{job_id}] Starting step {state['current_step']} via opencode...")
    
    try:
        # Use opencode CLI which gives the agent tool access
        res = subprocess.run(["opencode", "run", "-m", "anthropic/claude-sonnet-4-6", prompt], capture_output=True, text=True)
        print("Opencode output:\n" + res.stdout)
        
        new_state = extract_json(res.stdout)
        if new_state:
            if "exit_signal" in new_state:
                state["exit_signal"] = new_state["exit_signal"]
            if "completed_steps" in new_state:
                state["completed_steps"].extend(new_state["completed_steps"])
            if "current_step" in new_state:
                state["current_step"] = new_state["current_step"]
            state["errors"] = 0
        else:
            print(f"[{job_id}] Failed to parse JSON from model output.")
            state["errors"] += 1
            if state["errors"] >= 5:
                state["exit_signal"] = "ERROR_CIRCUIT_BROKEN"
                
    except Exception as e:
        print(f"[{job_id}] Execution error: {e}")
        state["errors"] += 1
        
    save_state(job_id, state)
    print(f"[{job_id}] Finished. State saved.")

if __name__ == "__main__":
    main()
