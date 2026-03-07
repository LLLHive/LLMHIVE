#!/usr/bin/env python3
"""Launch-Candidate Evaluation Gate for Elite+.

Offline gate that determines go/no-go for shipping Elite+ as the public
premium tier.  Runs category benchmarks with Elite+ active policy and
evaluates against per-category floors defined in
benchmark_configs/launch_candidate_floors.json.

Usage:
    python scripts/run_launch_candidate_gate.py
    python scripts/run_launch_candidate_gate.py --sample-percent 10
    python scripts/run_launch_candidate_gate.py --include-real-user-pack prompts.json
    python scripts/run_launch_candidate_gate.py --output custom_report.json

Gate logic:
    P0 categories (tool_use, rag, dialogue, math) block launch on failure.
    P1/P2 categories emit warnings but don't block.
    Exit code 0 = PASS, exit code 1 = FAIL (P0 floor violated).
"""
from __future__ import annotations

import json
import os
import statistics
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
_SCRIPT_DIR = Path(__file__).resolve().parent
_ROOT = _SCRIPT_DIR.parent
_FLOORS_PATH = _ROOT / "benchmark_configs" / "launch_candidate_floors.json"
_DEFAULT_OUTPUT = _ROOT / "benchmark_reports" / f"launch_candidate_gate_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

_SAMPLE_PERCENT = 25
_SEED = 42


def _parse_args() -> Dict[str, Any]:
    args: Dict[str, Any] = {
        "sample_percent": _SAMPLE_PERCENT,
        "output": str(_DEFAULT_OUTPUT),
        "real_user_pack": None,
    }
    i = 1
    while i < len(sys.argv):
        if sys.argv[i] == "--sample-percent" and i + 1 < len(sys.argv):
            args["sample_percent"] = int(sys.argv[i + 1])
            i += 2
        elif sys.argv[i] == "--output" and i + 1 < len(sys.argv):
            args["output"] = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] == "--include-real-user-pack" and i + 1 < len(sys.argv):
            args["real_user_pack"] = sys.argv[i + 1]
            i += 2
        else:
            i += 1
    return args


def _load_floors() -> Dict[str, Any]:
    if not _FLOORS_PATH.exists():
        print(f"ERROR: Floors config not found: {_FLOORS_PATH}")
        sys.exit(2)
    return json.loads(_FLOORS_PATH.read_text())


def _evaluate_category(
    cat: str,
    floor: Dict[str, Any],
    shadow_entries: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Evaluate a single category against its floors."""
    n = len(shadow_entries)
    min_n = floor.get("min_n", 5)

    result: Dict[str, Any] = {
        "category": cat,
        "priority": floor.get("priority", "P2"),
        "sample_count": n,
        "min_n": min_n,
        "checks": {},
        "pass": True,
        "failures": [],
    }

    require_data = floor_config.get("require_nonzero_data", False)
    if n == 0:
        if require_data:
            result["pass"] = False
            result["skipped"] = False
            result["failures"].append(
                f"no_samples — P0 category requires data (require_nonzero_data=true)"
            )
        else:
            result["pass"] = True
            result["skipped"] = True
            result["failures"].append(f"no_samples (skipped — not evaluated)")
        return result

    if n < min_n:
        result["pass"] = False
        result["failures"].append(f"insufficient_samples ({n} < {min_n})")
        return result

    # Cost check
    costs = [e.get("estimated_cost_usd", 0) for e in shadow_entries]
    avg_cost = statistics.mean(costs) if costs else 0
    max_cost = floor.get("max_cost_usd_avg", 999)
    cost_ok = avg_cost <= max_cost
    result["checks"]["avg_cost_usd"] = {"value": round(avg_cost, 6), "max": max_cost, "pass": cost_ok}
    if not cost_ok:
        result["pass"] = False
        result["failures"].append(f"cost ${avg_cost:.5f} > ${max_cost}")

    # Paid call rate
    paid_calls = sum(1 for e in shadow_entries if e.get("paid_calls_count", 0) > 0)
    paid_pct = (paid_calls / n) * 100
    max_paid = floor.get("max_paid_call_pct", 100)
    paid_ok = paid_pct <= max_paid
    result["checks"]["paid_call_pct"] = {"value": round(paid_pct, 1), "max": max_paid, "pass": paid_ok}
    if not paid_ok:
        result["pass"] = False
        result["failures"].append(f"paid_rate {paid_pct:.0f}% > {max_paid}%")

    # Stage distribution
    stages: Dict[str, int] = {}
    for e in shadow_entries:
        s = e.get("stage_used", "unknown")
        stages[s] = stages.get(s, 0) + 1
    result["stage_distribution"] = stages

    fallback_count = stages.get("fallback_elite", 0)
    result["fallback_elite_pct"] = round((fallback_count / n) * 100, 1)

    # Tool-specific: error rate
    if cat == "tool_use":
        tool_errors = sum(1 for e in shadow_entries if e.get("tool_error_type", "none") != "none")
        err_pct = (tool_errors / n) * 100
        max_err = floor.get("max_tool_error_rate_pct", 100)
        err_ok = err_pct <= max_err
        result["checks"]["tool_error_rate_pct"] = {"value": round(err_pct, 1), "max": max_err, "pass": err_ok}
        if not err_ok:
            result["pass"] = False
            result["failures"].append(f"tool_error_rate {err_pct:.0f}% > {max_err}%")

    # RAG-specific: ungrounded rate
    if cat == "rag":
        ungrounded = sum(1 for e in shadow_entries if e.get("rag_grounding_status") == "fail")
        ug_pct = (ungrounded / n) * 100
        max_ug = floor.get("max_rag_ungrounded_pct", 100)
        ug_ok = ug_pct <= max_ug
        result["checks"]["rag_ungrounded_pct"] = {"value": round(ug_pct, 1), "max": max_ug, "pass": ug_ok}
        if not ug_ok:
            result["pass"] = False
            result["failures"].append(f"rag_ungrounded {ug_pct:.0f}% > {max_ug}%")

    # Latency
    latencies = [e.get("total_latency_ms", 0) for e in shadow_entries]
    if latencies:
        result["latency_p50_ms"] = round(statistics.median(latencies))
        sorted_lat = sorted(latencies)
        p95_idx = int(len(sorted_lat) * 0.95)
        result["latency_p95_ms"] = sorted_lat[min(p95_idx, len(sorted_lat) - 1)]

    # Escalation reasons
    esc_reasons: Dict[str, int] = {}
    for e in shadow_entries:
        for r in e.get("escalation_reason", []):
            key = r.split(":")[0] if ":" in r else r
            esc_reasons[key] = esc_reasons.get(key, 0) + 1
    result["escalation_reasons"] = esc_reasons

    return result


def main() -> None:
    args = _parse_args()
    floors_config = _load_floors()
    cat_floors = floors_config.get("categories", {})
    global_floors = floors_config.get("global", {})

    print("=" * 70)
    print("ELITE+ LAUNCH-CANDIDATE EVALUATION GATE")
    print("=" * 70)
    print(f"  Floors config:  {_FLOORS_PATH}")
    print(f"  Sample percent: {args['sample_percent']}%")
    print(f"  Output:         {args['output']}")
    if args["real_user_pack"]:
        print(f"  User pack:      {args['real_user_pack']}")
    print()

    # Look for the most recent Elite+ eval report (check both locations)
    reports_dir = _ROOT / "benchmark_reports"
    eval_files = sorted(reports_dir.glob("elite_plus_eval_*.json"), reverse=True)
    if not eval_files:
        alt_dir = _SCRIPT_DIR / "benchmark_reports"
        eval_files = sorted(alt_dir.glob("elite_plus_eval_*.json"), reverse=True)
    if not eval_files:
        print("ERROR: No elite_plus_eval_*.json reports found in benchmark_reports/")
        print("       Run benchmarks first with ELITE_PLUS_EVAL=1")
        print("       Example: ELITE_PLUS_EVAL=1 ALLOW_INTERNAL_BENCH_OUTPUT=1 \\")
        print("                python scripts/run_category_benchmarks.py")
        sys.exit(2)

    report_path = eval_files[0]
    print(f"  Using eval report: {report_path.name}")
    report = json.loads(report_path.read_text())

    shadow_log = report.get("shadow_log", [])
    if not shadow_log:
        print("ERROR: shadow_log is empty in the eval report.")
        sys.exit(2)
    print(f"  Shadow log entries: {len(shadow_log)}")

    # Group by category
    by_cat: Dict[str, List[Dict[str, Any]]] = {}
    for entry in shadow_log:
        by_cat.setdefault(entry.get("category", "unknown"), []).append(entry)

    # Evaluate each category
    category_results: Dict[str, Dict[str, Any]] = {}
    p0_failures: List[str] = []
    p1_warnings: List[str] = []

    for cat, floor in cat_floors.items():
        entries = by_cat.get(cat, [])
        cr = _evaluate_category(cat, floor, entries)
        category_results[cat] = cr

        if not cr["pass"]:
            prio = floor.get("priority", "P2")
            msg = f"{cat} ({prio}): {', '.join(cr['failures'])}"
            if prio == "P0":
                p0_failures.append(msg)
            else:
                p1_warnings.append(msg)

    # Global checks
    all_costs = [e.get("estimated_cost_usd", 0) for e in shadow_log]
    all_latencies = [e.get("total_latency_ms", 0) for e in shadow_log]
    n_total = len(shadow_log)
    global_result: Dict[str, Any] = {}

    if all_costs:
        sorted_costs = sorted(all_costs)
        p50_cost = sorted_costs[len(sorted_costs) // 2]
        p95_idx = int(len(sorted_costs) * 0.95)
        p95_cost = sorted_costs[min(p95_idx, len(sorted_costs) - 1)]
        global_result["cost_p50_usd"] = round(p50_cost, 6)
        global_result["cost_p95_usd"] = round(p95_cost, 6)
        budget_p50 = global_floors.get("budget_p50_usd", 0.010)
        budget_p95 = global_floors.get("budget_p95_usd", 0.020)
        global_result["budget_p50_pass"] = p50_cost <= budget_p50
        global_result["budget_p95_pass"] = p95_cost <= budget_p95
        if not global_result["budget_p50_pass"]:
            p0_failures.append(f"GLOBAL cost p50 ${p50_cost:.5f} > ${budget_p50}")
        if not global_result["budget_p95_pass"]:
            p0_failures.append(f"GLOBAL cost p95 ${p95_cost:.5f} > ${budget_p95}")

    fallback_count = sum(
        1 for e in shadow_log if e.get("stage_used") == "fallback_elite"
    )
    fallback_pct = (fallback_count / max(n_total, 1)) * 100
    max_fallback = global_floors.get("max_fallback_elite_pct", 15)
    global_result["fallback_elite_pct"] = round(fallback_pct, 1)
    global_result["fallback_elite_pass"] = fallback_pct <= max_fallback
    if not global_result["fallback_elite_pass"]:
        p1_warnings.append(f"GLOBAL fallback_elite {fallback_pct:.0f}% > {max_fallback}%")

    if all_latencies:
        sorted_lat = sorted(all_latencies)
        global_result["latency_p50_ms"] = sorted_lat[len(sorted_lat) // 2]
        p95_idx = int(len(sorted_lat) * 0.95)
        global_result["latency_p95_ms"] = sorted_lat[min(p95_idx, len(sorted_lat) - 1)]

    # Print results
    gate_pass = len(p0_failures) == 0

    print(f"\n{'='*70}")
    print("CATEGORY RESULTS")
    print(f"{'='*70}")
    print(f"  {'Category':<18} {'Prio':>4} {'N':>5} {'Pass':>5} {'Failures'}")
    print(f"  {'-'*18} {'-'*4} {'-'*5} {'-'*5} {'-'*30}")
    for cat in sorted(category_results.keys()):
        cr = category_results[cat]
        status = "PASS" if cr["pass"] else "FAIL"
        fails = "; ".join(cr["failures"]) if cr["failures"] else "-"
        print(f"  {cat:<18} {cr['priority']:>4} {cr['sample_count']:>5} {status:>5} {fails}")

    print(f"\n{'='*70}")
    print("GLOBAL CHECKS")
    print(f"{'='*70}")
    for k, v in sorted(global_result.items()):
        print(f"  {k}: {v}")

    if p0_failures:
        print(f"\n{'='*70}")
        print("P0 FAILURES (LAUNCH BLOCKED)")
        print(f"{'='*70}")
        for f in p0_failures:
            print(f"  FAIL: {f}")

    if p1_warnings:
        print(f"\n  P1/P2 WARNINGS (non-blocking):")
        for w in p1_warnings:
            print(f"    WARN: {w}")

    # Next actions
    print(f"\n{'='*70}")
    print("NEXT ACTIONS")
    print(f"{'='*70}")
    if gate_pass:
        print("  GATE: PASS — Elite+ is ready for launch.")
        print("  1. Deploy with PREMIUM_DEFAULT_TIER=elite_plus ELITE_PUBLIC_ENABLED=0")
        print("  2. Monitor telemetry for cost/escalation drift")
    else:
        # Analyze which policies caused failures
        all_reasons: Dict[str, int] = {}
        for cr in category_results.values():
            for r, cnt in cr.get("escalation_reasons", {}).items():
                all_reasons[r] = all_reasons.get(r, 0) + cnt
        print("  GATE: FAIL — Fix the following before launch:")
        for f in p0_failures:
            print(f"    - {f}")
        if all_reasons:
            top_reasons = sorted(all_reasons.items(), key=lambda x: -x[1])[:5]
            print(f"\n  Top escalation triggers to investigate:")
            for r, cnt in top_reasons:
                print(f"    {r}: {cnt} occurrences")
        print(f"\n  Suggested fixes:")
        for f in p0_failures:
            cat_name = f.split(" ")[0]
            if "tool_error" in f:
                print(f"    - {cat_name}: improve tool-call prompt or switch ELITE_PLUS_PAID_ANCHOR_TOOL_USE")
            elif "rag_ungrounded" in f:
                print(f"    - {cat_name}: improve RAG recall or lower ELITE_PLUS_LOW_CONF_THRESHOLD")
            elif "cost" in f:
                print(f"    - {cat_name}: reduce paid call rate or switch to cheaper anchor")
            elif "paid_rate" in f:
                print(f"    - {cat_name}: raise ELITE_PLUS_LOW_CONF_THRESHOLD to reduce escalations")
            else:
                print(f"    - {cat_name}: review floor thresholds or improve free model quality")

    # Save report
    output_path = Path(args["output"])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    gate_report = {
        "timestamp": datetime.now().isoformat(),
        "gate_pass": gate_pass,
        "source_eval_report": str(report_path.name),
        "sample_percent": args["sample_percent"],
        "total_samples": n_total,
        "p0_failures": p0_failures,
        "p1_warnings": p1_warnings,
        "category_results": category_results,
        "global_result": global_result,
        "floors_config": floors_config,
    }
    output_path.write_text(json.dumps(gate_report, indent=2, default=str) + "\n")
    print(f"\n  Report saved: {output_path}")

    print(f"\n{'='*70}")
    print(f"GATE RESULT: {'PASS' if gate_pass else 'FAIL'}")
    print(f"{'='*70}")

    sys.exit(0 if gate_pass else 1)


if __name__ == "__main__":
    main()
