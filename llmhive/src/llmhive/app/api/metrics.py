"""Metrics and observability endpoints for LLMHive.

This module provides:
- Prometheus-compatible metrics endpoint
- Health check endpoints
- System metrics (CPU, memory, etc.)
- Application metrics (requests, latencies, etc.)
"""
from __future__ import annotations

import logging
import os
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, Response, status, Header, HTTPException, Depends
from pydantic import BaseModel

from ..startup_checks import get_config_summary

logger = logging.getLogger(__name__)

router = APIRouter()
def _require_metrics_auth(x_api_key: Optional[str] = Header(default=None)) -> None:
    """Simple header-based guard for metrics endpoints."""
    expected = os.getenv("METRICS_API_KEY")
    if expected:
        if not x_api_key or x_api_key != expected:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
    # If no key configured, allow (backward compatible)


# In-memory metrics storage (for basic metrics without Prometheus dependency)
_metrics: Dict[str, Any] = {
    "start_time": datetime.now(timezone.utc).isoformat(),
    "request_count": 0,
    "error_count": 0,
    "total_latency_ms": 0,
    "orchestrations": {
        "total": 0,
        "success": 0,
        "failure": 0,
        "avg_latency_ms": 0,
    },
    "models_used": {},
    "agents_invoked": {},
}


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    timestamp: str
    version: str = "1.0.0"
    environment: str = "development"


class MetricsResponse(BaseModel):
    """Metrics response model."""
    uptime_seconds: float
    request_count: int
    error_count: int
    error_rate: float
    orchestrations: Dict[str, Any]
    models_used: Dict[str, int]
    agents_invoked: Dict[str, int]
    config: Dict[str, Any]


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Basic health check endpoint.
    
    Returns:
        HealthResponse with status and timestamp
    """
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now(timezone.utc).isoformat(),
        version=os.getenv("APP_VERSION", "1.0.0"),
        environment=os.getenv("ENVIRONMENT", "development"),
    )


@router.get("/health/live")
async def liveness_probe() -> Dict[str, str]:
    """Kubernetes liveness probe endpoint.
    
    Returns 200 if the application is running.
    """
    return {"status": "ok"}


@router.get("/health/ready")
async def readiness_probe() -> Dict[str, Any]:
    """Kubernetes readiness probe endpoint.
    
    Checks if the application is ready to receive traffic.
    """
    # Check if at least one LLM provider is configured
    config = get_config_summary()
    has_provider = any(config["llm_providers"].values())
    
    if has_provider or os.getenv("ALLOW_STUB_PROVIDER", "false").lower() == "true":
        return {"status": "ready", "providers": config["llm_providers"]}
    else:
        return Response(
            content='{"status": "not_ready", "reason": "No LLM providers configured"}',
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            media_type="application/json",
        )


@router.get("/metrics", response_model=MetricsResponse, dependencies=[Depends(_require_metrics_auth)])
async def get_metrics() -> MetricsResponse:
    """Get application metrics.
    
    Returns:
        MetricsResponse with current metrics
    """
    start_time = datetime.fromisoformat(_metrics["start_time"])
    uptime = (datetime.now(timezone.utc) - start_time).total_seconds()
    
    request_count = _metrics["request_count"]
    error_count = _metrics["error_count"]
    error_rate = error_count / request_count if request_count > 0 else 0.0
    
    return MetricsResponse(
        uptime_seconds=uptime,
        request_count=request_count,
        error_count=error_count,
        error_rate=error_rate,
        orchestrations=_metrics["orchestrations"],
        models_used=_metrics["models_used"],
        agents_invoked=_metrics["agents_invoked"],
        config=get_config_summary(),
    )


@router.get("/metrics/prometheus", dependencies=[Depends(_require_metrics_auth)])
async def prometheus_metrics() -> Response:
    """Prometheus-compatible metrics endpoint.
    
    Returns metrics in Prometheus text format.
    """
    start_time = datetime.fromisoformat(_metrics["start_time"])
    uptime = (datetime.now(timezone.utc) - start_time).total_seconds()
    
    lines = [
        "# HELP llmhive_uptime_seconds Time since application start",
        "# TYPE llmhive_uptime_seconds gauge",
        f"llmhive_uptime_seconds {uptime}",
        "",
        "# HELP llmhive_requests_total Total number of requests",
        "# TYPE llmhive_requests_total counter",
        f'llmhive_requests_total {_metrics["request_count"]}',
        "",
        "# HELP llmhive_errors_total Total number of errors",
        "# TYPE llmhive_errors_total counter",
        f'llmhive_errors_total {_metrics["error_count"]}',
        "",
        "# HELP llmhive_orchestrations_total Total orchestrations",
        "# TYPE llmhive_orchestrations_total counter",
        f'llmhive_orchestrations_total{{status="success"}} {_metrics["orchestrations"]["success"]}',
        f'llmhive_orchestrations_total{{status="failure"}} {_metrics["orchestrations"]["failure"]}',
        "",
        "# HELP llmhive_orchestration_latency_ms Average orchestration latency in milliseconds",
        "# TYPE llmhive_orchestration_latency_ms gauge",
        f'llmhive_orchestration_latency_ms {_metrics["orchestrations"]["avg_latency_ms"]}',
        "",
        "# HELP llmhive_models_used_total Model usage counts",
        "# TYPE llmhive_models_used_total counter",
    ]
    
    for model, count in _metrics["models_used"].items():
        lines.append(f'llmhive_models_used_total{{model="{model}"}} {count}')
    
    lines.extend([
        "",
        "# HELP llmhive_agents_invoked_total Agent invocation counts",
        "# TYPE llmhive_agents_invoked_total counter",
    ])
    
    for agent, count in _metrics["agents_invoked"].items():
        lines.append(f'llmhive_agents_invoked_total{{agent="{agent}"}} {count}')
    
    return Response(
        content="\n".join(lines) + "\n",
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )


# Metrics recording functions (to be called from other modules)

def record_request() -> None:
    """Record an incoming request."""
    _metrics["request_count"] += 1


def record_error() -> None:
    """Record an error."""
    _metrics["error_count"] += 1


def record_orchestration(success: bool, latency_ms: float, models: list[str]) -> None:
    """Record an orchestration result.
    
    Args:
        success: Whether the orchestration succeeded
        latency_ms: Latency in milliseconds
        models: List of models used
    """
    orch = _metrics["orchestrations"]
    orch["total"] += 1
    
    if success:
        orch["success"] += 1
    else:
        orch["failure"] += 1
    
    # Update average latency (rolling average)
    total = orch["total"]
    current_avg = orch["avg_latency_ms"]
    orch["avg_latency_ms"] = ((current_avg * (total - 1)) + latency_ms) / total
    
    # Track model usage
    for model in models:
        _metrics["models_used"][model] = _metrics["models_used"].get(model, 0) + 1


def record_agent_invocation(agent_type: str) -> None:
    """Record an agent invocation.
    
    Args:
        agent_type: Type of agent invoked
    """
    _metrics["agents_invoked"][agent_type] = _metrics["agents_invoked"].get(agent_type, 0) + 1


def get_metrics_snapshot() -> Dict[str, Any]:
    """Get a snapshot of current metrics.
    
    Returns:
        Copy of current metrics dictionary
    """
    return _metrics.copy()


def reset_metrics() -> None:
    """Reset all metrics (useful for testing)."""
    global _metrics
    _metrics = {
        "start_time": datetime.now(timezone.utc).isoformat(),
        "request_count": 0,
        "error_count": 0,
        "total_latency_ms": 0,
        "orchestrations": {
            "total": 0,
            "success": 0,
            "failure": 0,
            "avg_latency_ms": 0,
        },
        "models_used": {},
        "agents_invoked": {},
    }
