#!/usr/bin/env bash
# Worktree-scoped dispatcher for parallel agent runs
# Modeled after oh-my-opencode v3.9.0 worktree pattern.
# Isolates Prometheus/Atlas pipeline into separate worktrees to avoid context collision.

if [ "$#" -lt 2 ]; then
    echo "Usage: $0 <branch-name> <command...>"
    exit 1
fi

BRANCH="$1"
shift
CMD="$@"

WORKTREE_DIR=".worktrees/$BRANCH"
REPO_ROOT=$(git rev-parse --show-toplevel)

if [ -z "$REPO_ROOT" ]; then
    echo "Error: Not in a git repository."
    exit 1
fi

WORKTREE_PATH="$REPO_ROOT/$WORKTREE_DIR"

# Create worktree if it doesn't exist
if [ ! -d "$WORKTREE_PATH" ]; then
    mkdir -p "$REPO_ROOT/.worktrees"
    git worktree add "$WORKTREE_PATH" -b "$BRANCH" || {
        # Fallback if branch already exists
        git worktree add "$WORKTREE_PATH" "$BRANCH" || {
            echo "Failed to create worktree."
            exit 1
        }
    }
fi

echo "Running in worktree: $WORKTREE_PATH"
cd "$WORKTREE_PATH" || exit 1

# Execute command
export WORKTREE_PATH="$WORKTREE_PATH"
eval "$CMD"
EXIT_CODE=$?

cd "$REPO_ROOT" || exit 1

echo "Command finished with exit code $EXIT_CODE"
exit $EXIT_CODE
