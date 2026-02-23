"""Continuous Performance Feedback Loop.

After each benchmark run:
  - Update benchmark_reports/performance_history.json
  - Compute rolling 30-day score, volatility, degradation detection
  - Raise warning if elite drops > 5%
  - Never auto-switch models

Append-only: every run is an immutable record.
"""
from __future__ import annotations

import json
import logging
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

HISTORY_PATH = "benchmark_reports/performance_history.json"
DEGRADATION_THRESHOLD_PCT = 5.0


def _load_history(path: str = HISTORY_PATH) -> Dict[str, Any]:
    p = Path(path)
    if not p.exists():
        return {"runs": [], "alerts": []}
    try:
        return json.loads(p.read_text())
    except Exception:
        return {"runs": [], "alerts": []}


def _save_history(data: Dict[str, Any], path: str = HISTORY_PATH) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2, default=str))


def record_benchmark_run(
    commit_hash: str,
    branch: str,
    categories: Dict[str, Dict[str, Any]],
    total_cost_usd: float = 0.0,
    total_runtime_seconds: float = 0.0,
) -> Dict[str, Any]:
    """Append a benchmark run to history and return analysis."""
    history = _load_history()

    run_record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "commit": commit_hash,
        "branch": branch,
        "categories": categories,
        "total_cost_usd": total_cost_usd,
        "total_runtime_seconds": total_runtime_seconds,
    }
    history["runs"].append(run_record)

    analysis = _analyze(history)
    history["latest_analysis"] = analysis

    for alert in analysis.get("alerts", []):
        history["alerts"].append(alert)

    _save_history(history)
    return analysis


def _analyze(history: Dict[str, Any]) -> Dict[str, Any]:
    runs = history.get("runs", [])
    if not runs:
        return {"status": "no_data"}

    latest = runs[-1]
    categories = latest.get("categories", {})

    rolling: Dict[str, List[float]] = {}
    for run in runs[-30:]:
        for cat, data in run.get("categories", {}).items():
            rolling.setdefault(cat, []).append(data.get("accuracy", 0))

    analysis: Dict[str, Any] = {
        "run_count": len(runs),
        "latest_timestamp": latest.get("timestamp"),
        "categories": {},
        "alerts": [],
    }

    for cat, scores in rolling.items():
        mean = sum(scores) / len(scores) if scores else 0
        variance = sum((s - mean) ** 2 for s in scores) / len(scores) if len(scores) > 1 else 0
        volatility = math.sqrt(variance)

        cat_analysis = {
            "current": scores[-1] if scores else 0,
            "rolling_30_mean": round(mean, 2),
            "volatility": round(volatility, 3),
            "trend": "stable",
        }

        if len(scores) >= 2:
            delta = scores[-1] - scores[-2]
            if delta < -DEGRADATION_THRESHOLD_PCT:
                cat_analysis["trend"] = "degrading"
                alert = {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "category": cat,
                    "severity": "warning",
                    "message": (
                        f"Elite performance drop: {cat} dropped {abs(delta):.1f}% "
                        f"(from {scores[-2]:.1f}% to {scores[-1]:.1f}%)"
                    ),
                }
                analysis["alerts"].append(alert)
                logger.warning(alert["message"])
            elif delta > DEGRADATION_THRESHOLD_PCT:
                cat_analysis["trend"] = "improving"

        analysis["categories"][cat] = cat_analysis

    return analysis


def print_performance_summary(path: str = HISTORY_PATH) -> None:
    """Print the latest performance analysis."""
    history = _load_history(path)
    analysis = history.get("latest_analysis", {})
    if not analysis or analysis.get("status") == "no_data":
        print("  No performance history available.")
        return

    print("\n  ╔═══════════════════════════════════════════════╗")
    print("  ║      PERFORMANCE FEEDBACK LOOP SUMMARY        ║")
    print("  ╚═══════════════════════════════════════════════╝")
    print(f"  Total runs recorded: {analysis.get('run_count', 0)}")
    print(f"  Latest: {analysis.get('latest_timestamp', 'n/a')}")
    cats = analysis.get("categories", {})
    if cats:
        print(f"  {'Category':<16} {'Current':>8} {'30d Mean':>10} {'Volatility':>11} {'Trend':>10}")
        print("  " + "-" * 55)
        for cat, info in sorted(cats.items()):
            print(
                f"  {cat:<16} {info['current']:>7.1f}% {info['rolling_30_mean']:>9.1f}% "
                f"{info['volatility']:>10.3f} {info['trend']:>10}"
            )
    alerts = analysis.get("alerts", [])
    if alerts:
        print(f"\n  Active alerts ({len(alerts)}):")
        for a in alerts:
            print(f"    [{a['severity'].upper()}] {a['message']}")
    print()
