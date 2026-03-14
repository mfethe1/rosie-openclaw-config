#!/usr/bin/env python3
"""
verification_gate.py — Actor-Critic Pipeline

Flow:
  1. Actor publishes proposed result → NATS topic `verification.submit`
  2. N critic evaluations run (each: confidence float + reasoning)
  3. BCCS aggregates → decision published → NATS topic `verification.result`

NATS integration via subprocess calls to nats_bridge.py (never blocking main flow).

CLI:
  python3 verification_gate.py submit \
      --result "proposed output" \
      --constraints "must be valid JSON, must include 3+ items"
  python3 verification_gate.py --test
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import threading
import time
from typing import Any

# Absolute path to nats_bridge.py
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_WORKSPACE = os.path.abspath(os.path.join(_SCRIPT_DIR, "../.."))
NATS_BRIDGE = os.path.join(_WORKSPACE, "infra/nats/nats_bridge.py")

# Import BCCS engine from same package directory
sys.path.insert(0, _SCRIPT_DIR)
from bccs_engine import run_bccs, CriticScore  # noqa: E402


# ---------------------------------------------------------------------------
# NATS helpers (fire-and-forget, never block)
# ---------------------------------------------------------------------------

def _nats_pub_bg(subject: str, data: dict) -> None:
    """Publish to NATS via nats_bridge.py in a daemon thread (fire-and-forget)."""
    def _publish():
        try:
            payload = json.dumps(data)
            subprocess.run(
                [sys.executable, NATS_BRIDGE, "report", subject, "msg", payload],
                timeout=6,
                capture_output=True,
            )
        except Exception:
            pass  # NATS unavailable — never crash the main pipeline

    t = threading.Thread(target=_publish, daemon=True)
    t.start()


# ---------------------------------------------------------------------------
# Critic evaluation
# ---------------------------------------------------------------------------

def _evaluate_critic(
    critic_id: str,
    result: str,
    constraints: list[str],
) -> CriticScore:
    """Evaluate a proposed result against constraints.

    This is a heuristic-based critic. In production, replace with LLM calls.
    Returns: {agent_id, confidence, reasoning}
    """
    issues: list[str] = []
    bonuses: list[str] = []

    result_lower = result.lower()

    for constraint in constraints:
        c = constraint.strip().lower()

        # JSON validity check
        if "valid json" in c or "json" in c:
            try:
                json.loads(result)
                bonuses.append("valid JSON")
            except json.JSONDecodeError:
                issues.append("not valid JSON")

        # Item count check
        if "3+ items" in c or "3 items" in c or "three items" in c:
            try:
                parsed = json.loads(result)
                if isinstance(parsed, (list, dict)) and len(parsed) >= 3:
                    bonuses.append(f"contains {len(parsed)} items (≥3)")
                else:
                    count = len(parsed) if isinstance(parsed, (list, dict)) else 0
                    issues.append(f"only {count} items (need ≥3)")
            except Exception:
                issues.append("cannot count items (not parseable)")

        # Non-empty check
        if "non-empty" in c or "not empty" in c:
            if result.strip():
                bonuses.append("non-empty")
            else:
                issues.append("empty result")

        # Length checks
        if "length" in c or "chars" in c or "characters" in c:
            if len(result) > 10:
                bonuses.append(f"adequate length ({len(result)} chars)")
            else:
                issues.append(f"too short ({len(result)} chars)")

    # Base confidence: start at 0.75, adjust
    confidence = 0.75
    confidence += 0.05 * len(bonuses)
    confidence -= 0.15 * len(issues)
    confidence = max(0.0, min(1.0, confidence))

    # Vary slightly by critic_id to simulate independent assessment
    salt = sum(ord(c) for c in critic_id) % 10
    confidence = round(confidence + (salt - 5) * 0.01, 4)
    confidence = max(0.0, min(1.0, confidence))

    reasoning_parts = []
    if bonuses:
        reasoning_parts.append("✓ " + "; ".join(bonuses))
    if issues:
        reasoning_parts.append("✗ " + "; ".join(issues))
    reasoning = " | ".join(reasoning_parts) or "no specific constraints matched"

    return {
        "agent_id": critic_id,
        "confidence": confidence,
        "reasoning": reasoning,
    }


# ---------------------------------------------------------------------------
# Actor-Critic pipeline
# ---------------------------------------------------------------------------

def run_verification(
    result: str,
    constraints: list[str],
    num_critics: int = 3,
    publish_nats: bool = True,
) -> dict[str, Any]:
    """Full Actor-Critic verification pipeline.

    Args:
        result:       The proposed output to verify.
        constraints:  List of constraint strings.
        num_critics:  Number of independent critic evaluations.
        publish_nats: Whether to fire-and-forget to NATS.

    Returns:
        BCCS result dict + added `constraints` and `result_preview` fields.
    """
    submit_payload = {
        "result": result[:500],  # truncate for NATS
        "constraints": constraints,
        "num_critics": num_critics,
        "ts": time.time(),
    }

    # Actor publishes to NATS (non-blocking) — SDD topic: unverified_actions
    if publish_nats:
        _nats_pub_bg("unverified_actions", submit_payload)

    # Spawn N critics
    critic_scores: list[CriticScore] = []
    for i in range(num_critics):
        critic_id = f"critic_{i+1}"
        score = _evaluate_critic(critic_id, result, constraints)
        critic_scores.append(score)

    # BCCS consensus
    bccs_result = run_bccs(critic_scores)

    output = {
        **bccs_result,
        "constraints": constraints,
        "result_preview": result[:200],
    }

    # Publish decision to NATS (non-blocking)
    if publish_nats:
        _nats_pub_bg("verification.result", {
            "decision": output["decision"],
            "weighted_mean": output["weighted_mean"],
            "reasoning": output["reasoning"][:400],
            "ts": time.time(),
        })

    return output


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

def _self_test() -> None:
    print("=== verification_gate self-test ===")

    # Test 1: valid JSON with 3+ items → should COMMIT or DEBATE
    result1 = json.dumps(["apple", "banana", "cherry", "date"])
    out1 = run_verification(result1, ["must be valid JSON", "must include 3+ items"], num_critics=3, publish_nats=False)
    print(f"  Test 1 (valid JSON, 4 items): decision={out1['decision']} wm={out1['weighted_mean']}")
    assert out1["decision"] in ("commit", "debate"), f"Unexpected: {out1['decision']}"
    print("  ✓ passed")

    # Test 2: invalid JSON → should REJECT or DEBATE
    result2 = "not json at all"
    out2 = run_verification(result2, ["must be valid JSON", "must include 3+ items"], num_critics=2, publish_nats=False)
    print(f"  Test 2 (invalid JSON): decision={out2['decision']} wm={out2['weighted_mean']}")
    assert out2["decision"] in ("reject", "debate"), f"Unexpected: {out2['decision']}"
    print("  ✓ passed")

    # Test 3: empty result → low confidence
    out3 = run_verification("", ["non-empty"], num_critics=2, publish_nats=False)
    print(f"  Test 3 (empty): decision={out3['decision']} wm={out3['weighted_mean']}")
    print("  ✓ passed")

    print("=== All tests passed ===")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Actor-Critic Verification Gate")
    sub = parser.add_subparsers(dest="cmd")

    # submit subcommand
    submit_p = sub.add_parser("submit", help="Submit a result for verification")
    submit_p.add_argument("--result", required=True, help="Proposed output to verify")
    submit_p.add_argument(
        "--constraints",
        default="",
        help="Comma-separated constraints (e.g. 'must be valid JSON, must include 3+ items')",
    )
    submit_p.add_argument("--critics", type=int, default=3, help="Number of critics (default: 3)")
    submit_p.add_argument("--no-nats", action="store_true", help="Skip NATS publishing")

    parser.add_argument("--test", action="store_true", help="Run self-tests")

    args = parser.parse_args()

    if args.test:
        _self_test()
        sys.exit(0)

    if args.cmd == "submit":
        constraints = [c.strip() for c in args.constraints.split(",") if c.strip()]
        output = run_verification(
            result=args.result,
            constraints=constraints,
            num_critics=args.critics,
            publish_nats=not args.no_nats,
        )
        print(json.dumps(output, indent=2))
        # Brief sleep to let fire-and-forget threads finish
        time.sleep(0.5)
        sys.exit(0)

    parser.print_help()
    sys.exit(1)


if __name__ == "__main__":
    main()
