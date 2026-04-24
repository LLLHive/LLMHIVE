#!/usr/bin/env bash
# =============================================================================
# LLMHIVE full backup (frontend, backend, git state, env, local DB, settings)
# =============================================================================
# Creates:
#   backups/LLMHIVE_full_backup_<UTC_DATE>_<TIME>.tar.gz  — source + .git + ignored .env (heavy dirs excluded)
#   backups/LLMHIVE_full_backup_<...>.tar.gz.sha256
#   backups/full_backup_manifest_<...>.txt              — git + sizes + optional tag hint
#
# Does NOT auto-commit. Uncommitted work is inside the tarball; git tag (optional) is only HEAD.
#
# Usage:
#   ./scripts/full-backup.sh
#   ./scripts/full-backup.sh my-backup-label   # optional lightweight git tag (annotated)
# =============================================================================

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BACKUP_DIR="$PROJECT_ROOT/backups"
TIMESTAMP="$(date '+%Y%m%d_%H%M%S')"
PARENT="$(dirname "$PROJECT_ROOT")"
BASE="$(basename "$PROJECT_ROOT")"
ARCHIVE_NAME="LLMHIVE_full_backup_${TIMESTAMP}.tar.gz"
ARCHIVE_PATH="$BACKUP_DIR/$ARCHIVE_NAME"
MANIFEST="$BACKUP_DIR/full_backup_manifest_${TIMESTAMP}.txt"
OPTIONAL_TAG="${1:-}"

mkdir -p "$BACKUP_DIR"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}LLMHIVE full backup${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e "Project: ${YELLOW}$PROJECT_ROOT${NC}"
echo -e "Archive: ${YELLOW}$ARCHIVE_PATH${NC}"
echo ""

if [[ ! -d "$PROJECT_ROOT/.git" ]]; then
  echo -e "${RED}ERROR: Not a git checkout: $PROJECT_ROOT${NC}" >&2
  exit 1
fi

if [[ -n "$(git -C "$PROJECT_ROOT" status --porcelain 2>/dev/null)" ]]; then
  echo -e "${YELLOW}⚠ Working tree has uncommitted changes — they will be included in the tarball.${NC}"
  echo -e "${YELLOW}  (No automatic commit.)${NC}"
  echo ""
fi

echo -e "${YELLOW}Writing manifest...${NC}"
{
  echo "LLMHIVE full backup manifest"
  echo "============================="
  echo "Created (local): $(date)"
  echo "Timestamp ID: $TIMESTAMP"
  echo "Host: $(hostname 2>/dev/null || echo unknown)"
  echo ""
  echo "Git HEAD: $(git -C "$PROJECT_ROOT" rev-parse HEAD)"
  echo "Git branch: $(git -C "$PROJECT_ROOT" branch --show-current 2>/dev/null || echo unknown)"
  echo ""
  echo "git status --short:"
  git -C "$PROJECT_ROOT" status --short || true
  echo ""
  echo "Remotes:"
  git -C "$PROJECT_ROOT" remote -v || true
  echo ""
  echo "Approximate tree size (excluding common caches):"
  du -sh "$PROJECT_ROOT" 2>/dev/null || true
  echo ""
  echo "Env files present (paths only):"
  find "$PROJECT_ROOT" \( -name ".env" -o -name ".env.*" \) -type f 2>/dev/null | grep -v '/.env.example$' | sort || true
  echo ""
  echo "Local DB / sqlite files:"
  find "$PROJECT_ROOT" \( -name "*.db" -o -name "*.sqlite" -o -name "*.sqlite3" \) -type f 2>/dev/null | sort || true
} > "$MANIFEST"
echo -e "${GREEN}✓${NC} $MANIFEST"

echo -e "\n${YELLOW}Creating compressed archive (this may take several minutes)...${NC}"
# Write archive into backups/ while tarring from parent, and exclude backups/ so we never pack the tarball into itself.
COPYFILE_DISABLE=1 tar -czf "$ARCHIVE_PATH" \
  -C "$PARENT" \
  --exclude="$BASE/node_modules" \
  --exclude="$BASE/.next" \
  --exclude="$BASE/out" \
  --exclude="$BASE/build" \
  --exclude="$BASE/dist" \
  --exclude="$BASE/.venv" \
  --exclude="$BASE/venv" \
  --exclude="$BASE/env" \
  --exclude="$BASE/.venv_modeldb" \
  --exclude="$BASE/llmhive/.venv" \
  --exclude="$BASE/backups" \
  --exclude="$BASE/coverage" \
  --exclude="$BASE/playwright-report" \
  --exclude="$BASE/test-results" \
  --exclude="$BASE/blob-report" \
  --exclude="$BASE/.vercel" \
  --exclude="$BASE/.pytest_cache" \
  --exclude="$BASE/.mypy_cache" \
  --exclude="$BASE/.ruff_cache" \
  --exclude="$BASE/playwright/.cache" \
  "$BASE"

echo -e "${GREEN}✓${NC} Archive written"

echo -e "\n${YELLOW}Checksumming...${NC}"
( cd "$BACKUP_DIR" && shasum -a 256 "$ARCHIVE_NAME" > "${ARCHIVE_NAME}.sha256" )
echo -e "${GREEN}✓${NC} ${ARCHIVE_PATH}.sha256"

if [[ -n "$OPTIONAL_TAG" ]]; then
  echo -e "\n${YELLOW}Creating annotated git tag at HEAD: $OPTIONAL_TAG${NC}"
  if git -C "$PROJECT_ROOT" tag -a "$OPTIONAL_TAG" -m "Full backup archive $ARCHIVE_NAME ($(date '+%Y-%m-%d %H:%M:%S'))" 2>/dev/null; then
    echo -e "${GREEN}✓${NC} Tag $OPTIONAL_TAG created (points at HEAD only)."
    echo -e "${YELLOW}  Push when ready: git push origin $OPTIONAL_TAG${NC}"
  else
    echo -e "${YELLOW}⚠ Tag '$OPTIONAL_TAG' already exists or could not be created; skipping.${NC}"
  fi
fi

echo -e "\n${BLUE}========================================${NC}"
echo -e "${GREEN}Full backup complete.${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e "Archive:     ${YELLOW}$ARCHIVE_PATH${NC}"
echo -e "Checksum:    ${YELLOW}${ARCHIVE_PATH}.sha256${NC}"
echo -e "Manifest:    ${YELLOW}$MANIFEST${NC}"
echo ""
echo -e "${YELLOW}Restore (example):${NC}"
echo -e "  mkdir -p ~/restore && tar -xzf \"$ARCHIVE_PATH\" -C ~/restore"
echo -e "  # then: cd ~/restore/$BASE && npm ci && (cd llmhive && pip install -r requirements.txt)  # as needed"
echo ""
echo -e "${YELLOW}Copy backups/ to external storage; it is gitignored.${NC}"
