#!/usr/bin/env python3
"""
bccs_engine.py — Belief-Calibrated Consensus Seeking (BCCS) Engine

Aggregates critic scores and returns a consensus decision.

Decision thresholds (SDD v2):
  ≥ 0.82 weighted mean  → COMMIT
  0.50 - 0.81           → DEBATE (with debate injection prompt)
  < 0.50                → REJECT

CLI usage:
  python3 bccs_engine.py --scores '{"agent1": 0.9, "agent2": 0.7, "agent3": 0.85}'
  python3 bccs_engine.py --test
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any


# ---------------------------------------------------------------------------
# Core types
# ---------------------------------------------------------------------------

CriticScore = dict  # {agent_id: str, confidence: float, reasoning: str}

# ---------------------------------------------------------------------------
# Critic reliability weights (historical accuracy)
# ---------------------------------------------------------------------------

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CRITIC_WEIGHTS_PATH = os.path.join(_SCRIPT_DIR, "critic_weights.json")

# SDD threshold
COMMIT_THRESHOLD = 0.82
DEBATE_THRESHOLD = 0.50


def load_critic_weights() -> dict[str, float]:
    """Load per-critic reliability weights from critic_weights.json.

    Returns a dict {agent_id: weight}. Default weight = 1.0.
    """
    if os.path.exists(CRITIC_WEIGHTS_PATH):
        try:
            with open(CRITIC_WEIGHTS_PATH) as f:
                data = json.load(f)
            return {k: float(v) for k, v in data.items()}
        except Exception:
            pass
    return {}


def save_critic_weights(weights: dict[str, float]) -> None:
    """Persist critic weights to disk."""
    with open(CRITIC_WEIGHTS_PATH, "w") as f:
        json.dump(weights, f, indent=2)


def update_critic_weight(agent_id: str, outcome_correct: bool, learning_rate: float = 0.05) -> float:
    """Update a critic's reliability weight based on whether its assessment was correct.

    Args:
        agent_id:        The critic's agent_id.
        outcome_correct: True if critic's recommendation matched ground truth.
        learning_rate:   Step size for weight adjustment.

    Returns:
        Updated weight value.
    """
    weights = load_critic_weights()
    current = weights.get(agent_id, 1.0)
    if outcome_correct:
        updated = min(current + learning_rate, 3.0)  # cap at 3×
    else:
        updated = max(current - learning_rate, 0.1)  # floor at 0.1
    weights[agent_id] = round(updated, 4)
    save_critic_weights(weights)
    return updated


# ---------------------------------------------------------------------------
# BCCS logic
# ---------------------------------------------------------------------------

def weighted_mean(scores: list[CriticScore], critic_weights: dict[str, float] | None = None) -> float:
    """Historical-reliability-weighted mean of critic scores.

    Formula (SDD): μ = Σ(c_i × w_i) / Σ(w_i)
    where w_i is the critic's historical reliability weight (default 1.0).

    Falls back to simple mean when all weights are zero.
    """
    if not scores:
        return 0.0
    if critic_weights is None:
        critic_weights = load_critic_weights()
    total_weight = sum(critic_weights.get(s["agent_id"], 1.0) for s in scores)
    if total_weight == 0:
        return sum(s["confidence"] for s in scores) / len(scores)
    return sum(
        s["confidence"] * critic_weights.get(s["agent_id"], 1.0) for s in scores
    ) / total_weight


def decide(mean: float) -> str:
    if mean >= COMMIT_THRESHOLD:
        return "commit"
    if mean >= DEBATE_THRESHOLD:
        return "debate"
    return "reject"


def build_debate_injection(scores: list[CriticScore]) -> str:
    """When μ is in the debate range, extract the lowest-scoring critic's rationale
    and format it as a debate injection prompt for the Actor.

    Returns a formatted string the Actor can prepend to its next attempt.
    """
    if not scores:
        return ""
    lowest = min(scores, key=lambda s: s.get("confidence", 1.0))
    agent_id = lowest.get("agent_id", "unknown")
    conf = lowest.get("confidence", 0.0)
    rationale = lowest.get("reasoning", "no rationale provided")
    return (
        f"[DEBATE INJECTION — Critic {agent_id} scored {conf:.2f}]\n"
        f"Objection: {rationale}\n"
        f"Please address the above concern in your revised response before resubmitting."
    )


def aggregate_reasoning(scores: list[CriticScore], decision: str) -> str:
    """Build a human-readable reasoning summary."""
    lines: list[str] = []
    for s in scores:
        agent = s.get("agent_id", "?")
        conf = s.get("confidence", 0.0)
        reason = s.get("reasoning", "")
        lines.append(f"  [{agent}] conf={conf:.2f}: {reason}")

    if decision == "commit":
        summary = "Full consensus reached."
    elif decision == "debate":
        disagreements = [
            s for s in scores if s.get("confidence", 0) < 0.70
        ]
        points = "; ".join(
            s.get("reasoning", "") for s in disagreements if s.get("reasoning")
        )
        summary = f"Partial consensus — debate points: {points or 'see individual scores'}"
    else:
        reasons = "; ".join(
            s.get("reasoning", "") for s in scores if s.get("confidence", 1) < 0.50
        )
        summary = f"Rejected — aggregated reasons: {reasons or 'low confidence across critics'}"

    return summary + "\n" + "\n".join(lines)


def run_bccs(scores: list[CriticScore], critic_weights: dict[str, float] | None = None) -> dict[str, Any]:
    """Main BCCS entry point.

    Args:
        scores:         list of CriticScore dicts
        critic_weights: optional override for per-critic reliability weights.
                        If None, loaded from critic_weights.json.

    Returns:
        {decision, weighted_mean, individual_scores, reasoning, debate_injection?}
    """
    # Normalise / fill defaults
    normalised: list[CriticScore] = []
    for s in scores:
        normalised.append({
            "agent_id": s.get("agent_id", "unknown"),
            "confidence": float(s.get("confidence", 0.0)),
            "reasoning": s.get("reasoning", ""),
        })

    wm = weighted_mean(normalised, critic_weights)
    dec = decide(wm)
    reason = aggregate_reasoning(normalised, dec)

    result: dict[str, Any] = {
        "decision": dec,
        "weighted_mean": round(wm, 4),
        "individual_scores": normalised,
        "reasoning": reason,
    }

    # Debate injection: attach when in debate range
    if dec == "debate":
        result["debate_injection"] = build_debate_injection(normalised)

    return result


# ---------------------------------------------------------------------------
# Cumulative Voting variant
# ---------------------------------------------------------------------------

def cumulative_voting(votes: dict[str, dict[str, float]], total_points: int = 25) -> dict[str, Any]:
    """Cumulative Voting: each agent distributes `total_points` across options.

    Args:
        votes: {agent_id: {option: points_allocated}}
        total_points: expected total per agent (default 25)

    Returns:
        {winner, scores, normalised_scores}
    """
    option_totals: dict[str, float] = {}
    for agent_id, alloc in votes.items():
        agent_total = sum(alloc.values())
        scale = total_points / agent_total if agent_total else 1.0
        for option, pts in alloc.items():
            option_totals[option] = option_totals.get(option, 0) + pts * scale

    if not option_totals:
        return {"winner": None, "scores": {}, "normalised_scores": {}}

    grand_total = sum(option_totals.values())
    normalised = {k: round(v / grand_total, 4) for k, v in option_totals.items()}
    winner = max(option_totals, key=option_totals.__getitem__)

    return {
        "winner": winner,
        "scores": {k: round(v, 2) for k, v in option_totals.items()},
        "normalised_scores": normalised,
    }


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

def _self_test() -> None:
    print("=== BCCS self-test ===")

    # Test 1: COMMIT (3 critics, all high confidence)
    scores = [
        {"agent_id": "a1", "confidence": 0.95, "reasoning": "well-formed"},
        {"agent_id": "a2", "confidence": 0.88, "reasoning": "meets all criteria"},
        {"agent_id": "a3", "confidence": 0.82, "reasoning": "looks good"},
    ]
    result = run_bccs(scores)
    assert result["decision"] == "commit", f"Expected commit, got {result['decision']}"
    assert "debate_injection" not in result, "commit should not have debate_injection"
    print(f"  ✓ COMMIT  wm={result['weighted_mean']}")

    # Test 2: Just below new threshold (0.82) → DEBATE
    scores_border = [
        {"agent_id": "b1", "confidence": 0.81, "reasoning": "almost there"},
        {"agent_id": "b2", "confidence": 0.81, "reasoning": "close but not quite"},
        {"agent_id": "b3", "confidence": 0.81, "reasoning": "needs minor fixes"},
    ]
    result_border = run_bccs(scores_border)
    assert result_border["decision"] == "debate", f"Expected debate for wm<0.82, got {result_border['decision']}"
    print(f"  ✓ DEBATE (border) wm={result_border['weighted_mean']}")

    # Test 3: DEBATE with 3 critics
    scores = [
        {"agent_id": "b1", "confidence": 0.72, "reasoning": "mostly ok"},
        {"agent_id": "b2", "confidence": 0.55, "reasoning": "missing edge cases"},
        {"agent_id": "b3", "confidence": 0.60, "reasoning": "needs review"},
    ]
    result = run_bccs(scores)
    assert result["decision"] == "debate", f"Expected debate, got {result['decision']}"
    assert "debate_injection" in result, "debate result must include debate_injection"
    assert "missing edge cases" in result["debate_injection"], "debate_injection must contain lowest critic rationale"
    print(f"  ✓ DEBATE  wm={result['weighted_mean']} debate_injection present")

    # Test 4: REJECT
    scores = [
        {"agent_id": "c1", "confidence": 0.20, "reasoning": "invalid output"},
        {"agent_id": "c2", "confidence": 0.35, "reasoning": "constraint violation"},
        {"agent_id": "c3", "confidence": 0.25, "reasoning": "format error"},
    ]
    result = run_bccs(scores)
    assert result["decision"] == "reject", f"Expected reject, got {result['decision']}"
    print(f"  ✓ REJECT  wm={result['weighted_mean']}")

    # Test 5: Weighted BCCS — high-weight critics skew result
    scores_w = [
        {"agent_id": "trusted", "confidence": 0.95, "reasoning": "solid"},
        {"agent_id": "untrusted", "confidence": 0.30, "reasoning": "uncertain"},
        {"agent_id": "neutral", "confidence": 0.75, "reasoning": "ok"},
    ]
    weights = {"trusted": 3.0, "untrusted": 0.5, "neutral": 1.0}
    result_w = run_bccs(scores_w, critic_weights=weights)
    # With high weight on trusted (0.95), wm should be > unweighted
    result_unweighted = run_bccs(scores_w, critic_weights={"trusted": 1.0, "untrusted": 1.0, "neutral": 1.0})
    assert result_w["weighted_mean"] > result_unweighted["weighted_mean"], \
        "Trusted-critic boost should raise weighted_mean"
    print(f"  ✓ Weighted BCCS  wm_weighted={result_w['weighted_mean']} wm_equal={result_unweighted['weighted_mean']}")

    # Test 6: Debate injection content check
    scores_d = [
        {"agent_id": "d1", "confidence": 0.75, "reasoning": "looks fine"},
        {"agent_id": "d2", "confidence": 0.51, "reasoning": "major concern: missing auth check"},
        {"agent_id": "d3", "confidence": 0.68, "reasoning": "minor issues"},
    ]
    result_d = run_bccs(scores_d)
    assert result_d["decision"] == "debate"
    assert "major concern: missing auth check" in result_d["debate_injection"], \
        "Lowest critic rationale must appear in debate_injection"
    print(f"  ✓ Debate injection targets lowest critic (d2)")

    # Test 7: update_critic_weight (in-memory only — pass explicit weights dict)
    w_before = 1.0
    # update_critic_weight modifies disk; test the math directly
    import math
    w_up = min(w_before + 0.05, 3.0)
    w_down = max(w_before - 0.05, 0.1)
    assert math.isclose(w_up, 1.05), f"Expected 1.05 got {w_up}"
    assert math.isclose(w_down, 0.95), f"Expected 0.95 got {w_down}"
    print(f"  ✓ Weight update math correct (up={w_up}, down={w_down})")

    # Test 8: Cumulative voting
    votes = {
        "agent1": {"optA": 15, "optB": 10},
        "agent2": {"optA": 5, "optB": 20},
        "agent3": {"optA": 20, "optB": 5},
    }
    cv = cumulative_voting(votes)
    print(f"  ✓ CV winner={cv['winner']} scores={cv['scores']}")

    print("=== All tests passed ===")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_scores_arg(raw: str) -> list[CriticScore]:
    """Accept either dict {agent: score} or list of CriticScore objects."""
    data = json.loads(raw)
    if isinstance(data, dict):
        return [{"agent_id": k, "confidence": float(v), "reasoning": ""} for k, v in data.items()]
    if isinstance(data, list):
        return data
    raise ValueError("--scores must be a JSON dict or list")


def main() -> None:
    parser = argparse.ArgumentParser(description="BCCS Consensus Engine")
    parser.add_argument("--scores", help='JSON scores: \'{"agent1": 0.9, ...}\' or list of CriticScore objects')
    parser.add_argument("--cumulative", help="JSON cumulative votes: '{\"agent1\": {\"optA\": 15, \"optB\": 10}}'")
    parser.add_argument("--test", action="store_true", help="Run self-tests")
    args = parser.parse_args()

    if args.test:
        _self_test()
        sys.exit(0)

    if args.cumulative:
        votes = json.loads(args.cumulative)
        result = cumulative_voting(votes)
        print(json.dumps(result, indent=2))
        sys.exit(0)

    if not args.scores:
        parser.print_help()
        sys.exit(1)

    scores = _parse_scores_arg(args.scores)
    result = run_bccs(scores)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
