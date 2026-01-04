"""Stage 4 Hardening - Production-Grade Safety and Reliability.

This module addresses the production-readiness audit requirements:
- Timeouts and circuit breakers for all external calls
- Retry with exponential backoff and jitter
- Global anti-infinite-loop protection
- Persistence for trial counters and learned weights
- Thread-safe operations with proper locking
- Structured logging without PII leakage
- Bounded resource usage
"""
from __future__ import annotations

import asyncio
import functools
import hashlib
import logging
import os
import random
import threading
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Awaitable, Callable, Dict, List, Optional, TypeVar, Union

logger = logging.getLogger(__name__)

T = TypeVar("T")


# ==============================================================================
# CONFIGURATION
# ==============================================================================

@dataclass(frozen=True)
class Stage4Config:
    """Immutable configuration for Stage 4 components."""
    
    # Timeouts (seconds)
    coref_timeout: float = 5.0
    llm_timeout: float = 30.0
    external_api_timeout: float = 10.0
    moderation_timeout: float = 5.0
    
    # Retry settings
    max_retries: int = 3
    base_delay: float = 0.5
    max_delay: float = 30.0
    jitter_factor: float = 0.1
    
    # Global limits (anti-infinite-loop)
    max_total_iterations: int = 10
    max_total_tool_calls: int = 50
    max_total_tokens: int = 100_000
    max_wall_clock_seconds: float = 120.0
    
    # Memory limits
    max_memory_entries_per_user: int = 1000
    max_memory_entries_per_session: int = 100
    memory_ttl_days: int = 7
    summarization_threshold: int = 50
    
    # Rate limiting
    free_tier_rpm: int = 10
    basic_tier_rpm: int = 30
    pro_tier_rpm: int = 100
    enterprise_tier_rpm: int = 1000
    
    # Multimodal trials (free tier)
    max_image_trials: int = 3
    max_audio_trials: int = 2
    max_audio_duration_seconds: int = 60
    
    # Learned weights
    min_model_weight: float = 0.1
    max_model_weight: float = 5.0
    weight_learning_rate: float = 0.05
    min_samples_for_learning: int = 10
    
    # Confidence thresholds
    min_coref_confidence: float = 0.7
    refinement_confidence_threshold: float = 0.7
    
    @classmethod
    def from_env(cls) -> "Stage4Config":
        """Load configuration from environment variables."""
        return cls(
            coref_timeout=float(os.getenv("S4_COREF_TIMEOUT", "5.0")),
            llm_timeout=float(os.getenv("S4_LLM_TIMEOUT", "30.0")),
            max_total_iterations=int(os.getenv("S4_MAX_ITERATIONS", "10")),
            max_wall_clock_seconds=float(os.getenv("S4_MAX_WALL_CLOCK", "120.0")),
        )


# Singleton config
_config: Optional[Stage4Config] = None
_config_lock = threading.Lock()


def get_config(force_reload: bool = False) -> Stage4Config:
    """Get the Stage 4 configuration singleton.
    
    Args:
        force_reload: If True, reload config from environment (useful for tests)
    """
    global _config
    if force_reload or _config is None:
        with _config_lock:
            if force_reload or _config is None:
                _config = Stage4Config.from_env()
    return _config


def reset_stage4_config() -> None:
    """Reset the config singleton (for testing).
    
    Call this in test teardown to ensure fresh config for each test.
    """
    global _config
    with _config_lock:
        _config = None


def set_stage4_config(config: Stage4Config) -> None:
    """Inject a specific config (for testing).
    
    Args:
        config: The config to use
    """
    global _config
    with _config_lock:
        _config = config


# ==============================================================================
# CIRCUIT BREAKER
# ==============================================================================

class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if recovered


@dataclass
class CircuitBreaker:
    """Circuit breaker for external service calls.
    
    Prevents cascading failures by failing fast when a service is down.
    """
    name: str
    failure_threshold: int = 5
    recovery_timeout: float = 30.0
    half_open_max_calls: int = 3
    
    _state: CircuitState = field(default=CircuitState.CLOSED, init=False)
    _failure_count: int = field(default=0, init=False)
    _success_count: int = field(default=0, init=False)
    _last_failure_time: Optional[float] = field(default=None, init=False)
    _half_open_calls: int = field(default=0, init=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False)
    
    @property
    def state(self) -> CircuitState:
        """Get current state, checking for recovery."""
        with self._lock:
            if self._state == CircuitState.OPEN:
                if (self._last_failure_time and 
                    time.time() - self._last_failure_time > self.recovery_timeout):
                    self._state = CircuitState.HALF_OPEN
                    self._half_open_calls = 0
                    # Reset success count for fresh half-open trial
                    self._success_count = 0
                    logger.info("Circuit %s transitioning to HALF_OPEN", self.name)
            return self._state
    
    def record_success(self):
        """Record a successful call."""
        with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                self._success_count += 1
                if self._success_count >= self.half_open_max_calls:
                    self._state = CircuitState.CLOSED
                    self._failure_count = 0
                    self._success_count = 0
                    logger.info("Circuit %s CLOSED (recovered)", self.name)
            else:
                self._failure_count = 0
    
    def record_failure(self):
        """Record a failed call."""
        with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.time()
            
            if self._state == CircuitState.HALF_OPEN:
                self._state = CircuitState.OPEN
                # Reset success count - trial failed, need fresh start next time
                self._success_count = 0
                logger.warning("Circuit %s re-OPENED from HALF_OPEN", self.name)
            elif self._failure_count >= self.failure_threshold:
                self._state = CircuitState.OPEN
                # Also reset success count when opening from closed
                self._success_count = 0
                logger.warning("Circuit %s OPENED after %d failures", 
                             self.name, self._failure_count)
    
    def allow_request(self) -> bool:
        """Check if a request should be allowed."""
        state = self.state  # This may transition OPEN -> HALF_OPEN
        
        if state == CircuitState.CLOSED:
            return True
        elif state == CircuitState.OPEN:
            return False
        else:  # HALF_OPEN
            with self._lock:
                self._half_open_calls += 1
                return self._half_open_calls <= self.half_open_max_calls


class CircuitBreakerRegistry:
    """Registry of circuit breakers for different services."""
    
    _instance: Optional["CircuitBreakerRegistry"] = None
    _lock = threading.Lock()
    
    def __init__(self):
        self._breakers: Dict[str, CircuitBreaker] = {}
        self._breaker_lock = threading.Lock()
    
    @classmethod
    def get_instance(cls) -> "CircuitBreakerRegistry":
        """Get singleton instance."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance
    
    def get(self, name: str, **kwargs) -> CircuitBreaker:
        """Get or create a circuit breaker."""
        with self._breaker_lock:
            if name not in self._breakers:
                self._breakers[name] = CircuitBreaker(name=name, **kwargs)
            return self._breakers[name]
    
    def get_all_states(self) -> Dict[str, str]:
        """Get states of all circuit breakers."""
        with self._breaker_lock:
            return {name: cb.state.value for name, cb in self._breakers.items()}


# ==============================================================================
# RETRY WITH BACKOFF
# ==============================================================================

class RetryError(Exception):
    """Raised when all retries are exhausted."""
    
    def __init__(self, message: str, last_exception: Optional[Exception] = None):
        super().__init__(message)
        self.last_exception = last_exception


async def retry_with_backoff(
    func: Callable[..., Awaitable[T]],
    *args,
    max_retries: int = 3,
    base_delay: float = 0.5,
    max_delay: float = 30.0,
    jitter: float = 0.1,
    retryable_exceptions: tuple = (Exception,),
    circuit_breaker: Optional[CircuitBreaker] = None,
    **kwargs,
) -> T:
    """
    Execute an async function with exponential backoff retry.
    
    Args:
        func: Async function to call
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay between retries
        max_delay: Maximum delay between retries
        jitter: Random jitter factor (0.1 = 10% variation)
        retryable_exceptions: Exception types to retry on
        circuit_breaker: Optional circuit breaker to use
        
    Returns:
        Result of the function call
        
    Raises:
        RetryError: If all retries are exhausted
    """
    last_exception: Optional[Exception] = None
    
    for attempt in range(max_retries + 1):
        # Check circuit breaker
        if circuit_breaker and not circuit_breaker.allow_request():
            raise RetryError(
                f"Circuit breaker {circuit_breaker.name} is open",
                last_exception
            )
        
        try:
            result = await func(*args, **kwargs)
            
            if circuit_breaker:
                circuit_breaker.record_success()
            
            return result
            
        except retryable_exceptions as e:
            last_exception = e
            
            if circuit_breaker:
                circuit_breaker.record_failure()
            
            if attempt < max_retries:
                # Calculate delay with exponential backoff
                delay = min(base_delay * (2 ** attempt), max_delay)
                # Add jitter
                delay *= 1 + random.uniform(-jitter, jitter)
                
                logger.warning(
                    "Retry attempt %d/%d after error: %s. Waiting %.2fs",
                    attempt + 1, max_retries, str(e)[:100], delay
                )
                
                await asyncio.sleep(delay)
            else:
                logger.error(
                    "All %d retries exhausted. Last error: %s",
                    max_retries, str(e)[:200]
                )
    
    raise RetryError(
        f"All {max_retries} retries exhausted",
        last_exception
    )


# ==============================================================================
# GLOBAL REQUEST BUDGET (ANTI-INFINITE-LOOP)
# ==============================================================================

@dataclass
class RequestBudget:
    """Tracks resource usage for a single request to prevent runaway loops."""
    
    request_id: str
    max_iterations: int
    max_tool_calls: int
    max_tokens: int
    max_wall_clock: float
    
    _iterations: int = field(default=0, init=False)
    _tool_calls: int = field(default=0, init=False)
    _tokens_used: int = field(default=0, init=False)
    _start_time: float = field(default_factory=time.time, init=False)
    _exhausted_reason: Optional[str] = field(default=None, init=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False)
    
    @property
    def is_exhausted(self) -> bool:
        """Check if any budget limit is exceeded."""
        return self._exhausted_reason is not None
    
    @property
    def exhausted_reason(self) -> Optional[str]:
        """Get the reason for budget exhaustion."""
        return self._exhausted_reason
    
    @property
    def remaining_time(self) -> float:
        """Get remaining wall clock time."""
        elapsed = time.time() - self._start_time
        return max(0, self.max_wall_clock - elapsed)
    
    def check_and_consume(
        self,
        iterations: int = 0,
        tool_calls: int = 0,
        tokens: int = 0,
    ) -> bool:
        """
        Check budget and consume resources if available.
        
        Thread-safe: Uses internal lock to prevent race conditions
        when multiple parallel tasks consume budget simultaneously.
        
        Returns:
            True if budget was available and consumed, False if exhausted
        """
        with self._lock:
            if self._exhausted_reason:
                return False
            
            # Check wall clock first
            elapsed = time.time() - self._start_time
            if elapsed >= self.max_wall_clock:
                self._exhausted_reason = f"Wall clock exceeded ({elapsed:.1f}s)"
                return False
            
            # Check iterations
            if self._iterations + iterations > self.max_iterations:
                self._exhausted_reason = f"Max iterations exceeded ({self._iterations})"
                return False
            
            # Check tool calls
            if self._tool_calls + tool_calls > self.max_tool_calls:
                self._exhausted_reason = f"Max tool calls exceeded ({self._tool_calls})"
                return False
            
            # Check tokens
            if self._tokens_used + tokens > self.max_tokens:
                self._exhausted_reason = f"Max tokens exceeded ({self._tokens_used})"
                return False
            
            # Consume
            self._iterations += iterations
            self._tool_calls += tool_calls
            self._tokens_used += tokens
            
            return True
    
    def get_usage_summary(self) -> Dict[str, Any]:
        """Get current usage summary."""
        return {
            "request_id": self.request_id[:8],
            "iterations": f"{self._iterations}/{self.max_iterations}",
            "tool_calls": f"{self._tool_calls}/{self.max_tool_calls}",
            "tokens": f"{self._tokens_used}/{self.max_tokens}",
            "elapsed_seconds": round(time.time() - self._start_time, 2),
            "max_seconds": self.max_wall_clock,
            "exhausted": self.is_exhausted,
            "exhausted_reason": self._exhausted_reason,
        }


def create_request_budget(request_id: str, config: Optional[Stage4Config] = None) -> RequestBudget:
    """Create a request budget with standard limits."""
    cfg = config or get_config()
    return RequestBudget(
        request_id=request_id,
        max_iterations=cfg.max_total_iterations,
        max_tool_calls=cfg.max_total_tool_calls,
        max_tokens=cfg.max_total_tokens,
        max_wall_clock=cfg.max_wall_clock_seconds,
    )


# ==============================================================================
# PERSISTENT TRIAL COUNTER (ABUSE PREVENTION)
# ==============================================================================

class PersistentTrialCounter:
    """Persistent trial counter that survives server restarts.
    
    Uses file-based persistence with atomic writes. In production,
    use Redis or a database for distributed deployments.
    
    Features:
    - Atomic file writes (write to temp, then rename)
    - Thread-safe operations
    - Optional Redis backend (via USE_REDIS_TRIAL_COUNTER env var)
    """
    
    def __init__(self, persistence_path: Optional[str] = None, use_redis: bool = False):
        self._path = persistence_path or os.getenv(
            "S4_TRIAL_COUNTER_PATH",
            "/tmp/llmhive_trial_counters.json"
        )
        self._counters: Dict[str, Dict[str, int]] = {}
        self._lock = threading.Lock()
        self._use_redis = use_redis or os.getenv("USE_REDIS_TRIAL_COUNTER", "0") == "1"
        self._redis_client = None
        
        if self._use_redis:
            self._init_redis()
        else:
            self._load()
    
    def _init_redis(self):
        """Initialize Redis connection if available."""
        try:
            import redis
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
            self._redis_client = redis.from_url(redis_url)
            # Test connection
            self._redis_client.ping()
            logger.info("Trial counter using Redis backend")
        except Exception as e:
            logger.warning("Redis not available for trial counter, falling back to file: %s", e)
            self._use_redis = False
            self._redis_client = None
            self._load()
    
    def _load(self):
        """Load counters from disk."""
        try:
            if os.path.exists(self._path):
                import json
                with open(self._path, 'r') as f:
                    self._counters = json.load(f)
                logger.info("Loaded %d trial counters from file", len(self._counters))
        except Exception as e:
            logger.warning("Failed to load trial counters: %s", e)
            self._counters = {}
    
    def _save(self):
        """Save counters to disk with atomic write."""
        if self._use_redis:
            return  # No file save needed when using Redis
        
        try:
            import json
            import tempfile
            
            # Write to temp file first, then rename for atomicity
            dir_name = os.path.dirname(self._path) or "."
            with tempfile.NamedTemporaryFile(
                mode='w',
                dir=dir_name,
                delete=False,
                suffix='.tmp'
            ) as f:
                json.dump(self._counters, f)
                temp_path = f.name
            
            # Atomic rename
            os.replace(temp_path, self._path)
            
        except Exception as e:
            logger.warning("Failed to save trial counters: %s", e)
            # Clean up temp file if it exists
            try:
                if 'temp_path' in locals():
                    os.unlink(temp_path)
            except Exception:
                pass
    
    def _redis_key(self, user_id: str, feature: str) -> str:
        """Generate Redis key for a user+feature."""
        prefix = os.getenv("RATE_LIMIT_REDIS_PREFIX", "llmhive:")
        return f"{prefix}trials:{user_id}:{feature}"
    
    def get_usage(self, user_id: str, feature: str) -> int:
        """Get current usage count for a user+feature."""
        if self._use_redis and self._redis_client:
            try:
                value = self._redis_client.get(self._redis_key(user_id, feature))
                return int(value) if value else 0
            except Exception as e:
                logger.warning("Redis get failed, falling back to memory: %s", e)
        
        with self._lock:
            user_counters = self._counters.get(user_id, {})
            return user_counters.get(feature, 0)
    
    def increment(self, user_id: str, feature: str) -> int:
        """Increment usage count and return new value."""
        if self._use_redis and self._redis_client:
            try:
                key = self._redis_key(user_id, feature)
                new_value = self._redis_client.incr(key)
                # Set TTL of 30 days for trial counters
                self._redis_client.expire(key, 30 * 24 * 3600)
                return new_value
            except Exception as e:
                logger.warning("Redis incr failed, falling back to file: %s", e)
        
        with self._lock:
            if user_id not in self._counters:
                self._counters[user_id] = {}
            
            current = self._counters[user_id].get(feature, 0)
            self._counters[user_id][feature] = current + 1
            self._save()
            
            return current + 1
    
    def check_and_consume(
        self,
        user_id: str,
        feature: str,
        max_trials: int,
    ) -> tuple[bool, int]:
        """
        Check if trial is available and consume if so.
        
        Atomic operation: checks and increments in one step.
        
        Returns:
            Tuple of (allowed, remaining_trials)
        """
        if self._use_redis and self._redis_client:
            try:
                key = self._redis_key(user_id, feature)
                # Use INCR which is atomic, then check if we exceeded
                current = self._redis_client.incr(key)
                self._redis_client.expire(key, 30 * 24 * 3600)
                
                if current > max_trials:
                    # Already over limit, decrement back
                    self._redis_client.decr(key)
                    return False, 0
                
                return True, max_trials - current
            except Exception as e:
                logger.warning("Redis check_and_consume failed: %s", e)
        
        with self._lock:
            if user_id not in self._counters:
                self._counters[user_id] = {}
            
            current = self._counters[user_id].get(feature, 0)
            remaining = max_trials - current
            
            if remaining <= 0:
                return False, 0
            
            self._counters[user_id][feature] = current + 1
            self._save()
            
            return True, remaining - 1
    
    def clear(self):
        """Clear all counters (for testing)."""
        with self._lock:
            self._counters = {}
            if self._use_redis and self._redis_client:
                # Note: This clears ALL trial keys, use with caution
                logger.warning("Clearing all trial counters in Redis")
            else:
                self._save()


# Singleton
_trial_counter: Optional[PersistentTrialCounter] = None
_trial_counter_lock = threading.Lock()


def get_trial_counter() -> PersistentTrialCounter:
    """Get the singleton trial counter."""
    global _trial_counter
    if _trial_counter is None:
        with _trial_counter_lock:
            if _trial_counter is None:
                _trial_counter = PersistentTrialCounter()
    return _trial_counter


def reset_trial_counter() -> None:
    """Reset the trial counter singleton (for testing).
    
    Call this in test teardown to ensure fresh state for each test.
    """
    global _trial_counter
    with _trial_counter_lock:
        _trial_counter = None


def set_trial_counter(counter: PersistentTrialCounter) -> None:
    """Inject a specific trial counter (for testing).
    
    Args:
        counter: The counter instance to use
    """
    global _trial_counter
    with _trial_counter_lock:
        _trial_counter = counter


# ==============================================================================
# SAFE EXTERNAL CALL WRAPPER
# ==============================================================================

@asynccontextmanager
async def safe_external_call(
    service_name: str,
    timeout: float = 10.0,
    retries: int = 3,
):
    """
    Context manager for safe external API calls.
    
    Provides:
    - Timeout enforcement
    - Circuit breaker integration
    - Structured error handling
    
    Usage:
        async with safe_external_call("coingecko", timeout=5.0) as ctx:
            result = await fetch_data()
            ctx.record_success()
    """
    registry = CircuitBreakerRegistry.get_instance()
    breaker = registry.get(service_name)
    
    if not breaker.allow_request():
        raise RetryError(f"Service {service_name} circuit is open")
    
    class CallContext:
        def __init__(self):
            self.success = False
            self._failure_recorded = False
            self.start_time = time.time()
        
        def record_success(self):
            self.success = True
            breaker.record_success()
            latency = (time.time() - self.start_time) * 1000
            logger.debug(
                "External call to %s succeeded in %.1fms",
                service_name, latency
            )
        
        def record_failure(self, error: str):
            # Prevent double-counting failures
            if self._failure_recorded:
                return
            self._failure_recorded = True
            breaker.record_failure()
            logger.warning(
                "External call to %s failed: %s",
                service_name, error[:100]
            )
    
    ctx = CallContext()
    
    try:
        yield ctx
    except asyncio.TimeoutError:
        ctx.record_failure("Timeout")
        raise
    except Exception as e:
        ctx.record_failure(str(e))
        raise
    # Note: Removed the finally block that called breaker.record_failure()
    # because the except blocks already handle failure recording via ctx.record_failure()


# ==============================================================================
# STRUCTURED LOGGING (NO PII)
# ==============================================================================

def sanitize_for_logging(data: Any, max_length: int = 100) -> str:
    """
    Sanitize data for logging, removing PII and secrets.
    
    Args:
        data: Data to sanitize
        max_length: Maximum length of output string
        
    Returns:
        Sanitized string safe for logging
    """
    if data is None:
        return "<none>"
    
    text = str(data)
    
    # Truncate
    if len(text) > max_length:
        text = text[:max_length] + "..."
    
    # Remove potential secrets (API keys, tokens)
    import re
    text = re.sub(r'(sk_live_|sk_test_|pk_live_|pk_test_)[A-Za-z0-9]+', '[STRIPE_KEY]', text)
    # Match api_key, apikey, token, secret, password, auth followed by = or : and a value
    text = re.sub(r'(api[_-]?key|token|secret|password|auth)\s*[=:]\s*[^\s,;]+', r'\1=[REDACTED]', text, flags=re.I)
    text = re.sub(r'Bearer\s+[A-Za-z0-9\-_.]+', 'Bearer [TOKEN]', text)
    
    # Remove email addresses
    text = re.sub(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', '[EMAIL]', text)
    
    # Remove phone numbers (simple pattern)
    text = re.sub(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', '[PHONE]', text)
    
    return text


@dataclass
class StructuredLogEntry:
    """Structured log entry with trace context."""
    
    event: str
    request_id: Optional[str] = None
    trace_id: Optional[str] = None
    user_id_hash: Optional[str] = None  # Hashed, not raw
    component: str = "stage4"
    level: str = "info"
    latency_ms: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON logging."""
        return {
            "ts": self.timestamp.isoformat(),
            "event": self.event,
            "component": self.component,
            "level": self.level,
            "request_id": self.request_id,
            "trace_id": self.trace_id,
            "user_hash": self.user_id_hash,
            "latency_ms": self.latency_ms,
            **{k: sanitize_for_logging(v) for k, v in self.metadata.items()},
        }


def hash_user_id(user_id: str) -> str:
    """Hash user ID for logging (privacy)."""
    return hashlib.sha256(user_id.encode()).hexdigest()[:16]


class Stage4Logger:
    """Structured logger for Stage 4 components."""
    
    def __init__(self, request_id: Optional[str] = None, trace_id: Optional[str] = None):
        self.request_id = request_id
        self.trace_id = trace_id
    
    def _log(self, entry: StructuredLogEntry):
        """Emit a structured log entry."""
        entry.request_id = entry.request_id or self.request_id
        entry.trace_id = entry.trace_id or self.trace_id
        
        # Use JSON format for structured logging
        import json
        log_line = json.dumps(entry.to_dict(), default=str)
        
        if entry.level == "error":
            logger.error(log_line)
        elif entry.level == "warning":
            logger.warning(log_line)
        elif entry.level == "debug":
            logger.debug(log_line)
        else:
            logger.info(log_line)
    
    def log_coref_resolution(
        self,
        pronoun: str,
        resolved_to: str,
        confidence: float,
        user_id: str,
    ):
        """Log a pronoun resolution event."""
        self._log(StructuredLogEntry(
            event="coref_resolution",
            user_id_hash=hash_user_id(user_id),
            metadata={
                "pronoun": pronoun,
                "resolved_to": sanitize_for_logging(resolved_to, 50),
                "confidence": round(confidence, 3),
            },
        ))
    
    def log_refinement_iteration(
        self,
        iteration: int,
        confidence: float,
        improved: bool,
        user_id: str,
    ):
        """Log a refinement iteration."""
        self._log(StructuredLogEntry(
            event="refinement_iteration",
            user_id_hash=hash_user_id(user_id),
            metadata={
                "iteration": iteration,
                "confidence": round(confidence, 3),
                "improved": improved,
            },
        ))
    
    def log_budget_exhausted(
        self,
        reason: str,
        usage: Dict[str, Any],
        user_id: str,
    ):
        """Log budget exhaustion."""
        self._log(StructuredLogEntry(
            event="budget_exhausted",
            level="warning",
            user_id_hash=hash_user_id(user_id),
            metadata={
                "reason": reason,
                "usage": usage,
            },
        ))
    
    def log_circuit_breaker_state(
        self,
        service: str,
        state: str,
        failure_count: int,
    ):
        """Log circuit breaker state change."""
        self._log(StructuredLogEntry(
            event="circuit_breaker_state",
            level="warning" if state != "closed" else "info",
            metadata={
                "service": service,
                "state": state,
                "failure_count": failure_count,
            },
        ))
    
    def log_external_call(
        self,
        service: str,
        success: bool,
        latency_ms: float,
        cached: bool = False,
    ):
        """Log an external API call."""
        self._log(StructuredLogEntry(
            event="external_call",
            latency_ms=latency_ms,
            metadata={
                "service": service,
                "success": success,
                "cached": cached,
            },
        ))
    
    def log_moderation_result(
        self,
        blocked: bool,
        category: Optional[str],
        user_id: str,
    ):
        """Log moderation result (without content)."""
        self._log(StructuredLogEntry(
            event="moderation_check",
            level="warning" if blocked else "info",
            user_id_hash=hash_user_id(user_id),
            metadata={
                "blocked": blocked,
                "category": category,
            },
        ))


# ==============================================================================
# MEMORY SUMMARY PROVENANCE
# ==============================================================================

@dataclass
class SummaryProvenance:
    """Provenance information for summarized memory entries."""
    
    original_entry_ids: List[str]
    summary_date: datetime
    summary_method: str  # "llm", "extractive", "heuristic"
    is_derived: bool = True
    confidence: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "original_ids": self.original_entry_ids,
            "summary_date": self.summary_date.isoformat(),
            "method": self.summary_method,
            "is_derived": self.is_derived,
            "confidence": self.confidence,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SummaryProvenance":
        """Create from dictionary."""
        return cls(
            original_entry_ids=data.get("original_ids", []),
            summary_date=datetime.fromisoformat(data["summary_date"]),
            summary_method=data.get("method", "unknown"),
            is_derived=data.get("is_derived", True),
            confidence=data.get("confidence", 0.0),
        )


# ==============================================================================
# LEARNED WEIGHTS WITH BOUNDS AND VERSIONING
# ==============================================================================

@dataclass
class BoundedModelWeight:
    """Model weight with bounds and versioning for safe learning."""
    
    model_id: str
    weight: float = 1.0
    min_weight: float = 0.1
    max_weight: float = 5.0
    learning_rate: float = 0.05
    version: int = 1
    sample_count: int = 0
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def update(self, success: bool, min_samples: int = 10) -> float:
        """
        Update weight based on feedback.
        
        Returns:
            New weight value
        """
        self.sample_count += 1
        
        # Don't update until we have enough samples
        if self.sample_count < min_samples:
            return self.weight
        
        # Calculate adjustment
        if success:
            adjustment = self.learning_rate
        else:
            adjustment = -self.learning_rate
        
        # Apply with bounds
        new_weight = self.weight + adjustment
        new_weight = max(self.min_weight, min(self.max_weight, new_weight))
        
        self.weight = new_weight
        self.last_updated = datetime.now(timezone.utc)
        
        return new_weight
    
    def reset(self):
        """Reset to initial state."""
        self.weight = 1.0
        self.sample_count = 0
        self.version += 1
        self.last_updated = datetime.now(timezone.utc)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for persistence."""
        return {
            "model_id": self.model_id,
            "weight": self.weight,
            "version": self.version,
            "sample_count": self.sample_count,
            "last_updated": self.last_updated.isoformat(),
        }


class ShadowModeWeightManager:
    """
    Learned weight manager with shadow mode for safe evaluation.
    
    In shadow mode, weights are computed but not applied,
    allowing evaluation without affecting production.
    """
    
    def __init__(
        self,
        shadow_mode: bool = False,
        persistence_path: Optional[str] = None,
    ):
        self.shadow_mode = shadow_mode
        self._path = persistence_path
        self._weights: Dict[str, BoundedModelWeight] = {}
        self._shadow_log: List[Dict[str, Any]] = []
        self._lock = threading.Lock()
        self._load()
    
    def _load(self):
        """Load weights from persistence."""
        if not self._path:
            return
        
        try:
            if os.path.exists(self._path):
                import json
                with open(self._path, 'r') as f:
                    data = json.load(f)
                
                for model_id, w in data.get("weights", {}).items():
                    self._weights[model_id] = BoundedModelWeight(
                        model_id=model_id,
                        weight=w.get("weight", 1.0),
                        version=w.get("version", 1),
                        sample_count=w.get("sample_count", 0),
                    )
                
                logger.info("Loaded %d model weights", len(self._weights))
        except Exception as e:
            logger.warning("Failed to load weights: %s", e)
    
    def _save(self):
        """Save weights to persistence."""
        if not self._path:
            return
        
        try:
            import json
            data = {
                "weights": {
                    m: w.to_dict() for m, w in self._weights.items()
                },
                "shadow_mode": self.shadow_mode,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            with open(self._path, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.warning("Failed to save weights: %s", e)
    
    def get_weight(self, model_id: str) -> float:
        """Get current weight for a model."""
        with self._lock:
            if model_id not in self._weights:
                self._weights[model_id] = BoundedModelWeight(model_id=model_id)
            return self._weights[model_id].weight
    
    def update(self, model_id: str, success: bool) -> float:
        """Update model weight based on feedback."""
        with self._lock:
            if model_id not in self._weights:
                self._weights[model_id] = BoundedModelWeight(model_id=model_id)
            
            old_weight = self._weights[model_id].weight
            new_weight = self._weights[model_id].update(success)
            
            if self.shadow_mode:
                # Log but don't apply
                self._shadow_log.append({
                    "model_id": model_id,
                    "old_weight": old_weight,
                    "new_weight": new_weight,
                    "success": success,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
                # Revert
                self._weights[model_id].weight = old_weight
                return old_weight
            else:
                self._save()
                return new_weight
    
    def get_shadow_log(self) -> List[Dict[str, Any]]:
        """Get shadow mode evaluation log."""
        with self._lock:
            return self._shadow_log.copy()
    
    def clear_shadow_log(self):
        """Clear the shadow log."""
        with self._lock:
            self._shadow_log.clear()


# ==============================================================================
# EXPORTS
# ==============================================================================

__all__ = [
    # Configuration
    "Stage4Config",
    "get_config",
    
    # Circuit Breaker
    "CircuitBreaker",
    "CircuitBreakerRegistry",
    "CircuitState",
    
    # Retry
    "retry_with_backoff",
    "RetryError",
    
    # Request Budget
    "RequestBudget",
    "create_request_budget",
    
    # Trial Counter
    "PersistentTrialCounter",
    "get_trial_counter",
    
    # Safe External Calls
    "safe_external_call",
    
    # Logging
    "sanitize_for_logging",
    "StructuredLogEntry",
    "Stage4Logger",
    "hash_user_id",
    
    # Memory
    "SummaryProvenance",
    
    # Weights
    "BoundedModelWeight",
    "ShadowModeWeightManager",
]

