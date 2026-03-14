"""
consensus — Actor-Critic verification package.

Quick start:
    from self_improvement.consensus import verify_output

    result = verify_output(
        result='["a", "b", "c"]',
        constraints=["must be valid JSON", "must include 3+ items"],
        num_critics=2,
    )
    print(result)  # {decision: "commit", confidence: 0.88}
"""

from __future__ import annotations

import sys
import os

# Make package-relative imports work when called from any CWD
_PKG_DIR = os.path.dirname(os.path.abspath(__file__))
if _PKG_DIR not in sys.path:
    sys.path.insert(0, _PKG_DIR)

from bccs_engine import run_bccs, cumulative_voting  # noqa: F401
from verification_gate import run_verification  # noqa: F401


def verify_output(
    result: str,
    constraints: str | list[str],
    num_critics: int = 2,
    publish_nats: bool = True,
) -> dict:
    """Verify a proposed output against constraints using the Actor-Critic pipeline.

    Args:
        result:       The proposed output string to verify.
        constraints:  Either a list of constraint strings or a comma-separated string.
        num_critics:  Number of independent critic evaluations (default: 2).
        publish_nats: Publish events to NATS (fire-and-forget, default: True).

    Returns:
        dict with keys:
            decision    — "commit" | "debate" | "reject"
            confidence  — weighted mean confidence (0.0-1.0)
            reasoning   — human-readable reasoning string
            individual_scores — list of per-critic scores
    """
    if isinstance(constraints, str):
        constraints = [c.strip() for c in constraints.split(",") if c.strip()]

    raw = run_verification(
        result=result,
        constraints=constraints,
        num_critics=num_critics,
        publish_nats=publish_nats,
    )

    return {
        "decision": raw["decision"],
        "confidence": raw["weighted_mean"],
        "reasoning": raw["reasoning"],
        "individual_scores": raw["individual_scores"],
    }


__all__ = [
    "verify_output",
    "run_bccs",
    "run_verification",
    "cumulative_voting",
]
