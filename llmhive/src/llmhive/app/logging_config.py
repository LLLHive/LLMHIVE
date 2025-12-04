"""Structured logging configuration for LLMHive.

This module provides:
- JSON structured logging for production
- Human-readable format for development
- Request/response timing metrics
- Agent contribution tracking
- Correlation ID injection
"""
from __future__ import annotations

import json
import logging
import os
import sys
import time
from contextvars import ContextVar
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, TypeVar

# Context variables for request tracking
request_id_var: ContextVar[str] = ContextVar('request_id', default='')
user_id_var: ContextVar[str] = ContextVar('user_id', default='')
session_id_var: ContextVar[str] = ContextVar('session_id', default='')


# =============================================================================
# JSON Formatter
# =============================================================================

class JSONFormatter(logging.Formatter):
    """JSON log formatter for production environments.
    
    Produces structured JSON logs compatible with:
    - Google Cloud Logging
    - AWS CloudWatch
    - ELK Stack
    - Datadog
    """
    
    # Fields to exclude from extra data
    RESERVED_ATTRS = {
        'name', 'msg', 'args', 'created', 'filename', 'funcName',
        'levelname', 'levelno', 'lineno', 'module', 'msecs',
        'pathname', 'process', 'processName', 'relativeCreated',
        'stack_info', 'exc_info', 'exc_text', 'thread', 'threadName',
        'taskName', 'message',
    }
    
    def __init__(
        self,
        *,
        include_timestamp: bool = True,
        include_level: bool = True,
        include_logger: bool = True,
        include_location: bool = True,
    ):
        super().__init__()
        self.include_timestamp = include_timestamp
        self.include_level = include_level
        self.include_logger = include_logger
        self.include_location = include_location
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        # Base log entry
        log_entry: Dict[str, Any] = {}
        
        if self.include_timestamp:
            log_entry["timestamp"] = datetime.fromtimestamp(
                record.created, tz=timezone.utc
            ).isoformat()
        
        if self.include_level:
            log_entry["level"] = record.levelname
            log_entry["severity"] = record.levelname  # For GCP
        
        log_entry["message"] = record.getMessage()
        
        if self.include_logger:
            log_entry["logger"] = record.name
        
        if self.include_location:
            log_entry["location"] = {
                "file": record.filename,
                "line": record.lineno,
                "function": record.funcName,
            }
        
        # Add context variables
        from .errors import get_correlation_id
        correlation_id = get_correlation_id()
        if correlation_id:
            log_entry["correlation_id"] = correlation_id
        
        request_id = request_id_var.get()
        if request_id:
            log_entry["request_id"] = request_id
        
        user_id = user_id_var.get()
        if user_id:
            log_entry["user_id"] = user_id
        
        session_id = session_id_var.get()
        if session_id:
            log_entry["session_id"] = session_id
        
        # Add extra fields from record
        for key, value in record.__dict__.items():
            if key not in self.RESERVED_ATTRS and not key.startswith('_'):
                try:
                    # Ensure value is JSON serializable
                    json.dumps(value)
                    log_entry[key] = value
                except (TypeError, ValueError):
                    log_entry[key] = str(value)
        
        # Add exception info
        if record.exc_info:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": self.formatException(record.exc_info),
            }
        
        return json.dumps(log_entry)


class DevelopmentFormatter(logging.Formatter):
    """Human-readable formatter for development.
    
    Includes colors for different log levels.
    """
    
    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[32m',      # Green
        'WARNING': '\033[33m',   # Yellow
        'ERROR': '\033[31m',     # Red
        'CRITICAL': '\033[35m',  # Magenta
    }
    RESET = '\033[0m'
    
    def __init__(self, use_colors: bool = True):
        super().__init__()
        self.use_colors = use_colors and sys.stderr.isatty()
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record with optional colors."""
        # Get correlation ID
        from .errors import get_correlation_id
        correlation_id = get_correlation_id()
        
        # Build prefix
        level_color = self.COLORS.get(record.levelname, '') if self.use_colors else ''
        reset = self.RESET if self.use_colors else ''
        
        timestamp = datetime.fromtimestamp(record.created).strftime('%H:%M:%S.%f')[:-3]
        
        # Format: TIME [LEVEL] [correlation_id] logger - message
        prefix_parts = [
            f"{timestamp}",
            f"{level_color}{record.levelname:8s}{reset}",
        ]
        
        if correlation_id:
            prefix_parts.append(f"[{correlation_id}]")
        
        prefix_parts.append(f"{record.name}")
        
        prefix = " ".join(prefix_parts)
        message = record.getMessage()
        
        # Add extra fields
        extras = []
        for key, value in record.__dict__.items():
            if key not in JSONFormatter.RESERVED_ATTRS and not key.startswith('_'):
                extras.append(f"{key}={value}")
        
        if extras:
            message = f"{message} | {' '.join(extras)}"
        
        formatted = f"{prefix} - {message}"
        
        # Add exception info
        if record.exc_info:
            formatted += f"\n{self.formatException(record.exc_info)}"
        
        return formatted


# =============================================================================
# Logging Configuration
# =============================================================================

def configure_logging(
    *,
    level: str = "INFO",
    json_format: bool = False,
    include_location: bool = True,
) -> None:
    """Configure application logging.
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_format: Use JSON format (for production)
        include_location: Include file/line in logs
    """
    # Determine format from environment
    if json_format is None:
        json_format = os.environ.get("LOG_FORMAT", "").lower() == "json"
    
    # Determine level from environment
    env_level = os.environ.get("LOG_LEVEL", level).upper()
    
    # Create handler
    handler = logging.StreamHandler(sys.stdout)
    
    if json_format:
        handler.setFormatter(JSONFormatter(include_location=include_location))
    else:
        handler.setFormatter(DevelopmentFormatter())
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, env_level, logging.INFO))
    
    # Remove existing handlers
    for existing_handler in root_logger.handlers[:]:
        root_logger.removeHandler(existing_handler)
    
    root_logger.addHandler(handler)
    
    # Set levels for noisy loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)


# =============================================================================
# Timing Metrics
# =============================================================================

@dataclass
class TimingMetric:
    """Timing metric for a single operation."""
    name: str
    duration_ms: float
    start_time: float
    end_time: float
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RequestMetrics:
    """Metrics for a single request."""
    request_id: str
    correlation_id: str
    start_time: float
    end_time: Optional[float] = None
    total_duration_ms: Optional[float] = None
    stages: List[TimingMetric] = field(default_factory=list)
    models_used: List[str] = field(default_factory=list)
    agent_contributions: Dict[str, float] = field(default_factory=dict)
    token_count: int = 0
    success: bool = True
    error: Optional[str] = None
    
    def add_stage(self, name: str, duration_ms: float, **metadata) -> None:
        """Add a timing stage."""
        now = time.time()
        self.stages.append(TimingMetric(
            name=name,
            duration_ms=duration_ms,
            start_time=now - duration_ms / 1000,
            end_time=now,
            metadata=metadata,
        ))
    
    def add_model(self, model: str) -> None:
        """Add a model to the models used list."""
        if model not in self.models_used:
            self.models_used.append(model)
    
    def add_agent_contribution(self, agent: str, weight: float) -> None:
        """Add agent contribution weight."""
        self.agent_contributions[agent] = weight
    
    def finalize(self, success: bool = True, error: Optional[str] = None) -> None:
        """Finalize metrics at request end."""
        self.end_time = time.time()
        self.total_duration_ms = (self.end_time - self.start_time) * 1000
        self.success = success
        self.error = error
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging."""
        return {
            "request_id": self.request_id,
            "correlation_id": self.correlation_id,
            "total_duration_ms": self.total_duration_ms,
            "stages": [
                {
                    "name": s.name,
                    "duration_ms": s.duration_ms,
                    **s.metadata,
                }
                for s in self.stages
            ],
            "models_used": self.models_used,
            "agent_contributions": self.agent_contributions,
            "token_count": self.token_count,
            "success": self.success,
            "error": self.error,
        }
    
    def log_summary(self, logger: logging.Logger) -> None:
        """Log a summary of the request metrics."""
        if self.success:
            logger.info(
                "Request completed: %.0fms, models=%s, tokens=%d",
                self.total_duration_ms or 0,
                ",".join(self.models_used) or "none",
                self.token_count,
                extra=self.to_dict(),
            )
        else:
            logger.error(
                "Request failed after %.0fms: %s",
                self.total_duration_ms or 0,
                self.error,
                extra=self.to_dict(),
            )


# Context variable for current request metrics
_current_metrics: ContextVar[Optional[RequestMetrics]] = ContextVar(
    'current_metrics', default=None
)


def start_request_metrics(request_id: str, correlation_id: str) -> RequestMetrics:
    """Start tracking metrics for a request."""
    metrics = RequestMetrics(
        request_id=request_id,
        correlation_id=correlation_id,
        start_time=time.time(),
    )
    _current_metrics.set(metrics)
    return metrics


def get_current_metrics() -> Optional[RequestMetrics]:
    """Get current request metrics."""
    return _current_metrics.get()


def end_request_metrics(success: bool = True, error: Optional[str] = None) -> Optional[RequestMetrics]:
    """End and return request metrics."""
    metrics = _current_metrics.get()
    if metrics:
        metrics.finalize(success=success, error=error)
        _current_metrics.set(None)
    return metrics


# =============================================================================
# Decorators for Timing
# =============================================================================

F = TypeVar('F', bound=Callable[..., Any])


def timed(name: Optional[str] = None) -> Callable[[F], F]:
    """Decorator to time a function and log its duration.
    
    Usage:
        @timed("model_call")
        async def call_model():
            ...
    """
    def decorator(func: F) -> F:
        stage_name = name or func.__name__
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            logger = logging.getLogger(func.__module__)
            start = time.perf_counter()
            
            try:
                result = await func(*args, **kwargs)
                duration_ms = (time.perf_counter() - start) * 1000
                
                # Add to current request metrics if available
                metrics = get_current_metrics()
                if metrics:
                    metrics.add_stage(stage_name, duration_ms)
                
                logger.debug(
                    "%s completed in %.2fms",
                    stage_name,
                    duration_ms,
                    extra={"stage": stage_name, "duration_ms": duration_ms},
                )
                
                return result
                
            except Exception as e:
                duration_ms = (time.perf_counter() - start) * 1000
                logger.error(
                    "%s failed after %.2fms: %s",
                    stage_name,
                    duration_ms,
                    str(e),
                    extra={
                        "stage": stage_name,
                        "duration_ms": duration_ms,
                        "error": str(e),
                    },
                )
                raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            logger = logging.getLogger(func.__module__)
            start = time.perf_counter()
            
            try:
                result = func(*args, **kwargs)
                duration_ms = (time.perf_counter() - start) * 1000
                
                logger.debug(
                    "%s completed in %.2fms",
                    stage_name,
                    duration_ms,
                    extra={"stage": stage_name, "duration_ms": duration_ms},
                )
                
                return result
                
            except Exception as e:
                duration_ms = (time.perf_counter() - start) * 1000
                logger.error(
                    "%s failed after %.2fms: %s",
                    stage_name,
                    duration_ms,
                    str(e),
                    extra={
                        "stage": stage_name,
                        "duration_ms": duration_ms,
                        "error": str(e),
                    },
                )
                raise
        
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore
        else:
            return sync_wrapper  # type: ignore
    
    return decorator


# =============================================================================
# Agent Contribution Logger
# =============================================================================

class AgentContributionLogger:
    """Track and log agent contributions during orchestration."""
    
    def __init__(self, correlation_id: str):
        self.correlation_id = correlation_id
        self.contributions: Dict[str, Dict[str, Any]] = {}
        self.logger = logging.getLogger(__name__)
    
    def record_contribution(
        self,
        agent_name: str,
        *,
        model: str,
        task: str,
        duration_ms: float,
        tokens_used: int = 0,
        quality_score: Optional[float] = None,
        selected_for_final: bool = False,
    ) -> None:
        """Record an agent's contribution."""
        self.contributions[agent_name] = {
            "model": model,
            "task": task,
            "duration_ms": duration_ms,
            "tokens_used": tokens_used,
            "quality_score": quality_score,
            "selected_for_final": selected_for_final,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        
        self.logger.info(
            "Agent %s contributed: model=%s, task=%s, %.0fms, %d tokens",
            agent_name,
            model,
            task,
            duration_ms,
            tokens_used,
            extra={
                "correlation_id": self.correlation_id,
                "agent": agent_name,
                **self.contributions[agent_name],
            },
        )
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary of all agent contributions."""
        total_duration = sum(c["duration_ms"] for c in self.contributions.values())
        total_tokens = sum(c["tokens_used"] for c in self.contributions.values())
        
        return {
            "total_agents": len(self.contributions),
            "total_duration_ms": total_duration,
            "total_tokens": total_tokens,
            "agents": self.contributions,
            "selected_agents": [
                name for name, c in self.contributions.items()
                if c.get("selected_for_final")
            ],
        }
    
    def log_summary(self) -> None:
        """Log a summary of agent contributions."""
        summary = self.get_summary()
        self.logger.info(
            "Agent contributions summary: %d agents, %.0fms total, %d tokens",
            summary["total_agents"],
            summary["total_duration_ms"],
            summary["total_tokens"],
            extra={
                "correlation_id": self.correlation_id,
                **summary,
            },
        )
