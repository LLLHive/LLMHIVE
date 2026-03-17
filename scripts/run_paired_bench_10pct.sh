#!/usr/bin/env bash
# Decision-grade paired benchmark (10% first)
# Compares free_first_verified vs leader_first_verified on stratified sample.
set -euo pipefail

# ---------- Config ----------
export SAMPLE_PERCENT="${SAMPLE_PERCENT:-10}"
export CATEGORY_BENCH_SEED="${CATEGORY_BENCH_SEED:-20260308}"
export MIN_PER_CATEGORY="${MIN_PER_CATEGORY:-reasoning=20 multilingual=20 coding=10 math=20 tool_use=10 rag=40 long_context=10 dialogue=10}"

# Internal bench gating (does NOT alter production defaults)
export ELITE_PLUS_ENABLED=1
export ALLOW_INTERNAL_BENCH=1
export ELITE_PLUS_LEADERBOARD_AWARE=1
export ELITE_PLUS_LEADER_FIRST_ALLOWED=1
export ELITE_PLUS_LEADER_FIRST_INTERNAL_BENCH_ONLY=1
# Optional: MCQ_DIAGNOSTIC_MODE=1 for debug JSONL; ELITE_PLUS_BENCH_MCQ_TIEBREAK=third_free for tie-break
export MCQ_DIAGNOSTIC_MODE="${MCQ_DIAGNOSTIC_MODE:-0}"
export ELITE_PLUS_BENCH_MCQ_TIEBREAK="${ELITE_PLUS_BENCH_MCQ_TIEBREAK:-}"

# Keep production behavior unchanged by default
export ELITE_PLUS_POLICY="${ELITE_PLUS_POLICY:-free_first_verified}"
export ELITE_PLUS_ENABLE_AUTO_DOMINANCE="${ELITE_PLUS_ENABLE_AUTO_DOMINANCE:-0}"

# ---------- Safety: refuse to run if benchmark already running ----------
echo "Checking for existing paired benchmark process..."
if ps aux 2>/dev/null | grep -E "run_short_paired_benchmark\.py|PAIRED_POLICY_OVERRIDE" | grep -v grep >/dev/null; then
  echo "ERROR: A paired benchmark process appears to already be running. Refusing to start another run."
  ps aux | grep -E "run_short_paired_benchmark\.py|PAIRED_POLICY_OVERRIDE" | grep -v grep || true
  exit 2
fi

# Optional: warn if marketing pipeline is running
echo "Checking for marketing pipeline activity..."
if ps aux 2>/dev/null | grep -E "run_marketing_certified_release\.py|run_category_benchmarks\.py" | grep -v grep >/dev/null; then
  echo "WARNING: Marketing pipeline appears to be running. This can distort benchmark results via rate limits."
  echo "Recommendation: run this paired benchmark in CI / separate machine, or wait."
fi

# ---------- Create run dirs ----------
cd "$(git rev-parse --show-toplevel)"
mkdir -p artifacts/paired_bench
mkdir -p benchmark_reports

RUN_TS="$(date -u +%Y%m%dT%H%M%SZ)"
LOG="artifacts/paired_bench/paired_bench_${RUN_TS}.log"
echo "Logging to: $LOG"

# ---------- Clean checkpoint for fresh paired run ----------
CHECKPOINT="benchmark_reports/category_benchmarks_checkpoint.json"
if [ -f "$CHECKPOINT" ]; then
  echo "Removing existing checkpoint for fresh paired run..." | tee -a "$LOG"
  rm -f "$CHECKPOINT"
fi

# ---------- Quick sanity checks ----------
echo "Python:" | tee -a "$LOG"
python3 --version | tee -a "$LOG"
echo "Verifying script exists..." | tee -a "$LOG"
test -f scripts/run_short_paired_benchmark.py
echo "Compiling the benchmark script..." | tee -a "$LOG"
python3 -m py_compile scripts/run_short_paired_benchmark.py 2>&1 | tee -a "$LOG"

# ---------- Run benchmark ----------
echo "Starting paired benchmark: sample=${SAMPLE_PERCENT}% seed=${CATEGORY_BENCH_SEED} min-per-category=${MIN_PER_CATEGORY}" | tee -a "$LOG"
python3 scripts/run_short_paired_benchmark.py \
  --sample-percent "$SAMPLE_PERCENT" \
  --min-per-category "$MIN_PER_CATEGORY" \
  --seed "$CATEGORY_BENCH_SEED" \
  2>&1 | tee -a "$LOG"

# ---------- Locate newest report ----------
REPORT="$(ls -t benchmark_reports/paired_policy_short_*.json 2>/dev/null | head -n 1)"
if [ -z "${REPORT:-}" ] || [ ! -f "$REPORT" ]; then
  echo "ERROR: Expected paired benchmark report was not created under benchmark_reports/." | tee -a "$LOG"
  exit 3
fi
echo "Paired benchmark report: $REPORT" | tee -a "$LOG"

# ---------- Run promotion gate ----------
echo "Running promotion gate..." | tee -a "$LOG"
python3 scripts/run_policy_promotion_gate.py --report "$REPORT" 2>&1 | tee -a "$LOG" || true
echo "Promotion gate completed." | tee -a "$LOG"

# ---------- Archive artifacts ----------
OUTDIR="artifacts/paired_bench/run_${RUN_TS}"
mkdir -p "$OUTDIR"
cp -f "$REPORT" "$OUTDIR/"
cp -f "$LOG" "$OUTDIR/"
echo "$CATEGORY_BENCH_SEED" > "$OUTDIR/seed.txt"
echo "$SAMPLE_PERCENT" > "$OUTDIR/sample_percent.txt"
echo "$MIN_PER_CATEGORY" > "$OUTDIR/min_per_category.txt"

echo "Archived run bundle at: $OUTDIR"
echo "DONE ✅"
