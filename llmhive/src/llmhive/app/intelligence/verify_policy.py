"""Verify Pipeline Policy — Deterministic verification model isolation.

Separates GENERATION_MODEL from VERIFY_MODEL.
Enforces deterministic elite reasoning for verification.
Logs verify traces independently.

Timeout enforcement:
  > 12s → warn
  > 20s → fail immediately (do not allow verify to retry indefinitely)
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .elite_policy import get_verify_model, is_benchmark_mode
from .model_registry_2026 import get_model_registry_2026

logger = logging.getLogger(__name__)

VERIFY_TIMEOUT_WARN_MS = 12_000
VERIFY_TIMEOUT_FAIL_MS = 20_000
CIRCUIT_BREAKER_CONSECUTIVE = 5


@dataclass
class VerifyTrace:
    question_id: str
    generation_model: str
    verify_model: str
    verify_provider: str
    latency_ms: int
    passed: bool
    generation_answer: str = ""
    verify_answer: str = ""
    drift_detected: bool = False
    timeout_warning: bool = False
    timeout_failed: bool = False


class VerifyTimeoutError(RuntimeError):
    """Raised when verify call exceeds the hard 30s timeout."""
    pass


class VerifyPolicy:
    """Enforces deterministic verification model selection and trace logging."""

    ROLLING_WINDOW = 50
    SLA_TIMEOUT_RATE_WARN = 0.08

    def __init__(self) -> None:
        self._registry = get_model_registry_2026()
        self._traces: List[VerifyTrace] = []
        self._consecutive_failures = 0
        self._circuit_open = False
        self._timeout_count = 0
        self._sla_warnings: List[str] = []

    @property
    def verify_model_id(self) -> str:
        return get_verify_model()

    @property
    def verify_entry(self):
        return self._registry.get(self.verify_model_id)

    def assert_verify_model(self, actual_model: str) -> None:
        """In benchmark mode, raise if verify model doesn't match policy."""
        if not is_benchmark_mode():
            return
        expected = self.verify_model_id
        if actual_model.lower().strip() != expected.lower().strip():
            raise RuntimeError(
                f"Verify model drift: expected={expected}, actual={actual_model}"
            )

    def check_timeout(self, latency_ms: int, question_id: str) -> None:
        """Enforce hard timeout. Must be called before record_trace."""
        if latency_ms > VERIFY_TIMEOUT_FAIL_MS:
            self._timeout_count += 1
            logger.error(
                "Verify HARD TIMEOUT: %dms > %dms limit (question=%s)",
                latency_ms, VERIFY_TIMEOUT_FAIL_MS, question_id,
            )
            raise VerifyTimeoutError(
                f"Verify latency {latency_ms}ms exceeds {VERIFY_TIMEOUT_FAIL_MS}ms hard limit"
            )

    def record_trace(self, trace: VerifyTrace) -> None:
        if trace.latency_ms > VERIFY_TIMEOUT_WARN_MS:
            trace.timeout_warning = True
            logger.warning(
                "Verify latency %dms > %dms warn threshold (question=%s)",
                trace.latency_ms, VERIFY_TIMEOUT_WARN_MS, trace.question_id,
            )

        if trace.latency_ms > VERIFY_TIMEOUT_FAIL_MS:
            trace.timeout_failed = True
            self._timeout_count += 1

        if not trace.passed:
            self._consecutive_failures += 1
            if self._consecutive_failures >= CIRCUIT_BREAKER_CONSECUTIVE:
                self._circuit_open = True
                logger.error(
                    "Verify circuit breaker OPEN after %d consecutive failures",
                    self._consecutive_failures,
                )
        else:
            self._consecutive_failures = 0

        self._traces.append(trace)
        self._check_rolling_sla()

    def _check_rolling_sla(self) -> None:
        window = self._traces[-self.ROLLING_WINDOW:]
        if len(window) < 10:
            return
        timeouts = sum(1 for t in window if t.timeout_warning or t.timeout_failed)
        rate = timeouts / len(window)
        if rate > self.SLA_TIMEOUT_RATE_WARN:
            msg = (
                f"VERIFY_SLA_WARNING: rolling timeout rate {rate:.1%} > "
                f"{self.SLA_TIMEOUT_RATE_WARN:.0%} over last {len(window)} calls"
            )
            if msg not in self._sla_warnings:
                self._sla_warnings.append(msg)
                logger.warning(msg)

    @property
    def is_circuit_open(self) -> bool:
        return self._circuit_open

    @property
    def timeout_rate(self) -> float:
        total = len(self._traces)
        if total == 0:
            return 0.0
        return self._timeout_count / total

    @property
    def verify_penalty(self) -> float:
        """Rolling penalty decay: penalty = min(1.0, timeout_rate * 1.5).

        Fed into ensemble weighting to reduce trust when verify is degraded.
        """
        return min(1.0, self.timeout_rate * 1.5)

    def get_latency_distribution(self) -> Dict[str, Any]:
        latencies = [t.latency_ms for t in self._traces]
        if not latencies:
            return {"p50": 0, "p95": 0, "max": 0, "count": 0}
        s = sorted(latencies)
        return {
            "p50": s[len(s) // 2],
            "p95": s[int(len(s) * 0.95)],
            "max": s[-1],
            "count": len(s),
        }

    def get_failure_classification(self) -> Dict[str, int]:
        classes = {"timeout": 0, "mismatch": 0, "exception": 0}
        for t in self._traces:
            if t.passed:
                continue
            if t.timeout_failed:
                classes["timeout"] += 1
            elif t.generation_answer and t.verify_answer and t.generation_answer != t.verify_answer:
                classes["mismatch"] += 1
            else:
                classes["exception"] += 1
        return classes

    @property
    def verify_latency_p95(self) -> int:
        latencies = sorted(t.latency_ms for t in self._traces)
        if not latencies:
            return 0
        return latencies[int(len(latencies) * 0.95)]

    def get_summary(self) -> Dict[str, Any]:
        total = len(self._traces)
        passed = sum(1 for t in self._traces if t.passed)
        timeouts_warn = sum(1 for t in self._traces if t.timeout_warning)
        timeouts_fail = sum(1 for t in self._traces if t.timeout_failed)
        latencies = [t.latency_ms for t in self._traces]
        avg_latency = sum(latencies) / total if total else 0
        max_latency = max(latencies) if latencies else 0
        return {
            "total_verifications": total,
            "passed": passed,
            "failed": total - passed,
            "timeout_warnings": timeouts_warn,
            "timeout_failures": timeouts_fail,
            "timeout_rate": round(self.timeout_rate, 4),
            "verify_penalty": round(self.verify_penalty, 4),
            "avg_latency_ms": round(avg_latency),
            "max_latency_ms": max_latency,
            "verify_latency_p95": self.verify_latency_p95,
            "latency_distribution": self.get_latency_distribution(),
            "failure_classification": self.get_failure_classification(),
            "sla_warnings": self._sla_warnings,
            "circuit_open": self._circuit_open,
            "consecutive_failures": self._consecutive_failures,
            "verify_model": self.verify_model_id,
        }

    def generate_stability_summary(self) -> Dict[str, Any]:
        from datetime import datetime, timezone
        summary = self.get_summary()
        summary["timestamp"] = datetime.now(timezone.utc).isoformat()
        window = self._traces[-self.ROLLING_WINDOW:]
        if window:
            rolling_timeouts = sum(1 for t in window if t.timeout_warning or t.timeout_failed)
            summary["rolling_timeout_rate"] = round(rolling_timeouts / len(window), 4)
        else:
            summary["rolling_timeout_rate"] = 0.0
        return summary


_instance: Optional[VerifyPolicy] = None


def get_verify_policy() -> VerifyPolicy:
    global _instance
    if _instance is None:
        _instance = VerifyPolicy()
    return _instance
