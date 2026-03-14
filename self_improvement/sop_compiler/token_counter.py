#!/usr/bin/env python3
"""
Token Counter
Estimates token counts for original Markdown vs compiled XML.
Uses word_count * 1.3 approximation (matches GPT-family tokenizer heuristic).

Usage:
  python3 token_counter.py <file_or_text> [--xml <compiled.xml>]
  python3 token_counter.py --test
"""

import sys
import argparse
from pathlib import Path


def estimate_tokens(text: str) -> int:
    """Estimate token count: words * 1.3."""
    words = len(text.split())
    return int(words * 1.3)


def token_report(orig_text: str, comp_text: str,
                 orig_label: str = "original", comp_label: str = "compiled") -> dict:
    orig_tokens = estimate_tokens(orig_text)
    comp_tokens = estimate_tokens(comp_text)
    orig_chars = len(orig_text)
    comp_chars = len(comp_text)

    token_reduction = (1 - comp_tokens / orig_tokens) * 100 if orig_tokens else 0
    char_reduction = (1 - comp_chars / orig_chars) * 100 if orig_chars else 0

    return {
        "orig_label": orig_label,
        "comp_label": comp_label,
        "orig_tokens": orig_tokens,
        "comp_tokens": comp_tokens,
        "token_reduction_pct": round(token_reduction, 1),
        "orig_chars": orig_chars,
        "comp_chars": comp_chars,
        "char_reduction_pct": round(char_reduction, 1),
    }


def print_report(r: dict) -> None:
    w = 40
    print(f"{'─' * w}")
    print(f"  Token Count Comparison")
    print(f"{'─' * w}")
    print(f"  {'File':<20} {'Tokens':>8}  {'Chars':>8}")
    print(f"  {'─'*20} {'─'*8}  {'─'*8}")
    print(f"  {r['orig_label']:<20} {r['orig_tokens']:>8,}  {r['orig_chars']:>8,}")
    print(f"  {r['comp_label']:<20} {r['comp_tokens']:>8,}  {r['comp_chars']:>8,}")
    print(f"{'─' * w}")
    print(f"  Token reduction : {r['token_reduction_pct']:>5.1f}%")
    print(f"  Char reduction  : {r['char_reduction_pct']:>5.1f}%")
    print(f"{'─' * w}")
    # Rating
    pct = r['token_reduction_pct']
    if pct >= 50:
        rating = "🟢 Excellent (≥50%)"
    elif pct >= 40:
        rating = "🟡 Good (40-50%)"
    elif pct >= 20:
        rating = "🟠 Moderate (20-40%)"
    else:
        rating = "🔴 Low (<20%)"
    print(f"  Rating          : {rating}")
    print(f"{'─' * w}")


def run_tests() -> None:
    print("Running token_counter self-tests...")

    verbose = """
    ## Section 1: Introduction
    This section provides an overview of the system and its capabilities.
    It is important to read this carefully before proceeding with any configuration.
    
    - Do not skip any steps in the process outlined below.
    - Always verify your environment before running any commands.
    - Make sure to backup all data before making changes to the system.
    - Report any issues to the system administrator immediately.
    - Never store credentials in plain text files on the filesystem.
    """ * 5  # repeat to get reasonable size

    compact = """
    <state id="intro">
      <constraint>NO skip steps</constraint>
      <constraint>ALWAYS verify env before commands</constraint>
      <constraint>ALWAYS backup data before changes</constraint>
      <action>Report issues to admin immediately</action>
      <constraint>NEVER store credentials in plaintext</constraint>
    </state>
    """ * 5

    r = token_report(verbose, compact, "verbose.md", "compact.xml")

    assert r["orig_tokens"] > r["comp_tokens"], "Compact should have fewer tokens"
    print("  ✓ Compact has fewer tokens")

    assert 0 < r["token_reduction_pct"] <= 100, "Reduction should be 0-100%"
    print(f"  ✓ Token reduction: {r['token_reduction_pct']}%")

    # Test estimate_tokens
    assert estimate_tokens("hello world") == int(2 * 1.3), "2 words → int(2.6)=2"
    print("  ✓ Token estimation formula")

    print_report(r)
    print("All tests passed.")


def main():
    parser = argparse.ArgumentParser(description="Token Counter for SOP compiler")
    parser.add_argument("--test", action="store_true", help="Run self-tests")
    parser.add_argument("input", nargs="?", help="Original file (.md)")
    parser.add_argument("--xml", "--compiled", dest="compiled",
                        help="Compiled XML file to compare against")
    parser.add_argument("--text", help="Raw text to count (instead of file)")

    args = parser.parse_args()

    if args.test:
        run_tests()
        return

    if args.text:
        tokens = estimate_tokens(args.text)
        print(f"Tokens (est): {tokens:,}  |  Chars: {len(args.text):,}")
        return

    if not args.input:
        parser.print_help()
        sys.exit(1)

    orig_path = Path(args.input)
    if not orig_path.exists():
        print(f"ERROR: {orig_path} not found", file=sys.stderr)
        sys.exit(1)

    orig_text = orig_path.read_text(encoding="utf-8")

    if args.compiled:
        comp_path = Path(args.compiled)
        if not comp_path.exists():
            print(f"ERROR: {comp_path} not found", file=sys.stderr)
            sys.exit(1)
        comp_text = comp_path.read_text(encoding="utf-8")
        r = token_report(orig_text, comp_text, orig_path.name, comp_path.name)
        print_report(r)
    else:
        # Just report count for single file
        tokens = estimate_tokens(orig_text)
        chars = len(orig_text)
        words = len(orig_text.split())
        print(f"File   : {orig_path}")
        print(f"Words  : {words:,}")
        print(f"Tokens : {tokens:,}  (words × 1.3)")
        print(f"Chars  : {chars:,}")


if __name__ == "__main__":
    main()
