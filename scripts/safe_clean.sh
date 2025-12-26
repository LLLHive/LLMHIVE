#!/bin/bash
# =============================================================================
# LLMHive Safe Repository Cleanup Script
# =============================================================================
#
# This script safely cleans build artifacts from the repository WITHOUT
# deleting critical files like secrets, .env files, archives, or evals.
#
# ⚠️  DO NOT use `git clean -xfd` directly - it will delete secrets and
#     other critical files that are gitignored but necessary for the project.
#
# Usage:
#   ./scripts/safe_clean.sh           # Dry run (shows what would be deleted)
#   ./scripts/safe_clean.sh --force   # Actually delete files
#   ./scripts/safe_clean.sh --help    # Show help
#
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory and repo root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# =============================================================================
# Protected paths (NEVER delete these)
# =============================================================================
PROTECTED_PATHS=(
    "data/modeldb/secrets/"
    "data/modeldb/.env"
    "data/modeldb/.env.*"
    "data/modeldb/archives/"
    "data/modeldb/evals/"
    ".venv/"
    ".venv_modeldb/"
    "llmhive/.venv/"
    "venv/"
    ".env"
    ".env.local"
    "llmhive/.env"
    "llmhive/.env.local"
)

# Directories safe to delete (build artifacts)
SAFE_TO_DELETE_DIRS=(
    "node_modules"
    ".next"
    "out"
    "build"
    "dist"
    "__pycache__"
    ".pytest_cache"
    ".mypy_cache"
    ".ruff_cache"
    "coverage"
    "playwright-report"
    "test-results"
    ".vercel"
)

# File patterns safe to delete
SAFE_TO_DELETE_PATTERNS=(
    "*.pyc"
    "*.pyo"
    "*.log"
    "npm-debug.log*"
    "yarn-debug.log*"
    "pnpm-debug.log*"
    ".DS_Store"
    "Thumbs.db"
)

# =============================================================================
# Helper functions
# =============================================================================

print_header() {
    echo ""
    echo -e "${BLUE}=============================================================================${NC}"
    echo -e "${BLUE}  LLMHive Safe Repository Cleanup${NC}"
    echo -e "${BLUE}=============================================================================${NC}"
    echo ""
}

print_protected() {
    echo -e "${GREEN}Protected paths (will NEVER be deleted):${NC}"
    for path in "${PROTECTED_PATHS[@]}"; do
        echo -e "  ${GREEN}✓${NC} $path"
    done
    echo ""
}

show_help() {
    print_header
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --force     Actually delete files (default is dry-run)"
    echo "  --help      Show this help message"
    echo ""
    echo "This script safely removes build artifacts while protecting:"
    echo "  - ModelDB secrets (data/modeldb/secrets/)"
    echo "  - Environment files (.env, .env.local, etc.)"
    echo "  - ModelDB archives (data/modeldb/archives/)"
    echo "  - ModelDB eval prompts (data/modeldb/evals/)"
    echo "  - Virtual environments (.venv/, venv/)"
    echo ""
    echo -e "${RED}⚠️  DO NOT use 'git clean -xfd' directly!${NC}"
    echo "It will delete secrets and break the project."
    echo ""
    exit 0
}

check_git_status() {
    cd "$REPO_ROOT"
    
    # Check for uncommitted changes
    if ! git diff --quiet HEAD 2>/dev/null; then
        echo -e "${YELLOW}⚠️  Warning: You have uncommitted changes.${NC}"
        echo ""
        git status --short
        echo ""
        
        if [[ "$FORCE" != "true" ]]; then
            echo "Run with --force to clean anyway, or commit/stash your changes first."
            return 1
        fi
    fi
    
    return 0
}

verify_protected_exist() {
    echo -e "${BLUE}Checking protected paths...${NC}"
    
    local found_protected=false
    
    for path in "${PROTECTED_PATHS[@]}"; do
        # Handle glob patterns
        if [[ "$path" == *"*"* ]]; then
            continue
        fi
        
        local full_path="$REPO_ROOT/$path"
        if [[ -e "$full_path" ]]; then
            found_protected=true
            echo -e "  ${GREEN}✓${NC} Found: $path"
        fi
    done
    
    if [[ "$found_protected" == "true" ]]; then
        echo -e "${GREEN}Protected paths will be preserved.${NC}"
    fi
    echo ""
}

clean_directory() {
    local dir_name="$1"
    local count=0
    
    while IFS= read -r -d '' dir; do
        if [[ "$DRY_RUN" == "true" ]]; then
            echo -e "  ${YELLOW}Would delete:${NC} $dir"
        else
            rm -rf "$dir"
            echo -e "  ${RED}Deleted:${NC} $dir"
        fi
        ((count++)) || true
    done < <(find "$REPO_ROOT" -type d -name "$dir_name" -not -path "*/.git/*" -print0 2>/dev/null)
    
    return $count
}

clean_pattern() {
    local pattern="$1"
    local count=0
    
    while IFS= read -r -d '' file; do
        # Check if file is in a protected path
        local skip=false
        for protected in "${PROTECTED_PATHS[@]}"; do
            if [[ "$file" == *"$protected"* ]]; then
                skip=true
                break
            fi
        done
        
        if [[ "$skip" == "true" ]]; then
            continue
        fi
        
        if [[ "$DRY_RUN" == "true" ]]; then
            echo -e "  ${YELLOW}Would delete:${NC} $file"
        else
            rm -f "$file"
            echo -e "  ${RED}Deleted:${NC} $file"
        fi
        ((count++)) || true
    done < <(find "$REPO_ROOT" -type f -name "$pattern" -not -path "*/.git/*" -print0 2>/dev/null)
    
    return $count
}

# =============================================================================
# Main execution
# =============================================================================

# Parse arguments
FORCE=false
DRY_RUN=true

while [[ $# -gt 0 ]]; do
    case "$1" in
        --force)
            FORCE=true
            DRY_RUN=false
            shift
            ;;
        --help|-h)
            show_help
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            echo "Run with --help for usage information."
            exit 1
            ;;
    esac
done

# Start
print_header

if [[ "$DRY_RUN" == "true" ]]; then
    echo -e "${YELLOW}DRY RUN MODE - No files will be deleted${NC}"
    echo "Run with --force to actually delete files."
    echo ""
fi

# Show protected paths
print_protected

# Check git status (unless forced)
if [[ "$FORCE" != "true" ]]; then
    if ! check_git_status; then
        exit 1
    fi
fi

# Verify protected paths exist
verify_protected_exist

# Clean directories
echo -e "${BLUE}Cleaning build artifact directories...${NC}"
total_dirs=0

for dir_name in "${SAFE_TO_DELETE_DIRS[@]}"; do
    clean_directory "$dir_name"
    total_dirs=$((total_dirs + $?))
done

echo ""

# Clean file patterns
echo -e "${BLUE}Cleaning temporary files...${NC}"
total_files=0

for pattern in "${SAFE_TO_DELETE_PATTERNS[@]}"; do
    clean_pattern "$pattern"
    total_files=$((total_files + $?))
done

echo ""

# Summary
echo -e "${BLUE}=============================================================================${NC}"
if [[ "$DRY_RUN" == "true" ]]; then
    echo -e "${YELLOW}DRY RUN COMPLETE${NC}"
    echo ""
    echo "Would delete:"
    echo "  - Directories: $total_dirs"
    echo "  - Files: $total_files"
    echo ""
    echo "To actually delete, run:"
    echo -e "  ${GREEN}$0 --force${NC}"
else
    echo -e "${GREEN}CLEANUP COMPLETE${NC}"
    echo ""
    echo "Deleted:"
    echo "  - Directories: $total_dirs"
    echo "  - Files: $total_files"
fi
echo ""
echo -e "Protected paths remain ${GREEN}untouched${NC}."
echo -e "${BLUE}=============================================================================${NC}"

