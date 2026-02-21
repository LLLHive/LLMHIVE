#!/usr/bin/env bash
# ===========================================================================
# LLMHive — Final Full-Suite Certification Runner
# ===========================================================================
# Runs the complete 8-category benchmark suite with cost and time controls.
#
# Usage:
#   bash scripts/final_full_suite_runner.sh [--dry-run]
#
# Prerequisites:
#   - API_KEY or LLMHIVE_API_KEY set
#   - HF_TOKEN set
#   - Python venv activated (or .venv present)
#   - verify_authentication.py passes
#   - micro_validation.py --dry-run passes
# ===========================================================================

set -euo pipefail

# ---- Parse arguments ------------------------------------------------------
DRY_RUN=false
for arg in "$@"; do
    case "$arg" in
        --dry-run) DRY_RUN=true ;;
    esac
done

# ---- Configuration --------------------------------------------------------
export MAX_RUNTIME_MINUTES="${MAX_RUNTIME_MINUTES:-180}"
export MAX_TOTAL_COST_USD="${MAX_TOTAL_COST_USD:-5.00}"
export CATEGORY_BENCH_SEED="${CATEGORY_BENCH_SEED:-42}"
export CATEGORY_BENCH_TIER="${CATEGORY_BENCH_TIER:-elite}"
export CATEGORY_BENCH_REASONING_MODE="${CATEGORY_BENCH_REASONING_MODE:-deep}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
REPORT_DIR="$PROJECT_ROOT/benchmark_reports"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
REPORT_FILE="$REPORT_DIR/full_suite_${TIMESTAMP}.json"
LOG_FILE="$REPORT_DIR/full_suite_${TIMESTAMP}.log"

mkdir -p "$REPORT_DIR"

# ---- Environment fingerprint ----------------------------------------------
COMMIT_HASH="$(git -C "$PROJECT_ROOT" rev-parse HEAD 2>/dev/null || echo 'unknown')"
BRANCH="$(git -C "$PROJECT_ROOT" branch --show-current 2>/dev/null || echo 'unknown')"
PYTHON_VERSION="$(python3 --version 2>&1 || echo 'unknown')"
HOSTNAME_VAL="$(hostname 2>/dev/null || echo 'unknown')"

cat <<HEADER | tee "$LOG_FILE"
======================================================================
LLMHive — Full-Suite Certification Run
======================================================================
  Timestamp:       $TIMESTAMP
  Commit:          $COMMIT_HASH
  Branch:          $BRANCH
  Python:          $PYTHON_VERSION
  Host:            $HOSTNAME_VAL
  Tier:            $CATEGORY_BENCH_TIER
  Seed:            $CATEGORY_BENCH_SEED
  Max Runtime:     ${MAX_RUNTIME_MINUTES} minutes
  Max Cost:        \$${MAX_TOTAL_COST_USD}
  Dry Run:         $DRY_RUN
======================================================================
HEADER

# ===========================================================================
# PHASE 3 — Cost & Runtime Cap Enforcement
# ===========================================================================

echo "" | tee -a "$LOG_FILE"
echo "Verifying cost & runtime caps..." | tee -a "$LOG_FILE"

if [[ "$MAX_TOTAL_COST_USD" != "5.00" ]]; then
    echo "❌ Max cost must be 5.00 for certification run (got: $MAX_TOTAL_COST_USD)" | tee -a "$LOG_FILE"
    exit 1
fi

if [[ "$MAX_RUNTIME_MINUTES" -gt 180 ]]; then
    echo "❌ Runtime cap exceeds certification limit (got: $MAX_RUNTIME_MINUTES, max: 180)" | tee -a "$LOG_FILE"
    exit 1
fi

echo "✅ Cost cap: \$${MAX_TOTAL_COST_USD}  |  Runtime cap: ${MAX_RUNTIME_MINUTES}m" | tee -a "$LOG_FILE"

# ===========================================================================
# PHASE 4 — Evaluator Placeholder Validation
# ===========================================================================

echo "" | tee -a "$LOG_FILE"
echo "Verifying evaluator placeholders..." | tee -a "$LOG_FILE"

EVAL_OK=true
for EVAL_VAR in LONGBENCH_EVAL_CMD TOOLBENCH_EVAL_CMD MTBENCH_EVAL_CMD; do
    CMD="${!EVAL_VAR:-}"
    SCRIPT_NAME=""
    case "$EVAL_VAR" in
        LONGBENCH_EVAL_CMD) SCRIPT_NAME="eval_longbench.py" ;;
        TOOLBENCH_EVAL_CMD) SCRIPT_NAME="eval_toolbench.py" ;;
        MTBENCH_EVAL_CMD)   SCRIPT_NAME="eval_mtbench.py" ;;
    esac
    if [[ -n "$CMD" && "$CMD" == *"{output_path}"* ]]; then
        echo "  ✅ $EVAL_VAR OK" | tee -a "$LOG_FILE"
    elif [[ -f "$SCRIPT_DIR/$SCRIPT_NAME" ]]; then
        echo "  ℹ  $EVAL_VAR auto-resolved from $SCRIPT_NAME (Python handles placeholders)" | tee -a "$LOG_FILE"
    else
        echo "  ❌ $EVAL_VAR not set and $SCRIPT_NAME not found" | tee -a "$LOG_FILE"
        EVAL_OK=false
    fi
done

if [[ "$EVAL_OK" != "true" ]]; then
    echo "ABORT: Evaluator placeholder validation failed." | tee -a "$LOG_FILE"
    exit 1
fi

# ===========================================================================
# PHASE 5 — Certification Lock Validation
# ===========================================================================

echo "" | tee -a "$LOG_FILE"
echo "Verifying certification lock..." | tee -a "$LOG_FILE"

if [[ "$DRY_RUN" == "true" ]]; then
    echo "  ℹ  Certification lock check skipped (dry-run mode)" | tee -a "$LOG_FILE"
else
    if [[ "${CERTIFICATION_LOCK:-}" != "true" ]]; then
        echo "❌ Certification lock not enabled (CERTIFICATION_LOCK != true)" | tee -a "$LOG_FILE"
        exit 1
    fi

    if [[ "${CERTIFICATION_OVERRIDE:-}" != "true" ]]; then
        echo "❌ Certification override missing (CERTIFICATION_OVERRIDE != true)" | tee -a "$LOG_FILE"
        exit 1
    fi

    echo "✅ CERTIFICATION_LOCK=true  |  CERTIFICATION_OVERRIDE=true" | tee -a "$LOG_FILE"
fi

# ===========================================================================
# Pre-flight: Authentication verification
# ===========================================================================

echo "" | tee -a "$LOG_FILE"
echo "Running authentication verification..." | tee -a "$LOG_FILE"

if ! python3 "$SCRIPT_DIR/verify_authentication.py" 2>&1 | tee -a "$LOG_FILE"; then
    echo "ABORT: Authentication verification failed." | tee -a "$LOG_FILE"
    exit 1
fi

echo "Authentication verified." | tee -a "$LOG_FILE"

# ===========================================================================
# Pre-flight: Zero regression audit
# ===========================================================================

echo "" | tee -a "$LOG_FILE"
echo "Running zero-regression audit..." | tee -a "$LOG_FILE"

if ! python3 "$SCRIPT_DIR/micro_validation.py" --dry-run 2>&1 | tee -a "$LOG_FILE"; then
    echo "ABORT: Zero-regression audit failed." | tee -a "$LOG_FILE"
    exit 1
fi

echo "Audit passed." | tee -a "$LOG_FILE"

# ===========================================================================
# PHASE 6 — Dry Run Gate
# ===========================================================================

if [[ "$DRY_RUN" == "true" ]]; then
    echo "" | tee -a "$LOG_FILE"
    echo "======================================================================" | tee -a "$LOG_FILE"
    echo "  DRY RUN COMPLETE — all checks passed." | tee -a "$LOG_FILE"
    echo "  Ready for execution." | tee -a "$LOG_FILE"
    echo "  To run for real: remove --dry-run flag." | tee -a "$LOG_FILE"
    echo "======================================================================" | tee -a "$LOG_FILE"
    exit 0
fi

# ===========================================================================
# Run full suite
# ===========================================================================

START_EPOCH="$(date +%s)"
echo "" | tee -a "$LOG_FILE"
echo "Starting 8-category benchmark suite at $(date -u +%Y-%m-%dT%H:%M:%SZ)..." | tee -a "$LOG_FILE"

python3 "$SCRIPT_DIR/run_category_benchmarks.py" 2>&1 | tee -a "$LOG_FILE"
EXIT_CODE=$?

END_EPOCH="$(date +%s)"
ELAPSED_SEC=$(( END_EPOCH - START_EPOCH ))
ELAPSED_MIN=$(( ELAPSED_SEC / 60 ))

echo "" | tee -a "$LOG_FILE"
echo "======================================================================" | tee -a "$LOG_FILE"
echo "  Completed in ${ELAPSED_MIN}m ${ELAPSED_SEC}s (exit code: $EXIT_CODE)" | tee -a "$LOG_FILE"
echo "======================================================================" | tee -a "$LOG_FILE"

# ---- Collect latest report ------------------------------------------------
LATEST_REPORT="$(ls -t "$REPORT_DIR"/category_benchmarks_elite_*.json 2>/dev/null | head -1)"

if [ -n "$LATEST_REPORT" ]; then
    cp "$LATEST_REPORT" "$REPORT_FILE"
    echo "Report saved to: $REPORT_FILE" | tee -a "$LOG_FILE"
else
    echo "WARNING: No benchmark report found after run." | tee -a "$LOG_FILE"
fi

# ---- Summary metadata -----------------------------------------------------
cat <<FOOTER >> "$LOG_FILE"

--- Execution Summary ---
commit: $COMMIT_HASH
branch: $BRANCH
seed: $CATEGORY_BENCH_SEED
tier: $CATEGORY_BENCH_TIER
start: $(date -u -r "$START_EPOCH" +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || echo $START_EPOCH)
end: $(date -u -r "$END_EPOCH" +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || echo $END_EPOCH)
elapsed_seconds: $ELAPSED_SEC
exit_code: $EXIT_CODE
report: $REPORT_FILE
FOOTER

echo "" | tee -a "$LOG_FILE"
echo "Full-suite run complete. Review $REPORT_FILE before deploying." | tee -a "$LOG_FILE"

exit $EXIT_CODE
