#!/usr/bin/env python3
"""
Critic Weight Trainer
Integrates with BCCS engine critic_weights.json to perform online weight updates
based on decision outcomes.
"""
import sys
import json
import os
import argparse
from datetime import datetime, date
from pathlib import Path

BASE_DIR = Path(__file__).parent
CONSENSUS_DIR = BASE_DIR.parent / "consensus"
WEIGHTS_FILE = CONSENSUS_DIR / "critic_weights.json"
LOGS_DIR = BASE_DIR / "logs"

WEIGHT_CAP = 2.0
WEIGHT_FLOOR = 0.5
AGREE_FACTOR = 1.05
DISAGREE_FACTOR = 0.95


def load_weights() -> dict:
    if WEIGHTS_FILE.exists():
        with open(WEIGHTS_FILE) as f:
            return json.load(f)
    return {}


def save_weights(weights: dict):
    WEIGHTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(WEIGHTS_FILE, "w") as f:
        json.dump(weights, f, indent=2)


def log_training(record: dict):
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOGS_DIR / f"critic_training-{date.today().isoformat()}.jsonl"
    with open(log_file, "a") as f:
        f.write(json.dumps(record) + "\n")


def train(decision: str, outcome: str, critics_input: dict) -> dict:
    """
    Update critic weights based on outcome.
    decision: the BCCS decision made (e.g. 'commit', 'reject')
    outcome: 'success' or 'failure'
    critics_input: {critic_id: confidence_score} — their vote/confidence
    Returns updated weights dict.
    """
    weights = load_weights()
    updates = {}

    # Determine which critics were "correct":
    # A critic with confidence > 0.5 implicitly supported the decision.
    # success + supported => agreed correctly => boost
    # success + opposed  => agreed incorrectly => penalize
    # failure + supported => agreed with wrong decision => penalize
    # failure + opposed  => correctly skeptical => boost
    outcome_success = outcome.lower() == "success"

    for critic_id, confidence in critics_input.items():
        supported = float(confidence) >= 0.5
        correct = (outcome_success and supported) or (not outcome_success and not supported)

        current_weight = weights.get(critic_id, 1.0)
        if correct:
            new_weight = min(current_weight * AGREE_FACTOR, WEIGHT_CAP)
        else:
            new_weight = max(current_weight * DISAGREE_FACTOR, WEIGHT_FLOOR)

        weights[critic_id] = round(new_weight, 6)
        updates[critic_id] = {
            "old": round(current_weight, 6),
            "new": round(new_weight, 6),
            "correct": correct
        }

    save_weights(weights)

    record = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "decision": decision,
        "outcome": outcome,
        "critics_input": critics_input,
        "updates": updates
    }
    log_training(record)

    return {"weights": weights, "updates": updates}


def report() -> dict:
    """Show current weights and basic accuracy stats from today's log."""
    weights = load_weights()
    stats = {"total": 0, "correct": 0, "by_critic": {}}

    # Aggregate from all log files
    if LOGS_DIR.exists():
        for log_file in sorted(LOGS_DIR.glob("critic_training-*.jsonl")):
            with open(log_file) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        rec = json.loads(line)
                        for cid, upd in rec.get("updates", {}).items():
                            if cid not in stats["by_critic"]:
                                stats["by_critic"][cid] = {"total": 0, "correct": 0}
                            stats["by_critic"][cid]["total"] += 1
                            stats["total"] += 1
                            if upd.get("correct"):
                                stats["by_critic"][cid]["correct"] += 1
                                stats["correct"] += 1
                    except json.JSONDecodeError:
                        pass

    # Compute accuracy per critic
    for cid, s in stats["by_critic"].items():
        s["accuracy"] = round(s["correct"] / s["total"], 3) if s["total"] else 0.0

    global_acc = round(stats["correct"] / stats["total"], 3) if stats["total"] else 0.0

    return {
        "current_weights": weights,
        "global_accuracy": global_acc,
        "total_decisions": stats["total"],
        "by_critic": stats["by_critic"]
    }


def run_tests():
    import tempfile, shutil
    print("Running critic_weight_trainer tests...")
    passed = 0
    failed = 0

    # Redirect paths to temp dir
    tmp = Path(tempfile.mkdtemp())
    orig_weights = WEIGHTS_FILE
    orig_logs = LOGS_DIR

    import critic_weight_trainer as cwt
    cwt.WEIGHTS_FILE = tmp / "critic_weights.json"
    cwt.LOGS_DIR = tmp / "logs"

    def check(name, cond, detail=""):
        nonlocal passed, failed
        status = "PASS" if cond else "FAIL"
        print(f"  [{status}] {name}" + (f": {detail}" if detail else ""))
        if cond:
            passed += 1
        else:
            failed += 1

    # Test 1: train success — supporter gets boosted
    critics = {"c1": 0.9, "c2": 0.3}
    result = cwt.train("commit", "success", critics)
    check("Supporter boosted on success",
          result["updates"]["c1"]["new"] > 1.0,
          result["updates"])
    check("Opposer penalized on success",
          result["updates"]["c2"]["new"] < 1.0,
          result["updates"])

    # Test 2: train failure — supporter penalized
    cwt.WEIGHTS_FILE = tmp / "critic_weights2.json"
    result2 = cwt.train("commit", "failure", {"c1": 0.9, "c2": 0.2})
    check("Supporter penalized on failure", result2["updates"]["c1"]["correct"] == False)
    check("Opposer rewarded on failure", result2["updates"]["c2"]["correct"] == True)

    # Test 3: Weight cap
    cwt.WEIGHTS_FILE = tmp / "critic_weights3.json"
    # Manually set a high weight
    cwt.save_weights({"c1": 1.95})
    r3 = cwt.train("commit", "success", {"c1": 0.9})
    check("Weight cap at 2.0", r3["weights"]["c1"] <= 2.0)

    # Test 4: Weight floor
    cwt.save_weights({"c1": 0.52})
    r4 = cwt.train("commit", "success", {"c1": 0.2})
    check("Weight floor at 0.5", r4["weights"]["c1"] >= 0.5)

    # Test 5: report
    cwt.LOGS_DIR = tmp / "logs"
    cwt.WEIGHTS_FILE = tmp / "critic_weights.json"
    rep = cwt.report()
    check("Report returns current_weights key", "current_weights" in rep)
    check("Report returns global_accuracy", "global_accuracy" in rep)

    # Restore
    cwt.WEIGHTS_FILE = orig_weights
    cwt.LOGS_DIR = orig_logs
    shutil.rmtree(tmp)

    print(f"\nResults: {passed} passed, {failed} failed")
    return failed == 0


def main():
    parser = argparse.ArgumentParser(description="Critic Weight Trainer")
    sub = parser.add_subparsers(dest="cmd")

    train_p = sub.add_parser("train")
    train_p.add_argument("--decision", required=True)
    train_p.add_argument("--outcome", required=True, choices=["success", "failure"])
    train_p.add_argument("--critics", required=True, help='JSON: {"c1": 0.9, ...}')

    sub.add_parser("report")
    parser.add_argument("--test", action="store_true")

    args = parser.parse_args()

    if args.test:
        success = run_tests()
        sys.exit(0 if success else 1)

    if args.cmd == "train":
        try:
            critics = json.loads(args.critics)
        except json.JSONDecodeError as e:
            print(f"Error parsing --critics JSON: {e}", file=sys.stderr)
            sys.exit(1)
        result = train(args.decision, args.outcome, critics)
        print(json.dumps(result, indent=2))

    elif args.cmd == "report":
        result = report()
        print(json.dumps(result, indent=2))

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
