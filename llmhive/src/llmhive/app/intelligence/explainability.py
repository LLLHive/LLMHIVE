"""Explainability Export — Enterprise audit-grade per-call decision trace.

Generates a structured record for every intelligence layer decision:
  - Which model was selected and why
  - Routing score breakdown
  - Ensemble entropy
  - Verify latency
  - Drift flags
  - Strategy DB gating status

Appends to: benchmark_reports/explainability_trace.jsonl
"""
from __future__ import annotations

import json
import logging
import threading
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ExplainabilityRecord:
    timestamp: str
    category: str
    model_used: str
    intelligence_mode: str
    routing_score_breakdown: Dict[str, float] = field(default_factory=dict)
    ensemble_entropy: Optional[float] = None
    ensemble_escalated: bool = False
    verify_latency_ms: Optional[int] = None
    verify_passed: Optional[bool] = None
    drift_flags: List[str] = field(default_factory=list)
    strategy_db_gating: bool = False
    strategy_recommendation: Optional[str] = None
    strategy_meets_stability: bool = False
    fallback_used: bool = False
    latency_ms: int = 0
    decision_reason: str = ""


class ExplainabilityExporter:
    """Thread-safe JSONL writer for enterprise audit trail."""

    def __init__(self) -> None:
        self._path: Optional[str] = None
        self._lock = threading.Lock()
        self._records: List[ExplainabilityRecord] = []

    def init_trace(self) -> str:
        report_dir = Path("benchmark_reports")
        report_dir.mkdir(parents=True, exist_ok=True)
        self._path = str(report_dir / "explainability_trace.jsonl")
        return self._path

    def record(self, entry: ExplainabilityRecord) -> None:
        self._records.append(entry)
        if not self._path:
            self.init_trace()
        try:
            line = json.dumps(asdict(entry), default=str) + "\n"
            with self._lock:
                with open(self._path, "a") as f:  # type: ignore
                    f.write(line)
        except Exception:
            pass

    def get_summary(self) -> Dict[str, Any]:
        total = len(self._records)
        if total == 0:
            return {"total_decisions": 0}

        categories: Dict[str, int] = {}
        models: Dict[str, int] = {}
        drift_count = 0
        escalation_count = 0
        gated_count = 0

        for r in self._records:
            categories[r.category] = categories.get(r.category, 0) + 1
            models[r.model_used] = models.get(r.model_used, 0) + 1
            if r.drift_flags:
                drift_count += 1
            if r.ensemble_escalated:
                escalation_count += 1
            if r.strategy_db_gating:
                gated_count += 1

        return {
            "total_decisions": total,
            "categories": categories,
            "models": models,
            "drift_events": drift_count,
            "escalations": escalation_count,
            "strategy_gated": gated_count,
            "trace_file": self._path,
        }


_instance: Optional[ExplainabilityExporter] = None


def get_explainability_exporter() -> ExplainabilityExporter:
    global _instance
    if _instance is None:
        _instance = ExplainabilityExporter()
    return _instance
