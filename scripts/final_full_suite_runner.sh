#!/usr/bin/env bash
# ===========================================================================
# LLMHive — Final Full-Suite Certification Runner
# ===========================================================================
# Runs the complete 8-category benchmark suite with cost and time controls.
#
# Usage:
#   bash scripts/final_full_suite_runner.sh
#
# Prerequisites:
#   - API_KEY or LLMHIVE_API_KEY set
#   - Python venv activated (or .venv present)
#   - micro_validation.py --dry-run passes
# ===========================================================================

set -euo pipefail

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
  Report:          $REPORT_FILE
======================================================================
HEADER

# ---- Pre-flight: zero regression audit ------------------------------------
echo "" | tee -a "$LOG_FILE"
echo "Running zero-regression audit..." | tee -a "$LOG_FILE"

if ! python3 "$SCRIPT_DIR/micro_validation.py" --dry-run 2>&1 | tee -a "$LOG_FILE"; then
    echo "ABORT: Zero-regression audit failed." | tee -a "$LOG_FILE"
    exit 1
fi

echo "Audit passed." | tee -a "$LOG_FILE"

# ---- Run full suite -------------------------------------------------------
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
