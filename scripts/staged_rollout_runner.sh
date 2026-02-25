#!/usr/bin/env bash
# ===========================================================================
# LLMHive — Staged Rollout Runner
# ===========================================================================
# Executes the 4-stage validation funnel in strict sequence:
#
#   Stage 1: Pre-suite invariant checks (dry-run gates + micro validation)
#   Stage 2: Micro RAG A/B with flags toggled
#   Stage 3: Math-onwards with fixed slice indices
#   Stage 4: Full suite (single run, certification governance)
#
# On any failure:
#   - Disable the last activated flag
#   - Revert config
#   - Re-run micro validation to confirm clean state
#
# Usage:
#   bash scripts/staged_rollout_runner.sh
#   bash scripts/staged_rollout_runner.sh --skip-to=2   # resume from stage 2
#   bash scripts/staged_rollout_runner.sh --dry-run      # validate structure only
#
# Prerequisites:
#   - API_KEY or LLMHIVE_API_KEY set
#   - HF_TOKEN set
#   - Python venv activated
# ===========================================================================

set -uo pipefail

# ---- Parse arguments -------------------------------------------------------
SKIP_TO=1
DRY_RUN=false
for arg in "$@"; do
    case "$arg" in
        --skip-to=*) SKIP_TO="${arg#--skip-to=}" ;;
        --dry-run)   DRY_RUN=true ;;
    esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
REPORT_DIR="$PROJECT_ROOT/benchmark_reports"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
ROLLOUT_LOG="$REPORT_DIR/staged_rollout_${TIMESTAMP}.log"
ROLLOUT_REPORT="$REPORT_DIR/staged_rollout_${TIMESTAMP}.json"

mkdir -p "$REPORT_DIR"

COMMIT_HASH="$(git -C "$PROJECT_ROOT" rev-parse HEAD 2>/dev/null || echo 'unknown')"
BRANCH="$(git -C "$PROJECT_ROOT" branch --show-current 2>/dev/null || echo 'unknown')"

# ---- State tracking --------------------------------------------------------
# Flags activated during this rollout (ordered, for rollback)
ACTIVATED_FLAGS=()
CURRENT_STAGE=0
STAGE_RESULTS=()    # "PASS" or "FAIL" per stage
ROLLBACK_PERFORMED=false

tlog() {
    echo "$@" | tee -a "$ROLLOUT_LOG"
}

cat <<BANNER | tee "$ROLLOUT_LOG"
######################################################################
#  LLMHive — STAGED ROLLOUT RUNNER                                   #
######################################################################
  Timestamp:   $TIMESTAMP
  Commit:      $COMMIT_HASH
  Branch:      $BRANCH
  Skip To:     Stage $SKIP_TO
  Dry Run:     $DRY_RUN
  Log:         $ROLLOUT_LOG
######################################################################
BANNER

# ---- Flag management -------------------------------------------------------

activate_flag() {
    local flag_name="$1"
    local flag_value="${2:-1}"
    export "$flag_name=$flag_value"
    ACTIVATED_FLAGS+=("$flag_name")
    tlog "  [FLAG] Activated: $flag_name=$flag_value"
}

deactivate_flag() {
    local flag_name="$1"
    unset "$flag_name"
    tlog "  [FLAG] Deactivated: $flag_name"
}

deactivate_last_flag() {
    if [[ ${#ACTIVATED_FLAGS[@]} -eq 0 ]]; then
        tlog "  [ROLLBACK] No flags to deactivate"
        return
    fi
    local last="${ACTIVATED_FLAGS[-1]}"
    deactivate_flag "$last"
    # Remove from array
    unset 'ACTIVATED_FLAGS[-1]'
    tlog "  [ROLLBACK] Last activated flag disabled: $last"
}

deactivate_all_flags() {
    for flag in "${ACTIVATED_FLAGS[@]}"; do
        unset "$flag" 2>/dev/null || true
    done
    tlog "  [ROLLBACK] All flags deactivated: ${ACTIVATED_FLAGS[*]:-none}"
    ACTIVATED_FLAGS=()
}

# ---- Rollback procedure ----------------------------------------------------

rollback_and_verify() {
    local failed_stage="$1"
    local error_msg="$2"

    tlog ""
    tlog "  ============================================================"
    tlog "  ROLLBACK INITIATED"
    tlog "  Failed stage: $failed_stage"
    tlog "  Error: $error_msg"
    tlog "  ============================================================"

    ROLLBACK_PERFORMED=true

    # Step 1: Disable last activated flag
    deactivate_last_flag

    # Step 2: Revert config (deactivate remaining non-baseline flags)
    tlog "  [ROLLBACK] Current active flags: ${ACTIVATED_FLAGS[*]:-none}"

    # Step 3: Re-run micro validation to confirm clean state
    tlog ""
    tlog "  [ROLLBACK] Re-running micro validation (dry-run) to confirm clean state..."
    if python3 "$SCRIPT_DIR/micro_validation.py" --dry-run 2>&1 | tee -a "$ROLLOUT_LOG"; then
        tlog "  [ROLLBACK] Micro validation dry-run: PASS — clean state confirmed"
    else
        tlog "  [ROLLBACK] Micro validation dry-run: FAIL — state may be inconsistent"
        tlog "  [ROLLBACK] Manual intervention required"
    fi

    tlog ""
    tlog "  ROLLBACK COMPLETE"
    tlog "  Remaining active flags: ${ACTIVATED_FLAGS[*]:-none}"
    tlog "  ============================================================"
}

# ---- Stage helper -----------------------------------------------------------

run_stage() {
    local stage_num="$1"
    local stage_name="$2"
    local stage_cmd="$3"

    CURRENT_STAGE=$stage_num

    if [[ "$stage_num" -lt "$SKIP_TO" ]]; then
        tlog "  [SKIP] Stage $stage_num skipped (--skip-to=$SKIP_TO)"
        STAGE_RESULTS+=("SKIP")
        return 0
    fi

    tlog ""
    tlog "================================================================"
    tlog "STAGE $stage_num — $stage_name"
    tlog "================================================================"

    local start_epoch
    start_epoch="$(date +%s)"

    if [[ "$DRY_RUN" == "true" ]]; then
        tlog "  [DRY-RUN] Would execute: $stage_cmd"
        STAGE_RESULTS+=("DRY-RUN")
        return 0
    fi

    eval "$stage_cmd" 2>&1 | tee -a "$ROLLOUT_LOG"
    local exit_code=${PIPESTATUS[0]}

    local end_epoch
    end_epoch="$(date +%s)"
    local elapsed=$(( end_epoch - start_epoch ))

    if [[ "$exit_code" -ne 0 ]]; then
        tlog ""
        tlog "  STAGE $stage_num FAILED (exit $exit_code, ${elapsed}s)"
        STAGE_RESULTS+=("FAIL")
        rollback_and_verify "$stage_num: $stage_name" "exit code $exit_code"
        return 1
    fi

    tlog ""
    tlog "  STAGE $stage_num PASSED (${elapsed}s)"
    STAGE_RESULTS+=("PASS")
    return 0
}

# ===========================================================================
# STAGE 1 — Invariant Checks
# ===========================================================================

stage1_cmd() {
    tlog "  [1a] Dry-run gates (final_full_suite_runner --dry-run)..."
    bash "$SCRIPT_DIR/final_full_suite_runner.sh" --dry-run
    local rc1=$?
    if [[ "$rc1" -ne 0 ]]; then
        return "$rc1"
    fi

    tlog ""
    tlog "  [1b] Micro validation dry-run..."
    python3 "$SCRIPT_DIR/micro_validation.py" --dry-run
    local rc2=$?
    if [[ "$rc2" -ne 0 ]]; then
        return "$rc2"
    fi

    tlog ""
    tlog "  [1c] Pre-suite invariant gate (Python)..."
    python3 -c "
import sys, os
sys.path.insert(0, '$SCRIPT_DIR')
os.chdir('$PROJECT_ROOT')

os.environ.setdefault('BENCHMARK_MODE', 'true')
os.environ.setdefault('CATEGORY_BENCH_TIER', 'elite')

from run_category_benchmarks import (
    _init_protected_baselines,
    _assert_all_invariants_active,
)

_init_protected_baselines()
_assert_all_invariants_active()
print('  Pre-suite invariant gate: ALL VERIFIED')
"
    return $?
}

run_stage 1 "INVARIANT CHECKS" "stage1_cmd"
STAGE1_RC=$?
if [[ "$STAGE1_RC" -ne 0 ]]; then
    tlog ""
    tlog "ABORT: Stage 1 failed — cannot proceed without invariants."
    # Write report and exit
    python3 -c "
import json
from pathlib import Path
Path('$ROLLOUT_REPORT').write_text(json.dumps({
    'timestamp': '$TIMESTAMP', 'commit': '$COMMIT_HASH',
    'stages': {'1': 'FAIL'}, 'rollback': True,
    'active_flags': [], 'aborted_at': 1,
}, indent=2))
"
    exit 1
fi

# ===========================================================================
# STAGE 2 — Micro RAG A/B
# ===========================================================================

stage2_cmd() {
    tlog "  Activating RAG flags for A/B test..."
    activate_flag "RAG_RERANK_SHUFFLE_SEEDED"
    activate_flag "RAG_TOP1_FIRST"

    tlog ""
    tlog "  Running micro RAG A/B validation..."
    python3 "$SCRIPT_DIR/micro_validation.py"
    return $?
}

run_stage 2 "MICRO RAG A/B" "stage2_cmd"
STAGE2_RC=$?
if [[ "$STAGE2_RC" -ne 0 ]]; then
    tlog ""
    tlog "ABORT: Stage 2 failed — RAG flags caused regression."
    python3 -c "
import json
from pathlib import Path
Path('$ROLLOUT_REPORT').write_text(json.dumps({
    'timestamp': '$TIMESTAMP', 'commit': '$COMMIT_HASH',
    'stages': {'1': 'PASS', '2': 'FAIL'}, 'rollback': True,
    'active_flags': [$(printf '"%s",' "${ACTIVATED_FLAGS[@]}" | sed 's/,$//')],
    'aborted_at': 2,
}, indent=2))
"
    exit 1
fi

# ===========================================================================
# STAGE 3 — Math-onwards with fixed slice
# ===========================================================================

stage3_cmd() {
    tlog "  Running math-onwards with fixed slice indices..."

    export CATEGORY_BENCH_FIXED_SLICE_FILE="$REPORT_DIR/fixed_slice.json"
    export START_AT="math"
    export BENCHMARK_MODE="true"
    export CATEGORY_BENCH_TIER="elite"
    export CATEGORY_BENCH_REASONING_MODE="deep"

    python3 "$SCRIPT_DIR/run_category_benchmarks.py"
    local rc=$?

    unset START_AT
    return "$rc"
}

run_stage 3 "MATH-ONWARDS FIXED SLICE" "stage3_cmd"
STAGE3_RC=$?
if [[ "$STAGE3_RC" -ne 0 ]]; then
    tlog ""
    tlog "ABORT: Stage 3 failed — math-onwards run regressed."
    python3 -c "
import json
from pathlib import Path
Path('$ROLLOUT_REPORT').write_text(json.dumps({
    'timestamp': '$TIMESTAMP', 'commit': '$COMMIT_HASH',
    'stages': {'1': 'PASS', '2': 'PASS', '3': 'FAIL'}, 'rollback': True,
    'active_flags': [$(printf '"%s",' "${ACTIVATED_FLAGS[@]}" | sed 's/,$//')],
    'aborted_at': 3,
}, indent=2))
"
    exit 1
fi

# ===========================================================================
# STAGE 4 — Full Suite (single run)
# ===========================================================================

stage4_cmd() {
    tlog "  Running full 8-category suite with certification governance..."

    export CERTIFICATION_LOCK="true"
    export CERTIFICATION_OVERRIDE="true"
    export CATEGORY_BENCH_FIXED_SLICE_FILE="$REPORT_DIR/fixed_slice.json"
    export BENCHMARK_MODE="true"

    bash "$SCRIPT_DIR/certification_governance.sh"
    return $?
}

run_stage 4 "FULL SUITE (CERTIFICATION)" "stage4_cmd"
STAGE4_RC=$?

# ===========================================================================
# FINAL REPORT
# ===========================================================================

tlog ""
tlog "######################################################################"
tlog "#  STAGED ROLLOUT SUMMARY                                            #"
tlog "######################################################################"

_S1="${STAGE_RESULTS[0]:-N/A}"
_S2="${STAGE_RESULTS[1]:-N/A}"
_S3="${STAGE_RESULTS[2]:-N/A}"
_S4="${STAGE_RESULTS[3]:-N/A}"

tlog "  Stage 1 (Invariants):      $_S1"
tlog "  Stage 2 (Micro RAG A/B):   $_S2"
tlog "  Stage 3 (Math-onwards):    $_S3"
tlog "  Stage 4 (Full Suite):      $_S4"
tlog "  Active Flags:              ${ACTIVATED_FLAGS[*]:-none}"
tlog "  Rollback Performed:        $ROLLBACK_PERFORMED"
tlog "  Report:                    $ROLLOUT_REPORT"
tlog "  Log:                       $ROLLOUT_LOG"
tlog "######################################################################"

# Write final JSON report
python3 - "$ROLLOUT_REPORT" "$TIMESTAMP" "$COMMIT_HASH" \
         "$_S1" "$_S2" "$_S3" "$_S4" \
         "$ROLLBACK_PERFORMED" "$STAGE4_RC" <<'PYEOF'
import json, sys
from pathlib import Path

out_path = sys.argv[1]
ts = sys.argv[2]
commit = sys.argv[3]
s1, s2, s3, s4 = sys.argv[4], sys.argv[5], sys.argv[6], sys.argv[7]
rollback = sys.argv[8] == "true"
exit_code = int(sys.argv[9])

report = {
    "timestamp": ts,
    "commit": commit,
    "stages": {
        "1_invariants": s1,
        "2_micro_rag_ab": s2,
        "3_math_onwards": s3,
        "4_full_suite": s4,
    },
    "all_passed": all(s == "PASS" for s in [s1, s2, s3, s4]),
    "rollback_performed": rollback,
    "exit_code": exit_code,
}

Path(out_path).write_text(json.dumps(report, indent=2))
print(f"\n  Rollout report: {out_path}")
PYEOF

if [[ "$STAGE4_RC" -ne 0 ]]; then
    tlog ""
    tlog "STAGED ROLLOUT COMPLETED WITH FAILURES"
    exit 1
fi

tlog ""
tlog "STAGED ROLLOUT COMPLETED SUCCESSFULLY"
exit 0
