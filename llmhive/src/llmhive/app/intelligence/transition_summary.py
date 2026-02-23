"""Go-to-market stabilization summary output.

Generates benchmark_reports/intelligence_transition_summary.json after a full suite
with all diagnostic distributions.
"""
from __future__ import annotations

import json
import statistics
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .elite_policy import ELITE_POLICY, get_intelligence_mode, is_benchmark_mode
from .model_registry_2026 import get_model_registry_2026


def generate_transition_summary(
    telemetry_summary: Dict[str, Any],
    verify_summary: Dict[str, Any],
    ensemble_stats: Dict[str, Any],
    strategy_recommendations: Dict[str, Any],
    benchmark_results: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Assemble the full intelligence transition summary."""
    registry = get_model_registry_2026()
    now = datetime.now(timezone.utc).isoformat()

    summary: Dict[str, Any] = {
        "generated_at": now,
        "intelligence_mode": get_intelligence_mode(),
        "benchmark_mode": is_benchmark_mode(),
        "registry_model_count": len(registry.list_models()),
        "elite_policy": dict(ELITE_POLICY),

        "model_usage_distribution": telemetry_summary.get("models_used", {}),
        "model_usage_pct": telemetry_summary.get("pct_per_model", {}),
        "total_api_calls": telemetry_summary.get("total_calls", 0),
        "fallback_calls": telemetry_summary.get("fallback_calls", 0),
        "drift_events": telemetry_summary.get("drift_events", 0),
        "non_elite_in_benchmark": telemetry_summary.get("non_elite_in_benchmark", 0),

        "ensemble": ensemble_stats,
        "verify": verify_summary,
        "strategy_recommendations": strategy_recommendations,
    }

    if benchmark_results:
        win_rates: Dict[str, Dict[str, float]] = {}
        for r in benchmark_results:
            if isinstance(r, dict) and "category" in r:
                cat = r["category"]
                acc = r.get("accuracy", 0)
                models = r.get("models_used", [])
                for m in models:
                    win_rates.setdefault(m, {})[cat] = acc
        summary["win_rate_per_model"] = win_rates

    return summary


def save_transition_summary(summary: Dict[str, Any]) -> str:
    """Save to benchmark_reports/ and return the path."""
    report_dir = Path("benchmark_reports")
    report_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = str(report_dir / f"intelligence_transition_summary_{ts}.json")
    Path(path).write_text(json.dumps(summary, indent=2, default=str))
    return path
