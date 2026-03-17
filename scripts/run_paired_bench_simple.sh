#!/usr/bin/env bash
# Simple paired benchmark runner — copy/paste or: bash scripts/run_paired_bench_simple.sh
# Fixes: --min-per-category must be ONE quoted string (not separate args)
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

export CATEGORY_BENCH_SEED="${CATEGORY_BENCH_SEED:-1337}"
export ALLOW_REGRESSION=1
export ELITE_PLUS_ENABLED=1
export ALLOW_INTERNAL_BENCH=1
export ELITE_PLUS_LEADERBOARD_AWARE=1
export ELITE_PLUS_LEADER_FIRST_ALLOWED=1
export ELITE_PLUS_LEADER_FIRST_INTERNAL_BENCH_ONLY=1
export MCQ_DIAGNOSTIC_MODE="${MCQ_DIAGNOSTIC_MODE:-0}"
export ELITE_PLUS_BENCH_MCQ_TIEBREAK=third_free

# IMPORTANT: min-per-category must be ONE quoted string
MIN_PER="reasoning=20 multilingual=20 coding=10 math=20 tool_use=10 rag=40 long_context=10 dialogue=10"

echo "Running 10% paired benchmark (seed=$CATEGORY_BENCH_SEED)..."
python3 scripts/run_short_paired_benchmark.py \
  --sample-percent 10 \
  --seed "$CATEGORY_BENCH_SEED" \
  --min-per-category "$MIN_PER"

echo "Done. Report: benchmark_reports/paired_policy_short_*.json"
