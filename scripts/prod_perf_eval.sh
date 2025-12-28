#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"

UTC_TS="$(date -u +"%Y%m%dT%H%M%SZ")"
LOG_DIR="$REPO_ROOT/logs/prod_perf_eval_${UTC_TS}"
mkdir -p "$LOG_DIR"

# log everything
exec > >(tee "$LOG_DIR/run.log") 2>&1

section() { echo ""; echo "▶ $1"; }

echo "LLMHive Prod Perf Eval Round"
echo "repo_root=$REPO_ROOT"
echo "utc_timestamp=$UTC_TS"
echo "git_sha=$(git rev-parse HEAD)"
echo "git_branch=$(git rev-parse --abbrev-ref HEAD)"
python -V || true

# ==============================================================================
# Parse flags and determine run mode
# ==============================================================================
# DRY_RUN_ONLY=1       → cheap mode, no secrets required
# RUN_FULL_MODELDB=1   → full run, secrets required
# RUN_UPDATE_STEP=1    → update step only, OpenRouter key required
# RUN_PIPELINE_STEP=1  → pipeline step, Pinecone + GCP keys required

DRY_RUN_ONLY="${DRY_RUN_ONLY:-0}"
RUN_FULL_MODELDB="${RUN_FULL_MODELDB:-0}"
RUN_UPDATE_STEP="${RUN_UPDATE_STEP:-0}"
RUN_PIPELINE_STEP="${RUN_PIPELINE_STEP:-0}"

# Determine if we need secrets
NEEDS_SECRETS=0
if [[ "$RUN_FULL_MODELDB" == "1" ]] || \
   [[ "$RUN_UPDATE_STEP" == "1" ]] || \
   [[ "$RUN_PIPELINE_STEP" == "1" ]]; then
  NEEDS_SECRETS=1
fi

echo ""
echo "Mode: DRY_RUN_ONLY=$DRY_RUN_ONLY RUN_FULL_MODELDB=$RUN_FULL_MODELDB"
echo "      RUN_UPDATE_STEP=$RUN_UPDATE_STEP RUN_PIPELINE_STEP=$RUN_PIPELINE_STEP"
echo "      NEEDS_SECRETS=$NEEDS_SECRETS"

# ------------------------------------------------------------------------------
# Guardrail: ensure nothing secret-like is TRACKED
# ----------------------------------------------------------------------------
section "secret_tracking_guardrail"
if command -v rg >/dev/null 2>&1; then
  if git ls-files | rg -n "data/modeldb/secrets|modeldb-writer|service-account|private_key" ; then
    echo "❌ Secret-like TRACKED files detected. STOP."
    exit 2
  fi
else
  if git ls-files | grep -E "data/modeldb/secrets|modeldb-writer|service-account|private_key" ; then
    echo "❌ Secret-like TRACKED files detected. STOP."
    exit 2
  fi
fi
echo "OK: No secret-like tracked files detected."

# ------------------------------------------------------------------------------
# Secret scan (repo-level)
# ------------------------------------------------------------------------------
section "secret_scan"
python scripts/check_no_service_account_keys.py

# ------------------------------------------------------------------------------
# Secret Manager Injection (if secrets needed and not already set)
# ------------------------------------------------------------------------------
if [[ "$NEEDS_SECRETS" == "1" ]]; then
  section "secret_manager_injection"
  
  # Check if secrets are already set
  SECRETS_OK=1
  if [[ -z "${OPENROUTER_API_KEY:-}" ]]; then
    echo "OPENROUTER_API_KEY: NOT SET"
    SECRETS_OK=0
  else
    echo "OPENROUTER_API_KEY: SET (${#OPENROUTER_API_KEY} chars)"
  fi
  
  if [[ -z "${PINECONE_API_KEY:-}" ]]; then
    echo "PINECONE_API_KEY: NOT SET"
    SECRETS_OK=0
  else
    echo "PINECONE_API_KEY: SET (${#PINECONE_API_KEY} chars)"
  fi
  
  # Attempt injection if needed
  if [[ "$SECRETS_OK" == "0" ]]; then
    echo ""
    echo "Attempting Secret Manager injection..."
    
    if [[ -f "$REPO_ROOT/scripts/gcp_secret_inject.sh" ]]; then
      # Source the injection script (will export vars)
      set +e
      # shellcheck source=./gcp_secret_inject.sh
      source "$REPO_ROOT/scripts/gcp_secret_inject.sh"
      INJECT_EXIT=$?
      set -e
      
      if [[ $INJECT_EXIT -ne 0 ]]; then
        echo ""
        echo "❌ SECRET INJECTION FAILED"
        echo ""
        echo "This expensive run requires API keys but they are not available."
        echo ""
        echo "To fix, use ONE of these methods:"
        echo ""
        echo "  1. Set env vars directly:"
        echo "     export OPENROUTER_API_KEY=sk-or-..."
        echo "     export PINECONE_API_KEY=..."
        echo ""
        echo "  2. Inject from Secret Manager (requires gcloud):"
        echo "     source scripts/gcp_secret_inject.sh"
        echo ""
        echo "  3. In Cloud Run, attach Secret Manager secrets as env vars"
        echo ""
        echo "  4. Run in dry-run mode (no secrets needed):"
        echo "     DRY_RUN_ONLY=1 bash scripts/prod_perf_eval.sh"
        echo ""
        exit 3
      fi
    else
      echo "❌ gcp_secret_inject.sh not found at $REPO_ROOT/scripts/"
      exit 3
    fi
    
    # Verify injection worked
    if [[ -z "${OPENROUTER_API_KEY:-}" ]] || [[ -z "${PINECONE_API_KEY:-}" ]]; then
      echo ""
      echo "❌ SECRET INJECTION INCOMPLETE"
      echo "   OPENROUTER_API_KEY: ${OPENROUTER_API_KEY:+SET}${OPENROUTER_API_KEY:-NOT SET}"
      echo "   PINECONE_API_KEY: ${PINECONE_API_KEY:+SET}${PINECONE_API_KEY:-NOT SET}"
      echo ""
      echo "Blocking expensive run. Set missing secrets or use DRY_RUN_ONLY=1"
      exit 3
    fi
    
    echo "✅ Secrets injected successfully"
  else
    echo "✅ All required secrets already set"
  fi
fi

# ------------------------------------------------------------------------------
# ModelDB doctor + dry-run (cheap, no writes)
# ------------------------------------------------------------------------------
section "modeldb_doctor"
python data/modeldb/run_modeldb_refresh.py --doctor || true

section "modeldb_dry_run"
python data/modeldb/run_modeldb_refresh.py --dry-run \
  --evals-enabled false --telemetry-enabled false

# If DRY_RUN_ONLY mode, stop here (cheap run complete)
if [[ "$DRY_RUN_ONLY" == "1" ]]; then
  echo ""
  echo "✅ DRY_RUN_ONLY=1 → Stopping after dry-run (cheap mode complete)."
  echo "   To run full evaluation: RUN_FULL_MODELDB=1 bash scripts/prod_perf_eval.sh"
  echo ""
  exit 0
fi

# ------------------------------------------------------------------------------
# HARD GATE: pytest must pass before any “performance evaluation” can run
# ------------------------------------------------------------------------------
section "pytest_gate"
set +e
python -m pytest -q \
  data/modeldb/tests/test_hf_enricher_safety.py \
  data/modeldb/tests/test_eval_telemetry_safety.py
PYTEST_EXIT=$?
set -e

if [[ $PYTEST_EXIT -ne 0 ]]; then
  echo "❌ Tests failed. BLOCKING performance evaluation."
  echo "Fix tests first, then re-run:"
  echo "  bash scripts/prod_perf_eval.sh"
  exit $PYTEST_EXIT
fi
echo "✅ Tests passed. Proceeding."

# ----------------------------------------------------------------------
# Optional: KB orchestrator evaluation (safe)
# ------------------------------------------------------------------------------
section "kb_orchestrator_eval"
if [[ -f scripts/eval_orchestrator_kb.py ]]; then
  python scripts/eval_orchestrator_kb.py
else
  echo "SKIP: scripts/eval_orchestrator_kb.py not found"
fi

# ------------------------------------------------------------------------------
# Optional: FULL ModelDB run with evals+telemetry (costly / needs keys)
# ------------------------------------------------------------------------------
section "modeldb_full_run_optional"
if [[ "${RUN_FULL_MODELDB:-0}" == "1" ]]; then
  echo "RUN_FULL_MODELDB=1 set → running full ModelDB refresh with evals+telemetry (limited defaults)."
  python data/modeldb/run_modeldb_refresh.py \
    --evals-enabled true --telemetry-enabled true \
    --evals-max-models "${EVALS_MAX_MODELS:-10}" \
    --telemetry-max-models "${TELEMETRY_MAX_MODELS:-10}" \
    --telemetry-trials "${TELEMETRY_TRIALS:-3}"
else
  echo "SKIP fullun. To run the costly full production eval, do:"
  echo "  RUN_FULL_MODELDB=1 EVALS_MAX_MODELS=10 TELEMETRY_MAX_MODELS=10 TELEMETRY_TRIALS=3 bash scripts/prod_perf_eval.sh"
fi

# ------------------------------------------------------------------------------
# Coverage report (cheap; helps confirm attempt-vs-metric reporting)
# ------------------------------------------------------------------------------
section "coverage_report"
python data/modeldb/modeldb_coverage_report.py

# ------------------------------------------------------------------------------
# Show latest artifacts
# ------------------------------------------------------------------------------
section "artifacts"
latest_refresh="$(ls -1t data/modeldb/archives/refresh_runlog_*.json 2>/dev/null | head -n 1 || true)"
latest_cov_md="$(ls -1t data/modeldb/archives/coverage_report_*.md 2>/dev/null | head -n 1 || true)"
latest_cov_json="$(ls -1t data/modeldb/archives/coverage_report_*.json 2>/dev/null | head -n 1 || true)"

{
  echo "Latest refresh runlog: ${latest_refresh:-NONE}"
  echo "Latest coverage report md: ${latest_cov_md:-NONE}"
  echo "Latest coverage report json: ${latest_cov_json:-NONE}"
} | tee "$LOG_DIR/latest_artifacts.txt"

if [[ -n "${latest_cov_md:-}" && -f "$latest_cov_md" ]]; then
  echo ""
  echo "Coverage report tail:"
  tail -n 80 "$latest_cov_md" | tee "$LOG_DIR/coverage_report_tail.txt"
fi

echo ""
echo "✅ DONE"
echo "Logs: $LOG_DIR"
