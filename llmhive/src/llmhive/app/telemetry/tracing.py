"""OpenTelemetry Tracing Implementation for LLMHive.

Provides distributed tracing capabilities for:
- Orchestration requests
- Agent invocations
- Tool executions
- Model API calls
- Memory operations
"""
from __future__ import annotations

import functools
import logging
import os
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Generator, Optional, TypeVar, Union

logger = logging.getLogger(__name__)

# Type variables for generic decorators
F = TypeVar("F", bound=Callable[..., Any])

# Try to import OpenTelemetry - gracefully degrade if not available
try:
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
    from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION
    from opentelemetry.trace import Status, StatusCode, Span, SpanKind
    from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
    from opentelemetry.context import Context
    
    # OTLP exporter (optional, requires opentelemetry-exporter-otlp)
    try:
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        OTLP_AVAILABLE = True
    except ImportError:
        OTLPSpanExporter = None
        OTLP_AVAILABLE = False
    
    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False
    trace = None
    TracerProvider = None
    Resource = None
    Span = None
    SpanKind = None
    logger.warning(
        "OpenTelemetry not available. Install with: pip install opentelemetry-api opentelemetry-sdk"
    )


@dataclass
class TracingConfig:
    """Configuration for OpenTelemetry tracing."""
    
    service_name: str = "llmhive-orchestrator"
    service_version: str = "1.0.0"
    environment: str = field(default_factory=lambda: os.getenv("ENVIRONMENT", "development"))
    
    # Exporter configuration
    otlp_endpoint: Optional[str] = field(default_factory=lambda: os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT"))
    use_console_exporter: bool = field(default_factory=lambda: os.getenv("OTEL_CONSOLE_EXPORT", "false").lower() == "true")
    
    # Sampling configuration
    sample_rate: float = field(default_factory=lambda: float(os.getenv("OTEL_SAMPLE_RATE", "1.0")))
    
    # Feature flags
    trace_orchestration: bool = True
    trace_agents: bool = True
    trace_tools: bool = True
    trace_model_calls: bool = True
    trace_memory: bool = True
    
    # Attribute limits
    max_attribute_length: int = 1024
    max_events: int = 128


# Global tracer instance
_tracer: Optional[Any] = None
_config: Optional[TracingConfig] = None
_initialized: bool = False


def init_tracing(config: Optional[TracingConfig] = None) -> bool:
    """Initialize OpenTelemetry tracing.
    
    Args:
        config: Tracing configuration. Uses defaults if not provided.
        
    Returns:
        True if tracing was initialized successfully, False otherwise.
    """
    global _tracer, _config, _initialized
    
    if not OTEL_AVAILABLE:
        logger.warning("OpenTelemetry not available, tracing disabled")
        return False
    
    if _initialized:
        logger.debug("Tracing already initialized")
        return True
    
    _config = config or TracingConfig()
    
    try:
        # Create resource with service info
        resource = Resource.create({
            SERVICE_NAME: _config.service_name,
            SERVICE_VERSION: _config.service_version,
            "deployment.environment": _config.environment,
        })
        
        # Create tracer provider
        provider = TracerProvider(resource=resource)
        
        # Add exporters based on config
        if _config.otlp_endpoint and OTLP_AVAILABLE:
            otlp_exporter = OTLPSpanExporter(endpoint=_config.otlp_endpoint)
            provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
            logger.info(f"OTLP exporter configured: {_config.otlp_endpoint}")
        
        if _config.use_console_exporter:
            console_exporter = ConsoleSpanExporter()
            provider.add_span_processor(BatchSpanProcessor(console_exporter))
            logger.info("Console exporter enabled")
        
        # If no exporters configured, add console for development
        if not _config.otlp_endpoint and not _config.use_console_exporter:
            if _config.environment == "development":
                console_exporter = ConsoleSpanExporter()
                provider.add_span_processor(BatchSpanProcessor(console_exporter))
                logger.info("Development mode: console exporter enabled")
        
        # Set global tracer provider
        trace.set_tracer_provider(provider)
        
        # Get tracer
        _tracer = trace.get_tracer(
            _config.service_name,
            _config.service_version,
        )
        
        _initialized = True
        logger.info(f"OpenTelemetry tracing initialized for {_config.service_name}")
        return True
        
    except Exception as e:
        logger.exception(f"Failed to initialize tracing: {e}")
        return False


def get_tracer() -> Optional[Any]:
    """Get the global tracer instance.
    
    Returns:
        The tracer instance, or None if not initialized.
    """
    if not _initialized:
        init_tracing()
    return _tracer


def get_current_span() -> Optional[Any]:
    """Get the current active span.
    
    Returns:
        The current span, or None if no span is active or tracing is disabled.
    """
    if not OTEL_AVAILABLE or not _initialized:
        return None
    return trace.get_current_span()


def add_span_attributes(attributes: Dict[str, Any]) -> None:
    """Add attributes to the current span.
    
    Args:
        attributes: Dictionary of attribute name-value pairs.
    """
    span = get_current_span()
    if span and hasattr(span, 'set_attributes'):
        # Filter and truncate attribute values
        filtered = {}
        for key, value in attributes.items():
            if value is not None:
                if isinstance(value, str) and _config:
                    value = value[:_config.max_attribute_length]
                filtered[key] = value
        span.set_attributes(filtered)


def record_exception(exception: Exception, attributes: Optional[Dict[str, Any]] = None) -> None:
    """Record an exception in the current span.
    
    Args:
        exception: The exception to record.
        attributes: Additional attributes to add to the event.
    """
    span = get_current_span()
    if span and hasattr(span, 'record_exception'):
        span.record_exception(exception, attributes=attributes)
        span.set_status(Status(StatusCode.ERROR, str(exception)))


@contextmanager
def _create_span(
    name: str,
    kind: Optional[Any] = None,
    attributes: Optional[Dict[str, Any]] = None,
) -> Generator[Optional[Any], None, None]:
    """Create a new span as a context manager.
    
    Args:
        name: Span name.
        kind: Span kind (INTERNAL, SERVER, CLIENT, etc.)
        attributes: Initial span attributes.
        
    Yields:
        The created span, or None if tracing is disabled.
    """
    tracer = get_tracer()
    if not tracer:
        yield None
        return
    
    span_kind = kind or (SpanKind.INTERNAL if OTEL_AVAILABLE else None)
    
    with tracer.start_as_current_span(
        name,
        kind=span_kind,
        attributes=attributes or {},
    ) as span:
        try:
            yield span
        except Exception as e:
            if span:
                record_exception(e)
            raise


@contextmanager
def trace_orchestration(
    prompt: str,
    reasoning_mode: str = "standard",
    domain_pack: str = "default",
    agent_mode: str = "team",
    accuracy_level: int = 3,
    models: Optional[list] = None,
) -> Generator[Optional[Any], None, None]:
    """Create a span for orchestration requests.
    
    Args:
        prompt: The user's prompt (truncated for safety).
        reasoning_mode: Reasoning mode being used.
        domain_pack: Domain pack selected.
        agent_mode: Agent mode (single/team).
        accuracy_level: Accuracy level (1-5).
        models: List of models being used.
        
    Yields:
        The orchestration span.
    """
    if not _config or not _config.trace_orchestration:
        yield None
        return
    
    attributes = {
        "llmhive.orchestration.prompt_length": len(prompt),
        "llmhive.orchestration.prompt_preview": prompt[:100] if prompt else "",
        "llmhive.orchestration.reasoning_mode": reasoning_mode,
        "llmhive.orchestration.domain_pack": domain_pack,
        "llmhive.orchestration.agent_mode": agent_mode,
        "llmhive.orchestration.accuracy_level": accuracy_level,
        "llmhive.orchestration.model_count": len(models) if models else 0,
    }
    
    if models:
        attributes["llmhive.orchestration.models"] = ",".join(models[:5])
    
    with _create_span("orchestration.run", SpanKind.SERVER if OTEL_AVAILABLE else None, attributes) as span:
        yield span


@contextmanager
def trace_agent(
    agent_type: str,
    task_type: str,
    agent_id: Optional[str] = None,
) -> Generator[Optional[Any], None, None]:
    """Create a span for agent invocations.
    
    Args:
        agent_type: Type of agent (qa, code, research, etc.).
        task_type: Type of task being performed.
        agent_id: Unique agent instance ID.
        
    Yields:
        The agent span.
    """
    if not _config or not _config.trace_agents:
        yield None
        return
    
    attributes = {
        "llmhive.agent.type": agent_type,
        "llmhive.agent.task_type": task_type,
    }
    if agent_id:
        attributes["llmhive.agent.id"] = agent_id
    
    with _create_span(f"agent.{agent_type}.{task_type}", attributes=attributes) as span:
        yield span


@contextmanager
def trace_tool(
    tool_name: str,
    tool_type: str,
    input_preview: Optional[str] = None,
) -> Generator[Optional[Any], None, None]:
    """Create a span for tool executions.
    
    Args:
        tool_name: Name of the tool being executed.
        tool_type: Type of tool (calculator, web_search, code_exec, etc.).
        input_preview: Preview of tool input (truncated).
        
    Yields:
        The tool span.
    """
    if not _config or not _config.trace_tools:
        yield None
        return
    
    attributes = {
        "llmhive.tool.name": tool_name,
        "llmhive.tool.type": tool_type,
    }
    if input_preview:
        attributes["llmhive.tool.input_preview"] = input_preview[:200]
    
    with _create_span(f"tool.{tool_type}.{tool_name}", SpanKind.CLIENT if OTEL_AVAILABLE else None, attributes) as span:
        yield span


@contextmanager
def trace_model_call(
    model: str,
    provider: str,
    prompt_tokens: Optional[int] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
) -> Generator[Optional[Any], None, None]:
    """Create a span for model API calls.
    
    Args:
        model: Model identifier.
        provider: Provider name (openai, anthropic, google, etc.).
        prompt_tokens: Estimated prompt tokens.
        temperature: Temperature setting.
        max_tokens: Max tokens setting.
        
    Yields:
        The model call span.
    """
    if not _config or not _config.trace_model_calls:
        yield None
        return
    
    attributes = {
        "llmhive.model.name": model,
        "llmhive.model.provider": provider,
    }
    if prompt_tokens is not None:
        attributes["llmhive.model.prompt_tokens"] = prompt_tokens
    if temperature is not None:
        attributes["llmhive.model.temperature"] = temperature
    if max_tokens is not None:
        attributes["llmhive.model.max_tokens"] = max_tokens
    
    with _create_span(f"model.{provider}.{model}", SpanKind.CLIENT if OTEL_AVAILABLE else None, attributes) as span:
        yield span


def traced(
    span_name: Optional[str] = None,
    attributes: Optional[Dict[str, Any]] = None,
) -> Callable[[F], F]:
    """Decorator to trace a function.
    
    Args:
        span_name: Custom span name. Defaults to function name.
        attributes: Static attributes to add to the span.
        
    Returns:
        Decorated function.
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            name = span_name or f"func.{func.__module__}.{func.__name__}"
            with _create_span(name, attributes=attributes):
                return func(*args, **kwargs)
        
        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            name = span_name or f"func.{func.__module__}.{func.__name__}"
            with _create_span(name, attributes=attributes):
                return await func(*args, **kwargs)
        
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore
        return wrapper  # type: ignore
    
    return decorator


# Export propagator for distributed tracing across services
def get_trace_context() -> Dict[str, str]:
    """Get trace context for propagation to other services.
    
    Returns:
        Dictionary with trace context headers.
    """
    if not OTEL_AVAILABLE or not _initialized:
        return {}
    
    carrier: Dict[str, str] = {}
    propagator = TraceContextTextMapPropagator()
    propagator.inject(carrier)
    return carrier


def inject_trace_context(headers: Dict[str, str]) -> Dict[str, str]:
    """Inject trace context into headers for outgoing requests.
    
    Args:
        headers: Headers dictionary to update.
        
    Returns:
        Updated headers with trace context.
    """
    context = get_trace_context()
    headers.update(context)
    return headers
