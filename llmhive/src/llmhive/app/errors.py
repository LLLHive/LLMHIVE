"""Comprehensive error handling for LLMHive.

This module provides:
- Custom exception hierarchy
- Circuit breaker pattern for provider failures
- Correlation ID tracking
- Consistent error response format
- Error codes for frontend handling
"""
from __future__ import annotations

import asyncio
import logging
import time
import uuid
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union

logger = logging.getLogger(__name__)

# Context variable for correlation ID (thread-safe)
correlation_id_var: ContextVar[str] = ContextVar('correlation_id', default='')


# =============================================================================
# Error Codes
# =============================================================================

class ErrorCode(str, Enum):
    """Error codes for frontend handling."""
    # General errors (1xxx)
    INTERNAL_ERROR = "E1000"
    VALIDATION_ERROR = "E1001"
    NOT_FOUND = "E1002"
    UNAUTHORIZED = "E1003"
    FORBIDDEN = "E1004"
    RATE_LIMITED = "E1005"
    TIMEOUT = "E1006"
    
    # Provider errors (2xxx)
    PROVIDER_UNAVAILABLE = "E2000"
    PROVIDER_TIMEOUT = "E2001"
    PROVIDER_RATE_LIMITED = "E2002"
    PROVIDER_AUTH_FAILED = "E2003"
    PROVIDER_ERROR = "E2004"
    ALL_PROVIDERS_FAILED = "E2005"
    MODEL_NOT_FOUND = "E2006"
    
    # Orchestration errors (3xxx)
    ORCHESTRATION_FAILED = "E3000"
    PLANNING_FAILED = "E3001"
    CONSENSUS_FAILED = "E3002"
    TOOL_EXECUTION_FAILED = "E3003"
    MEMORY_ERROR = "E3004"
    CONTEXT_TOO_LONG = "E3005"
    
    # Circuit breaker errors (4xxx)
    CIRCUIT_OPEN = "E4000"
    CIRCUIT_HALF_OPEN = "E4001"
    
    # User errors (5xxx)
    INVALID_REQUEST = "E5000"
    CONTENT_POLICY_VIOLATION = "E5001"
    TIER_LIMIT_EXCEEDED = "E5002"
    QUOTA_EXCEEDED = "E5003"


# =============================================================================
# Custom Exceptions
# =============================================================================

class LLMHiveError(Exception):
    """Base exception for LLMHive errors."""
    
    def __init__(
        self,
        message: str,
        code: ErrorCode = ErrorCode.INTERNAL_ERROR,
        *,
        details: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        recoverable: bool = True,
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}
        self.correlation_id = correlation_id or get_correlation_id()
        self.provider = provider
        self.model = model
        self.recoverable = recoverable
        self.timestamp = datetime.now(timezone.utc)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for JSON response."""
        return {
            "error": {
                "code": self.code.value,
                "message": self.message,
                "details": self.details,
                "recoverable": self.recoverable,
            },
            "correlation_id": self.correlation_id,
            "timestamp": self.timestamp.isoformat(),
        }
    
    def __str__(self) -> str:
        return f"[{self.code.value}] {self.message} (correlation_id={self.correlation_id})"


class ProviderError(LLMHiveError):
    """Error from an LLM provider."""
    
    def __init__(
        self,
        message: str,
        provider: str,
        *,
        model: Optional[str] = None,
        code: ErrorCode = ErrorCode.PROVIDER_ERROR,
        original_error: Optional[Exception] = None,
        **kwargs,
    ):
        super().__init__(
            message,
            code=code,
            provider=provider,
            model=model,
            **kwargs,
        )
        self.original_error = original_error


class ProviderTimeoutError(ProviderError):
    """Provider request timed out."""
    
    def __init__(self, provider: str, timeout: float, **kwargs):
        super().__init__(
            f"Provider {provider} timed out after {timeout:.1f}s",
            provider=provider,
            code=ErrorCode.PROVIDER_TIMEOUT,
            details={"timeout_seconds": timeout},
            **kwargs,
        )


class ProviderRateLimitError(ProviderError):
    """Provider rate limit exceeded."""
    
    def __init__(
        self,
        provider: str,
        *,
        retry_after: Optional[float] = None,
        **kwargs,
    ):
        super().__init__(
            f"Rate limit exceeded for provider {provider}",
            provider=provider,
            code=ErrorCode.PROVIDER_RATE_LIMITED,
            details={"retry_after_seconds": retry_after},
            **kwargs,
        )
        self.retry_after = retry_after


class AllProvidersFailedError(LLMHiveError):
    """All available providers failed."""
    
    def __init__(
        self,
        providers: List[str],
        errors: List[Exception],
        **kwargs,
    ):
        error_summary = ", ".join(
            f"{p}: {type(e).__name__}" 
            for p, e in zip(providers, errors)
        )
        super().__init__(
            f"All {len(providers)} provider(s) failed: {error_summary}",
            code=ErrorCode.ALL_PROVIDERS_FAILED,
            recoverable=False,
            **kwargs,
        )
        self.provider_errors = dict(zip(providers, errors))


class CircuitOpenError(LLMHiveError):
    """Circuit breaker is open for a provider."""
    
    def __init__(
        self,
        provider: str,
        *,
        reset_time: Optional[float] = None,
        **kwargs,
    ):
        super().__init__(
            f"Circuit breaker open for provider {provider}",
            code=ErrorCode.CIRCUIT_OPEN,
            provider=provider,
            details={"reset_after_seconds": reset_time},
            recoverable=True,
            **kwargs,
        )
        self.reset_time = reset_time


class OrchestrationError(LLMHiveError):
    """Error during orchestration."""
    
    def __init__(
        self,
        message: str,
        *,
        stage: Optional[str] = None,
        code: ErrorCode = ErrorCode.ORCHESTRATION_FAILED,
        **kwargs,
    ):
        super().__init__(message, code=code, **kwargs)
        self.stage = stage
        if stage:
            self.details["stage"] = stage


class ValidationError(LLMHiveError):
    """Input validation error."""
    
    def __init__(self, message: str, field: Optional[str] = None, **kwargs):
        super().__init__(
            message,
            code=ErrorCode.VALIDATION_ERROR,
            details={"field": field} if field else {},
            **kwargs,
        )


class ContentPolicyError(LLMHiveError):
    """Content policy violation."""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            code=ErrorCode.CONTENT_POLICY_VIOLATION,
            recoverable=False,
            **kwargs,
        )


# =============================================================================
# Correlation ID Management
# =============================================================================

def generate_correlation_id() -> str:
    """Generate a new correlation ID."""
    return str(uuid.uuid4())[:8]


def get_correlation_id() -> str:
    """Get the current correlation ID or generate a new one."""
    cid = correlation_id_var.get()
    if not cid:
        cid = generate_correlation_id()
        correlation_id_var.set(cid)
    return cid


def set_correlation_id(correlation_id: str) -> None:
    """Set the correlation ID for the current context."""
    correlation_id_var.set(correlation_id)


# =============================================================================
# Circuit Breaker
# =============================================================================

class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if recovered


@dataclass
class CircuitStats:
    """Statistics for a circuit breaker."""
    failures: int = 0
    successes: int = 0
    last_failure_time: Optional[float] = None
    last_success_time: Optional[float] = None
    state: CircuitState = CircuitState.CLOSED
    state_changed_at: float = field(default_factory=time.time)


class CircuitBreaker:
    """Circuit breaker for provider resilience.
    
    Implements the circuit breaker pattern:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Too many failures, requests are rejected immediately
    - HALF_OPEN: Testing recovery, allows limited requests
    
    Usage:
        breaker = CircuitBreaker(failure_threshold=5, reset_timeout=60)
        
        async with breaker.call("openai"):
            response = await provider.generate(...)
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        reset_timeout: float = 60.0,
        half_open_max_calls: int = 3,
    ):
        """Initialize circuit breaker.
        
        Args:
            failure_threshold: Number of failures before opening circuit
            reset_timeout: Seconds before attempting recovery
            half_open_max_calls: Max calls allowed in half-open state
        """
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.half_open_max_calls = half_open_max_calls
        self._circuits: Dict[str, CircuitStats] = {}
        self._half_open_calls: Dict[str, int] = {}
        self._lock = asyncio.Lock()
    
    def _get_circuit(self, name: str) -> CircuitStats:
        """Get or create circuit stats for a provider."""
        if name not in self._circuits:
            self._circuits[name] = CircuitStats()
        return self._circuits[name]
    
    async def _check_state(self, name: str) -> CircuitState:
        """Check and potentially update circuit state."""
        async with self._lock:
            circuit = self._get_circuit(name)
            current_time = time.time()
            
            if circuit.state == CircuitState.OPEN:
                # Check if reset timeout has passed
                if current_time - circuit.state_changed_at >= self.reset_timeout:
                    circuit.state = CircuitState.HALF_OPEN
                    circuit.state_changed_at = current_time
                    self._half_open_calls[name] = 0
                    logger.info(
                        "Circuit breaker for %s transitioning to HALF_OPEN",
                        name,
                        extra={"correlation_id": get_correlation_id()},
                    )
            
            return circuit.state
    
    async def record_success(self, name: str) -> None:
        """Record a successful call."""
        async with self._lock:
            circuit = self._get_circuit(name)
            circuit.successes += 1
            circuit.last_success_time = time.time()
            
            if circuit.state == CircuitState.HALF_OPEN:
                self._half_open_calls[name] = self._half_open_calls.get(name, 0) + 1
                if self._half_open_calls[name] >= self.half_open_max_calls:
                    # Recovered - close circuit
                    circuit.state = CircuitState.CLOSED
                    circuit.failures = 0
                    circuit.state_changed_at = time.time()
                    logger.info(
                        "Circuit breaker for %s recovered, state: CLOSED",
                        name,
                        extra={"correlation_id": get_correlation_id()},
                    )
    
    async def record_failure(self, name: str, error: Exception) -> None:
        """Record a failed call."""
        async with self._lock:
            circuit = self._get_circuit(name)
            circuit.failures += 1
            circuit.last_failure_time = time.time()
            
            if circuit.state == CircuitState.HALF_OPEN:
                # Failed during recovery - reopen circuit
                circuit.state = CircuitState.OPEN
                circuit.state_changed_at = time.time()
                logger.warning(
                    "Circuit breaker for %s reopened after failure in HALF_OPEN",
                    name,
                    extra={"correlation_id": get_correlation_id()},
                )
            elif circuit.state == CircuitState.CLOSED:
                if circuit.failures >= self.failure_threshold:
                    circuit.state = CircuitState.OPEN
                    circuit.state_changed_at = time.time()
                    logger.warning(
                        "Circuit breaker for %s opened after %d failures",
                        name,
                        circuit.failures,
                        extra={"correlation_id": get_correlation_id()},
                    )
    
    def is_open(self, name: str) -> bool:
        """Check if circuit is open for a provider."""
        circuit = self._get_circuit(name)
        return circuit.state == CircuitState.OPEN
    
    def get_stats(self, name: str) -> Dict[str, Any]:
        """Get circuit breaker stats for a provider."""
        circuit = self._get_circuit(name)
        return {
            "state": circuit.state.value,
            "failures": circuit.failures,
            "successes": circuit.successes,
            "last_failure": circuit.last_failure_time,
            "last_success": circuit.last_success_time,
        }
    
    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get stats for all circuits."""
        return {name: self.get_stats(name) for name in self._circuits}


# Global circuit breaker instance
_circuit_breaker: Optional[CircuitBreaker] = None


def get_circuit_breaker() -> CircuitBreaker:
    """Get the global circuit breaker instance."""
    global _circuit_breaker
    if _circuit_breaker is None:
        _circuit_breaker = CircuitBreaker()
    return _circuit_breaker


# =============================================================================
# Error Response Builder
# =============================================================================

@dataclass
class ErrorResponse:
    """Standardized error response format."""
    code: str
    message: str
    correlation_id: str
    timestamp: str
    details: Dict[str, Any] = field(default_factory=dict)
    recoverable: bool = True
    request_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON response."""
        return {
            "error": {
                "code": self.code,
                "message": self.message,
                "details": self.details,
                "recoverable": self.recoverable,
            },
            "correlation_id": self.correlation_id,
            "request_id": self.request_id,
            "timestamp": self.timestamp,
        }


def build_error_response(
    error: Union[LLMHiveError, Exception],
    *,
    request_id: Optional[str] = None,
) -> ErrorResponse:
    """Build a standardized error response from an exception."""
    correlation_id = get_correlation_id()
    timestamp = datetime.now(timezone.utc).isoformat()
    
    if isinstance(error, LLMHiveError):
        return ErrorResponse(
            code=error.code.value,
            message=error.message,
            correlation_id=error.correlation_id or correlation_id,
            timestamp=timestamp,
            details=error.details,
            recoverable=error.recoverable,
            request_id=request_id,
        )
    else:
        # Generic exception
        return ErrorResponse(
            code=ErrorCode.INTERNAL_ERROR.value,
            message=str(error) or "An unexpected error occurred",
            correlation_id=correlation_id,
            timestamp=timestamp,
            details={"exception_type": type(error).__name__},
            recoverable=True,
            request_id=request_id,
        )


# =============================================================================
# Decorators for Error Handling
# =============================================================================

F = TypeVar('F', bound=Callable[..., Any])


def with_error_handling(func: F) -> F:
    """Decorator to add error handling to async functions.
    
    Wraps exceptions in LLMHiveError and logs them with correlation ID.
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        correlation_id = get_correlation_id()
        start_time = time.perf_counter()
        
        try:
            result = await func(*args, **kwargs)
            duration = time.perf_counter() - start_time
            logger.debug(
                "Function %s completed in %.3fs",
                func.__name__,
                duration,
                extra={"correlation_id": correlation_id, "duration_ms": duration * 1000},
            )
            return result
        except LLMHiveError:
            # Re-raise LLMHive errors as-is
            raise
        except Exception as e:
            duration = time.perf_counter() - start_time
            logger.error(
                "Function %s failed after %.3fs: %s",
                func.__name__,
                duration,
                str(e),
                extra={
                    "correlation_id": correlation_id,
                    "duration_ms": duration * 1000,
                    "exception_type": type(e).__name__,
                },
                exc_info=True,
            )
            raise LLMHiveError(
                f"Unexpected error in {func.__name__}: {str(e)}",
                code=ErrorCode.INTERNAL_ERROR,
                correlation_id=correlation_id,
                details={"exception_type": type(e).__name__},
            ) from e
    
    return wrapper  # type: ignore


def with_circuit_breaker(provider_name: str) -> Callable[[F], F]:
    """Decorator to apply circuit breaker to provider calls.
    
    Usage:
        @with_circuit_breaker("openai")
        async def call_openai(prompt):
            ...
    """
    def decorator(func: F) -> F:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            breaker = get_circuit_breaker()
            state = await breaker._check_state(provider_name)
            
            if state == CircuitState.OPEN:
                reset_time = breaker.reset_timeout - (
                    time.time() - breaker._get_circuit(provider_name).state_changed_at
                )
                raise CircuitOpenError(
                    provider_name,
                    reset_time=max(0, reset_time),
                )
            
            try:
                result = await func(*args, **kwargs)
                await breaker.record_success(provider_name)
                return result
            except Exception as e:
                await breaker.record_failure(provider_name, e)
                raise
        
        return wrapper  # type: ignore
    
    return decorator


# =============================================================================
# Provider Call Wrapper with Fallback
# =============================================================================

async def call_with_fallback(
    providers: Dict[str, Any],
    method: str,
    *args,
    preferred_providers: Optional[List[str]] = None,
    **kwargs,
) -> Any:
    """Call a provider method with fallback to other providers.
    
    Args:
        providers: Dict of provider_name -> provider instance
        method: Method name to call (e.g., "generate", "complete")
        *args: Positional arguments for the method
        preferred_providers: Ordered list of preferred providers to try
        **kwargs: Keyword arguments for the method
        
    Returns:
        Result from the first successful provider call
        
    Raises:
        AllProvidersFailedError: If all providers fail
    """
    correlation_id = get_correlation_id()
    breaker = get_circuit_breaker()
    
    # Determine provider order
    if preferred_providers:
        provider_order = [p for p in preferred_providers if p in providers]
        # Add any remaining providers
        provider_order.extend([p for p in providers if p not in provider_order])
    else:
        provider_order = list(providers.keys())
    
    errors: List[Exception] = []
    tried_providers: List[str] = []
    
    for provider_name in provider_order:
        provider = providers[provider_name]
        
        # Skip providers with open circuits
        state = await breaker._check_state(provider_name)
        if state == CircuitState.OPEN:
            logger.info(
                "Skipping provider %s (circuit open)",
                provider_name,
                extra={"correlation_id": correlation_id},
            )
            continue
        
        tried_providers.append(provider_name)
        
        try:
            # Get the method and call it
            provider_method = getattr(provider, method, None)
            if provider_method is None:
                logger.warning(
                    "Provider %s does not have method %s",
                    provider_name,
                    method,
                    extra={"correlation_id": correlation_id},
                )
                continue
            
            start_time = time.perf_counter()
            result = await provider_method(*args, **kwargs)
            duration = time.perf_counter() - start_time
            
            await breaker.record_success(provider_name)
            
            logger.info(
                "Provider %s.%s succeeded in %.3fs",
                provider_name,
                method,
                duration,
                extra={
                    "correlation_id": correlation_id,
                    "provider": provider_name,
                    "method": method,
                    "duration_ms": duration * 1000,
                },
            )
            
            return result
            
        except asyncio.TimeoutError as e:
            await breaker.record_failure(provider_name, e)
            errors.append(ProviderTimeoutError(provider_name, kwargs.get("timeout", 60.0)))
            logger.warning(
                "Provider %s timed out",
                provider_name,
                extra={"correlation_id": correlation_id, "provider": provider_name},
            )
            
        except Exception as e:
            await breaker.record_failure(provider_name, e)
            
            # Classify the error
            error_str = str(e).lower()
            if "rate" in error_str and "limit" in error_str:
                errors.append(ProviderRateLimitError(provider_name, original_error=e))
            else:
                errors.append(ProviderError(str(e), provider_name, original_error=e))
            
            logger.warning(
                "Provider %s failed: %s",
                provider_name,
                str(e),
                extra={
                    "correlation_id": correlation_id,
                    "provider": provider_name,
                    "error_type": type(e).__name__,
                },
            )
    
    # All providers failed
    raise AllProvidersFailedError(tried_providers, errors)
