#!/usr/bin/env python3
"""
Verify Completion Gate for Ralph Loops.
Programmatically verifies if a Ralph loop or cron task actually completed 
by checking proof artifacts, instead of relying solely on the LLM's 'exit_signal: COMPLETE'.
"""
import os
import json
import logging

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

def verify_completion(state_file_path, required_artifacts=None):
    if not os.path.exists(state_file_path):
        logging.error(f"State file not found: {state_file_path}")
        return False

    try:
        with open(state_file_path, "r") as f:
            state = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logging.error(f"Failed to read state file: {e}")
        return False

    if state.get("exit_signal") != "COMPLETE":
        logging.info("Exit signal is not COMPLETE. Task is still running.")
        return False

    # Programmatic verification: check if required artifacts exist
    if required_artifacts:
        missing = []
        for artifact in required_artifacts:
            if not os.path.exists(artifact):
                missing.append(artifact)
        
        if missing:
            logging.error(f"False COMPLETE detected. Missing artifacts: {missing}")
            # Reset exit signal to prevent false completion
            state["exit_signal"] = None
            try:
                with open(state_file_path, "w") as f:
                    json.dump(state, f, indent=2)
                logging.info("Reset exit_signal to None to force continuation.")
            except OSError as e:
                logging.error(f"Failed to update state file: {e}")
            return False

    logging.info("Completion verified programmatically.")
    return True

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: verify_completion_gate.py <state_file_path> [required_artifact_1 ...]")
        sys.exit(1)
    
    state_file = sys.argv[1]
    artifacts = sys.argv[2:] if len(sys.argv) > 2 else None
    
    success = verify_completion(state_file, artifacts)
    sys.exit(0 if success else 1)
