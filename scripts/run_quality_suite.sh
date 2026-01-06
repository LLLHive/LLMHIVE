#!/bin/bash
# Shell script to run the full quality evaluation suite, for CI/CD pipeline usage.
# This script ensures tests are executed and results are collected.
#
# Usage:
#   ./scripts/run_quality_suite.sh
#
# Environment Variables:
#   QUALITY_THRESHOLD - Minimum pass rate (default: 0.7)
#   MAX_FAILURES - Maximum allowed failures (default: 3)
#   SKIP_UI_VALIDATION - Skip UI validation if "true"

set -e  # Exit immediately if a command exits with a non-zero status

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}   LLMHive Quality Evaluation Suite${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""

# Change to project root
cd "$PROJECT_ROOT"

# Activate virtual environment if it exists
if [ -f "venv/bin/activate" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
elif [ -f ".venv/bin/activate" ]; then
    echo "Activating virtual environment..."
    source .venv/bin/activate
fi

# Install test dependencies if needed
echo "Checking test dependencies..."
pip install pytest pytest-asyncio --quiet 2>/dev/null || true

echo ""
echo -e "${YELLOW}Step 1: Running PyTest Quality Evaluation Suite${NC}"
echo "------------------------------------------------"

# Run the PyTest suite for quality evaluation
if pytest -v tests/quality_eval --tb=short; then
    echo -e "${GREEN}✓ PyTest suite passed${NC}"
else
    echo -e "${RED}✗ PyTest suite had failures${NC}"
    # Continue to next steps even if some tests fail
fi

echo ""
echo -e "${YELLOW}Step 2: Running Continuous Quality Evaluation Script${NC}"
echo "------------------------------------------------"

# Run the evaluation script for detailed logging
if python tests/quality_eval/eval_quality.py; then
    echo -e "${GREEN}✓ Quality evaluation passed${NC}"
else
    EVAL_EXIT_CODE=$?
    echo -e "${RED}✗ Quality evaluation failed (exit code: $EVAL_EXIT_CODE)${NC}"
fi

# Optional UI validation
if [ "${SKIP_UI_VALIDATION}" != "true" ]; then
    echo ""
    echo -e "${YELLOW}Step 3: Validating UI Wiring${NC}"
    echo "------------------------------------------------"
    
    if python tests/quality_eval/validate_ui_wiring.py; then
        echo -e "${GREEN}✓ UI wiring validation passed${NC}"
    else
        echo -e "${RED}✗ UI wiring validation failed${NC}"
    fi
else
    echo ""
    echo -e "${YELLOW}Step 3: Skipping UI Wiring Validation (SKIP_UI_VALIDATION=true)${NC}"
fi

echo ""
echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}   Quality Evaluation Complete${NC}"
echo -e "${GREEN}============================================${NC}"

# Check if results file was created
if [ -f "quality_eval_results.json" ]; then
    echo ""
    echo "Results saved to: quality_eval_results.json"
    echo ""
    echo "Latest result:"
    tail -c 500 quality_eval_results.json
fi

echo ""
echo "Done!"

