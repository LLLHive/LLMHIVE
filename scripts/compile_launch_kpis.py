#!/usr/bin/env python3
"""Compile Launch KPIs from logs, benchmark reports, and runtime state.

Reads:
  - benchmark_reports/rc_summary.json (latest gate results)
  - benchmark_reports/latest/gate_result.json (category detail)
  - Runtime circuit breaker status (if importable)

Outputs:
  - launch_kpis.json  (machine-readable snapshot)

Usage:
    python scripts/compile_launch_kpis.py
    python scripts/compile_launch_kpis.py --output /tmp/kpis.json
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_RC_SUMMARY = _ROOT / "benchmark_reports" / "rc_summary.json"
_GATE_RESULT = _ROOT / "benchmark_reports" / "latest" / "gate_result.json"
_MANIFEST = _ROOT / "public" / "release_manifest.json"
_OUTPUT_DEFAULT = _ROOT / "launch_kpis.json"


def _load_json(path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text())
    return {}


def _metric_val(obj, key: str, default=0):
    """Extract a metric value that may be a plain number or a dict with 'value'/'actual'."""
    v = obj.get(key, default)
    if isinstance(v, dict):
        return v.get("actual", v.get("value", default))
    return v


def _parse_args() -> Path:
    out = _OUTPUT_DEFAULT
    for i, arg in enumerate(sys.argv[1:], 1):
        if arg == "--output" and i < len(sys.argv) - 1:
            out = Path(sys.argv[i + 1])
    return out


def main():
    output_path = _parse_args()

    rc = _load_json(_RC_SUMMARY)
    gate = _load_json(_GATE_RESULT)
    manifest = _load_json(_MANIFEST)

    # ── Cost KPIs ──
    category_results = rc.get("category_results", gate.get("category_results", {}))
    all_costs = []
    total_paid_calls = 0
    total_calls = 0
    for cat, cr in category_results.items():
        checks = cr.get("checks", {})
        if "cost_usd_avg" in checks:
            all_costs.append(checks["cost_usd_avg"].get("actual", 0))
        stage_dist = cr.get("stage_distribution", {})
        n = cr.get("sample_count", 0)
        total_calls += n
        paid_pct = stage_dist.get("paid_escalation", 0)
        total_paid_calls += int(n * paid_pct / 100) if paid_pct else 0

    cost_avg = sum(all_costs) / max(len(all_costs), 1)
    sorted_costs = sorted(all_costs)
    cost_p50 = sorted_costs[len(sorted_costs) // 2] if sorted_costs else 0.0
    cost_p95 = sorted_costs[int(len(sorted_costs) * 0.95)] if len(sorted_costs) >= 2 else cost_avg

    paid_call_rate = (total_paid_calls / max(total_calls, 1)) * 100

    # ── Tool KPIs ──
    tool_cr = category_results.get("tool_use", {})
    tool_checks = tool_cr.get("checks", {})
    tool_error_rate = tool_checks.get("tool_error_rate_pct", {}).get("actual", 0)
    tool_score = tool_checks.get("score", {}).get("actual", 0)

    # ── RAG KPIs ──
    rag_cr = category_results.get("rag", {})
    rag_checks = rag_cr.get("checks", {})
    rag_ungrounded_rate = rag_checks.get("rag_ungrounded_pct", {}).get("actual", 0)
    rag_score = rag_checks.get("score", {}).get("actual", 0)

    # ── Dialogue KPIs ──
    dialogue_cr = category_results.get("dialogue", {})
    dialogue_checks = dialogue_cr.get("checks", {})
    dialogue_score = dialogue_checks.get("score", {}).get("actual", 0)
    dialogue_esc_rate = dialogue_cr.get("stage_distribution", {}).get("paid_escalation", 0)

    # ── Latency ──
    global_result = rc.get("global_result", gate.get("global_result", {}))
    raw_lat = global_result.get("latency_p95_ms", 0)
    latency_p95 = raw_lat.get("actual", 0) if isinstance(raw_lat, dict) else raw_lat

    # ── Top escalation reasons ──
    top_reasons = rc.get("top_escalation_reasons", {})
    sorted_reasons = sorted(top_reasons.items(), key=lambda x: x[1], reverse=True)[:10]

    # ── Circuit breaker status (best-effort import) ──
    cb_status = {}
    try:
        sys.path.insert(0, str(_ROOT / "llmhive" / "src"))
        from llmhive.app.orchestration.elite_plus_orchestrator import get_circuit_breaker_status
        cb_status = get_circuit_breaker_status()
    except Exception:
        pass

    kpis = {
        "timestamp": datetime.now().isoformat(),
        "gate_status": rc.get("gate_status", "unknown"),
        "git_sha": rc.get("git_sha", manifest.get("git_sha", "unknown")),
        "model_registry_version": manifest.get("model_registry_version", "unknown"),
        "launch_mode_enabled": os.getenv("ELITE_PLUS_LAUNCH_MODE", "0") == "1",
        "cost": {
            "avg_usd": round(cost_avg, 5),
            "p50_usd": round(cost_p50, 5),
            "p95_usd": round(cost_p95, 5),
            "budget_p50_floor": float(os.getenv("ELITE_PLUS_BUDGET_USD_P50", "0.010")),
            "budget_p95_floor": float(os.getenv("ELITE_PLUS_BUDGET_USD_P95", "0.020")),
            "p50_pass": cost_p50 <= float(os.getenv("ELITE_PLUS_BUDGET_USD_P50", "0.010")),
            "p95_pass": cost_p95 <= float(os.getenv("ELITE_PLUS_BUDGET_USD_P95", "0.020")),
        },
        "paid_calls": {
            "total": total_paid_calls,
            "rate_pct": round(paid_call_rate, 2),
        },
        "tool_use": {
            "score": round(tool_score, 3),
            "error_rate_pct": round(tool_error_rate, 2),
        },
        "rag": {
            "score": round(rag_score, 3),
            "ungrounded_rate_pct": round(rag_ungrounded_rate, 2),
        },
        "dialogue": {
            "score": round(dialogue_score, 3),
            "escalation_rate_pct": round(dialogue_esc_rate, 2),
        },
        "latency": {
            "p95_ms": latency_p95,
        },
        "top_escalation_reasons": dict(sorted_reasons),
        "circuit_breaker": cb_status,
        "p0_failures": rc.get("p0_failures", []),
        "total_samples": rc.get("total_samples", total_calls),
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(kpis, indent=2) + "\n")
    print(f"Launch KPIs written: {output_path}")
    print(f"  Gate: {kpis['gate_status']}")
    print(f"  Cost p50: ${kpis['cost']['p50_usd']:.4f} (floor: ${kpis['cost']['budget_p50_floor']:.3f})")
    print(f"  Cost p95: ${kpis['cost']['p95_usd']:.4f} (floor: ${kpis['cost']['budget_p95_floor']:.3f})")
    print(f"  Paid call rate: {kpis['paid_calls']['rate_pct']:.1f}%")
    print(f"  Tool error rate: {kpis['tool_use']['error_rate_pct']:.1f}%")
    print(f"  RAG ungrounded: {kpis['rag']['ungrounded_rate_pct']:.1f}%")


if __name__ == "__main__":
    main()
