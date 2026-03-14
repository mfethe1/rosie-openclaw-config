


from pathlib import Path

# --- Cost-Waste Detection (added 2026-02-20) ---
def detect_cost_waste():
    """Flag crons with high cost-per-outcome ratio."""
    cost_db = Path("self_improvement/cost_tracker.jsonl")
    if not cost_db.exists():
        return []
    
    from collections import defaultdict
    import json
    
    cron_costs = defaultdict(lambda: {"total_cost": 0.0, "runs": 0, "models": set()})
    
    with open(cost_db) as f:
        for line in f:
            entry = json.loads(line)
            cron_id = entry.get("cron_id", "unknown")
            cost = entry.get("estimated_cost_usd", 0.0)
            model = entry.get("model", "unknown")
            
            cron_costs[cron_id]["total_cost"] += cost
            cron_costs[cron_id]["runs"] += 1
            cron_costs[cron_id]["models"].add(model)
    
    waste_flags = []
    for cron_id, data in cron_costs.items():
        cost_per_run = data["total_cost"] / max(data["runs"], 1)
        
        # Flag if: (a) >$0.50/run OR (b) using opus-4-6 for >10 runs without documented justification
        if cost_per_run > 0.50:
            waste_flags.append(f"COST-WASTE: {cron_id} averaging ${cost_per_run:.2f}/run over {data['runs']} runs — consider model downgrade")
        elif "anthropic/claude-opus-4-6" in data["models"] and data["runs"] > 10:
            waste_flags.append(f"COST-WATCH: {cron_id} using opus-4-6 for {data['runs']} runs (${data['total_cost']:.2f} total) — verify complexity justifies premium model")
    
    return waste_flags

# Hook into main scan
if __name__ == "__main__":
    # ... existing scan logic ...
    waste = detect_cost_waste()
    if waste:
        print("\n=== COST WASTE ALERTS ===")
        for w in waste:
            print(f"  ⚠ {w}")

