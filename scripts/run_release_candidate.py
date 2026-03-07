#!/usr/bin/env python3
"""Release Candidate Pipeline — bench → gate → promote.

Orchestrates the full RC flow:
  1. Run category benchmarks with Elite+ eval
  2. Run launch-candidate gate
  3. Produce rc_summary.json

Usage:
    python scripts/run_release_candidate.py
    python scripts/run_release_candidate.py --skip-bench   # use existing reports
    python scripts/run_release_candidate.py --sample-percent 10
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_REPORTS = _ROOT / "benchmark_reports"
_LATEST = _REPORTS / "latest"
_RC_SUMMARY = _REPORTS / "rc_summary.json"


def _parse_args():
    args = {"skip_bench": False, "sample_percent": 25}
    i = 1
    while i < len(sys.argv):
        if sys.argv[i] == "--skip-bench":
            args["skip_bench"] = True
            i += 1
        elif sys.argv[i] == "--sample-percent" and i + 1 < len(sys.argv):
            args["sample_percent"] = int(sys.argv[i + 1])
            i += 2
        else:
            i += 1
    return args


def _run(cmd: list, env_extra: dict = None, check: bool = True) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    if env_extra:
        env.update(env_extra)
    print(f"  $ {' '.join(cmd)}")
    return subprocess.run(cmd, cwd=str(_ROOT), env=env, capture_output=False, check=check)


def main():
    args = _parse_args()
    t0 = time.time()

    print("=" * 70)
    print("RELEASE CANDIDATE PIPELINE")
    print("=" * 70)
    print(f"  Time:    {datetime.now().isoformat()}")
    print(f"  Root:    {_ROOT}")
    print(f"  Skip bench: {args['skip_bench']}")
    print()

    _REPORTS.mkdir(exist_ok=True)
    _LATEST.mkdir(exist_ok=True)

    # Step 1: Run benchmarks (unless skipped)
    if not args["skip_bench"]:
        print("[1/3] Running category benchmarks with Elite+ eval...")
        bench_result = _run(
            [sys.executable, "scripts/run_category_benchmarks.py"],
            env_extra={
                "ELITE_PLUS_EVAL": "1",
                "ALLOW_INTERNAL_BENCH_OUTPUT": "1",
                "CATEGORY_BENCH_TIER": "elite",
            },
            check=False,
        )
        if bench_result.returncode != 0:
            print(f"  WARNING: Benchmarks exited with code {bench_result.returncode}")
    else:
        print("[1/3] Skipping benchmarks (--skip-bench)")

    # Step 2: Collect latest eval reports
    print("\n[2/3] Collecting eval reports...")
    eval_files = sorted(_REPORTS.glob("elite_plus_eval_*.json"), reverse=True)
    scripts_reports = Path(__file__).resolve().parent / "benchmark_reports"
    if scripts_reports.exists():
        eval_files.extend(sorted(scripts_reports.glob("elite_plus_eval_*.json"), reverse=True))
    eval_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)

    if not eval_files:
        print("  ERROR: No elite_plus_eval reports found.")
        sys.exit(2)

    latest_eval = eval_files[0]
    print(f"  Latest eval: {latest_eval.name}")
    shutil.copy2(latest_eval, _LATEST / latest_eval.name)

    # Step 3: Run launch-candidate gate
    print("\n[3/7] Running launch-candidate gate...")
    gate_output = _LATEST / "gate_result.json"
    gate_result = _run(
        [sys.executable, "scripts/run_launch_candidate_gate.py",
         "--output", str(gate_output)],
        check=False,
    )
    gate_pass = gate_result.returncode == 0

    # Load gate report for summary
    gate_data = {}
    if gate_output.exists():
        gate_data = json.loads(gate_output.read_text())
        dest = _LATEST / "gate_result.json"
        if gate_output.resolve() != dest.resolve():
            shutil.copy2(gate_output, dest)

    # Step 4: Marketing benchmark pack
    print("\n[4/7] Generating marketing benchmark pack...")
    _run(
        [sys.executable, "scripts/run_marketing_benchmark.py"],
        check=False,
    )
    for name in ["marketing_benchmark.json", "marketing_benchmark.md"]:
        src = _REPORTS / name
        if src.exists():
            shutil.copy2(src, _LATEST / name)

    # Step 5: Production preflight (offline)
    print("\n[5/7] Running production preflight (offline)...")
    preflight_out = _LATEST / "preflight_report.json"
    _run(
        [sys.executable, "scripts/run_prod_preflight.py",
         "--offline", "--output", str(preflight_out)],
        check=False,
    )

    # Step 6: Synthetic suite (offline)
    print("\n[6/7] Running synthetic production suite (offline)...")
    synthetic_out = _LATEST / "synthetic_suite_results.json"
    _run(
        [sys.executable, "scripts/run_synthetic_prod_suite.py",
         "--offline", "--output", str(synthetic_out)],
        check=False,
    )

    # Step 7: Build RC summary
    print("\n[7/7] Building RC summary...")
    elapsed = round(time.time() - t0, 1)
    git_sha = "unknown"
    try:
        r = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=str(_ROOT))
        if r.returncode == 0:
            git_sha = r.stdout.strip()[:12]
    except Exception:
        pass

    summary = {
        "timestamp": datetime.now().isoformat(),
        "gate_status": "pass" if gate_pass else "fail",
        "git_sha": git_sha,
        "elapsed_seconds": elapsed,
        "p0_failures": gate_data.get("p0_failures", []),
        "p1_warnings": gate_data.get("p1_warnings", []),
        "category_results": {},
        "global_result": gate_data.get("global_result", {}),
        "total_samples": gate_data.get("total_samples", 0),
        "top_escalation_reasons": {},
        "recommended_next_actions": [],
    }

    for cat, cr in gate_data.get("category_results", {}).items():
        summary["category_results"][cat] = {
            "priority": cr.get("priority", "P2"),
            "pass": cr.get("pass", False),
            "sample_count": cr.get("sample_count", 0),
            "checks": cr.get("checks", {}),
            "escalation_reasons": cr.get("escalation_reasons", {}),
            "stage_distribution": cr.get("stage_distribution", {}),
        }
        for reason, cnt in cr.get("escalation_reasons", {}).items():
            summary["top_escalation_reasons"][reason] = (
                summary["top_escalation_reasons"].get(reason, 0) + cnt
            )

    # Evidence bundle listing
    evidence_files = []
    for f in sorted(_LATEST.iterdir()):
        if f.is_file():
            evidence_files.append(f.name)
    summary["evidence_bundle"] = evidence_files

    # Check required artifacts
    required = ["rc_summary.json", "gate_result.json", "preflight_report.json",
                 "synthetic_suite_results.json"]
    missing = [r for r in required if r not in evidence_files]
    summary["missing_artifacts"] = missing

    if gate_pass:
        summary["recommended_next_actions"] = [
            "Run: python scripts/promote_release_candidate.py",
            "Deploy with ELITE_PLUS_LAUNCH_MODE=1",
            "Run: python scripts/run_prod_preflight.py --target <prod_url>",
            "Run: python scripts/run_synthetic_prod_suite.py --target <prod_url>",
            "Monitor /internal/launch_kpis for 30 minutes",
        ]
    else:
        summary["recommended_next_actions"] = [
            f"Fix P0 failure: {f}" for f in summary["p0_failures"]
        ]

    _RC_SUMMARY.write_text(json.dumps(summary, indent=2, default=str) + "\n")
    print(f"\n  RC summary saved: {_RC_SUMMARY}")

    # Copy to latest/
    shutil.copy2(_RC_SUMMARY, _LATEST / "rc_summary.json")

    print(f"\n{'='*70}")
    print(f"RELEASE CANDIDATE: {'PASS' if gate_pass else 'FAIL'}")
    print(f"{'='*70}")
    print(f"  Elapsed: {elapsed}s")
    print(f"  Git SHA: {git_sha}")
    if not gate_pass:
        for f in summary["p0_failures"]:
            print(f"  P0 FAIL: {f}")
    print()

    sys.exit(0 if gate_pass else 1)


if __name__ == "__main__":
    main()
