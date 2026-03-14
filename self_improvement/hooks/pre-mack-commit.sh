#!/bin/bash
# Pre-commit hook: validate Mack CHANGELOG entries have required quality fields.
# Install: ln -sf $(pwd)/self_improvement/hooks/pre-mack-commit.sh .git/hooks/pre-commit

set -e

if git diff --cached --name-only | grep -q 'self_improvement.*mack\.md'; then
    staged_file=$(git diff --cached --name-only | grep 'self_improvement.*mack\.md' | head -1)
    echo "[PRE-COMMIT] Validating Mack quality gates in $staged_file..."
    
    # Check for required fields in staged changes
    if ! git diff --cached "$staged_file" | grep -q '**Test command:**'; then
        echo "ERROR: Missing '**Test command:**' section"
        exit 1
    fi
    if ! git diff --cached "$staged_file" | grep -q '**Expected output:**'; then
        echo "ERROR: Missing '**Expected output:**' section"
        exit 1
    fi
    if ! git diff --cached "$staged_file" | grep -q '**Cleanup/rollback'; then
        echo "ERROR: Missing '**Cleanup/rollback if regressing:**' section"
        exit 1
    fi
    echo "[PRE-COMMIT] ✓ Quality gates passed"
fi
