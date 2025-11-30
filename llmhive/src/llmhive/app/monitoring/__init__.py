"""Monitoring and Observability for LLMHive.

This module provides:
- Prometheus metrics for requests, latency, tokens, errors
- Structured logging with request tracing
- Health checks and readiness probes
- Error tracking integration (Sentry)
- Performance dashboards
"""
from __future__ import annotations

# Metrics
try:
    from .metrics import (
        MetricsManager,
        get_metrics,
        track_request,
        track_llm_call,
        track_tool_call,
        track_error,
    )
    METRICS_AVAILABLE = True
except ImportError:
    METRICS_AVAILABLE = False
    MetricsManager = None  # type: ignore

# Logging
try:
    from .logging_config import (
        setup_logging,
        get_logger,
        RequestContext,
        log_request,
    )
    LOGGING_AVAILABLE = True
except ImportError:
    LOGGING_AVAILABLE = False

# Health checks
try:
    from .health import (
        HealthChecker,
        HealthStatus,
        get_health_checker,
    )
    HEALTH_AVAILABLE = True
except ImportError:
    HEALTH_AVAILABLE = False

__all__ = [
    "METRICS_AVAILABLE",
    "LOGGING_AVAILABLE",
    "HEALTH_AVAILABLE",
]

if METRICS_AVAILABLE:
    __all__.extend([
        "MetricsManager",
        "get_metrics",
        "track_request",
        "track_llm_call",
        "track_tool_call",
        "track_error",
    ])

if LOGGING_AVAILABLE:
    __all__.extend([
        "setup_logging",
        "get_logger",
        "RequestContext",
        "log_request",
    ])

if HEALTH_AVAILABLE:
    __all__.extend([
        "HealthChecker",
        "HealthStatus",
        "get_health_checker",
    ])

