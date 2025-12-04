"""Tests for graceful degradation when models fail."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

from llmhive.app.errors import (
    ProviderError,
    ProviderTimeoutError,
    AllProvidersFailedError,
    CircuitBreaker,
    call_with_fallback,
    get_circuit_breaker,
)


class TestGracefulDegradation:
    """Test graceful degradation when providers fail."""
    
    @pytest.fixture
    def mock_openai_provider(self):
        """Create a mock OpenAI provider."""
        provider = MagicMock()
        provider.name = "openai"
        
        async def generate(prompt, model="gpt-4", **kwargs):
            class Result:
                def __init__(self):
                    self.content = f"OpenAI response to: {prompt[:50]}"
                    self.text = self.content
                    self.model = model
                    self.tokens_used = 100
            return Result()
        
        provider.generate = generate
        return provider
    
    @pytest.fixture
    def mock_anthropic_provider(self):
        """Create a mock Anthropic provider."""
        provider = MagicMock()
        provider.name = "anthropic"
        
        async def generate(prompt, model="claude-3", **kwargs):
            class Result:
                def __init__(self):
                    self.content = f"Anthropic response to: {prompt[:50]}"
                    self.text = self.content
                    self.model = model
                    self.tokens_used = 100
            return Result()
        
        provider.generate = generate
        return provider
    
    @pytest.fixture
    def failing_provider(self):
        """Create a provider that always fails."""
        provider = MagicMock()
        provider.name = "failing"
        provider.generate = AsyncMock(side_effect=Exception("API temporarily unavailable"))
        return provider
    
    @pytest.fixture
    def timeout_provider(self):
        """Create a provider that times out."""
        provider = MagicMock()
        provider.name = "timeout"
        
        import asyncio
        async def slow_generate(prompt, **kwargs):
            await asyncio.sleep(10)  # Simulate slow response
            return MagicMock(content="Should not reach here")
        
        provider.generate = slow_generate
        return provider
    
    @pytest.fixture
    def rate_limited_provider(self):
        """Create a provider that returns rate limit errors."""
        provider = MagicMock()
        provider.name = "rate_limited"
        provider.generate = AsyncMock(side_effect=Exception("Rate limit exceeded"))
        return provider
    
    @pytest.mark.asyncio
    async def test_fallback_to_backup_on_primary_failure(
        self, failing_provider, mock_anthropic_provider
    ):
        """Test that system falls back to backup when primary fails."""
        providers = {
            "primary": failing_provider,
            "backup": mock_anthropic_provider,
        }
        
        result = await call_with_fallback(
            providers,
            "generate",
            "Test prompt",
            preferred_providers=["primary", "backup"],
        )
        
        assert result.content is not None
        assert "Anthropic" in result.content
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_prevents_repeated_failures(
        self, failing_provider
    ):
        """Test that circuit breaker prevents repeated calls to failing provider."""
        breaker = CircuitBreaker(failure_threshold=2, reset_timeout=60)
        
        # Cause failures to trip the circuit
        await breaker.record_failure("failing", Exception("fail"))
        await breaker.record_failure("failing", Exception("fail"))
        
        # Circuit should now be open
        assert breaker.is_open("failing")
    
    @pytest.mark.asyncio
    async def test_multiple_provider_fallback_chain(
        self, failing_provider, rate_limited_provider, mock_openai_provider
    ):
        """Test fallback through multiple failing providers."""
        providers = {
            "first": failing_provider,
            "second": rate_limited_provider,
            "third": mock_openai_provider,
        }
        
        result = await call_with_fallback(
            providers,
            "generate",
            "Complex query",
            preferred_providers=["first", "second", "third"],
        )
        
        assert result.content is not None
        assert "OpenAI" in result.content
    
    @pytest.mark.asyncio
    async def test_all_providers_fail_returns_error(
        self, failing_provider, rate_limited_provider
    ):
        """Test proper error when all providers fail."""
        providers = {
            "first": failing_provider,
            "second": rate_limited_provider,
        }
        
        with pytest.raises(AllProvidersFailedError) as exc_info:
            await call_with_fallback(
                providers,
                "generate",
                "Test prompt",
            )
        
        error = exc_info.value
        assert len(error.provider_errors) == 2
        assert "first" in error.provider_errors
        assert "second" in error.provider_errors
    
    @pytest.mark.asyncio
    async def test_provider_with_no_method_is_skipped(
        self, mock_openai_provider
    ):
        """Test that provider without requested method is skipped."""
        incomplete_provider = MagicMock()
        incomplete_provider.name = "incomplete"
        # No generate method
        
        providers = {
            "incomplete": incomplete_provider,
            "working": mock_openai_provider,
        }
        
        result = await call_with_fallback(
            providers,
            "generate",
            "Test",
            preferred_providers=["incomplete", "working"],
        )
        
        assert result.content is not None


class TestCircuitBreakerRecovery:
    """Test circuit breaker recovery behavior."""
    
    @pytest.mark.asyncio
    async def test_circuit_recovery_after_timeout(self):
        """Test that circuit recovers after reset timeout."""
        import asyncio
        
        breaker = CircuitBreaker(
            failure_threshold=2,
            reset_timeout=0.5,  # Short timeout for testing
            half_open_max_calls=2,
        )
        
        # Trip the circuit
        await breaker.record_failure("test", Exception("fail"))
        await breaker.record_failure("test", Exception("fail"))
        
        assert breaker.is_open("test")
        
        # Wait for reset timeout
        await asyncio.sleep(0.6)
        
        # Circuit should transition to half-open
        state = await breaker._check_state("test")
        from llmhive.app.errors import CircuitState
        assert state == CircuitState.HALF_OPEN
        
        # Successful calls should close the circuit
        await breaker.record_success("test")
        await breaker.record_success("test")
        
        state = await breaker._check_state("test")
        assert state == CircuitState.CLOSED
    
    @pytest.mark.asyncio
    async def test_circuit_reopens_on_half_open_failure(self):
        """Test that circuit reopens if failure occurs during recovery."""
        import asyncio
        
        breaker = CircuitBreaker(
            failure_threshold=2,
            reset_timeout=0.1,
        )
        
        # Trip the circuit
        await breaker.record_failure("test", Exception("fail"))
        await breaker.record_failure("test", Exception("fail"))
        
        # Wait for reset timeout
        await asyncio.sleep(0.2)
        await breaker._check_state("test")  # Transition to half-open
        
        # Fail during half-open
        await breaker.record_failure("test", Exception("fail again"))
        
        # Circuit should be open again
        assert breaker.is_open("test")


class TestErrorResponseFormat:
    """Test that error responses have consistent format."""
    
    def test_provider_error_format(self):
        """Test provider error response format."""
        from llmhive.app.errors import build_error_response
        
        error = ProviderError(
            "OpenAI API error: invalid_api_key",
            provider="openai",
            model="gpt-4",
        )
        
        response = build_error_response(error, request_id="req123")
        response_dict = response.to_dict()
        
        # Check required fields
        assert "error" in response_dict
        assert "code" in response_dict["error"]
        assert "message" in response_dict["error"]
        assert "correlation_id" in response_dict
        assert "timestamp" in response_dict
        assert response_dict["request_id"] == "req123"
    
    def test_all_providers_failed_error_format(self):
        """Test all providers failed error response format."""
        from llmhive.app.errors import build_error_response
        
        error = AllProvidersFailedError(
            ["openai", "anthropic"],
            [Exception("API error"), TimeoutError("Timeout")],
        )
        
        response = build_error_response(error)
        response_dict = response.to_dict()
        
        assert response_dict["error"]["code"] == "E2005"
        assert response_dict["error"]["recoverable"] is False


class TestMiddlewareIntegration:
    """Test error handling middleware integration."""
    
    def test_middleware_adds_correlation_id_to_response(self):
        """Test that middleware adds correlation ID to response headers."""
        from llmhive.app.main import app
        
        client = TestClient(app)
        response = client.get("/health")
        
        assert "X-Correlation-ID" in response.headers
        assert "X-Request-ID" in response.headers
        assert response.status_code == 200
    
    def test_middleware_logs_request_timing(self):
        """Test that middleware logs request timing."""
        from llmhive.app.main import app
        
        client = TestClient(app)
        response = client.get("/healthz")
        
        assert "X-Response-Time-Ms" in response.headers
        timing = float(response.headers["X-Response-Time-Ms"])
        assert timing >= 0
