"""Tests for LLMHive error handling module."""
import asyncio
import pytest
import time
from unittest.mock import AsyncMock, MagicMock, patch

# Import error handling components
from llmhive.app.errors import (
    LLMHiveError,
    ProviderError,
    ProviderTimeoutError,
    ProviderRateLimitError,
    AllProvidersFailedError,
    CircuitOpenError,
    OrchestrationError,
    ValidationError,
    ContentPolicyError,
    ErrorCode,
    CircuitBreaker,
    CircuitState,
    build_error_response,
    generate_correlation_id,
    get_correlation_id,
    set_correlation_id,
    with_error_handling,
    with_circuit_breaker,
    call_with_fallback,
)


class TestErrorCodes:
    """Test error code definitions."""
    
    def test_error_codes_are_unique(self):
        """All error codes should be unique."""
        codes = [code.value for code in ErrorCode]
        assert len(codes) == len(set(codes))
    
    def test_error_codes_start_with_e(self):
        """All error codes should start with E."""
        for code in ErrorCode:
            assert code.value.startswith("E")


class TestLLMHiveError:
    """Test base LLMHiveError exception."""
    
    def test_basic_error(self):
        """Test basic error creation."""
        error = LLMHiveError("Test error")
        assert error.message == "Test error"
        assert error.code == ErrorCode.INTERNAL_ERROR
        assert error.recoverable is True
        assert error.correlation_id is not None
    
    def test_error_with_code(self):
        """Test error with specific code."""
        error = LLMHiveError(
            "Not found",
            code=ErrorCode.NOT_FOUND,
            recoverable=False,
        )
        assert error.code == ErrorCode.NOT_FOUND
        assert error.recoverable is False
    
    def test_error_to_dict(self):
        """Test error serialization to dict."""
        error = LLMHiveError(
            "Test error",
            code=ErrorCode.VALIDATION_ERROR,
            details={"field": "email"},
        )
        result = error.to_dict()
        
        assert "error" in result
        assert result["error"]["code"] == "E1001"
        assert result["error"]["message"] == "Test error"
        assert result["error"]["details"]["field"] == "email"
        assert "correlation_id" in result
        assert "timestamp" in result
    
    def test_error_str_representation(self):
        """Test error string representation."""
        error = LLMHiveError("Test error", code=ErrorCode.TIMEOUT)
        error_str = str(error)
        assert "E1006" in error_str
        assert "Test error" in error_str


class TestProviderErrors:
    """Test provider-specific exceptions."""
    
    def test_provider_error(self):
        """Test basic provider error."""
        error = ProviderError("API failed", "openai", model="gpt-4")
        assert error.provider == "openai"
        assert error.model == "gpt-4"
        assert error.code == ErrorCode.PROVIDER_ERROR
    
    def test_provider_timeout_error(self):
        """Test provider timeout error."""
        error = ProviderTimeoutError("anthropic", timeout=30.0)
        assert "timed out" in error.message
        assert error.code == ErrorCode.PROVIDER_TIMEOUT
        assert error.details["timeout_seconds"] == 30.0
    
    def test_provider_rate_limit_error(self):
        """Test provider rate limit error."""
        error = ProviderRateLimitError("openai", retry_after=60.0)
        assert error.code == ErrorCode.PROVIDER_RATE_LIMITED
        assert error.retry_after == 60.0
    
    def test_all_providers_failed_error(self):
        """Test error when all providers fail."""
        providers = ["openai", "anthropic"]
        errors = [ValueError("API error"), TimeoutError("Timeout")]
        error = AllProvidersFailedError(providers, errors)
        
        assert error.code == ErrorCode.ALL_PROVIDERS_FAILED
        assert error.recoverable is False
        assert len(error.provider_errors) == 2


class TestCircuitOpenError:
    """Test circuit breaker errors."""
    
    def test_circuit_open_error(self):
        """Test circuit open error."""
        error = CircuitOpenError("openai", reset_time=45.0)
        assert error.code == ErrorCode.CIRCUIT_OPEN
        assert error.reset_time == 45.0
        assert error.recoverable is True


class TestCorrelationId:
    """Test correlation ID management."""
    
    def test_generate_correlation_id(self):
        """Test correlation ID generation."""
        cid = generate_correlation_id()
        assert len(cid) == 8
    
    def test_set_and_get_correlation_id(self):
        """Test setting and getting correlation ID."""
        set_correlation_id("test123")
        assert get_correlation_id() == "test123"
    
    def test_correlation_id_auto_generate(self):
        """Test auto-generation when not set."""
        set_correlation_id("")  # Clear
        cid = get_correlation_id()
        assert len(cid) == 8


class TestCircuitBreaker:
    """Test circuit breaker functionality."""
    
    @pytest.fixture
    def breaker(self):
        """Create a circuit breaker for testing."""
        return CircuitBreaker(
            failure_threshold=3,
            reset_timeout=1.0,  # Short timeout for testing
            half_open_max_calls=2,
        )
    
    @pytest.mark.asyncio
    async def test_initial_state_is_closed(self, breaker):
        """Test that circuit starts in closed state."""
        state = await breaker._check_state("test")
        assert state == CircuitState.CLOSED
    
    @pytest.mark.asyncio
    async def test_circuit_opens_after_failures(self, breaker):
        """Test that circuit opens after threshold failures."""
        for _ in range(3):
            await breaker.record_failure("test", Exception("fail"))
        
        state = await breaker._check_state("test")
        assert state == CircuitState.OPEN
    
    @pytest.mark.asyncio
    async def test_circuit_transitions_to_half_open(self, breaker):
        """Test that circuit transitions to half-open after timeout."""
        # Trip the circuit
        for _ in range(3):
            await breaker.record_failure("test", Exception("fail"))
        
        # Wait for reset timeout
        await asyncio.sleep(1.1)
        
        state = await breaker._check_state("test")
        assert state == CircuitState.HALF_OPEN
    
    @pytest.mark.asyncio
    async def test_circuit_closes_after_recovery(self, breaker):
        """Test that circuit closes after successful half-open calls."""
        # Trip the circuit
        for _ in range(3):
            await breaker.record_failure("test", Exception("fail"))
        
        # Wait for reset timeout
        await asyncio.sleep(1.1)
        
        # Simulate successful calls in half-open state
        await breaker._check_state("test")  # Transition to half-open
        await breaker.record_success("test")
        await breaker.record_success("test")
        
        state = await breaker._check_state("test")
        assert state == CircuitState.CLOSED
    
    @pytest.mark.asyncio
    async def test_circuit_reopens_on_half_open_failure(self, breaker):
        """Test that circuit reopens if failure in half-open state."""
        # Trip the circuit
        for _ in range(3):
            await breaker.record_failure("test", Exception("fail"))
        
        # Wait for reset timeout
        await asyncio.sleep(1.1)
        
        # Transition to half-open and fail
        await breaker._check_state("test")
        await breaker.record_failure("test", Exception("fail again"))
        
        state = await breaker._check_state("test")
        assert state == CircuitState.OPEN
    
    def test_get_stats(self, breaker):
        """Test getting circuit breaker stats."""
        stats = breaker.get_stats("test")
        assert "state" in stats
        assert "failures" in stats
        assert "successes" in stats


class TestBuildErrorResponse:
    """Test error response building."""
    
    def test_build_from_llmhive_error(self):
        """Test building response from LLMHive error."""
        error = LLMHiveError(
            "Test error",
            code=ErrorCode.VALIDATION_ERROR,
            details={"field": "email"},
        )
        response = build_error_response(error, request_id="req123")
        
        assert response.code == "E1001"
        assert response.message == "Test error"
        assert response.request_id == "req123"
    
    def test_build_from_generic_exception(self):
        """Test building response from generic exception."""
        error = ValueError("Something went wrong")
        response = build_error_response(error)
        
        assert response.code == "E1000"  # INTERNAL_ERROR
        assert "Something went wrong" in response.message
        assert "ValueError" in response.details.get("exception_type", "")


class TestWithErrorHandling:
    """Test error handling decorator."""
    
    @pytest.mark.asyncio
    async def test_successful_function(self):
        """Test decorator with successful function."""
        @with_error_handling
        async def success_func():
            return "success"
        
        result = await success_func()
        assert result == "success"
    
    @pytest.mark.asyncio
    async def test_function_raising_llmhive_error(self):
        """Test decorator with LLMHive error."""
        @with_error_handling
        async def error_func():
            raise ValidationError("Invalid input")
        
        with pytest.raises(ValidationError):
            await error_func()
    
    @pytest.mark.asyncio
    async def test_function_raising_generic_error(self):
        """Test decorator wraps generic errors."""
        @with_error_handling
        async def error_func():
            raise ValueError("Something broke")
        
        with pytest.raises(LLMHiveError) as exc_info:
            await error_func()
        
        assert exc_info.value.code == ErrorCode.INTERNAL_ERROR


class TestCallWithFallback:
    """Test provider fallback functionality."""
    
    @pytest.fixture
    def mock_providers(self):
        """Create mock providers."""
        success_provider = MagicMock()
        success_provider.generate = AsyncMock(return_value="success response")
        
        fail_provider = MagicMock()
        fail_provider.generate = AsyncMock(side_effect=Exception("API error"))
        
        return {
            "primary": fail_provider,
            "backup": success_provider,
        }
    
    @pytest.mark.asyncio
    async def test_fallback_to_backup_provider(self, mock_providers):
        """Test fallback when primary provider fails."""
        result = await call_with_fallback(
            mock_providers,
            "generate",
            "test prompt",
            preferred_providers=["primary", "backup"],
        )
        
        assert result == "success response"
        mock_providers["primary"].generate.assert_called_once()
        mock_providers["backup"].generate.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_all_providers_fail(self):
        """Test error when all providers fail."""
        fail_provider1 = MagicMock()
        fail_provider1.generate = AsyncMock(side_effect=Exception("Error 1"))
        
        fail_provider2 = MagicMock()
        fail_provider2.generate = AsyncMock(side_effect=Exception("Error 2"))
        
        providers = {"p1": fail_provider1, "p2": fail_provider2}
        
        with pytest.raises(AllProvidersFailedError):
            await call_with_fallback(providers, "generate", "test")
    
    @pytest.mark.asyncio
    async def test_skips_open_circuits(self):
        """Test that open circuits are skipped."""
        breaker = CircuitBreaker(failure_threshold=1)
        
        # Open the circuit for provider1
        await breaker.record_failure("p1", Exception("fail"))
        
        success_provider = MagicMock()
        success_provider.generate = AsyncMock(return_value="success")
        
        providers = {"p1": success_provider, "p2": success_provider}
        
        # With global breaker having p1 open, it should skip to p2
        with patch("llmhive.app.errors.get_circuit_breaker", return_value=breaker):
            result = await call_with_fallback(
                providers,
                "generate",
                "test",
                preferred_providers=["p1", "p2"],
            )
        
        assert result == "success"


class TestOrchestrationError:
    """Test orchestration-specific errors."""
    
    def test_orchestration_error_with_stage(self):
        """Test orchestration error with stage info."""
        error = OrchestrationError(
            "Planning failed",
            stage="hrm_planning",
            code=ErrorCode.PLANNING_FAILED,
        )
        
        assert error.stage == "hrm_planning"
        assert error.details["stage"] == "hrm_planning"
        assert error.code == ErrorCode.PLANNING_FAILED


class TestValidationError:
    """Test validation errors."""
    
    def test_validation_error_with_field(self):
        """Test validation error with field info."""
        error = ValidationError("Invalid email format", field="email")
        
        assert error.code == ErrorCode.VALIDATION_ERROR
        assert error.details["field"] == "email"


class TestContentPolicyError:
    """Test content policy errors."""
    
    def test_content_policy_error_not_recoverable(self):
        """Test content policy error is not recoverable."""
        error = ContentPolicyError("Content violates policy")
        
        assert error.code == ErrorCode.CONTENT_POLICY_VIOLATION
        assert error.recoverable is False
