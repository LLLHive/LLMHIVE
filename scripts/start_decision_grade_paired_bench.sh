#!/usr/bin/env bash
# PROMPT — START OR CONFIRM DECISION‑GRADE PAIRED BENCH (10% default)
# Safe to run even if already running: wrapper is idempotent and will exit 0.

set -euo pipefail

cd "$(git rev-parse --show-toplevel)"
_ROOT="$(pwd)"

# Crash resistance: strongly recommended
# If tmux is available, use it. If not, continue in current shell.
if command -v tmux >/dev/null 2>&1; then
  if ! tmux has-session -t paired_bench >/dev/null 2>&1; then
    tmux new-session -d -s paired_bench
  fi
  tmux send-keys -t paired_bench "cd '$_ROOT'" C-m
  tmux send-keys -t paired_bench "echo 'Starting paired benchmark in tmux session: paired_bench'" C-m
else
  echo "tmux not found; continuing in the current shell."
fi

# Determinism
export CATEGORY_BENCH_SEED="${CATEGORY_BENCH_SEED:-1337}"

# Internal-bench-only safety (no production behavior changes)
export ELITE_PLUS_ENABLED=1
export ALLOW_INTERNAL_BENCH=1

# Enable leaderboard metadata usage for the benchmark pathway only
export ELITE_PLUS_LEADERBOARD_AWARE=1
export ELITE_PLUS_LEADER_FIRST_ALLOWED=1
export ELITE_PLUS_LEADER_FIRST_INTERNAL_BENCH_ONLY=1

# MCQ diagnostic first pass + tie behavior (your recent fix expects these)
export MCQ_DIAGNOSTIC_MODE="${MCQ_DIAGNOSTIC_MODE:-1}"
export ELITE_PLUS_BENCH_MCQ_TIEBREAK="${ELITE_PLUS_BENCH_MCQ_TIEBREAK:-third_free}"

# Allow regression so benchmark completes even if scores regress (report still produced)
export ALLOW_REGRESSION="${ALLOW_REGRESSION:-1}"
# Optional: if your code exposes these envs, keep them strict (safe defaults)
export BENCH_5XX_MAX_ATTEMPTS="${BENCH_5XX_MAX_ATTEMPTS:-5}"
# infra_fail_rate is in percent (e.g., 2.0 = 2%)
export BENCH_INFRA_FAIL_RATE_MAX="${BENCH_INFRA_FAIL_RATE_MAX:-2.0}"

# Ensure output dirs exist (does not overwrite anything)
mkdir -p benchmark_reports/logs benchmark_reports/debug

echo "Seed: $CATEGORY_BENCH_SEED"
echo "MCQ_DIAGNOSTIC_MODE: $MCQ_DIAGNOSTIC_MODE"
echo "ELITE_PLUS_BENCH_MCQ_TIEBREAK: $ELITE_PLUS_BENCH_MCQ_TIEBREAK"
echo "Starting wrapper (safe if already running)..."

# Start the idempotent wrapper
if command -v tmux >/dev/null 2>&1; then
  tmux send-keys -t paired_bench "bash scripts/run_decision_grade_paired_bench.sh 2>&1 | tee benchmark_reports/logs/paired_bench_wrapper_\$(date -u +%Y%m%dT%H%M%SZ).log" C-m
  echo "Attached instructions:"
  echo "  tmux attach -t paired_bench"
else
  bash scripts/run_decision_grade_paired_bench.sh 2>&1 | tee "benchmark_reports/logs/paired_bench_wrapper_$(date -u +%Y%m%dT%H%M%SZ).log"
fi

echo "If the wrapper reported 'already running', do NOT restart anything."
echo "To monitor latest logs:"
echo "  ls -t benchmark_reports/logs/* 2>/dev/null | head -n 5"
echo "  tail -f \$(ls -t benchmark_reports/logs/* 2>/dev/null | head -n 1)"
