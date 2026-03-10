# Hashline-Edit Benchmark Suite Specification

## Objective
Scope and define a 46-test benchmark suite to validate the hashline-edit path.
Focus: deduplication validation, diff context limits, edge cases, and safety.

## Test Categories

1. **Basic Replacement (5 tests)**
   - Single line match and replace.
   - Multi-line match and replace.
   - Whitespace insensitivity checks.
   - Exact whitespace match requirements.
   - Empty file insertion.

2. **Deduplication Validation (10 tests)**
   - Multiple identical blocks in file (target first).
   - Multiple identical blocks in file (target last).
   - Target middle occurrence of identical blocks.
   - Deduplication with overlapping context.
   - Deduplication failure case (ambiguous match without context).

3. **Diff Context Limits (10 tests)**
   - Context too small (rejects).
   - Context perfectly sized (accepts).
   - Context too large (exceeds limit, truncates or rejects).
   - Asymmetric context (more before than after).
   - Asymmetric context (more after than before).

4. **Edge Cases & Safety (21 tests)**
   - Missing file.
   - File permissions (read-only).
   - Very large files (performance/timeout).
   - Encoding issues (UTF-8 with BOM, Latin-1).
   - Line ending variations (CRLF vs LF).
   - Replacing entire file contents.
   - Regular expression special characters in target text (ensuring literal match).
   - Malformed hash/ID.
   - Concurrent edits (lock testing).
   - ...and 12 more edge cases involving binary files, symlinks, and network storage.

## Implementation Plan
- **Phase 1:** Implement test runner using `pytest`.
- **Phase 2:** Implement Categories 1 & 2.
- **Phase 3:** Implement Categories 3 & 4.
- **Phase 4:** CI integration and gating.