import os
import time
import json
import sys

def check_loop_exit(loop_id, max_calls_per_hour=50, completion_file=None):
    """
    Dual-condition loop exit gate + hourly budget guard.
    Condition 1: Completion indicator is present (e.g., EXIT_SIGNAL or complete file)
    Condition 2: Hourly budget is not exceeded.
    """
    hourly_calls_file = f"/tmp/{loop_id}_hourly_calls.json"
    
    # Check budget
    current_time = time.time()
    calls = []
    if os.path.exists(hourly_calls_file):
        with open(hourly_calls_file, 'r') as f:
            calls = json.load(f)
            
    # Filter calls within last hour
    calls = [t for t in calls if current_time - t < 3600]
    
    if len(calls) >= max_calls_per_hour:
        print(f"EXIT_GUARD: Hourly budget of {max_calls_per_hour} calls exceeded for {loop_id}.")
        return True # Should exit
        
    # Check completion
    if completion_file and os.path.exists(completion_file):
        print(f"EXIT_GUARD: Completion signal detected for {loop_id}.")
        return True # Should exit
        
    # Record this call
    calls.append(current_time)
    with open(hourly_calls_file, 'w') as f:
        json.dump(calls, f)
        
    return False # Continue loop

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python loop_exit_guard.py <loop_id> [completion_file]")
        sys.exit(1)
        
    loop_id = sys.argv[1]
    completion_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    should_exit = check_loop_exit(loop_id, completion_file=completion_file)
    sys.exit(1 if should_exit else 0)
