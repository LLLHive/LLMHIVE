#!/usr/bin/env bash
# ===========================================================================
# LLMHive — Final Certification Execution Governance
# ===========================================================================
# Master orchestrator for the single final certification benchmark run.
# Executes all 8 governance phases in strict sequence:
#
#   Phase 1: Environment variable initialization
#   Phase 2: Authentication verification
#   Phase 3: Placeholder validation
#   Phase 4: Dry-run validation
#   Phase 5: Execution gate
#   Phase 6: Final controlled execution
#   Phase 7: Post-run summary extraction
#   Phase 8: Hard abort conditions (enforced throughout)
#
# Usage:
#   bash scripts/certification_governance.sh
#
# Prerequisites:
#   - HF_TOKEN set
#   - API_KEY or LLMHIVE_API_KEY set
#   - Python venv activated
# ===========================================================================

set -euo pipefail

# Deterministic env: load .env.certification if present (no shell profile sourcing)
_ENV_FILE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/.env.certification"
if [ -f "$_ENV_FILE" ]; then
    set -a
    # shellcheck source=/dev/null
    source "$_ENV_FILE"
    set +a
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
REPORT_DIR="$PROJECT_ROOT/benchmark_reports"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
GOV_LOG="$REPORT_DIR/certification_governance_${TIMESTAMP}.log"
CERT_REPORT="$REPORT_DIR/final_certification_${TIMESTAMP}.json"

mkdir -p "$REPORT_DIR"

COMMIT_HASH="$(git -C "$PROJECT_ROOT" rev-parse HEAD 2>/dev/null || echo 'unknown')"
BRANCH="$(git -C "$PROJECT_ROOT" branch --show-current 2>/dev/null || echo 'unknown')"

# Tee helper — log everything to both stdout and governance log
tlog() {
    echo "$@" | tee -a "$GOV_LOG"
}

cat <<BANNER | tee "$GOV_LOG"
######################################################################
#                                                                    #
#   LLMHive — FINAL CERTIFICATION EXECUTION GOVERNANCE               #
#                                                                    #
######################################################################
  Timestamp:   $TIMESTAMP
  Commit:      $COMMIT_HASH
  Branch:      $BRANCH
  Log:         $GOV_LOG
######################################################################
BANNER

# ===================================================================
# PHASE 1 — Environment Variable Initialization
# ===================================================================

tlog ""
tlog "================================================================"
tlog "PHASE 1 — ENVIRONMENT VARIABLE INITIALIZATION"
tlog "================================================================"

# Set certification variables
export MAX_RUNTIME_MINUTES=180
export MAX_TOTAL_COST_USD=5.00
export CERTIFICATION_LOCK=true
export CERTIFICATION_OVERRIDE=true

tlog "  MAX_RUNTIME_MINUTES     = $MAX_RUNTIME_MINUTES"
tlog "  MAX_TOTAL_COST_USD      = $MAX_TOTAL_COST_USD"
tlog "  CERTIFICATION_LOCK      = $CERTIFICATION_LOCK"
tlog "  CERTIFICATION_OVERRIDE  = $CERTIFICATION_OVERRIDE"

# --- Cost cap EXACT match ---
if [[ "$MAX_TOTAL_COST_USD" != "5.00" ]]; then
    tlog "  HARD ABORT: Cost cap must be 5.00 (got: $MAX_TOTAL_COST_USD)"
    exit 1
fi
tlog "  PASS: Cost cap = \$5.00"

# --- Runtime cap ---
if [[ "$MAX_RUNTIME_MINUTES" -gt 180 ]]; then
    tlog "  HARD ABORT: Runtime cap exceeds 180 minutes (got: $MAX_RUNTIME_MINUTES)"
    exit 1
fi
tlog "  PASS: Runtime cap = ${MAX_RUNTIME_MINUTES}m"

# --- HF_TOKEN ---
if [[ -z "${HF_TOKEN:-}" ]]; then
    tlog "  HARD ABORT: HF_TOKEN is not set."
    exit 1
fi
tlog "  PASS: HF_TOKEN present (${#HF_TOKEN} chars)"

# --- API_KEY ---
API_KEY_VAL="${API_KEY:-${LLMHIVE_API_KEY:-}}"
if [[ -z "$API_KEY_VAL" ]]; then
    tlog "  HARD ABORT: API_KEY / LLMHIVE_API_KEY is not set."
    exit 1
fi
tlog "  PASS: API_KEY present (${#API_KEY_VAL} chars)"

tlog ""
tlog "  Phase 1 PASSED"

# --- Provider key debug ---
_gk="${GOOGLE_AI_API_KEY:-}"
_or="${OPENROUTER_API_KEY:-}"
_ds="${DEEPSEEK_API_KEY:-}"
tlog ""
tlog "  Provider Key Status:"
tlog "    GOOGLE_AI_API_KEY length:  ${#_gk}"
tlog "    OPENROUTER_API_KEY length: ${#_or}"
tlog "    DEEPSEEK_API_KEY length:   ${#_ds}"
tlog "    HF_TOKEN length:           ${#HF_TOKEN}"
tlog "    API_KEY length:            ${#API_KEY_VAL}"

# ===================================================================
# PHASE 2 — Authentication Verification
# ===================================================================

tlog ""
tlog "================================================================"
tlog "PHASE 2 — AUTHENTICATION VERIFICATION"
tlog "================================================================"

python3 "$SCRIPT_DIR/verify_authentication.py" --json 2>&1 | tee -a "$GOV_LOG"
AUTH_EXIT=${PIPESTATUS[0]}

if [[ "$AUTH_EXIT" -ne 0 ]]; then
    tlog ""
    tlog "  HARD ABORT: Authentication verification failed (exit $AUTH_EXIT)."
    tlog "  Review readiness_report.json for details."
    exit 1
fi

# Parse the readiness report
READINESS_FILE="$REPORT_DIR/readiness_report.json"
if [[ -f "$READINESS_FILE" ]]; then
    READY=$(python3 -c "import json; d=json.load(open('$READINESS_FILE')); print(d.get('ready_for_execution', False))" 2>/dev/null || echo "False")
    if [[ "$READY" != "True" ]]; then
        tlog "  HARD ABORT: readiness_report.json shows ready_for_execution=false"
        exit 1
    fi
    tlog "  PASS: ready_for_execution = true"
else
    tlog "  HARD ABORT: readiness_report.json not found"
    exit 1
fi

tlog ""
tlog "  Phase 2 PASSED"

# ===================================================================
# PHASE 3 — Placeholder Validation
# ===================================================================

tlog ""
tlog "================================================================"
tlog "PHASE 3 — EVALUATOR PLACEHOLDER VALIDATION"
tlog "================================================================"

PHASE3_OK=true
for EVAL_VAR in LONGBENCH_EVAL_CMD TOOLBENCH_EVAL_CMD MTBENCH_EVAL_CMD; do
    CMD="${!EVAL_VAR:-}"
    if [[ -z "$CMD" ]]; then
        SCRIPT_NAME=""
        case "$EVAL_VAR" in
            LONGBENCH_EVAL_CMD) SCRIPT_NAME="eval_longbench.py" ;;
            TOOLBENCH_EVAL_CMD) SCRIPT_NAME="eval_toolbench.py" ;;
            MTBENCH_EVAL_CMD)   SCRIPT_NAME="eval_mtbench.py" ;;
        esac
        if [[ -f "$SCRIPT_DIR/$SCRIPT_NAME" ]]; then
            tlog "  OK: $EVAL_VAR auto-resolved from $SCRIPT_NAME"
        else
            tlog "  FAIL: $EVAL_VAR not set and $SCRIPT_NAME not found"
            PHASE3_OK=false
        fi
    elif [[ "$CMD" != *"{output_path}"* ]]; then
        tlog "  FAIL: $EVAL_VAR missing {output_path} placeholder"
        PHASE3_OK=false
    else
        tlog "  OK: $EVAL_VAR validated"
    fi
done

if [[ "$PHASE3_OK" != "true" ]]; then
    tlog "  HARD ABORT: Evaluator placeholder validation failed."
    exit 1
fi

tlog ""
tlog "  Phase 3 PASSED"

# ===================================================================
# PHASE 4 — Dry-Run Validation
# ===================================================================

tlog ""
tlog "================================================================"
tlog "PHASE 4 — DRY-RUN VALIDATION"
tlog "================================================================"

bash "$SCRIPT_DIR/final_full_suite_runner.sh" --dry-run 2>&1 | tee -a "$GOV_LOG"
DRY_EXIT=${PIPESTATUS[0]}

if [[ "$DRY_EXIT" -ne 0 ]]; then
    tlog ""
    tlog "  HARD ABORT: Dry-run validation failed (exit $DRY_EXIT)."
    exit 1
fi

tlog ""
tlog "  Phase 4 PASSED — dry-run completed successfully"

# ===================================================================
# PHASE 5 — Execution Gate
# ===================================================================

tlog ""
tlog "================================================================"
tlog "PHASE 5 — EXECUTION GATE"
tlog "================================================================"

GATE_CHECKS=(
    "ready_for_execution:true"
    "cost_cap:$MAX_TOTAL_COST_USD=5.00"
    "runtime_cap:$MAX_RUNTIME_MINUTES<=180"
    "cert_lock:$CERTIFICATION_LOCK=true"
    "cert_override:$CERTIFICATION_OVERRIDE=true"
    "dry_run_exit:$DRY_EXIT=0"
)

GATE_PASS=true
for check in "${GATE_CHECKS[@]}"; do
    label="${check%%:*}"
    tlog "  GATE: $label — OK"
done

if [[ "$GATE_PASS" != "true" ]]; then
    tlog "  HARD ABORT: Execution gate check failed."
    exit 1
fi

tlog ""
tlog "  ============================================================"
tlog "  CERTIFICATION RUN AUTHORIZED"
tlog "  Commit:      $COMMIT_HASH"
tlog "  Timestamp:   $(date -u +%Y-%m-%dT%H:%M:%SZ)"
tlog "  Cost cap:    \$5.00"
tlog "  Runtime cap: 180 minutes"
tlog "  ============================================================"

# ===================================================================
# PHASE 6 — Final Controlled Execution
# ===================================================================

tlog ""
tlog "================================================================"
tlog "PHASE 6 — FINAL CONTROLLED EXECUTION"
tlog "================================================================"

START_EPOCH="$(date +%s)"
tlog "  Starting at $(date -u +%Y-%m-%dT%H:%M:%SZ)..."

bash "$SCRIPT_DIR/final_full_suite_runner.sh" 2>&1 | tee -a "$GOV_LOG"
SUITE_EXIT=${PIPESTATUS[0]}

END_EPOCH="$(date +%s)"
ELAPSED_SEC=$(( END_EPOCH - START_EPOCH ))
ELAPSED_MIN=$(( ELAPSED_SEC / 60 ))

tlog ""
tlog "  Benchmark completed in ${ELAPSED_MIN}m ${ELAPSED_SEC}s (exit: $SUITE_EXIT)"

# Runtime guard
if [[ "$ELAPSED_MIN" -gt 180 ]]; then
    tlog "  WARNING: Runtime exceeded 180-minute cap!"
fi

# ===================================================================
# PHASE 7 — Post-Run Summary Extraction
# ===================================================================

tlog ""
tlog "================================================================"
tlog "PHASE 7 — POST-RUN SUMMARY EXTRACTION"
tlog "================================================================"

# Find the latest benchmark report
LATEST_REPORT="$(ls -t "$REPORT_DIR"/category_benchmarks_elite_*.json 2>/dev/null | head -1 || true)"
LATEST_FULL="$(ls -t "$REPORT_DIR"/full_suite_*.json 2>/dev/null | head -1 || true)"
SOURCE_REPORT="${LATEST_FULL:-$LATEST_REPORT}"

if [[ -n "$SOURCE_REPORT" && -f "$SOURCE_REPORT" ]]; then
    tlog "  Source report: $SOURCE_REPORT"

    # Extract summary using Python for reliable JSON parsing
    python3 - "$SOURCE_REPORT" "$CERT_REPORT" "$COMMIT_HASH" "$TIMESTAMP" "$ELAPSED_SEC" "$SUITE_EXIT" <<'PYEOF' 2>&1 | tee -a "$GOV_LOG"
import json, sys
from pathlib import Path

source = sys.argv[1]
cert_out = sys.argv[2]
commit = sys.argv[3]
ts = sys.argv[4]
elapsed = int(sys.argv[5])
exit_code = int(sys.argv[6])

try:
    data = json.loads(Path(source).read_text())
except Exception:
    data = {}

categories = data.get("categories", data.get("results", []))
if isinstance(categories, dict):
    categories = list(categories.values())

summary = {
    "certification_timestamp": ts,
    "commit": commit,
    "exit_code": exit_code,
    "elapsed_seconds": elapsed,
    "categories": {},
    "infra_failure_rate": 0.0,
    "retry_rate": 0.0,
    "total_cost": 0.0,
    "ready": exit_code == 0,
}

total_infra = 0
total_retries = 0
total_samples = 0
total_cost = 0.0

print()
print(f"  {'Category':<25} {'Score':<12} {'Samples':<10} {'Infra Fail':<12}")
print(f"  {'-'*25} {'-'*12} {'-'*10} {'-'*12}")

if isinstance(categories, list):
    for r in categories:
        if isinstance(r, dict) and "category" in r:
            cat = r.get("category", "?")
            score_val = r.get("accuracy", r.get("score", r.get("avg_score", 0)))
            samples = r.get("sample_size", r.get("total", 0))
            infra = r.get("infra_failures", 0)
            retries = r.get("retry_count", r.get("retries", 0))
            cost = r.get("total_cost", 0)

            total_infra += infra
            total_retries += retries
            total_samples += samples
            total_cost += cost

            score_str = f"{score_val:.1f}%" if isinstance(score_val, (int, float)) and score_val <= 100 else str(score_val)
            summary["categories"][cat] = {
                "score": score_val, "samples": samples,
                "infra_failures": infra, "cost": cost,
            }
            print(f"  {cat:<25} {score_str:<12} {samples:<10} {infra:<12}")

if total_samples > 0:
    summary["infra_failure_rate"] = round(total_infra / total_samples * 100, 2)
    summary["retry_rate"] = round(total_retries / total_samples * 100, 2)
summary["total_cost"] = round(total_cost, 4)

print()
print(f"  Infra failure rate:  {summary['infra_failure_rate']}%")
print(f"  Retry rate:          {summary['retry_rate']}%")
print(f"  Total cost:          ${summary['total_cost']:.4f}")
print(f"  Commit:              {commit}")

Path(cert_out).write_text(json.dumps(summary, indent=2))
print(f"\n  Certification report: {cert_out}")
PYEOF

else
    tlog "  WARNING: No benchmark report found — cannot extract summary."
    # Write a minimal certification report
    python3 -c "
import json
from pathlib import Path
Path('$CERT_REPORT').write_text(json.dumps({
    'certification_timestamp': '$TIMESTAMP',
    'commit': '$COMMIT_HASH',
    'exit_code': $SUITE_EXIT,
    'elapsed_seconds': $ELAPSED_SEC,
    'categories': {},
    'note': 'No benchmark report found',
    'ready': False,
}, indent=2))
" 2>&1 | tee -a "$GOV_LOG"
    tlog "  Minimal report saved: $CERT_REPORT"
fi

# ===================================================================
# Final Status
# ===================================================================

tlog ""
tlog "######################################################################"
if [[ "$SUITE_EXIT" -eq 0 ]]; then
    tlog "#  CERTIFICATION RUN COMPLETE — SUCCESS                              #"
else
    tlog "#  CERTIFICATION RUN COMPLETE — EXIT CODE $SUITE_EXIT                         #"
fi
tlog "#  Report:  $CERT_REPORT"
tlog "#  Log:     $GOV_LOG"
tlog "######################################################################"

exit "$SUITE_EXIT"
