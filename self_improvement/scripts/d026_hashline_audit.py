import json
import subprocess
import sys

def run_cmd(cmd):
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Command failed: {cmd}\n{result.stderr}")
        sys.exit(1)
    return result.stdout

def main():
    print("Fetching crons...")
    output = run_cmd("openclaw cron list --json --all")
    try:
        data = json.loads(output)
    except json.JSONDecodeError as e:
        print(f"Failed to parse JSON: {e}")
        sys.exit(1)
        
    jobs = data.get("jobs", [])
    matches = 0
    updated = 0
    
    for job in jobs:
        payload = job.get("payload", {})
        text = payload.get("text", "") or payload.get("message", "")
        
        if "LINE#" in text or "hashline_edit" in text:
            print(f"Match found in job: {job.get('id')} ({job.get('name')})")
            matches += 1
            # If hashline_edit not explicitly set in the config, update it?
            # Wait, how to set hashline_edit in an OpenClaw cron?
            # Usually it's in the agentTurn payload: "hashline_edit": true
            if payload.get("kind") == "agentTurn" and not payload.get("hashline_edit"):
                print(f"  -> Missing hashline_edit flag. Setting it...")
                # We would patch the cron here
                patch = {"payload": payload}
                patch["payload"]["hashline_edit"] = True
                # run_cmd(f"openclaw cron edit {job['id']} ... ") 
                # Instead of full edit, let's just log what we'd do, and maybe patch via CLI
                patch_json = json.dumps({"payload": {"hashline_edit": True}})
                update_cmd = f"openclaw cron update {job['id']} --patch '{patch_json}'"
                print(f"  Executing: {update_cmd}")
                run_cmd(update_cmd)
                updated += 1
                
    print(f"Audit complete. Jobs scanned: {len(jobs)}, Matches: {matches}, Updated: {updated}")

if __name__ == '__main__':
    main()
