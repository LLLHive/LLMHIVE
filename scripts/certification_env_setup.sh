#!/usr/bin/env bash
# ===========================================================================
# LLMHive — Certification Environment Setup
# ===========================================================================
# Sets and validates all required environment variables for a certification
# benchmark run.  Source this script before running the certification suite.
#
# Usage:
#   source scripts/certification_env_setup.sh
#
# This script ONLY sets environment variables and validates them.
# It does NOT execute any benchmark.
# ===========================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "======================================================================"
echo "LLMHive — Certification Environment Setup"
echo "  Timestamp: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "======================================================================"

# ------------------------------------------------------------------
# 1. Set required certification variables
# ------------------------------------------------------------------

export MAX_RUNTIME_MINUTES=180
export MAX_TOTAL_COST_USD=5.00
export CERTIFICATION_LOCK=true
export CERTIFICATION_OVERRIDE=true
export CATEGORY_BENCH_SEED="${CATEGORY_BENCH_SEED:-42}"
export CATEGORY_BENCH_TIER="${CATEGORY_BENCH_TIER:-elite}"
export CATEGORY_BENCH_REASONING_MODE="${CATEGORY_BENCH_REASONING_MODE:-deep}"

echo ""
echo "  Variables set:"
echo "    MAX_RUNTIME_MINUTES     = $MAX_RUNTIME_MINUTES"
echo "    MAX_TOTAL_COST_USD      = $MAX_TOTAL_COST_USD"
echo "    CERTIFICATION_LOCK      = $CERTIFICATION_LOCK"
echo "    CERTIFICATION_OVERRIDE  = $CERTIFICATION_OVERRIDE"
echo "    CATEGORY_BENCH_SEED     = $CATEGORY_BENCH_SEED"
echo "    CATEGORY_BENCH_TIER     = $CATEGORY_BENCH_TIER"

# ------------------------------------------------------------------
# 2. Validate cost cap — EXACT match
# ------------------------------------------------------------------

echo ""
echo "Validating cost cap..."

if [[ "$MAX_TOTAL_COST_USD" != "5.00" ]]; then
    echo "  ABORT: Cost cap must be 5.00 for certification (got: $MAX_TOTAL_COST_USD)"
    return 1 2>/dev/null || exit 1
fi
echo "  PASS: MAX_TOTAL_COST_USD = \$5.00"

# ------------------------------------------------------------------
# 3. Validate runtime cap
# ------------------------------------------------------------------

echo "Validating runtime cap..."

if [[ "$MAX_RUNTIME_MINUTES" -gt 180 ]]; then
    echo "  ABORT: Runtime cap exceeds certification limit (got: $MAX_RUNTIME_MINUTES, max: 180)"
    return 1 2>/dev/null || exit 1
fi
echo "  PASS: MAX_RUNTIME_MINUTES = $MAX_RUNTIME_MINUTES"

# ------------------------------------------------------------------
# 4. Verify HF_TOKEN exists
# ------------------------------------------------------------------

echo "Validating HF_TOKEN..."

if [[ -z "${HF_TOKEN:-}" ]]; then
    echo "  ABORT: HF_TOKEN is not set."
    echo "  Set it with:  export HF_TOKEN=hf_..."
    return 1 2>/dev/null || exit 1
fi
echo "  PASS: HF_TOKEN is set (${#HF_TOKEN} chars)"

# ------------------------------------------------------------------
# 5. Verify API_KEY exists
# ------------------------------------------------------------------

echo "Validating API_KEY..."

API_KEY_VAL="${API_KEY:-${LLMHIVE_API_KEY:-}}"
if [[ -z "$API_KEY_VAL" ]]; then
    echo "  ABORT: API_KEY / LLMHIVE_API_KEY is not set."
    echo "  Set it with:  export API_KEY=..."
    return 1 2>/dev/null || exit 1
fi
echo "  PASS: API_KEY is set (${#API_KEY_VAL} chars)"

# ------------------------------------------------------------------
# Summary
# ------------------------------------------------------------------

echo ""
echo "======================================================================"
echo "  Environment setup COMPLETE — all variables validated."
echo ""
echo "  Next steps:"
echo "    1. python3 scripts/verify_authentication.py --json"
echo "    2. bash scripts/final_full_suite_runner.sh --dry-run"
echo "    3. bash scripts/final_full_suite_runner.sh"
echo "======================================================================"
