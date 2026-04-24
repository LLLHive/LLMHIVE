#!/usr/bin/env bash
# =============================================================================
# One-shot: create a branch from origin/main and apply the chat UI layout fix
# (scroll viewport, min-h-0 flex chain, composer touch-target, bg will-change).
#
# Usage (from anywhere):
#   ./scripts/apply-chat-ui-fix.sh
#   ./scripts/apply-chat-ui-fix.sh --commit       # also git commit the five files
#   ./scripts/apply-chat-ui-fix.sh --stash        # stash all WIP first (incl. untracked), then apply
#   ./scripts/apply-chat-ui-fix.sh --stash --commit
#
# Safest (main folder untouched): see scripts/chat-ui-fix-via-worktree.sh
#
# Requires a clean working tree unless you pass --stash (see above).
#
# Regenerate the patch after editing the UI files on top of main:
#   git fetch origin && git diff origin/main -- \
#     components/chat-area.tsx components/chat-interface.tsx \
#     components/hive-activity-indicator.tsx app/page.tsx app/globals.css \
#     > scripts/patches/chat-ui-scroll-layout.patch
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PATCH_FILE="$SCRIPT_DIR/patches/chat-ui-scroll-layout.patch"
DO_COMMIT=false
DO_STASH=false
START_BRANCH=""
STASHED=false

for arg in "$@"; do
  case "$arg" in
    --commit) DO_COMMIT=true ;;
    --stash) DO_STASH=true ;;
    -h|--help)
      sed -n '1,30p' "$0"
      exit 0
      ;;
  esac
done

cd "$REPO_ROOT"

if [[ ! -f "$PATCH_FILE" ]]; then
  echo "ERROR: missing patch: $PATCH_FILE" >&2
  exit 1
fi

if [[ -n "$(git status --porcelain 2>/dev/null)" ]]; then
  if $DO_STASH; then
    START_BRANCH="$(git branch --show-current)"
    echo "Stashing all changes (including untracked) from branch: $START_BRANCH"
    git stash push -u -m "apply-chat-ui-fix auto-stash $(date '+%Y-%m-%d %H:%M:%S')"
    STASHED=true
  else
    echo "ERROR: working tree is not clean (commit or stash everything first)." >&2
    echo "  git status --short" >&2
    echo "" >&2
    echo "  Or re-run with:  ./scripts/apply-chat-ui-fix.sh --stash" >&2
    echo "  (then restore WIP: git switch <your-branch> && git stash pop)" >&2
    exit 1
  fi
fi

echo "Fetching origin..."
git fetch origin

BRANCH="${CHAT_UI_FIX_BRANCH:-fix/chat-ui-scroll-layout-$(date +%Y%m%d-%H%M%S)}"
if git show-ref --verify --quiet "refs/heads/$BRANCH"; then
  echo "ERROR: branch already exists: $BRANCH (set CHAT_UI_FIX_BRANCH to a new name)" >&2
  exit 1
fi

echo "Creating branch $BRANCH from origin/main..."
git switch -c "$BRANCH" origin/main

echo "Applying patch..."
git apply --verbose "$PATCH_FILE"

echo ""
echo "Applied. Changed files:"
git status --short

if $DO_COMMIT; then
  git add \
    components/chat-area.tsx \
    components/chat-interface.tsx \
    components/hive-activity-indicator.tsx \
    app/page.tsx \
    app/globals.css
  git commit -m "fix(ui): chat scroll layout and composer (viewport, min-h-0, iOS input)"
  echo ""
  echo "Committed on $BRANCH. Push with:"
  echo "  git push -u origin $BRANCH"
else
  echo ""
  echo "Review diff, then:"
  echo "  git add components/chat-area.tsx components/chat-interface.tsx \\"
  echo "    components/hive-activity-indicator.tsx app/page.tsx app/globals.css"
  echo "  git commit -m \"fix(ui): chat scroll layout and composer\""
  echo "  git push -u origin $BRANCH"
fi

echo ""
echo "Sanity checks:"
echo "  npm run lint && npm run build"

if $STASHED; then
  echo ""
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "TO PUT YOUR MAIN CLONE BACK EXACTLY AS BEFORE (discard this UI branch):"
  echo "  git switch $START_BRANCH"
  echo "  git branch -D $BRANCH"
  echo "  git stash pop"
  echo "That returns your branch + uncommitted work; the UI patch is gone locally."
  echo "If you already pushed $BRANCH, delete the remote branch on GitHub separately."
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "If you want to KEEP the fix for a PR: push $BRANCH first, then still run"
  echo "  git switch $START_BRANCH && git stash pop  (do not delete the branch until merged)."
fi
