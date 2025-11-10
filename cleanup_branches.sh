#!/usr/bin/env bash
# Delete obsolete branches called out in the Branch Audit:
# - codex/* (all)
# - copilot/fix-importerror-in-planner
# - copilot/update-logging-implementation
# - fix/tavily-bearer-auth-clean2
#
# Defaults to a DRY-RUN. Pass --apply (or -y) to actually delete.

set -Eeuo pipefail

REMOTE="${REMOTE:-origin}"
BASE_BRANCH="${BASE_BRANCH:-main}"
# Optional heuristic for extra legacy branches (OFF by default for safety).
INCLUDE_LEGACY="${INCLUDE_LEGACY:-0}"   # set to 1 to enable
AGE_DAYS="${AGE_DAYS:-90}"              # used only if INCLUDE_LEGACY=1

echo "Remote: $REMOTE"
echo "Base branch: $BASE_BRANCH"
echo "Heuristic legacy search: ${INCLUDE_LEGACY} (age >= ${AGE_DAYS} days)"


# ---- Preflight checks ----
if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "Error: not a git repository. Open the terminal in your LLMHIVE repo and try again."
  exit 1
fi

if ! git config --get remote.${REMOTE}.url >/dev/null 2>&1; then
  echo "Error: remote '$REMOTE' not found. If your remote is named differently, run: REMOTE=<name> bash $0"
  exit 1
fi

echo "Fetching latest refs (and pruning)..."
git fetch --prune "$REMOTE" >/dev/null 2>&1 || true

# Make sure we are not on a branch that will be deleted; prefer switching to main.
if git show-ref --verify --quiet "refs/heads/${BASE_BRANCH}"; then
  git checkout "${BASE_BRANCH}" >/dev/null 2>&1 || true
elif git show-ref --verify --quiet "refs/remotes/${REMOTE}/${BASE_BRANCH}"; then
  git checkout -B "${BASE_BRANCH}" "${REMOTE}/${BASE_BRANCH}" >/dev/null 2>&1 || true
fi


# ---- Collect remote branches ----
REMOTE_BRANCHES=()
while IFS= read -r line; do
  # strip 'origin/' prefix if present; we asked for strip=3 below already
  REMOTE_BRANCHES+=("$line")
done < <(git for-each-ref --format='%(refname:strip=3)' "refs/remotes/${REMOTE}/" | sort -u)

if ((${#REMOTE_BRANCHES[@]}==0)); then
  echo "No remote branches found on ${REMOTE}."
  exit 0
fi

# ---- Build candidate list (exact list from your request) ----
CANDIDATES=()
for b in "${REMOTE_BRANCHES[@]}"; do
  case "$b" in
    codex/*) CANDIDATES+=("$b");;
    copilot/fix-importerror-in-planner) CANDIDATES+=("$b");;
    copilot/update-logging-implementation) CANDIDATES+=("$b");;
    fix/tavily-bearer-auth-clean2) CANDIDATES+=("$b");;
  esac
done

# ---- Optional heuristic for "legacy clean slate / deployment experiment" branches ----
# OFF by default. Enable by running: INCLUDE_LEGACY=1 bash cleanup_branches.sh --apply
if [[ "$INCLUDE_LEGACY" == "1" ]]; then
  # patterns that often indicate old experiment branches
  LEGACY_PATTERNS='clean|slate|vercel|cloudrun|deploy|deployment'
  NOW=$(date -u +%s || echo 0)
  for b in "${REMOTE_BRANCHES[@]}"; do
    if [[ "$b" =~ $LEGACY_PATTERNS ]]; then
      ts=$(git log -1 --format=%ct "${REMOTE}/${b}" 2>/dev/null || echo 0)
      if [[ "$ts" -gt 0 ]]; then
        age_days=$(( (NOW - ts) / 86400 ))
        if [[ "$age_days" -ge "$AGE_DAYS" ]]; then
          CANDIDATES+=("$b")
        fi
      fi
    fi
  done
fi

# ---- De-duplicate candidates ----
if ((${#CANDIDATES[@]})); then
  # sort -u without mapfile (works in bash 3.x)
  TMP_LIST=$(printf "%s\n" "${CANDIDATES[@]}" | sort -u)
  CANDIDATES=()
  while IFS= read -r line; do
    [[ -n "$line" ]] && CANDIDATES+=("$line")
  done <<<"$TMP_LIST"
fi

if ((${#CANDIDATES[@]}==0)); then
  echo "No branches matched the deletion criteria on ${REMOTE}."
  exit 0
fi

echo
echo "Branches scheduled for deletion on remote '${REMOTE}':"
for b in "${CANDIDATES[@]}"; do
  printf "  - %s\n" "$b"
done

APPLY="${1:-}"
if [[ "$APPLY" != "--apply" && "$APPLY" != "-y" ]]; then
  echo
  echo "Dry run complete. To proceed with deletion, run:"
  echo "  bash $0 --apply"
  echo
  exit 0
fi

echo
echo "Proceeding with deletion..."

# ---- Delete remote branches (and any matching local branches) ----
for b in "${CANDIDATES[@]}"; do
  echo "Deleting remote branch: ${b}"
  if git push "$REMOTE" --delete "$b" >/dev/null 2>&1; then
    echo "  removed remote/${b}"
  else
    echo "  WARN: could not remove remote/${b} (may already be deleted or protected)"
  fi

  if git show-ref --verify --quiet "refs/heads/${b}"; then
    git branch -D "${b}" >/dev/null 2>&1 && echo "  removed local ${b}"
  fi
done

echo "Pruning remote-tracking refs..."
git fetch "$REMOTE" --prune >/dev/null 2>&1 || true

echo
echo "Done. Verify on GitHub (Branches tab) that the branches are gone."
