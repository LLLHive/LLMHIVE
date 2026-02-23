"""Enterprise Reliability Guard — SLA monitoring and breach alerting.

Tracks per-model:
  - Latency variance (p50, p95, max)
  - Provider failure frequency
  - Error rate

SLA breach alerts when:
  - p95 latency > 2x baseline
  - error rate > 2%
  - verify timeout frequency > threshold

Advisory only — no automatic rerouting.
"""
from __future__ import annotations

import json
import logging
import math
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .model_registry_2026 import get_model_registry_2026

logger = logging.getLogger(__name__)

SLA_LATENCY_MULTIPLIER = 2.0
SLA_ERROR_RATE_THRESHOLD = 0.02
SLA_VERIFY_TIMEOUT_THRESHOLD = 0.05

SLA_TIERS: Dict[str, Dict[str, Any]] = {
    "standard": {
        "max_latency_ms": 5000,
        "max_error_rate": 0.05,
        "verify_timeout_threshold": 0.10,
        "drift_tolerance": "warn",
        "description": "Default tier — relaxed thresholds for development / testing",
    },
    "enterprise": {
        "max_latency_ms": 3000,
        "max_error_rate": 0.02,
        "verify_timeout_threshold": 0.05,
        "drift_tolerance": "log_critical",
        "description": "Enterprise tier — production SLA for paying customers",
    },
    "mission_critical": {
        "max_latency_ms": 1500,
        "max_error_rate": 0.005,
        "verify_timeout_threshold": 0.02,
        "drift_tolerance": "abort",
        "description": "Mission-critical tier — zero tolerance for finance / healthcare",
    },
}


@dataclass
class ModelReliabilityStats:
    model_id: str
    provider: str
    total_calls: int = 0
    successes: int = 0
    failures: int = 0
    latencies_ms: List[int] = field(default_factory=list)
    verify_timeouts: int = 0
    sla_breaches: List[str] = field(default_factory=list)

    @property
    def error_rate(self) -> float:
        return self.failures / self.total_calls if self.total_calls else 0.0

    @property
    def p50_latency(self) -> int:
        if not self.latencies_ms:
            return 0
        s = sorted(self.latencies_ms)
        return s[len(s) // 2]

    @property
    def p95_latency(self) -> int:
        if not self.latencies_ms:
            return 0
        s = sorted(self.latencies_ms)
        idx = int(len(s) * 0.95)
        return s[min(idx, len(s) - 1)]

    @property
    def max_latency(self) -> int:
        return max(self.latencies_ms) if self.latencies_ms else 0

    @property
    def latency_stddev(self) -> float:
        if len(self.latencies_ms) < 2:
            return 0.0
        mean = sum(self.latencies_ms) / len(self.latencies_ms)
        var = sum((x - mean) ** 2 for x in self.latencies_ms) / len(self.latencies_ms)
        return math.sqrt(var)


class ReliabilityGuard:
    """Enterprise SLA monitoring — advisory only, no rerouting."""

    def __init__(self) -> None:
        self._stats: Dict[str, ModelReliabilityStats] = {}
        self._provider_failures: Dict[str, int] = defaultdict(int)
        self._alerts: List[Dict[str, Any]] = []

    def record_call(
        self,
        model_id: str,
        provider: str,
        latency_ms: int,
        success: bool,
        is_verify_timeout: bool = False,
    ) -> None:
        if model_id not in self._stats:
            self._stats[model_id] = ModelReliabilityStats(
                model_id=model_id, provider=provider,
            )
        stats = self._stats[model_id]
        stats.total_calls += 1
        if success:
            stats.successes += 1
        else:
            stats.failures += 1
            self._provider_failures[provider] += 1
        stats.latencies_ms.append(latency_ms)
        if is_verify_timeout:
            stats.verify_timeouts += 1

        self._check_sla(stats)

    def _check_sla(self, stats: ModelReliabilityStats) -> None:
        if stats.total_calls < 5:
            return

        registry = get_model_registry_2026()
        entry = registry.get(stats.model_id)
        baseline_p95 = entry.latency_profile.p95 if entry else 2000

        # p95 latency breach
        if stats.p95_latency > baseline_p95 * SLA_LATENCY_MULTIPLIER:
            msg = (
                f"SLA BREACH: {stats.model_id} p95 latency {stats.p95_latency}ms "
                f"> {baseline_p95 * SLA_LATENCY_MULTIPLIER:.0f}ms (2x baseline)"
            )
            if msg not in stats.sla_breaches:
                stats.sla_breaches.append(msg)
                self._alerts.append({
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "type": "latency_breach",
                    "model_id": stats.model_id,
                    "message": msg,
                })
                logger.warning(msg)

        # Error rate breach
        if stats.error_rate > SLA_ERROR_RATE_THRESHOLD:
            msg = (
                f"SLA BREACH: {stats.model_id} error rate "
                f"{stats.error_rate:.1%} > {SLA_ERROR_RATE_THRESHOLD:.1%}"
            )
            if msg not in stats.sla_breaches:
                stats.sla_breaches.append(msg)
                self._alerts.append({
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "type": "error_rate_breach",
                    "model_id": stats.model_id,
                    "message": msg,
                })
                logger.warning(msg)

        # Verify timeout frequency
        if stats.total_calls > 0:
            timeout_rate = stats.verify_timeouts / stats.total_calls
            if timeout_rate > SLA_VERIFY_TIMEOUT_THRESHOLD:
                msg = (
                    f"SLA BREACH: {stats.model_id} verify timeout rate "
                    f"{timeout_rate:.1%} > {SLA_VERIFY_TIMEOUT_THRESHOLD:.1%}"
                )
                if msg not in stats.sla_breaches:
                    stats.sla_breaches.append(msg)
                    self._alerts.append({
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "type": "verify_timeout_breach",
                        "model_id": stats.model_id,
                        "message": msg,
                    })
                    logger.warning(msg)

    def _compute_sla_compliance(
        self, models_summary: Dict[str, Any]
    ) -> Dict[str, Any]:
        compliance: Dict[str, Any] = {}
        for tier_name, tier_cfg in SLA_TIERS.items():
            max_lat = tier_cfg["max_latency_ms"]
            max_err = tier_cfg["max_error_rate"]
            max_vt = tier_cfg["verify_timeout_threshold"]
            total_models = len(models_summary)
            compliant = 0
            for mid, mdata in models_summary.items():
                p95 = mdata.get("p95_latency_ms", 0)
                err = mdata.get("error_rate", 0.0)
                tc = mdata.get("total_calls", 0)
                vt = mdata.get("verify_timeouts", 0)
                vt_rate = vt / tc if tc else 0.0
                if p95 <= max_lat and err <= max_err and vt_rate <= max_vt:
                    compliant += 1
            pct = round(compliant / total_models * 100, 1) if total_models else 0.0
            compliance[tier_name] = {
                "compliant_models": compliant,
                "total_models": total_models,
                "compliance_pct": pct,
            }
        return compliance

    def get_summary(self) -> Dict[str, Any]:
        models_summary = {}
        for mid, stats in self._stats.items():
            models_summary[mid] = {
                "total_calls": stats.total_calls,
                "error_rate": round(stats.error_rate, 4),
                "p50_latency_ms": stats.p50_latency,
                "p95_latency_ms": stats.p95_latency,
                "max_latency_ms": stats.max_latency,
                "latency_stddev_ms": round(stats.latency_stddev, 1),
                "verify_timeouts": stats.verify_timeouts,
                "sla_breaches": stats.sla_breaches,
            }
        sla_compliance = self._compute_sla_compliance(models_summary)

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "models": models_summary,
            "provider_failures": dict(self._provider_failures),
            "total_alerts": len(self._alerts),
            "alerts": self._alerts[-20:],
            "sla_tiers": {name: tier["description"] for name, tier in SLA_TIERS.items()},
            "sla_compliance": sla_compliance,
        }

    def save_summary(self) -> str:
        report_dir = Path("benchmark_reports")
        report_dir.mkdir(parents=True, exist_ok=True)
        path = str(report_dir / "reliability_summary.json")
        Path(path).write_text(json.dumps(self.get_summary(), indent=2, default=str))
        return path


_instance: Optional[ReliabilityGuard] = None


def get_reliability_guard() -> ReliabilityGuard:
    global _instance
    if _instance is None:
        _instance = ReliabilityGuard()
    return _instance
