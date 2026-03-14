#!/usr/bin/env python3
"""promem_prompts.py — ProMem Prompt Templates (D-017 follow-on, Winnie cycle #10).

Three-phase prompt template library for LLM-powered ProMem extraction
to complement the regex-heuristic baseline in knowledge_extractor.py.

Usage:
    from promem_prompts import P_EXTRACT, P_QUESTION, P_VERIFY
    from promem_prompts import extract_facts, verify_fact

    facts = extract_facts(transcript_text, use_llm=True)
    verified = [f for f in facts if verify_fact(f, transcript_text)]

Reference: arXiv:2601.04463 "Beyond Static Summarization: Proactive Memory Extraction"
           Yang et al., Nanjing University, Jan 2026
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

# ---------------------------------------------------------------------------
# Phase 1 — P_EXTRACT
# Initial extraction: pull candidate memory-worthy facts from a cycle output.
# ---------------------------------------------------------------------------
P_EXTRACT = """\
You are a memory extraction agent reviewing an AI agent's work log.
Your job: extract up to 15 concise, self-contained memory items that
would help future agents avoid mistakes, re-use decisions, or recall
important context.

RULES:
- Each item MUST be a single sentence (≤120 chars).
- Prefer concrete, verifiable facts over vague observations.
- Include: decisions adopted/skipped, bugs fixed, benchmarks, constraints,
  file paths created, and command patterns that worked.
- EXCLUDE: progress updates, tentative plans, and meta-commentary.
- Output ONLY valid JSON: {"facts": ["fact 1", "fact 2", ...]}

SOURCE LOG:
---
{transcript}
---

Respond with JSON only. No preamble or explanation."""

# ---------------------------------------------------------------------------
# Phase 2 — P_QUESTION
# Self-question generation: for each candidate fact, produce a verification
# question that can be answered directly from the source transcript.
# ---------------------------------------------------------------------------
P_QUESTION = """\
You are a rigorous fact-checker.
Given a candidate memory item, write ONE concise yes/no or fill-in-the-blank
question that — if answered correctly from the source — would confirm the
item is accurate.

RULES:
- The question must be answerable from the source document alone.
- It should challenge a specific, falsifiable detail (number, path, status).
- Output ONLY valid JSON: {"question": "...", "expected_answer_hint": "..."}

CANDIDATE FACT:
{fact}

Respond with JSON only."""

# ---------------------------------------------------------------------------
# Phase 3 — P_VERIFY
# Verification: given a question and source, check if evidence exists.
# Returns confidence 0.0-1.0 and the supporting snippet.
# ---------------------------------------------------------------------------
P_VERIFY = """\
You are a transcript evidence verifier.
Given a question and a source document, determine whether the source
contains clear evidence to answer the question correctly.

RULES:
- Return confidence between 0.0 (no evidence) and 1.0 (direct quote match).
- Extract the exact supporting snippet (≤80 chars).
- If no evidence, return confidence 0.0 and snippet null.
- Output ONLY valid JSON:
  {"confidence": 0.0-1.0, "snippet": "...", "verdict": "PASS"|"FAIL"}

THRESHOLD: confidence ≥ 0.7 → PASS; below 0.7 → FAIL (discard fact).

QUESTION:
{question}

SOURCE:
---
{transcript}
---

Respond with JSON only."""


# ---------------------------------------------------------------------------
# Lightweight integration helpers (no external LLM dependency required
# in the default path — uses the regex extractor as fallback)
# ---------------------------------------------------------------------------

def _regex_extract(text: str) -> list[str]:
    """Regex-based extraction (fallback when LLM unavailable)."""
    patterns = [
        re.compile(r"(?i)(DECISION|ADOPT|SKIP|RESOLVED|DONE|→|✅|⚠️|🔴|🟠).*:.{20,}"),
        re.compile(r"(?i)(implemented|shipped|fixed|added|created|deployed)\s+.{15,}"),
        re.compile(r"(?i)(key (lesson|finding|constraint|rule|note)|critical|important):\s*.{20,}"),
    ]
    results: list[str] = []
    seen: set[str] = set()
    for line in text.splitlines():
        line = line.strip()
        if len(line) < 30 or len(line) > 400:
            continue
        for pat in patterns:
            if pat.search(line):
                key = line[:80].lower()
                if key not in seen:
                    seen.add(key)
                    results.append(line[:200])
                break
    return results


def _regex_verify(fact: str, source: str) -> float:
    """Heuristic verification: word-overlap ratio (Phase 2/3 fallback)."""
    words = [w for w in re.split(r"\W+", fact.lower()) if len(w) > 3]
    if not words:
        return 0.0
    matches = sum(1 for w in words if w in source.lower())
    return matches / len(words)


def extract_facts(
    transcript: str,
    use_llm: bool = False,
    llm_fn: "callable | None" = None,
) -> list[dict]:
    """Phase 1: extract candidate facts from a transcript.

    Args:
        transcript: Raw text of an agent cycle output.
        use_llm: If True, call llm_fn with P_EXTRACT prompt.
        llm_fn: Callable(prompt: str) -> str. Required when use_llm=True.

    Returns:
        List of dicts: {"body": str, "topic": str, "source": "extracted"}
    """
    if use_llm and llm_fn is not None:
        prompt = P_EXTRACT.format(transcript=transcript[:6000])
        try:
            raw = llm_fn(prompt)
            data = json.loads(raw)
            facts = data.get("facts", [])
        except (json.JSONDecodeError, KeyError, TypeError):
            facts = _regex_extract(transcript)
    else:
        facts = _regex_extract(transcript)

    return [
        {
            "body": f[:200],
            "topic": re.sub(r"[*_`#→✅⚠️🔴🟠\[\]]", "", f)[:60].strip(" :-"),
            "source": "extracted",
        }
        for f in facts
    ]


def generate_question(
    fact: str,
    use_llm: bool = False,
    llm_fn: "callable | None" = None,
) -> str:
    """Phase 2: generate a verification question for a fact."""
    if use_llm and llm_fn is not None:
        prompt = P_QUESTION.format(fact=fact)
        try:
            raw = llm_fn(prompt)
            data = json.loads(raw)
            return data.get("question", fact)
        except (json.JSONDecodeError, KeyError, TypeError):
            pass
    # Fallback: strip to key noun phrase as yes/no question
    return f"Does the source confirm: '{fact[:80]}'?"


def verify_fact(
    fact: str,
    source: str,
    question: str | None = None,
    use_llm: bool = False,
    llm_fn: "callable | None" = None,
    threshold: float = 0.6,
) -> tuple[bool, float]:
    """Phase 3: verify a fact against its source, return (passed, confidence).

    Args:
        fact: The candidate memory item body.
        source: Original transcript text.
        question: Optional pre-generated verification question.
        use_llm: If True, call llm_fn with P_VERIFY prompt.
        llm_fn: Callable(prompt: str) -> str.
        threshold: Min confidence to consider PASS (default 0.6).

    Returns:
        Tuple[bool, float]: (passed, confidence_score)
    """
    if use_llm and llm_fn is not None and question is not None:
        prompt = P_VERIFY.format(question=question, transcript=source[:6000])
        try:
            raw = llm_fn(prompt)
            data = json.loads(raw)
            confidence = float(data.get("confidence", 0.0))
            return confidence >= threshold, confidence
        except (json.JSONDecodeError, KeyError, TypeError, ValueError):
            pass
    # Regex fallback
    score = _regex_verify(fact, source)
    return score >= threshold, round(score, 3)


def run_promem_pipeline(
    transcript: str,
    use_llm: bool = False,
    llm_fn: "callable | None" = None,
    threshold: float = 0.6,
) -> list[dict]:
    """Full three-phase ProMem pipeline on one transcript.

    Returns list of verified facts with provenance_score.
    """
    facts = extract_facts(transcript, use_llm=use_llm, llm_fn=llm_fn)
    verified: list[dict] = []
    for f in facts:
        q = generate_question(f["body"], use_llm=use_llm, llm_fn=llm_fn)
        passed, score = verify_fact(
            f["body"], transcript, question=q,
            use_llm=use_llm, llm_fn=llm_fn,
            threshold=threshold
        )
        if passed:
            f["provenance_score"] = score
            f["question"] = q
            verified.append(f)
    return verified


if __name__ == "__main__":
    # Quick self-test on a small sample
    import sys
    sample = """
    DECISION: ADOPT sentence-transformers/all-MiniLM-L6-v2 as Phase 2 embedding model.
    Benchmark: 8.67ms avg latency, 384-dim vectors, $0/call (local), privacy-safe.
    SKIP: OpenAI text-embedding-3-small (network dependency, privacy risk).
    Fixed B-008: memU server start.sh now has PID-file + health-check restart logic.
    Key constraint: sqlite-vec requires Python 3.13 (Homebrew), NOT system Python 3.9.6.
    """
    results = run_promem_pipeline(sample, use_llm=False, threshold=0.5)
    print(f"Verified {len(results)} fact(s):")
    for r in results:
        print(f"  [{r['provenance_score']:.2f}] {r['body'][:100]}")
    print("Self-test PASSED" if results else "Self-test: no facts extracted (check patterns)")
