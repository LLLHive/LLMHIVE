#!/usr/bin/env python3
"""Decision-grade paired benchmark: free_first_verified vs leader_first_verified.

Runs category benchmarks twice on the same sampled items (fixed seed) with different
Elite+ policies. Produces a single decision report with deltas, cost, and promotion
recommendation.

Usage:
  set -euo pipefail
  export ELITE_PLUS_ENABLED=1
  export ALLOW_INTERNAL_BENCH=1
  export ELITE_PLUS_LEADERBOARD_AWARE=1
  export ELITE_PLUS_LEADER_FIRST_ALLOWED=1
  export ELITE_PLUS_LEADER_FIRST_INTERNAL_BENCH_ONLY=1

  python3 scripts/run_short_paired_benchmark.py \\
    --sample-percent 10 \\
    --min-per-category reasoning=20 multilingual=20 coding=10 math=20 tool_use=10 rag=40 long_context=10 dialogue=10

Output:
  benchmark_reports/paired_policy_short_<timestamp>.json
"""
from __future__ import annotations

import json
import os
import shutil
import statistics
import subprocess
import sys
from datetime import datetime
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent

# Default min-per-category for decision-grade benchmark
_DEFAULT_MIN_PER_CATEGORY = {
    "reasoning": 20,
    "multilingual": 20,
    "coding": 10,
    "math": 20,
    "tool_use": 10,
    "rag": 40,
    "long_context": 10,
    "dialogue": 10,
}

# Map benchmark category display names to internal keys
_CATEGORY_TO_KEY = {
    "General Reasoning (MMLU)": "reasoning",
    "Coding (HumanEval)": "coding",
    "Math (GSM8K)": "math",
    "Multilingual (MMMLU)": "multilingual",
    "Long Context (LongBench)": "long_context",
    "Tool Use (ToolBench)": "tool_use",
    "RAG (MS MARCO)": "rag",
    "Dialogue (MT-Bench)": "dialogue",
}


def _parse_min_per_category(s: str) -> dict[str, int]:
    """Parse 'reasoning=20 multilingual=20 ...' into dict."""
    out: dict[str, int] = dict(_DEFAULT_MIN_PER_CATEGORY)
    for part in s.split():
        if "=" in part:
            k, v = part.split("=", 1)
            k = k.strip().lower()
            try:
                out[k] = int(v.strip())
            except ValueError:
                pass
    return out


def _run_benchmark(
    policy_override: str,
    sample_percent: int,
    min_per_category: dict[str, int],
    seed: int,
) -> tuple[Path | None, Path | None, int, bool]:
    """Run run_category_benchmarks. Returns (main_report_path, elite_plus_report_path, exit_code, regression_gate_failed).
    Reports are written before regression gate; we always look for them even on non-zero exit.
    """
    env = os.environ.copy()
    env["PAIRED_POLICY_EVAL"] = "1"
    env["PAIRED_POLICY_OVERRIDE"] = policy_override
    env["ELITE_PLUS_EVAL"] = "1"
    env["SHORT_PAIRED_BENCH"] = "1"
    env["CATEGORY_BENCH_SEED"] = str(seed)
    env.setdefault("ALLOW_INTERNAL_BENCH_OUTPUT", "1")

    # Set per-category sample sizes
    for cat, n in min_per_category.items():
        if cat == "reasoning":
            env["CATEGORY_BENCH_MMLU_SAMPLES"] = str(n)
        elif cat == "coding":
            env["CATEGORY_BENCH_HUMANEVAL_SAMPLES"] = str(n)
        elif cat == "math":
            env["CATEGORY_BENCH_GSM8K_SAMPLES"] = str(n)
        elif cat == "multilingual":
            env["CATEGORY_BENCH_MMMLU_SAMPLES"] = str(n)
        elif cat == "long_context":
            env["CATEGORY_BENCH_LONGBENCH_SAMPLES"] = str(n)
        elif cat == "tool_use":
            env["CATEGORY_BENCH_TOOLBENCH_SAMPLES"] = str(n)
        elif cat == "rag":
            env["CATEGORY_BENCH_MSMARCO_SAMPLES"] = str(n)
        elif cat == "dialogue":
            env["CATEGORY_BENCH_MTBENCH_SAMPLES"] = str(n)

    cmd = [
        sys.executable,
        str(_ROOT / "scripts" / "run_category_benchmarks.py"),
        "--sample-percent", str(sample_percent),
        "--elite-plus-eval",
    ]
    result = subprocess.run(cmd, env=env, cwd=str(_ROOT))
    regression_gate_failed = result.returncode != 0

    reports_dir = _ROOT / "benchmark_reports"
    main_reports = sorted(reports_dir.glob("category_benchmarks_elite_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    ep_reports = sorted(reports_dir.glob("elite_plus_eval_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)

    if result.returncode != 0:
        print(f"Benchmark with {policy_override} exited {result.returncode} (regression gate or error)")
        if main_reports:
            print(f"  Using latest report: {main_reports[0].name} (written before abort)")

    return (
        main_reports[0] if main_reports else None,
        ep_reports[0] if ep_reports else None,
        result.returncode,
        regression_gate_failed,
    )


def _extract_costs(shadow_log: list) -> tuple[list[float], float, float]:
    """Extract cost list, p50, p95 from shadow log."""
    costs = [e.get("estimated_cost_usd", 0) for e in shadow_log if isinstance(e.get("estimated_cost_usd"), (int, float))]
    if not costs:
        return [], 0.0, 0.0
    costs_sorted = sorted(costs)
    n = len(costs_sorted)
    p50 = costs_sorted[int(n * 0.5)] if n else 0.0
    p95 = costs_sorted[int(n * 0.95)] if n > 1 else costs_sorted[0]
    return costs, p50, p95


def _extract_failure_rates(shadow_log: list) -> dict:
    """Extract verification failure rates from shadow log."""
    total = len(shadow_log)
    if total == 0:
        return {}
    grounding_fail = sum(1 for e in shadow_log if e.get("rag_grounding_status") == "fail")
    tool_schema_invalid = sum(1 for e in shadow_log if e.get("tool_schema_valid") is False)
    fallback = sum(1 for e in shadow_log if e.get("stage_used") == "fallback_elite")
    return {
        "grounding_fail_rate": grounding_fail / total,
        "tool_schema_invalid_rate": tool_schema_invalid / total,
        "fallback_rate": fallback / total,
        "grounding_fail_count": grounding_fail,
        "tool_schema_invalid_count": tool_schema_invalid,
        "fallback_count": fallback,
    }


def _main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description="Short paired policy benchmark")
    parser.add_argument("--sample-percent", type=int, default=10)
    parser.add_argument(
        "--min-per-category",
        type=str,
        default="reasoning=20 multilingual=20 coding=10 math=20 tool_use=10 rag=40 long_context=10 dialogue=10",
        help="Min samples per category, e.g. reasoning=20 multilingual=20",
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--skip-run", action="store_true", help="Only build report from existing artifacts")
    args = parser.parse_args()

    min_per = _parse_min_per_category(args.min_per_category)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    reports_dir = _ROOT / "benchmark_reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    free_main = reports_dir / "paired_short_free_main.json"
    free_ep = reports_dir / "paired_short_free_ep.json"
    leader_main = reports_dir / "paired_short_leader_main.json"
    leader_ep = reports_dir / "paired_short_leader_ep.json"

    checkpoint_path = reports_dir / "category_benchmarks_checkpoint.json"

    phase_exit_codes: dict[str, int] = {"free_first": 0, "leader_first": 0}
    phase_regression_gate_failed: dict[str, bool] = {"free_first": False, "leader_first": False}

    if not args.skip_run:
        # Remove checkpoint for fresh run (avoids config mismatch between paired runs)
        if checkpoint_path.exists():
            checkpoint_path.unlink()
            print("Removed existing checkpoint for fresh paired run.")
        print("Running free_first_verified...")
        m1, e1, ec1, rg1 = _run_benchmark("free_first", args.sample_percent, min_per, args.seed)
        phase_exit_codes["free_first"] = ec1
        phase_regression_gate_failed["free_first"] = rg1
        if m1:
            shutil.copy(m1, free_main)
        if e1:
            shutil.copy(e1, free_ep)

        # Remove checkpoint before second run (different policy = different config)
        if checkpoint_path.exists():
            checkpoint_path.unlink()
        print("Running leader_first_verified...")
        m2, e2, ec2, rg2 = _run_benchmark("leader_first", args.sample_percent, min_per, args.seed)
        phase_exit_codes["leader_first"] = ec2
        phase_regression_gate_failed["leader_first"] = rg2
        if m2:
            shutil.copy(m2, leader_main)
        if e2:
            shutil.copy(e2, leader_ep)

    # Always attempt to write the report even if one phase is missing
    if not free_main.exists() and not leader_main.exists():
        print("FAIL: Both benchmark reports missing. Run without --skip-run first.")
        return 1

    free_data = json.loads(free_main.read_text()) if free_main.exists() else {"results": []}
    leader_data = json.loads(leader_main.read_text()) if leader_main.exists() else {"results": []}
    if not free_main.exists():
        print("WARNING: free_first report missing — report will have partial data")
    if not leader_main.exists():
        print("WARNING: leader_first report missing — report will have partial data")
    free_results = {r["category"]: r for r in free_data.get("results", []) if r.get("category")}
    leader_results = {r["category"]: r for r in leader_data.get("results", []) if r.get("category")}

    # Per-category deltas (with infra failure separation)
    categories = sorted(set(free_results) | set(leader_results))
    per_category = {}
    for cat in categories:
        fr = free_results.get(cat, {})
        lr = leader_results.get(cat, {})
        acc_f = fr.get("accuracy")
        acc_l = lr.get("accuracy")
        delta = (acc_l - acc_f) if (acc_f is not None and acc_l is not None) else None

        # Separate infra failures from accuracy
        infra_errors_f = fr.get("infra_errors", fr.get("errors", 0))
        infra_errors_l = lr.get("infra_errors", lr.get("errors", 0))
        sample_f = fr.get("sample_size", 0)
        sample_l = lr.get("sample_size", 0)
        infra_rate_f = round(infra_errors_f / max(sample_f, 1) * 100, 2)
        infra_rate_l = round(infra_errors_l / max(sample_l, 1) * 100, 2)

        per_category[cat] = {
            "free_first_accuracy": acc_f,
            "leader_first_accuracy": acc_l,
            "delta_pp": round(delta, 1) if delta is not None else None,
            "verdict": "better" if (delta is not None and delta > 0) else ("worse" if (delta is not None and delta < 0) else "neutral"),
            "infra_errors": {"free_first": infra_errors_f, "leader_first": infra_errors_l},
            "infra_rate_pct": {"free_first": infra_rate_f, "leader_first": infra_rate_l},
        }

    # Overall weighted delta
    total_f = sum(free_results.get(c, {}).get("correct", 0) for c in categories)
    total_c = sum(free_results.get(c, {}).get("sample_size", 0) - free_results.get(c, {}).get("errors", 0) for c in categories)
    total_f_l = sum(leader_results.get(c, {}).get("correct", 0) for c in categories)
    total_c_l = sum(leader_results.get(c, {}).get("sample_size", 0) - leader_results.get(c, {}).get("errors", 0) for c in categories)
    overall_f = (total_f / total_c * 100) if total_c else 0
    overall_l = (total_f_l / total_c_l * 100) if total_c_l else 0
    overall_delta = round(overall_l - overall_f, 1)

    # Cost and paid-call stats from elite_plus reports
    free_shadow = []
    leader_shadow = []
    if free_ep.exists():
        free_ep_data = json.loads(free_ep.read_text())
        free_shadow = free_ep_data.get("shadow_log", [])
    if leader_ep.exists():
        leader_ep_data = json.loads(leader_ep.read_text())
        leader_shadow = leader_ep_data.get("shadow_log", [])

    free_costs, free_p50, free_p95 = _extract_costs(free_shadow)
    leader_costs, leader_p50, leader_p95 = _extract_costs(leader_shadow)
    free_paid_pct = (sum(1 for e in free_shadow if e.get("paid_calls_count", 0) > 0) / len(free_shadow) * 100) if free_shadow else 0
    leader_paid_pct = (sum(1 for e in leader_shadow if e.get("paid_calls_count", 0) > 0) / len(leader_shadow) * 100) if leader_shadow else 0
    free_paid_count = sum(e.get("paid_calls_count", 0) for e in free_shadow)
    leader_paid_count = sum(e.get("paid_calls_count", 0) for e in leader_shadow)

    # v2/v3 telemetry: paid_call_made flag (more reliable than paid_calls_count)
    free_paid_made_count = sum(1 for e in free_shadow if e.get("paid_call_made", False))
    leader_paid_made_count = sum(1 for e in leader_shadow if e.get("paid_call_made", False))
    leader_anchor_models = {}
    for e in leader_shadow:
        anchor = e.get("anchor_model_used", "")
        if anchor:
            leader_anchor_models[anchor] = leader_anchor_models.get(anchor, 0) + 1

    free_failures = _extract_failure_rates(free_shadow)
    leader_failures = _extract_failure_rates(leader_shadow)

    # MCQ telemetry and infra_fail_rate from main reports
    free_reasoning = free_results.get("General Reasoning (MMLU)", {})
    leader_reasoning = leader_results.get("General Reasoning (MMLU)", {})
    mcq_telemetry = {
        "free_first": {
            "mcq_tie_detected": free_reasoning.get("mcq_tie_detected", 0),
            "mcq_tie_break_strategy": free_reasoning.get("mcq_tie_break_strategy", "none"),
            "mcq_invalid_extraction_count": free_reasoning.get("mcq_invalid_extraction_count", 0),
            "mcq_retry_count": free_reasoning.get("mcq_retry_count", 0),
        },
        "leader_first": {
            "mcq_tie_detected": leader_reasoning.get("mcq_tie_detected", 0),
            "mcq_tie_break_strategy": leader_reasoning.get("mcq_tie_break_strategy", "none"),
            "mcq_invalid_extraction_count": leader_reasoning.get("mcq_invalid_extraction_count", 0),
            "mcq_retry_count": leader_reasoning.get("mcq_retry_count", 0),
        },
    }
    infra_fail_rate_free = free_data.get("infra_fail_rate")
    infra_fail_rate_leader = leader_data.get("infra_fail_rate")

    # Promotion recommendation
    reasoning_delta = per_category.get("General Reasoning (MMLU)", {}).get("delta_pp")
    multilingual_delta = per_category.get("Multilingual (MMMLU)", {}).get("delta_pp")
    cost_ceiling = float(os.getenv("ELITE_PLUS_MAX_COST_USD_REQUEST", "0.025"))
    paid_limit_pct = 100.0  # configurable

    infra_ok = (infra_fail_rate_leader or 0) <= 2.0 and (infra_fail_rate_free or 0) <= 2.0
    promote_mcq = (
        (reasoning_delta is not None and reasoning_delta >= 2)
        and (multilingual_delta is not None and multilingual_delta >= 2)
        and leader_p95 <= cost_ceiling
        and leader_paid_pct <= paid_limit_pct
        and infra_ok
    )
    leader_sample = max(leader_reasoning.get("sample_size", 0), 1)
    mcq_invalid_count = leader_reasoning.get("mcq_invalid_extraction_count", 0)
    mcq_invalid_rate = mcq_invalid_count / leader_sample
    promote_mcq = promote_mcq and (mcq_invalid_rate <= 0.01 or mcq_invalid_count == 0)

    recommendation = "PROMOTE leader-first for MCQ categories" if promote_mcq else "HOLD — insufficient evidence or gate failure"

    # Dominance assertion: check all deterministic categories
    _DETERMINISTIC_DISPLAY = {
        "General Reasoning (MMLU)", "Coding (HumanEval)", "Math (GSM8K)",
        "Multilingual (MMMLU)", "Tool Use (ToolBench)", "RAG (MS MARCO)",
    }
    dominance_violations = []
    for cat in _DETERMINISTIC_DISPLAY:
        entry = per_category.get(cat, {})
        delta = entry.get("delta_pp")
        if delta is not None and delta < 0:
            dominance_violations.append({"category": cat, "delta_pp": delta})

    report = {
        "timestamp": datetime.now().isoformat(),
        "sample_percent": args.sample_percent,
        "seed": args.seed,
        "min_per_category": min_per,
        "overall": {
            "free_first_accuracy": round(overall_f, 1),
            "leader_first_accuracy": round(overall_l, 1),
            "delta_pp": overall_delta,
        },
        "per_category": per_category,
        "cost": {
            "free_first": {"p50_usd": round(free_p50, 6), "p95_usd": round(free_p95, 6)},
            "leader_first": {"p50_usd": round(leader_p50, 6), "p95_usd": round(leader_p95, 6)},
        },
        "paid_calls": {
            "free_first": {"pct": round(free_paid_pct, 1), "count": free_paid_count, "paid_call_made_count": free_paid_made_count},
            "leader_first": {"pct": round(leader_paid_pct, 1), "count": leader_paid_count, "paid_call_made_count": leader_paid_made_count},
        },
        "anchor_models_used": leader_anchor_models,
        "fallback_rates": {
            "free_first": free_failures,
            "leader_first": leader_failures,
        },
        "mcq_telemetry": mcq_telemetry,
        "infra_fail_rate": {
            "free_first": infra_fail_rate_free,
            "leader_first": infra_fail_rate_leader,
        },
        "phase_exit_codes": phase_exit_codes,
        "phase_regression_gate_failed": phase_regression_gate_failed,
        "promotion_recommendation": recommendation,
        "promotion_gate": {
            "reasoning_delta_pp": reasoning_delta,
            "multilingual_delta_pp": multilingual_delta,
            "cost_p95_within_ceiling": leader_p95 <= cost_ceiling,
            "paid_pct_under_limit": leader_paid_pct <= paid_limit_pct,
            "infra_fail_rate_ok": infra_ok,
        },
        "dominance_assertion": {
            "all_deterministic_pass": len(dominance_violations) == 0,
            "violations": dominance_violations,
        },
    }

    out_path = reports_dir / f"paired_policy_short_{timestamp}.json"
    out_path.write_text(json.dumps(report, indent=2, default=str) + "\n")
    print(f"Wrote {out_path}")
    print(f"\nPromotion recommendation: {recommendation}")

    # Run promotion gate separately (PASS/FAIL independent of report creation)
    gate_script = _ROOT / "scripts" / "run_policy_promotion_gate.py"
    if gate_script.exists():
        gate_result = subprocess.run(
            [sys.executable, str(gate_script), "--report", str(out_path)],
            cwd=str(_ROOT),
        )
        gate_status = "PASS" if gate_result.returncode == 0 else "FAIL"
        print(f"\nPromotion gate: {gate_status}")

    return 0


if __name__ == "__main__":
    sys.exit(_main())
