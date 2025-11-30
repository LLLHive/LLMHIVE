"""Helper functions for testing."""
from __future__ import annotations

import time
import asyncio
from typing import Any, Dict, List, Callable
from contextlib import contextmanager


def measure_time(func: Callable) -> tuple[Any, float]:
    """Measure execution time of a function.
    
    Args:
        func: Function to measure
        
    Returns:
        Tuple of (result, execution_time_seconds)
    """
    start = time.time()
    result = func()
    elapsed = time.time() - start
    return result, elapsed


async def measure_async_time(coro: Callable) -> tuple[Any, float]:
    """Measure execution time of an async function.
    
    Args:
        coro: Async function to measure
        
    Returns:
        Tuple of (result, execution_time_seconds)
    """
    start = time.time()
    result = await coro
    elapsed = time.time() - start
    return result, elapsed


@contextmanager
def assert_raises(exception_type: type[Exception], message: str = ""):
    """Context manager to assert exception is raised.
    
    Args:
        exception_type: Expected exception type
        message: Optional message to check in exception
    """
    try:
        yield
        assert False, f"Expected {exception_type.__name__} to be raised"
    except exception_type as e:
        if message:
            assert message in str(e), f"Exception message should contain '{message}'"
        return e


def assert_response_format(response: Dict[str, Any]) -> None:
    """Assert response has expected format.
    
    Args:
        response: Response dictionary to validate
    """
    assert "content" in response or "answer" in response, "Response missing content/answer"
    assert isinstance(response.get("content") or response.get("answer"), str), "Content must be string"


def assert_no_sensitive_data(data: Any, sensitive_patterns: List[str] = None) -> None:
    """Assert data doesn't contain sensitive information.
    
    Args:
        data: Data to check
        sensitive_patterns: List of patterns to check for
    """
    if sensitive_patterns is None:
        sensitive_patterns = [
            "password",
            "api_key",
            "secret",
            "token",
            "credential",
        ]
    
    data_str = str(data).lower()
    for pattern in sensitive_patterns:
        assert pattern not in data_str, f"Sensitive data '{pattern}' found in output"


def assert_within_timeout(func: Callable, timeout: float, *args, **kwargs) -> Any:
    """Assert function completes within timeout.
    
    Args:
        func: Function to execute
        timeout: Maximum time in seconds
        *args: Function arguments
        **kwargs: Function keyword arguments
        
    Returns:
        Function result
    """
    start = time.time()
    result = func(*args, **kwargs)
    elapsed = time.time() - start
    assert elapsed < timeout, f"Function took {elapsed}s, exceeded timeout of {timeout}s"
    return result


async def assert_async_within_timeout(coro: Callable, timeout: float) -> Any:
    """Assert async function completes within timeout.
    
    Args:
        coro: Async function to execute
        timeout: Maximum time in seconds
        
    Returns:
        Function result
    """
    try:
        result = await asyncio.wait_for(coro, timeout=timeout)
        return result
    except asyncio.TimeoutError:
        assert False, f"Async function exceeded timeout of {timeout}s"


def create_concurrent_requests(count: int, request_func: Callable) -> List[Any]:
    """Create multiple concurrent requests.
    
    Args:
        count: Number of concurrent requests
        request_func: Function to call for each request
        
    Returns:
        List of results
    """
    import concurrent.futures
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=count) as executor:
        futures = [executor.submit(request_func) for _ in range(count)]
        return [future.result() for future in concurrent.futures.as_completed(futures)]


async def create_async_concurrent_requests(count: int, coro_func: Callable) -> List[Any]:
    """Create multiple concurrent async requests.
    
    Args:
        count: Number of concurrent requests
        coro_func: Async function to call for each request
        
    Returns:
        List of results
    """
    tasks = [coro_func() for _ in range(count)]
    return await asyncio.gather(*tasks)


def assert_memory_usage_acceptable(max_mb: float = 500.0) -> None:
    """Assert memory usage is within acceptable limits.
    
    Args:
        max_mb: Maximum memory in MB
    """
    import psutil
    import os
    
    process = psutil.Process(os.getpid())
    memory_mb = process.memory_info().rss / 1024 / 1024
    assert memory_mb < max_mb, f"Memory usage {memory_mb:.2f}MB exceeds limit of {max_mb}MB"


def assert_response_time_acceptable(response_time: float, max_seconds: float = 10.0) -> None:
    """Assert response time is acceptable.
    
    Args:
        response_time: Response time in seconds
        max_seconds: Maximum acceptable time
    """
    assert response_time < max_seconds, f"Response time {response_time}s exceeds limit of {max_seconds}s"


def assert_token_usage_acceptable(tokens: int, max_tokens: int = 10000) -> None:
    """Assert token usage is within limits.
    
    Args:
        tokens: Number of tokens used
        max_tokens: Maximum acceptable tokens
    """
    assert tokens < max_tokens, f"Token usage {tokens} exceeds limit of {max_tokens}"


def extract_claims_from_text(text: str) -> List[str]:
    """Extract factual claims from text for fact-checking.
    
    Args:
        text: Text to extract claims from
        
    Returns:
        List of claims
    """
    # Simple implementation - can be enhanced
    import re
    sentences = re.split(r'[.!?]+', text)
    claims = [s.strip() for s in sentences if len(s.strip()) > 20]
    return claims[:10]  # Limit to 10 claims


def simulate_slow_response(delay: float = 1.0):
    """Decorator to simulate slow response.
    
    Args:
        delay: Delay in seconds
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            await asyncio.sleep(delay)
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def assert_error_message_user_friendly(error: Exception) -> None:
    """Assert error message is user-friendly.
    
    Args:
        error: Exception to check
    """
    error_str = str(error).lower()
    # Should not contain technical details
    technical_terms = ["traceback", "stack", "file", "line", "exception", "error code"]
    for term in technical_terms:
        assert term not in error_str, f"Error message contains technical term: {term}"


def assert_no_console_errors(captured_logs: List[str]) -> None:
    """Assert no console errors in logs.
    
    Args:
        captured_logs: List of log messages
    """
    error_keywords = ["error", "exception", "failed", "crash"]
    for log in captured_logs:
        log_lower = log.lower()
        # Allow intentional error logging, but not unhandled errors
        if any(keyword in log_lower for keyword in error_keywords):
            # Check if it's a handled error (logged intentionally)
            if "handled" not in log_lower and "caught" not in log_lower:
                assert False, f"Unhandled error in logs: {log}"

