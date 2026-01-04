"""Comprehensive tests for Stage 4 Hardening module.

Tests cover:
- Circuit breaker behavior
- Retry with backoff
- Request budget limits
- Trial counter persistence
- Structured logging safety
- Learned weights bounds
- Timeouts and fallbacks
"""
import asyncio
import os
import tempfile
import time
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ==============================================================================
# CIRCUIT BREAKER TESTS
# ==============================================================================

class TestCircuitBreaker:
    """Tests for circuit breaker behavior."""
    
    def test_initial_state_is_closed(self):
        """Circuit starts in closed state."""
        from llmhive.app.orchestration.stage4_hardening import CircuitBreaker
        
        cb = CircuitBreaker(name="test", failure_threshold=3)
        assert cb.state.value == "closed"
        assert cb.allow_request()
    
    def test_opens_after_threshold_failures(self):
        """Circuit opens after failure threshold is reached."""
        from llmhive.app.orchestration.stage4_hardening import CircuitBreaker, CircuitState
        
        cb = CircuitBreaker(name="test", failure_threshold=3)
        
        # Record failures
        for _ in range(3):
            cb.record_failure()
        
        assert cb.state == CircuitState.OPEN
        assert not cb.allow_request()
    
    def test_resets_on_success(self):
        """Failure count resets on success."""
        from llmhive.app.orchestration.stage4_hardening import CircuitBreaker, CircuitState
        
        cb = CircuitBreaker(name="test", failure_threshold=3)
        
        # Record 2 failures
        cb.record_failure()
        cb.record_failure()
        
        # Success resets count
        cb.record_success()
        
        # 2 more failures shouldn't open (count reset)
        cb.record_failure()
        cb.record_failure()
        
        assert cb.state == CircuitState.CLOSED
    
    def test_transitions_to_half_open(self):
        """Circuit transitions to half-open after recovery timeout."""
        from llmhive.app.orchestration.stage4_hardening import CircuitBreaker, CircuitState
        
        cb = CircuitBreaker(name="test", failure_threshold=2, recovery_timeout=0.1)
        
        # Open the circuit
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.OPEN
        
        # Wait for recovery
        time.sleep(0.15)
        
        # Should transition to half-open
        assert cb.state == CircuitState.HALF_OPEN
        assert cb.allow_request()  # Allows limited requests
    
    def test_closes_after_successful_half_open_calls(self):
        """Circuit closes after successful calls in half-open state."""
        from llmhive.app.orchestration.stage4_hardening import CircuitBreaker, CircuitState
        
        cb = CircuitBreaker(
            name="test", 
            failure_threshold=2, 
            recovery_timeout=0.01,
            half_open_max_calls=2
        )
        
        # Open and wait
        cb.record_failure()
        cb.record_failure()
        time.sleep(0.02)
        
        # Half-open
        assert cb.state == CircuitState.HALF_OPEN
        
        # Successful calls
        cb.record_success()
        cb.record_success()
        
        assert cb.state == CircuitState.CLOSED


class TestCircuitBreakerRegistry:
    """Tests for circuit breaker registry."""
    
    def test_singleton_instance(self):
        """Registry is a singleton."""
        from llmhive.app.orchestration.stage4_hardening import CircuitBreakerRegistry
        
        r1 = CircuitBreakerRegistry.get_instance()
        r2 = CircuitBreakerRegistry.get_instance()
        
        assert r1 is r2
    
    def test_creates_breaker_on_demand(self):
        """Creates circuit breaker on first access."""
        from llmhive.app.orchestration.stage4_hardening import CircuitBreakerRegistry
        
        registry = CircuitBreakerRegistry.get_instance()
        
        cb1 = registry.get("service_a")
        cb2 = registry.get("service_a")
        cb3 = registry.get("service_b")
        
        assert cb1 is cb2  # Same breaker
        assert cb1 is not cb3  # Different services


# ==============================================================================
# RETRY WITH BACKOFF TESTS
# ==============================================================================

class TestRetryWithBackoff:
    """Tests for retry with exponential backoff."""
    
    @pytest.mark.asyncio
    async def test_returns_on_first_success(self):
        """Returns immediately on first successful call."""
        from llmhive.app.orchestration.stage4_hardening import retry_with_backoff
        
        call_count = 0
        
        async def succeeds():
            nonlocal call_count
            call_count += 1
            return "success"
        
        result = await retry_with_backoff(succeeds, max_retries=3)
        
        assert result == "success"
        assert call_count == 1
    
    @pytest.mark.asyncio
    async def test_retries_on_failure(self):
        """Retries on transient failures."""
        from llmhive.app.orchestration.stage4_hardening import retry_with_backoff
        
        call_count = 0
        
        async def fails_twice_then_succeeds():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Transient error")
            return "success"
        
        result = await retry_with_backoff(
            fails_twice_then_succeeds,
            max_retries=3,
            base_delay=0.01,
        )
        
        assert result == "success"
        assert call_count == 3
    
    @pytest.mark.asyncio
    async def test_raises_after_all_retries_exhausted(self):
        """Raises RetryError after all retries are exhausted."""
        from llmhive.app.orchestration.stage4_hardening import (
            retry_with_backoff,
            RetryError,
        )
        
        async def always_fails():
            raise ValueError("Always fails")
        
        with pytest.raises(RetryError) as exc_info:
            await retry_with_backoff(
                always_fails,
                max_retries=2,
                base_delay=0.01,
            )
        
        assert "2 retries exhausted" in str(exc_info.value)
        assert exc_info.value.last_exception is not None
    
    @pytest.mark.asyncio
    async def test_respects_circuit_breaker(self):
        """Fails fast when circuit breaker is open."""
        from llmhive.app.orchestration.stage4_hardening import (
            retry_with_backoff,
            RetryError,
            CircuitBreaker,
        )
        
        cb = CircuitBreaker(name="test", failure_threshold=1)
        cb.record_failure()  # Open the circuit
        
        async def should_not_be_called():
            raise AssertionError("Should not be called")
        
        with pytest.raises(RetryError) as exc_info:
            await retry_with_backoff(
                should_not_be_called,
                circuit_breaker=cb,
            )
        
        assert "is open" in str(exc_info.value)


# ==============================================================================
# REQUEST BUDGET TESTS
# ==============================================================================

class TestRequestBudget:
    """Tests for request budget (anti-infinite-loop)."""
    
    def test_allows_within_limits(self):
        """Allows operations within budget."""
        from llmhive.app.orchestration.stage4_hardening import RequestBudget
        
        budget = RequestBudget(
            request_id="test",
            max_iterations=10,
            max_tool_calls=50,
            max_tokens=1000,
            max_wall_clock=60.0,
        )
        
        assert budget.check_and_consume(iterations=1, tool_calls=5, tokens=100)
        assert budget.check_and_consume(iterations=1, tool_calls=5, tokens=100)
        assert not budget.is_exhausted
    
    def test_exhausts_on_iteration_limit(self):
        """Exhausts budget when iteration limit is exceeded."""
        from llmhive.app.orchestration.stage4_hardening import RequestBudget
        
        budget = RequestBudget(
            request_id="test",
            max_iterations=3,
            max_tool_calls=100,
            max_tokens=10000,
            max_wall_clock=60.0,
        )
        
        assert budget.check_and_consume(iterations=3)
        assert not budget.check_and_consume(iterations=1)
        assert budget.is_exhausted
        assert "iterations" in budget.exhausted_reason.lower()
    
    def test_exhausts_on_tool_call_limit(self):
        """Exhausts budget when tool call limit is exceeded."""
        from llmhive.app.orchestration.stage4_hardening import RequestBudget
        
        budget = RequestBudget(
            request_id="test",
            max_iterations=100,
            max_tool_calls=5,
            max_tokens=10000,
            max_wall_clock=60.0,
        )
        
        assert budget.check_and_consume(tool_calls=5)
        assert not budget.check_and_consume(tool_calls=1)
        assert budget.is_exhausted
    
    def test_exhausts_on_token_limit(self):
        """Exhausts budget when token limit is exceeded."""
        from llmhive.app.orchestration.stage4_hardening import RequestBudget
        
        budget = RequestBudget(
            request_id="test",
            max_iterations=100,
            max_tool_calls=100,
            max_tokens=100,
            max_wall_clock=60.0,
        )
        
        assert budget.check_and_consume(tokens=100)
        assert not budget.check_and_consume(tokens=1)
        assert budget.is_exhausted
    
    def test_exhausts_on_wall_clock(self):
        """Exhausts budget when wall clock limit is exceeded."""
        from llmhive.app.orchestration.stage4_hardening import RequestBudget
        
        budget = RequestBudget(
            request_id="test",
            max_iterations=100,
            max_tool_calls=100,
            max_tokens=10000,
            max_wall_clock=0.05,  # 50ms
        )
        
        time.sleep(0.06)
        
        assert not budget.check_and_consume(iterations=1)
        assert budget.is_exhausted
        assert "clock" in budget.exhausted_reason.lower()
    
    def test_usage_summary(self):
        """Usage summary includes all metrics."""
        from llmhive.app.orchestration.stage4_hardening import RequestBudget
        
        budget = RequestBudget(
            request_id="test123",
            max_iterations=10,
            max_tool_calls=50,
            max_tokens=1000,
            max_wall_clock=60.0,
        )
        
        budget.check_and_consume(iterations=2, tool_calls=5, tokens=100)
        
        summary = budget.get_usage_summary()
        
        assert summary["request_id"] == "test123"[:8]
        assert "2/10" in summary["iterations"]
        assert "5/50" in summary["tool_calls"]
        assert "100/1000" in summary["tokens"]


# ==============================================================================
# TRIAL COUNTER TESTS
# ==============================================================================

class TestPersistentTrialCounter:
    """Tests for persistent trial counter."""
    
    def test_starts_at_zero(self):
        """Usage starts at zero for new users."""
        from llmhive.app.orchestration.stage4_hardening import PersistentTrialCounter
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as f:
            path = f.name
        
        try:
            counter = PersistentTrialCounter(persistence_path=path)
            
            usage = counter.get_usage("new_user", "image_analysis")
            assert usage == 0
        finally:
            os.unlink(path)
    
    def test_increments_usage(self):
        """Increments and persists usage."""
        from llmhive.app.orchestration.stage4_hardening import PersistentTrialCounter
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as f:
            path = f.name
        
        try:
            counter = PersistentTrialCounter(persistence_path=path)
            
            counter.increment("user_1", "image")
            counter.increment("user_1", "image")
            counter.increment("user_1", "audio")
            
            assert counter.get_usage("user_1", "image") == 2
            assert counter.get_usage("user_1", "audio") == 1
            
            # New instance should load persisted data
            counter2 = PersistentTrialCounter(persistence_path=path)
            assert counter2.get_usage("user_1", "image") == 2
        finally:
            os.unlink(path)
    
    def test_check_and_consume_blocks_at_limit(self):
        """Blocks usage at trial limit."""
        from llmhive.app.orchestration.stage4_hardening import PersistentTrialCounter
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as f:
            path = f.name
        
        try:
            counter = PersistentTrialCounter(persistence_path=path)
            
            # Allow 3 trials
            allowed1, remaining1 = counter.check_and_consume("user_1", "image", 3)
            allowed2, remaining2 = counter.check_and_consume("user_1", "image", 3)
            allowed3, remaining3 = counter.check_and_consume("user_1", "image", 3)
            
            assert allowed1 and remaining1 == 2
            assert allowed2 and remaining2 == 1
            assert allowed3 and remaining3 == 0
            
            # 4th should be blocked
            allowed4, remaining4 = counter.check_and_consume("user_1", "image", 3)
            assert not allowed4
            assert remaining4 == 0
        finally:
            os.unlink(path)


# ==============================================================================
# LOGGING SAFETY TESTS
# ==============================================================================

class TestSanitizeForLogging:
    """Tests for log sanitization."""
    
    def test_redacts_api_keys(self):
        """Redacts various API key formats."""
        from llmhive.app.orchestration.stage4_hardening import sanitize_for_logging
        
        text = "Using api_key=sk_live_abc123xyz and token=secret123"
        sanitized = sanitize_for_logging(text)
        
        assert "sk_live" not in sanitized
        assert "secret123" not in sanitized
        assert "[REDACTED]" in sanitized or "[STRIPE_KEY]" in sanitized
    
    def test_redacts_bearer_tokens(self):
        """Redacts Bearer tokens."""
        from llmhive.app.orchestration.stage4_hardening import sanitize_for_logging
        
        text = "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
        sanitized = sanitize_for_logging(text)
        
        assert "eyJ" not in sanitized
        assert "[TOKEN]" in sanitized
    
    def test_redacts_emails(self):
        """Redacts email addresses."""
        from llmhive.app.orchestration.stage4_hardening import sanitize_for_logging
        
        text = "User email is john.doe@example.com"
        sanitized = sanitize_for_logging(text)
        
        assert "john.doe" not in sanitized
        assert "@example.com" not in sanitized
        assert "[EMAIL]" in sanitized
    
    def test_truncates_long_text(self):
        """Truncates text to max length."""
        from llmhive.app.orchestration.stage4_hardening import sanitize_for_logging
        
        text = "A" * 200
        sanitized = sanitize_for_logging(text, max_length=50)
        
        assert len(sanitized) <= 53  # 50 + "..."
        assert sanitized.endswith("...")


class TestHashUserId:
    """Tests for user ID hashing."""
    
    def test_produces_consistent_hash(self):
        """Same input produces same hash."""
        from llmhive.app.orchestration.stage4_hardening import hash_user_id
        
        hash1 = hash_user_id("user_123")
        hash2 = hash_user_id("user_123")
        
        assert hash1 == hash2
    
    def test_produces_different_hashes(self):
        """Different inputs produce different hashes."""
        from llmhive.app.orchestration.stage4_hardening import hash_user_id
        
        hash1 = hash_user_id("user_123")
        hash2 = hash_user_id("user_456")
        
        assert hash1 != hash2
    
    def test_hash_is_not_reversible(self):
        """Hash doesn't contain original ID."""
        from llmhive.app.orchestration.stage4_hardening import hash_user_id
        
        user_id = "secret_user_12345"
        hashed = hash_user_id(user_id)
        
        assert user_id not in hashed
        assert "12345" not in hashed


# ==============================================================================
# LEARNED WEIGHTS TESTS
# ==============================================================================

class TestBoundedModelWeight:
    """Tests for bounded model weights."""
    
    def test_initial_weight_is_one(self):
        """Weight starts at 1.0."""
        from llmhive.app.orchestration.stage4_hardening import BoundedModelWeight
        
        weight = BoundedModelWeight(model_id="gpt-4")
        assert weight.weight == 1.0
    
    def test_weight_increases_on_success(self):
        """Weight increases on success after min samples."""
        from llmhive.app.orchestration.stage4_hardening import BoundedModelWeight
        
        weight = BoundedModelWeight(
            model_id="gpt-4",
            learning_rate=0.1,
        )
        
        # Build up samples
        for _ in range(10):
            weight.update(success=True, min_samples=10)
        
        # Now weight should increase
        new_weight = weight.update(success=True, min_samples=10)
        
        assert new_weight > 1.0
    
    def test_weight_decreases_on_failure(self):
        """Weight decreases on failure after min samples."""
        from llmhive.app.orchestration.stage4_hardening import BoundedModelWeight
        
        weight = BoundedModelWeight(
            model_id="gpt-4",
            learning_rate=0.1,
        )
        
        # Build up samples
        for _ in range(10):
            weight.update(success=True, min_samples=10)
        
        # Failure should decrease
        new_weight = weight.update(success=False, min_samples=10)
        
        assert new_weight < 1.0 + 0.1  # Less than if it was success
    
    def test_weight_respects_bounds(self):
        """Weight stays within min/max bounds."""
        from llmhive.app.orchestration.stage4_hardening import BoundedModelWeight
        
        weight = BoundedModelWeight(
            model_id="test",
            min_weight=0.5,
            max_weight=2.0,
            learning_rate=0.5,  # Large rate for quick testing
        )
        
        # Many failures
        for _ in range(100):
            weight.update(success=False, min_samples=1)
        
        assert weight.weight >= 0.5
        
        # Many successes
        for _ in range(100):
            weight.update(success=True, min_samples=1)
        
        assert weight.weight <= 2.0
    
    def test_reset_reverts_weight(self):
        """Reset reverts weight and increments version."""
        from llmhive.app.orchestration.stage4_hardening import BoundedModelWeight
        
        weight = BoundedModelWeight(model_id="test")
        initial_version = weight.version
        
        # Modify
        for _ in range(20):
            weight.update(success=True, min_samples=5)
        
        assert weight.weight != 1.0
        
        # Reset
        weight.reset()
        
        assert weight.weight == 1.0
        assert weight.version == initial_version + 1
        assert weight.sample_count == 0


class TestShadowModeWeightManager:
    """Tests for shadow mode weight manager."""
    
    def test_shadow_mode_does_not_apply_updates(self):
        """In shadow mode, updates are logged but not applied."""
        from llmhive.app.orchestration.stage4_hardening import ShadowModeWeightManager
        
        manager = ShadowModeWeightManager(shadow_mode=True)
        
        initial = manager.get_weight("model_a")
        
        # Update in shadow mode
        for _ in range(20):
            manager.update("model_a", success=True)
        
        # Weight should not change
        assert manager.get_weight("model_a") == initial
        
        # But shadow log should have entries
        log = manager.get_shadow_log()
        assert len(log) == 20
    
    def test_production_mode_applies_updates(self):
        """In production mode, updates are applied."""
        from llmhive.app.orchestration.stage4_hardening import ShadowModeWeightManager
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as f:
            path = f.name
        
        try:
            manager = ShadowModeWeightManager(
                shadow_mode=False,
                persistence_path=path,
            )
            
            initial = manager.get_weight("model_a")
            
            # Many updates
            for _ in range(15):
                manager.update("model_a", success=True)
            
            # Weight should change (after min_samples)
            final = manager.get_weight("model_a")
            assert final != initial
        finally:
            os.unlink(path)


# ==============================================================================
# SUMMARY PROVENANCE TESTS
# ==============================================================================

class TestSummaryProvenance:
    """Tests for summary provenance tracking."""
    
    def test_serialization_roundtrip(self):
        """Provenance can be serialized and deserialized."""
        from llmhive.app.orchestration.stage4_hardening import SummaryProvenance
        
        original = SummaryProvenance(
            original_entry_ids=["entry_1", "entry_2", "entry_3"],
            summary_date=datetime.now(timezone.utc),
            summary_method="llm",
            confidence=0.85,
        )
        
        data = original.to_dict()
        restored = SummaryProvenance.from_dict(data)
        
        assert restored.original_entry_ids == original.original_entry_ids
        assert restored.summary_method == original.summary_method
        assert restored.is_derived == True
        assert abs(restored.confidence - original.confidence) < 0.001
    
    def test_is_derived_flag(self):
        """Summaries are marked as derived by default."""
        from llmhive.app.orchestration.stage4_hardening import SummaryProvenance
        
        prov = SummaryProvenance(
            original_entry_ids=["e1"],
            summary_date=datetime.now(timezone.utc),
            summary_method="extractive",
        )
        
        assert prov.is_derived == True


# ==============================================================================
# SAFE EXTERNAL CALL TESTS
# ==============================================================================

class TestSafeExternalCall:
    """Tests for safe external call wrapper."""
    
    @pytest.mark.asyncio
    async def test_records_success(self):
        """Records success when call completes."""
        from llmhive.app.orchestration.stage4_hardening import (
            safe_external_call,
            CircuitBreakerRegistry,
        )
        
        registry = CircuitBreakerRegistry.get_instance()
        
        async with safe_external_call("test_service") as ctx:
            # Simulate successful call
            await asyncio.sleep(0.01)
            ctx.record_success()
        
        # Circuit should remain closed
        breaker = registry.get("test_service")
        assert breaker.state.value == "closed"
    
    @pytest.mark.asyncio
    async def test_records_failure_on_exception(self):
        """Records failure when exception occurs."""
        from llmhive.app.orchestration.stage4_hardening import (
            safe_external_call,
            CircuitBreakerRegistry,
        )
        
        try:
            async with safe_external_call("failing_service") as ctx:
                raise ValueError("API error")
        except ValueError:
            pass
        
        # Should have recorded failure
        registry = CircuitBreakerRegistry.get_instance()
        breaker = registry.get("failing_service")
        assert breaker._failure_count >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

