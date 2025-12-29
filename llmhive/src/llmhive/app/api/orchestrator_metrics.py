"""Orchestrator Metrics Module for LLMHive.

Enhancement-2: Prometheus-compatible metrics for orchestrator observability.

This module provides:
- Strategy execution time histograms
- Tool usage counters
- Error rate tracking
- Memory usage gauge

Metrics are exposed via /api/v1/metrics/orchestrator endpoint.
"""
from __future__ import annotations

import logging
import os
from typing import Any, Dict

from fastapi import APIRouter, Response, Depends
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/metrics", tags=["metrics"])

# Try to import prometheus_client, fall back to simple counters if not available
try:
    from prometheus_client import Counter, Gauge, Histogram, generate_latest, CONTENT_TYPE_LATEST
    import psutil
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    logger.info("prometheus_client not available, using simple metrics")


# ==============================================================================
# Prometheus Metrics Definitions (when available)
# ==============================================================================

if PROMETHEUS_AVAILABLE:
    # Strategy execution duration histogram
    STRATEGY_TIME = Histogram(
        "orchestrator_strategy_duration_seconds",
        "Duration of orchestration (seconds) by strategy",
        ["strategy"],
        buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0)
    )
    
    # Tool usage counter with status label
    TOOL_USAGE = Counter(
        "orchestrator_tool_usage_total",
        "Count of tool invocations by tool type and status",
        ["tool_type", "status"]
    )
    
    # Orchestrator error counter
    ORCHESTRATOR_ERRORS = Counter(
        "orchestrator_errors_total",
        "Count of orchestrator errors by type",
        ["error_type"]
    )
    
    # Memory usage gauge
    MEMORY_USAGE = Gauge(
        "orchestrator_memory_bytes",
        "Current memory usage of orchestrator process in bytes"
    )
    
    # Cache metrics
    CACHE_HITS = Counter(
        "orchestrator_cache_hits_total",
        "Number of response cache hits"
    )
    
    CACHE_MISSES = Counter(
        "orchestrator_cache_misses_total",
        "Number of response cache misses"
    )
    
    # Active sessions gauge
    ACTIVE_SESSIONS = Gauge(
        "orchestrator_active_sessions",
        "Number of active collaboration sessions"
    )

else:
    # Simple in-memory counters as fallback
    class SimpleCounter:
        """Simple counter fallback when prometheus_client is not available."""
        def __init__(self, name: str):
            self.name = name
            self._values: Dict[tuple, int] = {}
        
        def labels(self, **kwargs) -> "SimpleCounter":
            self._current_labels = tuple(sorted(kwargs.items()))
            return self
        
        def inc(self, amount: int = 1) -> None:
            key = getattr(self, '_current_labels', ())
            self._values[key] = self._values.get(key, 0) + amount
        
        def get_samples(self) -> Dict[tuple, int]:
            return dict(self._values)
    
    class SimpleHistogram:
        """Simple histogram fallback."""
        def __init__(self, name: str):
            self.name = name
            self._values: Dict[tuple, list] = {}
        
        def labels(self, **kwargs) -> "SimpleHistogram":
            self._current_labels = tuple(sorted(kwargs.items()))
            return self
        
        def observe(self, value: float) -> None:
            key = getattr(self, '_current_labels', ())
            if key not in self._values:
                self._values[key] = []
            self._values[key].append(value)
            # Keep only last 1000 observations
            self._values[key] = self._values[key][-1000:]
        
        def get_samples(self) -> Dict[tuple, list]:
            return dict(self._values)
    
    class SimpleGauge:
        """Simple gauge fallback."""
        def __init__(self, name: str):
            self.name = name
            self._value = 0.0
        
        def set(self, value: float) -> None:
            self._value = value
        
        def inc(self, amount: float = 1.0) -> None:
            self._value += amount
        
        def dec(self, amount: float = 1.0) -> None:
            self._value -= amount
        
        def get(self) -> float:
            return self._value
    
    # Create simple metric instances
    STRATEGY_TIME = SimpleHistogram("orchestrator_strategy_duration_seconds")
    TOOL_USAGE = SimpleCounter("orchestrator_tool_usage_total")
    ORCHESTRATOR_ERRORS = SimpleCounter("orchestrator_errors_total")
    MEMORY_USAGE = SimpleGauge("orchestrator_memory_bytes")
    CACHE_HITS = SimpleCounter("orchestrator_cache_hits_total")
    CACHE_MISSES = SimpleCounter("orchestrator_cache_misses_total")
    ACTIVE_SESSIONS = SimpleGauge("orchestrator_active_sessions")


# ==============================================================================
# Metrics Response Models
# ==============================================================================

class OrchestratorMetricsResponse(BaseModel):
    """Response model for orchestrator metrics."""
    memory_bytes: int
    memory_mb: float
    cache_hit_rate: float
    active_sessions: int
    tool_usage: Dict[str, int]
    error_counts: Dict[str, int]
    strategy_latencies: Dict[str, float]


# ==============================================================================
# Metrics Endpoints
# ==============================================================================

@router.get("/orchestrator", tags=["metrics"])
def get_orchestrator_metrics() -> Response:
    """
    Prometheus metrics for orchestrator performance and usage.
    
    Enhancement-2: Returns metrics in Prometheus text format for scraping.
    """
    if PROMETHEUS_AVAILABLE:
        # Update memory gauge on each scrape
        try:
            import psutil
            process = psutil.Process(os.getpid())
            MEMORY_USAGE.set(process.memory_info().rss)
        except Exception as e:
            logger.warning(f"Failed to update memory metric: {e}")
        
        # Return all metrics in Prometheus text format
        metrics_data = generate_latest()
        return Response(content=metrics_data, media_type=CONTENT_TYPE_LATEST)
    else:
        # Return simple JSON metrics when Prometheus not available
        return Response(
            content=_generate_simple_metrics(),
            media_type="text/plain; version=0.0.4; charset=utf-8"
        )


@router.get("/orchestrator/json", response_model=OrchestratorMetricsResponse, tags=["metrics"])
def get_orchestrator_metrics_json() -> OrchestratorMetricsResponse:
    """
    Get orchestrator metrics in JSON format.
    
    Useful for frontend dashboards and debugging.
    """
    memory_bytes = 0
    try:
        import psutil
        process = psutil.Process(os.getpid())
        memory_bytes = process.memory_info().rss
    except Exception:
        pass
    
    # Collect tool usage
    tool_usage = {}
    if PROMETHEUS_AVAILABLE:
        # Extract from Prometheus metrics would require more complex parsing
        pass
    elif hasattr(TOOL_USAGE, 'get_samples'):
        for labels, count in TOOL_USAGE.get_samples().items():
            label_dict = dict(labels)
            key = f"{label_dict.get('tool_type', 'unknown')}_{label_dict.get('status', 'unknown')}"
            tool_usage[key] = count
    
    # Collect error counts
    error_counts = {}
    if hasattr(ORCHESTRATOR_ERRORS, 'get_samples'):
        for labels, count in ORCHESTRATOR_ERRORS.get_samples().items():
            label_dict = dict(labels)
            key = label_dict.get('error_type', 'unknown')
            error_counts[key] = count
    
    # Collect strategy latencies
    strategy_latencies = {}
    if hasattr(STRATEGY_TIME, 'get_samples'):
        for labels, values in STRATEGY_TIME.get_samples().items():
            label_dict = dict(labels)
            key = label_dict.get('strategy', 'unknown')
            if values:
                strategy_latencies[key] = sum(values) / len(values)
    
    # Get cache stats
    cache_hit_rate = 0.0
    try:
        from ..orchestration.response_cache import get_response_cache
        cache = get_response_cache()
        stats = cache.stats()
        if stats.get('hits', 0) + stats.get('misses', 0) > 0:
            cache_hit_rate = stats.get('hit_rate', 0.0)
    except Exception:
        pass
    
    # Get active sessions
    active_sessions = 0
    if hasattr(ACTIVE_SESSIONS, 'get'):
        active_sessions = int(ACTIVE_SESSIONS.get())
    
    return OrchestratorMetricsResponse(
        memory_bytes=memory_bytes,
        memory_mb=round(memory_bytes / (1024 * 1024), 2),
        cache_hit_rate=cache_hit_rate,
        active_sessions=active_sessions,
        tool_usage=tool_usage,
        error_counts=error_counts,
        strategy_latencies=strategy_latencies,
    )


def _generate_simple_metrics() -> str:
    """Generate simple Prometheus-like text output when prometheus_client not available."""
    lines = []
    
    # Memory
    memory_bytes = 0
    try:
        import psutil
        process = psutil.Process(os.getpid())
        memory_bytes = process.memory_info().rss
    except Exception:
        pass
    
    lines.extend([
        "# HELP orchestrator_memory_bytes Current memory usage",
        "# TYPE orchestrator_memory_bytes gauge",
        f"orchestrator_memory_bytes {memory_bytes}",
        "",
    ])
    
    # Tool usage
    lines.extend([
        "# HELP orchestrator_tool_usage_total Tool invocation counts",
        "# TYPE orchestrator_tool_usage_total counter",
    ])
    if hasattr(TOOL_USAGE, 'get_samples'):
        for labels, count in TOOL_USAGE.get_samples().items():
            label_dict = dict(labels)
            tool_type = label_dict.get('tool_type', 'unknown')
            status = label_dict.get('status', 'unknown')
            lines.append(f'orchestrator_tool_usage_total{{tool_type="{tool_type}",status="{status}"}} {count}')
    lines.append("")
    
    # Errors
    lines.extend([
        "# HELP orchestrator_errors_total Error counts by type",
        "# TYPE orchestrator_errors_total counter",
    ])
    if hasattr(ORCHESTRATOR_ERRORS, 'get_samples'):
        for labels, count in ORCHESTRATOR_ERRORS.get_samples().items():
            label_dict = dict(labels)
            error_type = label_dict.get('error_type', 'unknown')
            lines.append(f'orchestrator_errors_total{{error_type="{error_type}"}} {count}')
    lines.append("")
    
    # Active sessions
    lines.extend([
        "# HELP orchestrator_active_sessions Active collaboration sessions",
        "# TYPE orchestrator_active_sessions gauge",
    ])
    if hasattr(ACTIVE_SESSIONS, 'get'):
        lines.append(f"orchestrator_active_sessions {int(ACTIVE_SESSIONS.get())}")
    lines.append("")
    
    return "\n".join(lines) + "\n"


# ==============================================================================
# Convenience Functions for Recording Metrics
# ==============================================================================

def record_tool_invocation(tool_type: str, success: bool = True) -> None:
    """Record a tool invocation."""
    status = "success" if success else "failure"
    try:
        TOOL_USAGE.labels(tool_type=tool_type, status=status).inc()
    except Exception:
        pass


def record_orchestrator_error(error_type: str) -> None:
    """Record an orchestrator error."""
    try:
        ORCHESTRATOR_ERRORS.labels(error_type=error_type).inc()
    except Exception:
        pass


def record_strategy_duration(strategy: str, duration_seconds: float) -> None:
    """Record strategy execution duration."""
    try:
        STRATEGY_TIME.labels(strategy=strategy).observe(duration_seconds)
    except Exception:
        pass


def record_cache_hit() -> None:
    """Record a cache hit."""
    try:
        if hasattr(CACHE_HITS, 'inc'):
            CACHE_HITS.inc()
    except Exception:
        pass


def record_cache_miss() -> None:
    """Record a cache miss."""
    try:
        if hasattr(CACHE_MISSES, 'inc'):
            CACHE_MISSES.inc()
    except Exception:
        pass


def update_active_sessions(count: int) -> None:
    """Update the active sessions gauge."""
    try:
        if hasattr(ACTIVE_SESSIONS, 'set'):
            ACTIVE_SESSIONS.set(count)
    except Exception:
        pass

