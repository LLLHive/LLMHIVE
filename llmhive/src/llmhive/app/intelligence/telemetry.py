"""Intelligence Telemetry — Structured per-call trace for forensic analysis.

Extends existing model trace with:
  - capability_tags from registry
  - orchestration_mode context
  - consensus state
  - drift detection flags

Writes to benchmark_reports/intelligence_trace_<ts>.jsonl
Active only when BENCHMARK_MODE=true.
"""
from __future__ import annotations

import json
import os
import threading
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .elite_policy import ELITE_POLICY, is_benchmark_mode


@dataclass
class IntelligenceTraceEntry:
    timestamp: str
    category: str
    provider: str
    model_id: str
    display_name: str
    orchestration_mode: str
    consensus_enabled: bool
    reasoning_mode: str
    temperature: Optional[float]
    top_p: Optional[float]
    seed: Optional[int]
    fallback_used: bool
    retry_count: int
    latency_ms: int
    input_tokens: int
    output_tokens: int
    capability_tags: List[str] = field(default_factory=list)
    is_elite: bool = False
    drift_detected: bool = False
    # Same-model multi-provider failover telemetry
    failover_attempted: bool = False
    failover_provider: Optional[str] = None
    failure_type: Optional[str] = None
    provider_sla_breached: bool = False


class IntelligenceTelemetry:
    """Thread-safe, non-blocking telemetry writer."""

    def __init__(self, trace_path: Optional[str] = None) -> None:
        self._path = trace_path
        self._lock = threading.Lock()
        self._entries: List[IntelligenceTraceEntry] = []

    def init_trace_file(self) -> str:
        """Create trace file and return its path."""
        report_dir = Path("benchmark_reports")
        report_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._path = str(report_dir / f"intelligence_trace_{ts}.jsonl")
        return self._path

    def record(self, entry: IntelligenceTraceEntry) -> None:
        if not is_benchmark_mode():
            return
        expected_elite = ELITE_POLICY.get(entry.category, "")
        entry.is_elite = (
            entry.model_id.lower() == expected_elite.lower()
            if expected_elite else False
        )
        if is_benchmark_mode() and not entry.is_elite and expected_elite:
            entry.drift_detected = True

        self._entries.append(entry)
        self._write(entry)

    def _write(self, entry: IntelligenceTraceEntry) -> None:
        if not self._path:
            return
        try:
            line = json.dumps(asdict(entry), default=str) + "\n"
            with self._lock:
                with open(self._path, "a") as f:
                    f.write(line)
        except Exception:
            pass

    def get_summary(self) -> Dict[str, Any]:
        total = len(self._entries)
        if total == 0:
            return {"total_calls": 0}

        model_counts: Dict[str, int] = {}
        fallback_count = 0
        drift_count = 0
        non_elite_in_benchmark = 0
        failover_count = 0
        sla_breach_count = 0
        failover_providers: Dict[str, int] = {}
        failure_types: Dict[str, int] = {}

        for e in self._entries:
            model_counts[e.display_name] = model_counts.get(e.display_name, 0) + 1
            if e.fallback_used:
                fallback_count += 1
            if e.drift_detected:
                drift_count += 1
            if is_benchmark_mode() and not e.is_elite:
                non_elite_in_benchmark += 1
            if e.failover_attempted:
                failover_count += 1
                if e.failover_provider:
                    failover_providers[e.failover_provider] = (
                        failover_providers.get(e.failover_provider, 0) + 1
                    )
            if e.provider_sla_breached:
                sla_breach_count += 1
            if e.failure_type:
                failure_types[e.failure_type] = (
                    failure_types.get(e.failure_type, 0) + 1
                )

        return {
            "total_calls": total,
            "models_used": model_counts,
            "pct_per_model": {
                k: round(v / total * 100, 1) for k, v in model_counts.items()
            },
            "fallback_calls": fallback_count,
            "drift_events": drift_count,
            "non_elite_in_benchmark": non_elite_in_benchmark,
            "failover_events": failover_count,
            "failover_providers": failover_providers,
            "sla_breaches": sla_breach_count,
            "failure_types": failure_types,
            "trace_file": self._path,
        }

    def print_summary(self) -> None:
        s = self.get_summary()
        if s["total_calls"] == 0:
            return
        print("\n  ╔═══════════════════════════════════════════════╗")
        print("  ║       INTELLIGENCE TELEMETRY SUMMARY          ║")
        print("  ╚═══════════════════════════════════════════════╝")
        print(f"  Total API calls:     {s['total_calls']}")
        print(f"  Fallback calls:      {s['fallback_calls']}")
        print(f"  Drift events:        {s['drift_events']}")
        if s.get("failover_events"):
            print(f"  Failover events:     {s['failover_events']}")
            for prov, cnt in s.get("failover_providers", {}).items():
                print(f"    \u2192 {prov:<24s} {cnt:>4d} times")
        if s.get("sla_breaches"):
            print(f"  SLA breaches:        {s['sla_breaches']}")
        if s.get("failure_types"):
            print("  Failure types:")
            for ft, cnt in s["failure_types"].items():
                print(f"    {ft:<30s} {cnt:>4d}")
        if is_benchmark_mode():
            print(f"  Non-elite (bench):   {s['non_elite_in_benchmark']}")
        print("  Models observed:")
        for model, count in sorted(s["models_used"].items(), key=lambda x: -x[1]):
            pct = s["pct_per_model"][model]
            print(f"    {model:<30s} {count:>4d} calls ({pct:.1f}%)")
        if self._path:
            print(f"  Trace file: {self._path}")
        print()


_instance: Optional[IntelligenceTelemetry] = None


def get_intelligence_telemetry() -> IntelligenceTelemetry:
    global _instance
    if _instance is None:
        _instance = IntelligenceTelemetry()
    return _instance
