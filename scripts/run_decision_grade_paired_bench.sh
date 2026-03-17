#!/usr/bin/env bash
# PROMPT — RUN DECISION-GRADE PAIRED BENCH (10% THEN CLEAN) WITH MCQ + 5xx HARDENING
#
# Mission:
# I will (1) determine if a paired benchmark is already running, (2) if not, start a 10% paired benchmark
# with MCQ diagnostics enabled to validate benchmark integrity, (3) if it passes sanity checks, rerun
# a clean 10% paired benchmark for the decision artifact, and (4) run the promotion gate on the report.
#
# Non-negotiables:
# - I do NOT change production defaults. This is internal bench only.
# - I do NOT run multiple benchmark processes concurrently (avoids provider throttling + corrupted outputs).
# - I keep results reproducible (fixed seed, fixed min-per-category).
# - I fail fast if infra failures or MCQ skew indicates the run is invalid.
#
# Usage: bash scripts/run_decision_grade_paired_bench.sh
# Or:    run in tmux for crash resistance
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"
echo "Repo: $(pwd)"
echo "Branch: $(git branch --show-current)"
echo "HEAD:   $(git rev-parse --short=12 HEAD)"

# ------------------------------------------------------------
# A) Is a benchmark already running?
# ------------------------------------------------------------
echo ""
echo "Checking for an existing benchmark process..."
if pgrep -f "scripts/run_short_paired_benchmark.py" >/dev/null 2>&1; then
  echo "FOUND: run_short_paired_benchmark.py is already running."
  echo "Action: do NOT start another run. Monitor logs / wait for completion."
  pgrep -af "scripts/run_short_paired_benchmark.py" || true
  exit 0
fi
if pgrep -f "run_paired_bench_10pct.sh" >/dev/null 2>&1; then
  echo "FOUND: run_paired_bench_10pct.sh is already running."
  echo "Action: do NOT start another run. Monitor logs / wait for completion."
  pgrep -af "run_paired_bench_10pct.sh" || true
  exit 0
fi
if pgrep -f "run_decision_grade_paired_bench.sh" >/dev/null 2>&1; then
  _other=$(pgrep -af "run_decision_grade_paired_bench.sh" | grep -v "$$" || true)
  if [ -n "$_other" ]; then
    echo "FOUND: Another run_decision_grade_paired_bench.sh is already running."
    echo "Action: do NOT start another run. Monitor logs / wait for completion."
    echo "$_other"
    exit 0
  fi
fi
echo "No running paired benchmark process detected."

# ------------------------------------------------------------
# B) Preflight: ensure scripts exist
# ------------------------------------------------------------
echo ""
echo "Sanity-checking required scripts..."
test -f scripts/run_short_paired_benchmark.py
test -f scripts/run_policy_promotion_gate.py
# Optional shell wrapper (ok if missing)
if [ -f scripts/run_paired_bench_10pct.sh ]; then
  echo "Wrapper present: scripts/run_paired_bench_10pct.sh"
else
  echo "Wrapper not found (ok). Will run python entrypoint directly."
fi

# ------------------------------------------------------------
# C) Export deterministic bench settings (internal bench only)
# ------------------------------------------------------------
export CATEGORY_BENCH_SEED="${CATEGORY_BENCH_SEED:-1337}"
export ELITE_PLUS_ENABLED=1
export ALLOW_INTERNAL_BENCH=1
# Leader-first is enabled for INTERNAL bench only.
export ELITE_PLUS_LEADERBOARD_AWARE=1
export ELITE_PLUS_LEADER_FIRST_ALLOWED=1
export ELITE_PLUS_LEADER_FIRST_INTERNAL_BENCH_ONLY=1
# MCQ diagnostic run first (to validate extraction correctness)
export MCQ_DIAGNOSTIC_MODE=1
# Tie-break policy: prefer a free 3rd voter first (keeps costs down)
export ELITE_PLUS_BENCH_MCQ_TIEBREAK="${ELITE_PLUS_BENCH_MCQ_TIEBREAK:-third_free}"
# Optional: make benchmark mode explicit if the code uses it
export BENCHMARK_MODE="${BENCHMARK_MODE:-1}"
# Telemetry: ensure shadow answer and eval telemetry are included in API responses
export ALLOW_INTERNAL_BENCH_OUTPUT="${ALLOW_INTERNAL_BENCH_OUTPUT:-1}"
export ELITE_PLUS_EVAL="${ELITE_PLUS_EVAL:-1}"
# Provider warmup (warm connection pools before benchmark)
export ELITE_PLUS_WARMUP="${ELITE_PLUS_WARMUP:-0}"
# RAG learning loop (internal bench only)
export RAG_LEARNING_MODE="${RAG_LEARNING_MODE:-0}"
# Dominance v3 hybrid ensemble (off by default; set ELITE_PLUS_ENABLE_DOMINANCE_V3=1 to activate)
export ELITE_PLUS_ENABLE_DOMINANCE_V3="${ELITE_PLUS_ENABLE_DOMINANCE_V3:-0}"
# Production split routing (off by default; set ELITE_PLUS_PRODUCTION_SPLIT=1 to activate)
export ELITE_PLUS_PRODUCTION_SPLIT="${ELITE_PLUS_PRODUCTION_SPLIT:-0}"
# Stability V1 gate (off by default; enables soft anchor guard, provider health auto-disable)
export ELITE_PLUS_STABILITY_V1="${ELITE_PLUS_STABILITY_V1:-0}"
# v2 is disabled when v3 is active (v3 delegates to v2 for tool_use/rag/multilingual/math)
if [ "$ELITE_PLUS_ENABLE_DOMINANCE_V3" = "1" ]; then
  export ELITE_PLUS_ENABLE_DOMINANCE_V2=1
fi

# ------------------------------------------------------------
# D) Run 10% paired benchmark (diagnostic) with robust logging
# ------------------------------------------------------------
TS="$(date -u +%Y%m%dT%H%M%SZ)"
LOG_DIR="benchmark_reports/logs"
mkdir -p "$LOG_DIR"
DIAG_LOG="$LOG_DIR/paired_10pct_diag_$TS.log"

echo ""
echo "Starting 10% paired benchmark (DIAGNOSTIC) ..."
echo "Log: $DIAG_LOG"
echo "Seed: $CATEGORY_BENCH_SEED"
echo "TieBreak: $ELITE_PLUS_BENCH_MCQ_TIEBREAK"

# Run in a way that preserves output even if the terminal dies.
# If you are in tmux, great. If not, this still captures logs.
PYTHONUNBUFFERED=1 python3 scripts/run_short_paired_benchmark.py \
  --sample-percent 10 \
  --seed "$CATEGORY_BENCH_SEED" \
  --min-per-category "reasoning=20 multilingual=20 coding=10 math=20 tool_use=10 rag=40 long_context=10 dialogue=10" \
  2>&1 | tee "$DIAG_LOG"

echo ""
echo "Diagnostic run finished."

# ------------------------------------------------------------
# E) Locate latest paired report JSON and run the promotion gate
# ------------------------------------------------------------
echo ""
echo "Finding the newest paired policy report..."
REPORT_JSON="$(ls -t benchmark_reports/paired_policy_short_*.json 2>/dev/null | head -n 1 || true)"
if [ -z "$REPORT_JSON" ]; then
  echo "ERROR: Could not find benchmark_reports/paired_policy_short_*.json after run."
  echo "Action: inspect the diagnostic log: $DIAG_LOG"
  exit 2
fi
echo "Newest report: $REPORT_JSON"

echo ""
echo "Running promotion gate against diagnostic report (should PASS for integrity)..."
python3 scripts/run_policy_promotion_gate.py --report "$REPORT_JSON" \
  2>&1 | tee "$LOG_DIR/promotion_gate_diag_$TS.log"

echo ""
echo "If the diagnostic run did NOT trigger A-skew / invalid extraction / infra-fail abort, proceed to clean run."

# ------------------------------------------------------------
# F) Re-run 10% paired benchmark (clean, no diagnostics) for publication-quality decision artifact
# ------------------------------------------------------------
export MCQ_DIAGNOSTIC_MODE=0
TS2="$(date -u +%Y%m%dT%H%M%SZ)"
CLEAN_LOG="$LOG_DIR/paired_10pct_clean_$TS2.log"

echo ""
echo "Starting 10% paired benchmark (CLEAN) ..."
echo "Log: $CLEAN_LOG"

PYTHONUNBUFFERED=1 python3 scripts/run_short_paired_benchmark.py \
  --sample-percent 10 \
  --seed "$CATEGORY_BENCH_SEED" \
  --min-per-category "reasoning=20 multilingual=20 coding=10 math=20 tool_use=10 rag=40 long_context=10 dialogue=10" \
  2>&1 | tee "$CLEAN_LOG"

echo ""
echo "Clean run finished."

REPORT_JSON2="$(ls -t benchmark_reports/paired_policy_short_*.json 2>/dev/null | head -n 1 || true)"
if [ -z "$REPORT_JSON2" ]; then
  echo "ERROR: Could not find benchmark_reports/paired_policy_short_*.json after clean run."
  echo "Action: inspect clean log: $CLEAN_LOG"
  exit 3
fi
echo "Newest clean report: $REPORT_JSON2"

echo ""
echo "Running promotion gate against clean report..."
python3 scripts/run_policy_promotion_gate.py --report "$REPORT_JSON2" \
  2>&1 | tee "$LOG_DIR/promotion_gate_clean_$TS2.log"

echo ""
echo "DONE ✅"
echo "Artifacts:"
echo "  Diagnostic log: $DIAG_LOG"
echo "  Clean log:      $CLEAN_LOG"
echo "  Clean report:   $REPORT_JSON2"
echo "Next: review per-category deltas + MCQ telemetry + infra_fail_rate in the report JSON."
