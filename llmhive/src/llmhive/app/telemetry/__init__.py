"""OpenTelemetry Distributed Tracing for LLMHive.

This module provides production-grade distributed tracing using OpenTelemetry.
It enables end-to-end visibility into request flows across the orchestration pipeline.
"""
from __future__ import annotations

from .tracing import (
    init_tracing,
    get_tracer,
    trace_orchestration,
    trace_agent,
    trace_tool,
    trace_model_call,
    get_current_span,
    add_span_attributes,
    record_exception,
    TracingConfig,
)

__all__ = [
    "init_tracing",
    "get_tracer",
    "trace_orchestration",
    "trace_agent",
    "trace_tool",
    "trace_model_call",
    "get_current_span",
    "add_span_attributes",
    "record_exception",
    "TracingConfig",
]
