#!/usr/bin/env python3
"""Promotion gate: PASS/FAIL for enabling leader-first / dominance_v2 in specific categories.

Input: paired benchmark report JSON (from run_short_paired_benchmark.py)
Output: PASS/FAIL + recommendations for enabling leader-first per category.

Fails if:
  - any P0 category regresses beyond tolerance
  - cost p95 exceeds ceiling
  - paid calls exceed caps
  - dominance assertion violated (Elite+ < Free on any deterministic category)

Usage:
  python scripts/run_policy_promotion_gate.py \\
    benchmark_reports/paired_policy_short_20260308_120000.json
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent

# P0 categories that must not regress
_P0_CATEGORIES = {"General Reasoning (MMLU)", "Coding (HumanEval)", "Math (GSM8K)", "Multilingual (MMMLU)"}
_REGRESSION_TOLERANCE_PP = float(os.getenv("PROMOTION_REGRESSION_TOLERANCE_PP", "2.0"))
_COST_CEILING_USD = float(os.getenv("ELITE_PLUS_MAX_COST_USD_REQUEST", "0.025"))
_PAID_CALL_PCT_LIMIT = float(os.getenv("PROMOTION_PAID_CALL_PCT_LIMIT", "100.0"))

# Deterministic categories where dominance must hold (Elite+ >= Free)
_DETERMINISTIC_CATEGORIES = {
    "General Reasoning (MMLU)", "Coding (HumanEval)", "Math (GSM8K)",
    "Multilingual (MMMLU)", "Tool Use (ToolBench)", "RAG (MS MARCO)",
}


def main() -> int:
    report_path = None
    i = 1
    while i < len(sys.argv):
        if sys.argv[i] in ("--report", "--input") and i + 1 < len(sys.argv):
            report_path = Path(sys.argv[i + 1])
            i += 2
        elif not sys.argv[i].startswith("-"):
            report_path = Path(sys.argv[i])
            i += 1
        else:
            i += 1

    if report_path is None:
        print("Usage: python run_policy_promotion_gate.py [--report|--input] <paired_report.json>")
        return 1
    if not report_path.exists():
        print(f"FAIL: Report not found: {report_path}")
        return 1

    data = json.loads(report_path.read_text())
    per_category = data.get("per_category", {})
    cost = data.get("cost", {})
    paid_calls = data.get("paid_calls", {})
    infra_fail_rate = data.get("infra_fail_rate", {})

    failures: list[str] = []
    warnings: list[str] = []
    recommendations: list[str] = []

    # Check P0 regressions
    for cat in _P0_CATEGORIES:
        entry = per_category.get(cat, {})
        delta = entry.get("delta_pp")
        if delta is not None and delta < -_REGRESSION_TOLERANCE_PP:
            failures.append(f"P0 regression: {cat} delta={delta}pp (tolerance={_REGRESSION_TOLERANCE_PP})")

    # Dominance assertion: Elite+ must not be worse than Free on deterministic categories
    for cat in _DETERMINISTIC_CATEGORIES:
        entry = per_category.get(cat, {})
        delta = entry.get("delta_pp")
        if delta is not None and delta < 0:
            infra_rate_free = infra_fail_rate.get("free_first", 0) if isinstance(infra_fail_rate, dict) else 0
            infra_rate_leader = infra_fail_rate.get("leader_first", 0) if isinstance(infra_fail_rate, dict) else 0
            if infra_rate_leader > 1.0 or infra_rate_free > 1.0:
                warnings.append(
                    f"Dominance violation on {cat} (delta={delta}pp) — "
                    f"likely infra-related (infra_fail: free={infra_rate_free}%, leader={infra_rate_leader}%)"
                )
            else:
                failures.append(f"Dominance violation: {cat} delta={delta}pp (Elite+ < Free)")

    # Check cost p95
    leader_p95 = cost.get("leader_first", {}).get("p95_usd", 0)
    if leader_p95 > _COST_CEILING_USD:
        failures.append(f"Cost p95 ${leader_p95:.4f} exceeds ceiling ${_COST_CEILING_USD}")

    # Check paid call %
    leader_paid_pct = paid_calls.get("leader_first", {}).get("pct", 0)
    if leader_paid_pct > _PAID_CALL_PCT_LIMIT:
        failures.append(f"Paid call % {leader_paid_pct:.1f} exceeds limit {_PAID_CALL_PCT_LIMIT}")

    # Build recommendations
    for cat, entry in per_category.items():
        delta = entry.get("delta_pp")
        verdict = entry.get("verdict", "")
        if delta is not None and verdict == "better":
            recommendations.append(f"ENABLE leader-first for {cat} (delta=+{delta}pp)")
        elif delta is not None and verdict == "worse":
            recommendations.append(f"DO NOT enable leader-first for {cat} (delta={delta}pp)")

    passed = len(failures) == 0
    print("=" * 60)
    print("POLICY PROMOTION GATE")
    print("=" * 60)
    print(f"Report: {report_path}")
    print(f"Result: {'PASS' if passed else 'FAIL'}")
    if failures:
        print("\nFailures:")
        for f in failures:
            print(f"  - {f}")
    if warnings:
        print("\nWarnings (infra-related, not blocking):")
        for w in warnings:
            print(f"  - {w}")
    if recommendations:
        print("\nRecommendations:")
        for r in recommendations:
            print(f"  - {r}")

    # Infra failure summary (separate from accuracy)
    if isinstance(infra_fail_rate, dict) and any(v for v in infra_fail_rate.values() if v):
        print("\nInfra failure rates:")
        for phase, rate in infra_fail_rate.items():
            print(f"  {phase}: {rate}%")

    print("=" * 60)
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
