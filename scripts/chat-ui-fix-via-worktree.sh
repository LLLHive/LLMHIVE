#!/usr/bin/env bash
# =============================================================================
# Apply the chat UI patch in a *separate directory* (git worktree).
# Your main LLMHIVE folder: same branch, same dirty/clean state, same files as
# before — nothing is switched and nothing is stashed there.
#
# Usage (from repo root or anywhere):
#   ./scripts/chat-ui-fix-via-worktree.sh
#   ./scripts/chat-ui-fix-via-worktree.sh --commit
#
# Optional: CHAT_UI_WORKTREE_PARENT=/path/to/parent  (default: parent of repo)
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PATCH_FILE="$SCRIPT_DIR/patches/chat-ui-scroll-layout.patch"
DO_COMMIT=false

for arg in "$@"; do
  case "$arg" in
    --commit) DO_COMMIT=true ;;
    -h|--help) sed -n '1,22p' "$0"; exit 0 ;;
  esac
done

PARENT="${CHAT_UI_WORKTREE_PARENT:-$(dirname "$REPO_ROOT")}"
BASE_NAME="$(basename "$REPO_ROOT")"
TS="$(date +%Y%m%d-%H%M%S)"
WT_PATH="${CHAT_UI_WORKTREE_PATH:-$PARENT/${BASE_NAME}-chat-ui-fix-$TS}"
BRANCH="fix/chat-ui-scroll-layout-wt-$TS"

if [[ ! -f "$PATCH_FILE" ]]; then
  echo "ERROR: missing patch: $PATCH_FILE" >&2
  exit 1
fi

if [[ -e "$WT_PATH" ]]; then
  echo "ERROR: path already exists: $WT_PATH" >&2
  exit 1
fi

echo "Main repo (unchanged after this): $REPO_ROOT"
echo "New worktree: $WT_PATH"
echo "Branch (only in this worktree at first): $BRANCH"
echo ""

git -C "$REPO_ROOT" fetch origin
git -C "$REPO_ROOT" worktree add -b "$BRANCH" "$WT_PATH" origin/main

echo "Applying patch inside worktree..."
git -C "$WT_PATH" apply --verbose "$PATCH_FILE"

echo ""
echo "Status in worktree:"
git -C "$WT_PATH" status --short

if $DO_COMMIT; then
  git -C "$WT_PATH" add \
    components/chat-area.tsx \
    components/chat-interface.tsx \
    components/hive-activity-indicator.tsx \
    app/page.tsx \
    app/globals.css
  git -C "$WT_PATH" commit -m "fix(ui): chat scroll layout and composer (viewport, min-h-0, iOS input)"
  echo ""
  echo "Committed in worktree. From $WT_PATH:"
  echo "  git push -u origin $BRANCH"
else
  echo ""
  echo "From $WT_PATH, commit when ready:"
  echo "  git add components/chat-area.tsx components/chat-interface.tsx \\"
  echo "    components/hive-activity-indicator.tsx app/page.tsx app/globals.css"
  echo "  git commit -m \"fix(ui): chat scroll layout and composer\""
  echo "  git push -u origin $BRANCH"
fi

echo ""
echo "Sanity checks (run inside worktree):"
echo "  cd \"$WT_PATH\" && npm ci && npm run lint && npm run build"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "TO REMOVE THIS EXPERIMENT (main repo still exactly as before):"
echo "  cd \"$REPO_ROOT\""
echo "  git worktree remove \"$WT_PATH\""
echo "  git branch -D $BRANCH"
echo "If you pushed the branch, delete it on GitHub too when you no longer need it."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
