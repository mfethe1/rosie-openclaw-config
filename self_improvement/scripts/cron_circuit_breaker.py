import json
import subprocess
import sys

def run_command(cmd):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True)

def main():
    print("Running Cron Circuit Breaker...")
    res = run_command("openclaw cron list --json")
    if res.returncode != 0:
        print(f"Failed to get cron list: {res.stderr}")
        sys.exit(1)
    
    try:
        data = json.loads(res.stdout)
    except Exception as e:
        print(f"Failed to parse JSON: {e}")
        sys.exit(1)
        
    jobs = data.get("jobs", [])
    disabled_count = 0
    
    for job in jobs:
        state = job.get("state", {})
        consecutive_errors = state.get("consecutiveErrors", 0)
        job_id = job.get("id")
        job_name = job.get("name", "Unknown")
        is_enabled = job.get("enabled", False)
        
        if is_enabled and consecutive_errors >= 5:
            print(f"Circuit Breaker Triggered: Job '{job_name}' (ID: {job_id}) has {consecutive_errors} consecutive errors.")
            disable_res = run_command(f"openclaw cron disable {job_id}")
            if disable_res.returncode == 0:
                print(f"Successfully disabled job '{job_name}'.")
                disabled_count += 1
                # Notify on Telegram (Self Improvement group or dev group)
                msg = f"🔌 *Circuit Breaker Triggered*\nCron job `{job_name}` disabled after {consecutive_errors} consecutive failures. Manual re-enable required."
                run_command(f"openclaw message send --to -1003753060481 --message \"{msg}\"")
            else:
                print(f"Failed to disable job '{job_name}': {disable_res.stderr}")
                
    print(f"Circuit Breaker complete. {disabled_count} jobs disabled.")

if __name__ == "__main__":
    main()
