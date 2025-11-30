"""Prometheus Metrics for LLMHive.

This module provides comprehensive metrics for monitoring:
- Request rates and latencies
- LLM provider performance
- Token usage and costs
- Tool execution metrics
- Error rates and types
- Cache hit rates

Usage:
    from llmhive.app.monitoring.metrics import get_metrics, track_request
    
    metrics = get_metrics()
    
    with track_request(method="POST", endpoint="/v1/chat"):
        result = await process_request()
"""
from __future__ import annotations

import os
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union

# Prometheus client
try:
    from prometheus_client import (
        Counter,
        Gauge,
        Histogram,
        Info,
        Summary,
        CollectorRegistry,
        generate_latest,
        CONTENT_TYPE_LATEST,
        multiprocess,
    )
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False

import logging

logger = logging.getLogger(__name__)


# ==============================================================================
# Metric Definitions
# ==============================================================================

# Histogram buckets for different measurements
LATENCY_BUCKETS = (0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0)
TOKEN_BUCKETS = (10, 50, 100, 250, 500, 1000, 2500, 5000, 10000, 25000)
COST_BUCKETS = (0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0, 10.0)


class MetricLabels:
    """Standard metric labels."""
    METHOD = "method"
    ENDPOINT = "endpoint"
    STATUS = "status"
    PROVIDER = "provider"
    MODEL = "model"
    TOOL = "tool"
    USER_TIER = "user_tier"
    ERROR_TYPE = "error_type"
    CACHE_STATUS = "cache_status"


# ==============================================================================
# Metrics Manager
# ==============================================================================

class MetricsManager:
    """Central manager for Prometheus metrics.
    
    Provides:
    - HTTP request metrics
    - LLM call metrics
    - Tool execution metrics
    - Token usage tracking
    - Error counting
    - Cache statistics
    
    Usage:
        metrics = MetricsManager()
        
        # Record a request
        metrics.record_request("POST", "/v1/chat", 200, 0.5)
        
        # Record LLM call
        metrics.record_llm_call("openai", "gpt-4o", 1.2, 1500, True)
    """
    
    def __init__(self, registry: Optional[Any] = None):
        """Initialize metrics manager."""
        if not PROMETHEUS_AVAILABLE:
            logger.warning("Prometheus client not available, metrics disabled")
            self._enabled = False
            return
        
        self._enabled = True
        self._registry = registry or CollectorRegistry()
        
        # HTTP Request Metrics
        self.http_requests_total = Counter(
            "llmhive_http_requests_total",
            "Total HTTP requests",
            [MetricLabels.METHOD, MetricLabels.ENDPOINT, MetricLabels.STATUS],
            registry=self._registry,
        )
        
        self.http_request_duration_seconds = Histogram(
            "llmhive_http_request_duration_seconds",
            "HTTP request duration in seconds",
            [MetricLabels.METHOD, MetricLabels.ENDPOINT],
            buckets=LATENCY_BUCKETS,
            registry=self._registry,
        )
        
        self.http_requests_in_progress = Gauge(
            "llmhive_http_requests_in_progress",
            "HTTP requests currently in progress",
            [MetricLabels.METHOD, MetricLabels.ENDPOINT],
            registry=self._registry,
        )
        
        # LLM Call Metrics
        self.llm_calls_total = Counter(
            "llmhive_llm_calls_total",
            "Total LLM API calls",
            [MetricLabels.PROVIDER, MetricLabels.MODEL, MetricLabels.STATUS],
            registry=self._registry,
        )
        
        self.llm_call_duration_seconds = Histogram(
            "llmhive_llm_call_duration_seconds",
            "LLM call duration in seconds",
            [MetricLabels.PROVIDER, MetricLabels.MODEL],
            buckets=LATENCY_BUCKETS,
            registry=self._registry,
        )
        
        self.llm_tokens_total = Counter(
            "llmhive_llm_tokens_total",
            "Total tokens used",
            [MetricLabels.PROVIDER, MetricLabels.MODEL, "token_type"],
            registry=self._registry,
        )
        
        self.llm_tokens_per_request = Histogram(
            "llmhive_llm_tokens_per_request",
            "Tokens per request",
            [MetricLabels.PROVIDER, MetricLabels.MODEL],
            buckets=TOKEN_BUCKETS,
            registry=self._registry,
        )
        
        self.llm_cost_dollars = Counter(
            "llmhive_llm_cost_dollars",
            "Estimated LLM cost in dollars",
            [MetricLabels.PROVIDER, MetricLabels.MODEL],
            registry=self._registry,
        )
        
        # Tool Metrics
        self.tool_calls_total = Counter(
            "llmhive_tool_calls_total",
            "Total tool calls",
            [MetricLabels.TOOL, MetricLabels.STATUS],
            registry=self._registry,
        )
        
        self.tool_call_duration_seconds = Histogram(
            "llmhive_tool_call_duration_seconds",
            "Tool call duration in seconds",
            [MetricLabels.TOOL],
            buckets=LATENCY_BUCKETS,
            registry=self._registry,
        )
        
        # Error Metrics
        self.errors_total = Counter(
            "llmhive_errors_total",
            "Total errors",
            [MetricLabels.ERROR_TYPE, MetricLabels.ENDPOINT],
            registry=self._registry,
        )
        
        # Cache Metrics
        self.cache_operations_total = Counter(
            "llmhive_cache_operations_total",
            "Total cache operations",
            [MetricLabels.CACHE_STATUS],
            registry=self._registry,
        )
        
        self.cache_size_bytes = Gauge(
            "llmhive_cache_size_bytes",
            "Current cache size in bytes",
            registry=self._registry,
        )
        
        # User/Tier Metrics
        self.requests_by_tier = Counter(
            "llmhive_requests_by_tier_total",
            "Requests by user tier",
            [MetricLabels.USER_TIER],
            registry=self._registry,
        )
        
        # Orchestration Metrics
        self.orchestration_steps_total = Counter(
            "llmhive_orchestration_steps_total",
            "Total orchestration steps",
            ["step_type"],
            registry=self._registry,
        )
        
        self.orchestration_duration_seconds = Histogram(
            "llmhive_orchestration_duration_seconds",
            "Total orchestration duration",
            ["orchestration_type"],
            buckets=LATENCY_BUCKETS,
            registry=self._registry,
        )
        
        # Safety/Guardrail Metrics
        self.safety_blocks_total = Counter(
            "llmhive_safety_blocks_total",
            "Safety filter blocks",
            ["block_type"],
            registry=self._registry,
        )
        
        # System Info
        self.info = Info(
            "llmhive",
            "LLMHive application info",
            registry=self._registry,
        )
        self.info.info({
            "version": os.getenv("LLMHIVE_VERSION", "1.0.0"),
            "environment": os.getenv("ENVIRONMENT", "development"),
        })
        
        logger.info("Metrics manager initialized")
    
    @property
    def enabled(self) -> bool:
        return self._enabled
    
    def record_request(
        self,
        method: str,
        endpoint: str,
        status_code: int,
        duration: float,
    ) -> None:
        """Record an HTTP request."""
        if not self._enabled:
            return
        
        self.http_requests_total.labels(
            method=method,
            endpoint=endpoint,
            status=str(status_code),
        ).inc()
        
        self.http_request_duration_seconds.labels(
            method=method,
            endpoint=endpoint,
        ).observe(duration)
    
    def record_llm_call(
        self,
        provider: str,
        model: str,
        duration: float,
        tokens: int,
        success: bool,
        input_tokens: int = 0,
        output_tokens: int = 0,
        cost: float = 0.0,
    ) -> None:
        """Record an LLM API call."""
        if not self._enabled:
            return
        
        status = "success" if success else "error"
        
        self.llm_calls_total.labels(
            provider=provider,
            model=model,
            status=status,
        ).inc()
        
        self.llm_call_duration_seconds.labels(
            provider=provider,
            model=model,
        ).observe(duration)
        
        self.llm_tokens_total.labels(
            provider=provider,
            model=model,
            token_type="total",
        ).inc(tokens)
        
        if input_tokens:
            self.llm_tokens_total.labels(
                provider=provider,
                model=model,
                token_type="input",
            ).inc(input_tokens)
        
        if output_tokens:
            self.llm_tokens_total.labels(
                provider=provider,
                model=model,
                token_type="output",
            ).inc(output_tokens)
        
        self.llm_tokens_per_request.labels(
            provider=provider,
            model=model,
        ).observe(tokens)
        
        if cost > 0:
            self.llm_cost_dollars.labels(
                provider=provider,
                model=model,
            ).inc(cost)
    
    def record_tool_call(
        self,
        tool: str,
        duration: float,
        success: bool,
    ) -> None:
        """Record a tool call."""
        if not self._enabled:
            return
        
        status = "success" if success else "error"
        
        self.tool_calls_total.labels(
            tool=tool,
            status=status,
        ).inc()
        
        self.tool_call_duration_seconds.labels(
            tool=tool,
        ).observe(duration)
    
    def record_error(
        self,
        error_type: str,
        endpoint: str = "unknown",
    ) -> None:
        """Record an error."""
        if not self._enabled:
            return
        
        self.errors_total.labels(
            error_type=error_type,
            endpoint=endpoint,
        ).inc()
    
    def record_cache_operation(self, hit: bool) -> None:
        """Record a cache operation."""
        if not self._enabled:
            return
        
        status = "hit" if hit else "miss"
        self.cache_operations_total.labels(cache_status=status).inc()
    
    def record_tier_request(self, tier: str) -> None:
        """Record a request by user tier."""
        if not self._enabled:
            return
        
        self.requests_by_tier.labels(user_tier=tier).inc()
    
    def record_orchestration_step(self, step_type: str) -> None:
        """Record an orchestration step."""
        if not self._enabled:
            return
        
        self.orchestration_steps_total.labels(step_type=step_type).inc()
    
    def record_safety_block(self, block_type: str) -> None:
        """Record a safety filter block."""
        if not self._enabled:
            return
        
        self.safety_blocks_total.labels(block_type=block_type).inc()
    
    def get_metrics(self) -> bytes:
        """Get Prometheus metrics output."""
        if not self._enabled:
            return b""
        
        return generate_latest(self._registry)
    
    def get_content_type(self) -> str:
        """Get Prometheus content type."""
        return CONTENT_TYPE_LATEST if PROMETHEUS_AVAILABLE else "text/plain"


# ==============================================================================
# Global Metrics Instance
# ==============================================================================

_metrics: Optional[MetricsManager] = None


def get_metrics() -> MetricsManager:
    """Get or create global metrics manager."""
    global _metrics
    if _metrics is None:
        _metrics = MetricsManager()
    return _metrics


# ==============================================================================
# Decorators and Context Managers
# ==============================================================================

@contextmanager
def track_request(method: str, endpoint: str):
    """Context manager for tracking HTTP requests."""
    metrics = get_metrics()
    
    if metrics.enabled:
        metrics.http_requests_in_progress.labels(
            method=method,
            endpoint=endpoint,
        ).inc()
    
    start = time.time()
    status_code = 200
    
    try:
        yield
    except Exception as e:
        status_code = 500
        metrics.record_error(type(e).__name__, endpoint)
        raise
    finally:
        duration = time.time() - start
        
        if metrics.enabled:
            metrics.http_requests_in_progress.labels(
                method=method,
                endpoint=endpoint,
            ).dec()
        
        metrics.record_request(method, endpoint, status_code, duration)


@contextmanager
def track_llm_call(provider: str, model: str):
    """Context manager for tracking LLM calls."""
    start = time.time()
    success = True
    tokens = 0
    
    try:
        result = yield
        if hasattr(result, 'tokens_used'):
            tokens = result.tokens_used
    except Exception:
        success = False
        raise
    finally:
        duration = time.time() - start
        get_metrics().record_llm_call(provider, model, duration, tokens, success)


@contextmanager
def track_tool_call(tool: str):
    """Context manager for tracking tool calls."""
    start = time.time()
    success = True
    
    try:
        yield
    except Exception:
        success = False
        raise
    finally:
        duration = time.time() - start
        get_metrics().record_tool_call(tool, duration, success)


def track_error(error_type: str, endpoint: str = "unknown") -> None:
    """Track an error."""
    get_metrics().record_error(error_type, endpoint)


# ==============================================================================
# FastAPI Integration
# ==============================================================================

def setup_metrics_endpoint(app):
    """Setup /metrics endpoint for Prometheus scraping."""
    from fastapi import Response
    
    @app.get("/metrics")
    async def metrics():
        metrics_manager = get_metrics()
        return Response(
            content=metrics_manager.get_metrics(),
            media_type=metrics_manager.get_content_type(),
        )
    
    logger.info("Metrics endpoint registered at /metrics")


def setup_fastapi_instrumentation(app):
    """Setup FastAPI instrumentation for automatic metrics."""
    try:
        from prometheus_fastapi_instrumentator import Instrumentator
        
        Instrumentator().instrument(app).expose(app)
        logger.info("FastAPI instrumentation enabled")
    except ImportError:
        logger.warning("prometheus_fastapi_instrumentator not available")

