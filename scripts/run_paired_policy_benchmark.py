#!/usr/bin/env python3
"""Run paired policy evaluation: free_first_verified vs leader_first_verified.

Runs the category benchmark twice on the same prompts with different Elite+ policies,
then compares scores and cost. Internal bench only.

Usage:
  export ELITE_PLUS_LEADERBOARD_AWARE=1
  export ELITE_PLUS_POLICY=leader_first_verified  # or free_first for baseline
  export ALLOW_INTERNAL_BENCH=1
  export PAIRED_POLICY_EVAL=1

  # Run free_first run
  PAIRED_POLICY_OVERRIDE=free_first python scripts/run_category_benchmarks.py \\
    --sample-percent 10 --elite-plus-eval

  # Run leader_first run (same server, policy override per request)
  PAIRED_POLICY_OVERRIDE=leader_first python scripts/run_category_benchmarks.py \\
    --sample-percent 10 --elite-plus-eval

  # Or use this wrapper to run both and compare:
  python scripts/run_paired_policy_benchmark.py --sample-percent 10

Output:
  - benchmark_reports/paired_policy_free_*.json
  - benchmark_reports/paired_policy_leader_*.json
  - benchmark_reports/paired_policy_comparison.md
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent


def _run_benchmark(policy_override: str, sample_percent: int, dest_path: Path) -> bool:
    """Run run_category_benchmarks with given policy override. Copies latest report to dest_path."""
    import shutil
    env = os.environ.copy()
    env["PAIRED_POLICY_EVAL"] = "1"
    env["PAIRED_POLICY_OVERRIDE"] = policy_override
    env["ELITE_PLUS_EVAL"] = "1"
    env.setdefault("ALLOW_INTERNAL_BENCH_OUTPUT", "1")

    cmd = [
        sys.executable,
        str(_ROOT / "scripts" / "run_category_benchmarks.py"),
        "--sample-percent", str(sample_percent),
        "--elite-plus-eval",
    ]
    result = subprocess.run(cmd, env=env, cwd=str(_ROOT))
    if result.returncode != 0:
        print(f"FAIL: Benchmark with {policy_override} exited {result.returncode}")
        return False
    reports = list((_ROOT / "benchmark_reports").glob("*.json"))
    reports.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    if reports:
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(reports[0], dest_path)
        return True
    return False


def _load_results(path: Path) -> dict:
    """Load benchmark results JSON."""
    data = json.loads(path.read_text())
    return data.get("results", data.get("scores", []))


def _main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description="Paired policy benchmark")
    parser.add_argument("--sample-percent", type=int, default=10)
    parser.add_argument("--skip-run", action="store_true", help="Only compare existing reports")
    args = parser.parse_args()

    free_path = _ROOT / "benchmark_reports" / "paired_policy_free_results.json"
    leader_path = _ROOT / "benchmark_reports" / "paired_policy_leader_results.json"

    if not args.skip_run:
        print("Running free_first_verified...")
        _run_benchmark("free_first", args.sample_percent, free_path)
        print("Running leader_first_verified...")
        _run_benchmark("leader_first", args.sample_percent, leader_path)

    if not free_path.exists() or not leader_path.exists():
        print("Missing report files. Run without --skip-run first.")
        return 1

    free_data = json.loads(free_path.read_text())
    leader_data = json.loads(leader_path.read_text())
    free_results = {r["category"]: r for r in free_data.get("results", []) if r.get("category")}
    leader_results = {r["category"]: r for r in leader_data.get("results", []) if r.get("category")}

    lines = [
        "# Paired Policy Comparison",
        "",
        f"*Generated: {datetime.now().isoformat()}*",
        "",
        "| Category | Free-first | Leader-first | Delta | Cost free | Cost leader |",
        "|----------|------------|--------------|-------|------------|--------------|",
    ]
    for cat in sorted(set(free_results) | set(leader_results)):
        fr = free_results.get(cat, {})
        lr = leader_results.get(cat, {})
        acc_f = fr.get("accuracy")
        acc_l = lr.get("accuracy")
        delta = (acc_l - acc_f) if (acc_f is not None and acc_l is not None) else None
        cost_f = fr.get("total_cost", fr.get("avg_cost", 0))
        cost_l = lr.get("total_cost", lr.get("avg_cost", 0))
        delta_str = f"{delta:+.1f}" if delta is not None else "—"
        lines.append(
            f"| {cat} | {acc_f or '—'} | {acc_l or '—'} | {delta_str} | {cost_f} | {cost_l} |"
        )

    out_path = _ROOT / "benchmark_reports" / "paired_policy_comparison.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines) + "\n")
    print(f"Wrote {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(_main())
