"""Structured Logging for LLMHive.

This module provides:
- JSON structured logging for production
- Request tracing with correlation IDs
- Sensitive data masking
- Audit logging
- Log levels based on environment

Usage:
    from llmhive.app.monitoring.logging_config import setup_logging, get_logger
    
    setup_logging(log_level="INFO", log_format="json")
    logger = get_logger(__name__)
    
    with RequestContext(request_id="abc123", user_id="user1"):
        logger.info("Processing request", extra={"action": "chat"})
"""
from __future__ import annotations

import json
import logging
import os
import re
import sys
import time
import uuid
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import datetime, timezone
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Set

# Structured logging support
try:
    import structlog
    STRUCTLOG_AVAILABLE = True
except ImportError:
    STRUCTLOG_AVAILABLE = False

try:
    from pythonjsonlogger import jsonlogger
    JSON_LOGGER_AVAILABLE = True
except ImportError:
    JSON_LOGGER_AVAILABLE = False


# ==============================================================================
# Context Variables for Request Tracing
# ==============================================================================

# Request context for correlation
_request_id: ContextVar[Optional[str]] = ContextVar("request_id", default=None)
_user_id: ContextVar[Optional[str]] = ContextVar("user_id", default=None)
_session_id: ContextVar[Optional[str]] = ContextVar("session_id", default=None)
_user_tier: ContextVar[Optional[str]] = ContextVar("user_tier", default=None)


class RequestContext:
    """Context manager for request tracing.
    
    Usage:
        with RequestContext(request_id="abc", user_id="user1"):
            logger.info("Processing...")  # Includes request_id, user_id
    """
    
    def __init__(
        self,
        request_id: Optional[str] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        user_tier: Optional[str] = None,
    ):
        self.request_id = request_id or str(uuid.uuid4())[:8]
        self.user_id = user_id
        self.session_id = session_id
        self.user_tier = user_tier
        
        self._tokens: List[Any] = []
    
    def __enter__(self):
        self._tokens.append(_request_id.set(self.request_id))
        if self.user_id:
            self._tokens.append(_user_id.set(self.user_id))
        if self.session_id:
            self._tokens.append(_session_id.set(self.session_id))
        if self.user_tier:
            self._tokens.append(_user_tier.set(self.user_tier))
        return self
    
    def __exit__(self, *args):
        for token in self._tokens:
            # Reset is handled automatically when context exits
            pass
    
    @staticmethod
    def get_context() -> Dict[str, Any]:
        """Get current context as dict."""
        ctx = {}
        if _request_id.get():
            ctx["request_id"] = _request_id.get()
        if _user_id.get():
            ctx["user_id"] = _user_id.get()
        if _session_id.get():
            ctx["session_id"] = _session_id.get()
        if _user_tier.get():
            ctx["user_tier"] = _user_tier.get()
        return ctx


def get_request_id() -> Optional[str]:
    """Get current request ID."""
    return _request_id.get()


def set_request_id(request_id: str) -> None:
    """Set current request ID."""
    _request_id.set(request_id)


# ==============================================================================
# Sensitive Data Masking
# ==============================================================================

# Patterns to mask
SENSITIVE_PATTERNS = [
    (re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'), "[EMAIL]"),
    (re.compile(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b'), "[PHONE]"),
    (re.compile(r'\b\d{3}[-]?\d{2}[-]?\d{4}\b'), "[SSN]"),
    (re.compile(r'\b\d{16}\b'), "[CARD_NUMBER]"),
    (re.compile(r'(api[_-]?key|apikey|secret|password|token|auth)["\']?\s*[:=]\s*["\']?[\w-]+', re.I), "[REDACTED_CREDENTIAL]"),
    (re.compile(r'sk-[a-zA-Z0-9]{32,}'), "[API_KEY]"),
    (re.compile(r'Bearer\s+[a-zA-Z0-9._-]+'), "Bearer [REDACTED]"),
]

# Fields to always mask
SENSITIVE_FIELDS = {
    "password", "secret", "token", "api_key", "apikey", "auth", "authorization",
    "credit_card", "card_number", "ssn", "social_security",
}


def mask_sensitive_data(data: Any, max_depth: int = 10) -> Any:
    """Mask sensitive data in logs.
    
    Args:
        data: Data to mask
        max_depth: Maximum recursion depth
        
    Returns:
        Masked data
    """
    if max_depth <= 0:
        return "[MAX_DEPTH]"
    
    if isinstance(data, str):
        result = data
        for pattern, replacement in SENSITIVE_PATTERNS:
            result = pattern.sub(replacement, result)
        return result
    
    elif isinstance(data, dict):
        return {
            k: "[REDACTED]" if k.lower() in SENSITIVE_FIELDS 
            else mask_sensitive_data(v, max_depth - 1)
            for k, v in data.items()
        }
    
    elif isinstance(data, (list, tuple)):
        return [mask_sensitive_data(item, max_depth - 1) for item in data]
    
    return data


# ==============================================================================
# Custom JSON Formatter
# ==============================================================================

class LLMHiveJsonFormatter(logging.Formatter):
    """JSON formatter with request context and masking."""
    
    def __init__(
        self,
        *args,
        mask_sensitive: bool = True,
        include_context: bool = True,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.mask_sensitive = mask_sensitive
        self.include_context = include_context
    
    def format(self, record: logging.LogRecord) -> str:
        log_record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add request context
        if self.include_context:
            ctx = RequestContext.get_context()
            if ctx:
                log_record["context"] = ctx
        
        # Add exception info
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields
        if hasattr(record, '__dict__'):
            extras = {
                k: v for k, v in record.__dict__.items()
                if k not in {
                    'name', 'msg', 'args', 'created', 'filename', 'funcName',
                    'levelname', 'levelno', 'lineno', 'module', 'msecs',
                    'pathname', 'process', 'processName', 'relativeCreated',
                    'stack_info', 'exc_info', 'exc_text', 'thread', 'threadName',
                    'message', 'taskName',
                }
            }
            if extras:
                log_record["extra"] = extras
        
        # Mask sensitive data
        if self.mask_sensitive:
            log_record = mask_sensitive_data(log_record)
        
        return json.dumps(log_record, default=str)


class LLMHiveTextFormatter(logging.Formatter):
    """Human-readable formatter for development."""
    
    def format(self, record: logging.LogRecord) -> str:
        # Get context
        ctx = RequestContext.get_context()
        ctx_str = f"[{ctx.get('request_id', 'no-req')}]" if ctx else ""
        
        # Format message
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        level = record.levelname.ljust(8)
        
        msg = f"{timestamp} {level} {ctx_str} {record.name}: {record.getMessage()}"
        
        if record.exc_info:
            msg += f"\n{self.formatException(record.exc_info)}"
        
        return msg


# ==============================================================================
# Logging Setup
# ==============================================================================

def setup_logging(
    log_level: str = "INFO",
    log_format: str = "auto",
    mask_sensitive: bool = True,
    log_file: Optional[str] = None,
) -> None:
    """Setup structured logging.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_format: Format type (json, text, auto)
        mask_sensitive: Mask sensitive data in logs
        log_file: Optional file path for logging
    """
    level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Determine format
    if log_format == "auto":
        log_format = os.getenv("LOG_FORMAT", "text")
        if os.getenv("ENVIRONMENT", "development") == "production":
            log_format = "json"
    
    # Create handler
    handler = logging.StreamHandler(sys.stdout)
    
    if log_format == "json":
        formatter = LLMHiveJsonFormatter(mask_sensitive=mask_sensitive)
    else:
        formatter = LLMHiveTextFormatter()
    
    handler.setFormatter(formatter)
    
    # Configure root logger
    root = logging.getLogger()
    root.setLevel(level)
    root.handlers = [handler]
    
    # Add file handler if specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(LLMHiveJsonFormatter(mask_sensitive=mask_sensitive))
        root.addHandler(file_handler)
    
    # Set levels for noisy loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    
    logging.info(
        "Logging configured",
        extra={"level": log_level, "format": log_format},
    )


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the given name."""
    return logging.getLogger(name)


# ==============================================================================
# Audit Logging
# ==============================================================================

class AuditLogger:
    """Logger for security and compliance auditing.
    
    Records:
    - Authentication events
    - Authorization decisions
    - Data access
    - Configuration changes
    - Safety filter triggers
    """
    
    def __init__(self, log_file: Optional[str] = None):
        self.logger = logging.getLogger("llmhive.audit")
        self.logger.setLevel(logging.INFO)
        
        # Always use JSON for audit logs
        if log_file:
            handler = logging.FileHandler(log_file)
            handler.setFormatter(LLMHiveJsonFormatter(mask_sensitive=False))
            self.logger.addHandler(handler)
    
    def log_auth(
        self,
        event: str,
        user_id: Optional[str],
        success: bool,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log authentication event."""
        self.logger.info(
            f"AUTH: {event}",
            extra={
                "audit_type": "authentication",
                "event": event,
                "user_id": user_id,
                "success": success,
                "details": details or {},
            },
        )
    
    def log_access(
        self,
        resource: str,
        action: str,
        user_id: Optional[str],
        granted: bool,
        reason: Optional[str] = None,
    ) -> None:
        """Log access control decision."""
        self.logger.info(
            f"ACCESS: {action} on {resource}",
            extra={
                "audit_type": "access_control",
                "resource": resource,
                "action": action,
                "user_id": user_id,
                "granted": granted,
                "reason": reason,
            },
        )
    
    def log_data_operation(
        self,
        operation: str,
        data_type: str,
        user_id: Optional[str],
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log data operation."""
        self.logger.info(
            f"DATA: {operation} on {data_type}",
            extra={
                "audit_type": "data_operation",
                "operation": operation,
                "data_type": data_type,
                "user_id": user_id,
                "details": details or {},
            },
        )
    
    def log_safety(
        self,
        trigger: str,
        content_type: str,
        action_taken: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log safety filter trigger."""
        self.logger.warning(
            f"SAFETY: {trigger}",
            extra={
                "audit_type": "safety",
                "trigger": trigger,
                "content_type": content_type,
                "action_taken": action_taken,
                "details": details or {},
            },
        )


# Global audit logger
_audit_logger: Optional[AuditLogger] = None


def get_audit_logger() -> AuditLogger:
    """Get global audit logger."""
    global _audit_logger
    if _audit_logger is None:
        audit_file = os.getenv("LLMHIVE_AUDIT_LOG")
        _audit_logger = AuditLogger(log_file=audit_file)
    return _audit_logger


# ==============================================================================
# Request Logging Decorator
# ==============================================================================

def log_request(func: Callable) -> Callable:
    """Decorator to log request start/end."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        request_id = str(uuid.uuid4())[:8]
        start_time = time.time()
        
        logger = get_logger(func.__module__)
        
        with RequestContext(request_id=request_id):
            logger.info(
                f"Request started: {func.__name__}",
                extra={"function": func.__name__},
            )
            
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                
                logger.info(
                    f"Request completed: {func.__name__}",
                    extra={
                        "function": func.__name__,
                        "duration_ms": round(duration * 1000, 2),
                        "success": True,
                    },
                )
                
                return result
                
            except Exception as e:
                duration = time.time() - start_time
                
                logger.error(
                    f"Request failed: {func.__name__}",
                    extra={
                        "function": func.__name__,
                        "duration_ms": round(duration * 1000, 2),
                        "error": str(e),
                        "error_type": type(e).__name__,
                    },
                    exc_info=True,
                )
                raise
    
    return wrapper

