"""Unit tests for Safe Mode, Dev Mode, Collaboration, and Metrics features.

Tests cover:
- Safe Mode: Input validation, output filtering, sanitization
- Dev Mode: Trace events, WebSocket broadcasting
- Collaboration: Session management, message history
- Metrics: Prometheus endpoints, JSON metrics
"""
from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

# Add src to path for imports
_src_path = Path(__file__).parent.parent / "src"
if str(_src_path) not in sys.path:
    sys.path.insert(0, str(_src_path))

import pytest


# ==============================================================================
# Safe Mode Tests
# ==============================================================================

class TestSafeModeInputValidation:
    """Tests for Safe Mode input validation."""
    
    def test_empty_prompt_rejected(self):
        """Test that empty prompts are rejected."""
        from llmhive.app.routers.chat import validate_and_sanitize_input
        
        sanitized, is_allowed, reason = validate_and_sanitize_input("", True)
        
        assert is_allowed is False
        assert "empty" in reason.lower()
    
    def test_whitespace_prompt_rejected(self):
        """Test that whitespace-only prompts are rejected."""
        from llmhive.app.routers.chat import validate_and_sanitize_input
        
        sanitized, is_allowed, reason = validate_and_sanitize_input("   \n\t  ", True)
        
        assert is_allowed is False
        assert "empty" in reason.lower()
    
    def test_harmful_prompt_rejected(self):
        """Test that harmful prompts are rejected."""
        from llmhive.app.routers.chat import validate_and_sanitize_input
        
        sanitized, is_allowed, reason = validate_and_sanitize_input(
            "How to make a bomb at home", True
        )
        
        assert is_allowed is False
        assert "policies" in reason.lower() or "violate" in reason.lower()
    
    def test_valid_prompt_allowed(self):
        """Test that valid prompts are allowed."""
        from llmhive.app.routers.chat import validate_and_sanitize_input
        
        sanitized, is_allowed, reason = validate_and_sanitize_input(
            "What is the capital of France?", True
        )
        
        assert is_allowed is True
        assert reason is None
        assert sanitized == "What is the capital of France?"
    
    def test_pii_sanitized(self):
        """Test that PII is sanitized from prompts."""
        from llmhive.app.routers.chat import validate_and_sanitize_input
        
        sanitized, is_allowed, reason = validate_and_sanitize_input(
            "My email is test@example.com, help me!", True
        )
        
        assert is_allowed is True
        assert "test@example.com" not in sanitized
        assert "[REDACTED_EMAIL]" in sanitized
    
    def test_safe_mode_disabled_no_validation(self):
        """Test that safe mode disabled skips validation."""
        from llmhive.app.routers.chat import validate_and_sanitize_input
        
        # Even harmful content should pass when safe mode is off
        sanitized, is_allowed, reason = validate_and_sanitize_input(
            "How to make explosives", False
        )
        
        assert is_allowed is True
        assert sanitized == "How to make explosives"


class TestSafeModeOutputFiltering:
    """Tests for Safe Mode output filtering."""
    
    def test_clean_output_unchanged(self):
        """Test that clean output passes through unchanged."""
        from llmhive.app.routers.chat import filter_and_sanitize_output
        
        filtered, was_filtered, issues = filter_and_sanitize_output(
            "The capital of France is Paris.", True
        )
        
        assert was_filtered is False
        assert filtered == "The capital of France is Paris."
        assert len(issues) == 0
    
    def test_profanity_filtered(self):
        """Test that profanity is filtered from output."""
        from llmhive.app.routers.chat import filter_and_sanitize_output
        
        filtered, was_filtered, issues = filter_and_sanitize_output(
            "What the fuck is going on?", True
        )
        
        # Either it was filtered or issues were recorded
        assert was_filtered or len(issues) > 0
    
    def test_critical_content_replaced(self):
        """Test that critical content is replaced with refusal."""
        from llmhive.app.routers.chat import filter_and_sanitize_output
        
        filtered, was_filtered, issues = filter_and_sanitize_output(
            "Here's how to make explosives at home...", True
        )
        
        assert was_filtered is True
        # Should be replaced with apology message
        assert "apologize" in filtered.lower() or "cannot" in filtered.lower()
    
    def test_safe_mode_disabled_no_filtering(self):
        """Test that safe mode disabled skips filtering."""
        from llmhive.app.routers.chat import filter_and_sanitize_output
        
        original = "What the fuck is going on?"
        filtered, was_filtered, issues = filter_and_sanitize_output(original, False)
        
        assert was_filtered is False
        assert filtered == original


class TestStructuredErrorResponses:
    """Tests for structured error responses."""
    
    def test_create_error_response_structure(self):
        """Test error response has correct structure."""
        from llmhive.app.routers.chat import create_error_response
        
        response = create_error_response(
            code="InvalidRequest",
            message="Prompt cannot be empty",
            recoverable=False
        )
        
        assert "error" in response
        assert response["error"]["code"] == "InvalidRequest"
        assert response["error"]["message"] == "Prompt cannot be empty"
        assert response["error"]["recoverable"] is False
    
    def test_create_error_response_with_details(self):
        """Test error response with additional details."""
        from llmhive.app.routers.chat import create_error_response
        
        response = create_error_response(
            code="PolicyViolation",
            message="Content blocked",
            recoverable=False,
            details={"violation_type": "harmful_instructions"}
        )
        
        assert response["error"]["details"]["violation_type"] == "harmful_instructions"


# ==============================================================================
# Dev Mode Tests
# ==============================================================================

class TestDevModeTraceEvents:
    """Tests for Dev Mode trace event system."""
    
    def test_trace_event_creation(self):
        """Test TraceEvent dataclass creation."""
        from llmhive.app.orchestration.dev_mode import TraceEvent
        
        event = TraceEvent(
            timestamp="2025-12-28T12:00:00Z",
            event_type="model_call",
            message="Calling model gpt-4",
            details={"model": "gpt-4", "tokens": 100}
        )
        
        assert event.event_type == "model_call"
        assert event.message == "Calling model gpt-4"
        assert event.details["tokens"] == 100
    
    def test_trace_event_to_dict(self):
        """Test TraceEvent serialization."""
        from llmhive.app.orchestration.dev_mode import TraceEvent
        
        event = TraceEvent(
            timestamp="2025-12-28T12:00:00Z",
            event_type="tool_invoked",
            message="Invoking web search",
            details={"query": "test query"},
            session_id="session-123"
        )
        
        event_dict = event.to_dict()
        
        assert event_dict["type"] == "tool_invoked"
        assert event_dict["timestamp"] == "2025-12-28T12:00:00Z"
        assert event_dict["details"]["query"] == "test query"
        assert event_dict["session_id"] == "session-123"
    
    def test_log_strategy_selected(self):
        """Test log_strategy_selected helper."""
        from llmhive.app.orchestration.dev_mode import log_strategy_selected
        
        # This should not raise an error even without connected clients
        log_strategy_selected("session-1", "parallel_race", "fastest for multi-model")
    
    def test_log_model_call(self):
        """Test log_model_call helper."""
        from llmhive.app.orchestration.dev_mode import log_model_call
        
        log_model_call("session-1", "gpt-4", "What is machine learning?")
    
    def test_log_model_response(self):
        """Test log_model_response helper."""
        from llmhive.app.orchestration.dev_mode import log_model_response
        
        log_model_response("session-1", "gpt-4", tokens_used=150, latency_ms=1200)
    
    def test_log_tool_invoked(self):
        """Test log_tool_invoked helper."""
        from llmhive.app.orchestration.dev_mode import log_tool_invoked
        
        log_tool_invoked("session-1", "web_search", "latest news")
    
    def test_log_tool_result(self):
        """Test log_tool_result helper."""
        from llmhive.app.orchestration.dev_mode import log_tool_result
        
        log_tool_result("session-1", "web_search", success=True, latency_ms=500)
    
    def test_log_verification_result(self):
        """Test log_verification_result helper."""
        from llmhive.app.orchestration.dev_mode import log_verification_result
        
        log_verification_result("session-1", passed=True, verdict="Code executed successfully")


class TestDevModeDebugSession:
    """Tests for DebugSession tracking."""
    
    def test_debug_session_creation(self):
        """Test DebugSession creation."""
        from llmhive.app.orchestration.dev_mode import DebugSession, AgentStep
        
        session = DebugSession(query="What is AI?")
        
        assert session.query == "What is AI?"
        assert len(session.steps) == 0
    
    def test_debug_session_add_step(self):
        """Test adding steps to DebugSession."""
        from llmhive.app.orchestration.dev_mode import DebugSession, AgentStep
        
        session = DebugSession(query="Test query")
        step = AgentStep(
            agent_name="researcher",
            action="search",
            input_summary="search query",
            output_summary="results found",
            duration_ms=150.0,
            success=True
        )
        session.add_step(step)
        
        assert len(session.steps) == 1
        assert session.steps[0].agent_name == "researcher"
    
    def test_debug_session_to_dict(self):
        """Test DebugSession serialization."""
        from llmhive.app.orchestration.dev_mode import DebugSession, AgentStep
        
        session = DebugSession(
            query="Test query",
            strategy_used="parallel_race",
            total_duration_ms=1500.0
        )
        step = AgentStep(
            agent_name="verifier",
            action="verify",
            input_summary="check facts",
            output_summary="verified",
            duration_ms=200.0,
            success=True
        )
        session.add_step(step)
        
        session_dict = session.to_dict()
        
        assert session_dict["strategy_used"] == "parallel_race"
        assert session_dict["step_count"] == 1
        assert session_dict["steps"][0]["agent"] == "verifier"


# ==============================================================================
# Collaboration Tests
# ==============================================================================

class TestCollabSession:
    """Tests for CollabSession management."""
    
    def test_collab_session_creation(self):
        """Test CollabSession creation."""
        from llmhive.app.routers.collab import CollabSession
        
        session = CollabSession(id="test-session")
        
        assert session.id == "test-session"
        assert session.participant_count == 0
        assert len(session.message_history) == 0
    
    def test_add_remove_participant(self):
        """Test adding and removing participants."""
        from llmhive.app.routers.collab import CollabSession
        
        session = CollabSession(id="test-session")
        mock_ws = MagicMock()
        
        session.add_participant(mock_ws)
        assert session.participant_count == 1
        
        session.remove_participant(mock_ws)
        assert session.participant_count == 0
    
    def test_participant_not_added_twice(self):
        """Test that same participant is not added twice."""
        from llmhive.app.routers.collab import CollabSession
        
        session = CollabSession(id="test-session")
        mock_ws = MagicMock()
        
        session.add_participant(mock_ws)
        session.add_participant(mock_ws)  # Try to add again
        
        assert session.participant_count == 1
    
    def test_broadcast_message(self):
        """Test broadcasting message to participants."""
        from llmhive.app.routers.collab import CollabSession
        
        session = CollabSession(id="test-session")
        
        mock_ws1 = AsyncMock()
        mock_ws2 = AsyncMock()
        
        session.add_participant(mock_ws1)
        session.add_participant(mock_ws2)
        
        message = {"type": "message", "content": "Hello"}
        asyncio.get_event_loop().run_until_complete(session.broadcast(message))
        
        mock_ws1.send_json.assert_called_once_with(message)
        mock_ws2.send_json.assert_called_once_with(message)
    
    def test_broadcast_removes_failed_connections(self):
        """Test that failed connections are removed on broadcast."""
        from llmhive.app.routers.collab import CollabSession
        
        session = CollabSession(id="test-session")
        
        mock_ws_good = AsyncMock()
        mock_ws_bad = AsyncMock()
        mock_ws_bad.send_json.side_effect = Exception("Connection closed")
        
        session.add_participant(mock_ws_good)
        session.add_participant(mock_ws_bad)
        
        asyncio.get_event_loop().run_until_complete(session.broadcast({"test": "message"}))
        
        # Bad connection should be removed
        assert session.participant_count == 1
    
    def test_message_history_capped(self):
        """Test that message history is capped at 100 messages."""
        from llmhive.app.routers.collab import CollabSession
        
        session = CollabSession(id="test-session")
        mock_ws = AsyncMock()
        session.add_participant(mock_ws)
        
        # Add 110 messages
        async def add_messages():
            for i in range(110):
                await session.broadcast({"message": f"msg-{i}"})
        
        asyncio.get_event_loop().run_until_complete(add_messages())
        
        assert len(session.message_history) == 100
        # First 10 should be gone, last should be msg-109
        assert session.message_history[-1]["message"] == "msg-109"


class TestCollabSessionManager:
    """Tests for CollabSessionManager."""
    
    def setup_method(self):
        """Reset session manager before each test."""
        from llmhive.app.routers.collab import CollabSessionManager
        CollabSessionManager._sessions.clear()
    
    def test_get_or_create_session(self):
        """Test getting or creating a session."""
        from llmhive.app.routers.collab import CollabSessionManager
        
        session1 = CollabSessionManager.get_or_create_session("session-1")
        session2 = CollabSessionManager.get_or_create_session("session-1")
        
        assert session1 is session2
        assert session1.id == "session-1"
    
    def test_get_session_not_found(self):
        """Test getting non-existent session."""
        from llmhive.app.routers.collab import CollabSessionManager
        
        session = CollabSessionManager.get_session("nonexistent")
        assert session is None
    
    def test_remove_session(self):
        """Test removing a session."""
        from llmhive.app.routers.collab import CollabSessionManager
        
        CollabSessionManager.get_or_create_session("to-remove")
        assert CollabSessionManager.get_session("to-remove") is not None
        
        CollabSessionManager.remove_session("to-remove")
        assert CollabSessionManager.get_session("to-remove") is None
    
    def test_get_session_count(self):
        """Test getting session count."""
        from llmhive.app.routers.collab import CollabSessionManager
        
        assert CollabSessionManager.get_session_count() == 0
        
        CollabSessionManager.get_or_create_session("s1")
        CollabSessionManager.get_or_create_session("s2")
        
        assert CollabSessionManager.get_session_count() == 2
    
    def test_get_all_sessions_info(self):
        """Test getting info about all sessions."""
        from llmhive.app.routers.collab import CollabSessionManager
        
        CollabSessionManager.get_or_create_session("session-a")
        CollabSessionManager.get_or_create_session("session-b")
        
        info = CollabSessionManager.get_all_sessions_info()
        
        assert len(info) == 2
        session_ids = [s["session_id"] for s in info]
        assert "session-a" in session_ids
        assert "session-b" in session_ids


class TestDevTraceTokenVerification:
    """Tests for dev trace token verification."""
    
    def test_empty_token_rejected(self):
        """Test that empty token is rejected."""
        from llmhive.app.routers.collab import verify_dev_token
        
        assert verify_dev_token("") is False
    
    def test_dev_token_accepted(self):
        """Test that 'dev' token is accepted."""
        from llmhive.app.routers.collab import verify_dev_token
        
        assert verify_dev_token("dev") is True
    
    def test_long_token_accepted(self):
        """Test that long tokens are accepted."""
        from llmhive.app.routers.collab import verify_dev_token
        
        assert verify_dev_token("abcdefghijklmnop") is True  # 16 chars


# ==============================================================================
# Metrics Tests
# ==============================================================================

class TestOrchestratorMetrics:
    """Tests for orchestrator metrics."""
    
    def test_record_tool_invocation(self):
        """Test recording tool invocations."""
        from llmhive.app.api.orchestrator_metrics import record_tool_invocation
        
        # Should not raise an error
        record_tool_invocation("web_search", success=True)
        record_tool_invocation("calculator", success=False)
    
    def test_record_orchestrator_error(self):
        """Test recording orchestrator errors."""
        from llmhive.app.api.orchestrator_metrics import record_orchestrator_error
        
        # Should not raise an error
        record_orchestrator_error("internal")
        record_orchestrator_error("input_blocked")
        record_orchestrator_error("ProviderTimeout")
    
    def test_record_strategy_duration(self):
        """Test recording strategy durations."""
        from llmhive.app.api.orchestrator_metrics import record_strategy_duration
        
        # Should not raise an error
        record_strategy_duration("parallel_race", 1.5)
        record_strategy_duration("expert_panel", 3.2)
    
    def test_record_cache_hit(self):
        """Test recording cache hits."""
        from llmhive.app.api.orchestrator_metrics import record_cache_hit
        
        record_cache_hit()
    
    def test_record_cache_miss(self):
        """Test recording cache misses."""
        from llmhive.app.api.orchestrator_metrics import record_cache_miss
        
        record_cache_miss()
    
    def test_update_active_sessions(self):
        """Test updating active sessions gauge."""
        from llmhive.app.api.orchestrator_metrics import update_active_sessions
        
        update_active_sessions(5)
        update_active_sessions(0)


class TestResponseCache:
    """Tests for response cache."""
    
    def test_cache_get_set(self):
        """Test cache get and set operations."""
        from llmhive.app.orchestration.response_cache import ResponseCache
        
        cache = ResponseCache(max_size=10, ttl_seconds=60)
        
        # Set a value
        cache.set("model-1", "prompt-1", {"response": "Hello"})
        
        # Get the value
        hit, value = cache.get("model-1", "prompt-1")
        
        assert hit is True
        assert value["response"] == "Hello"
    
    def test_cache_miss(self):
        """Test cache miss."""
        from llmhive.app.orchestration.response_cache import ResponseCache
        
        cache = ResponseCache()
        
        hit, value = cache.get("model-x", "nonexistent prompt")
        
        assert hit is False
        assert value is None
    
    def test_cache_ttl_expiration(self):
        """Test cache TTL expiration."""
        from llmhive.app.orchestration.response_cache import ResponseCache
        
        cache = ResponseCache(ttl_seconds=0.1)  # 100ms TTL
        
        cache.set("model-1", "prompt-1", "value")
        
        # Immediate get should hit
        hit1, _ = cache.get("model-1", "prompt-1")
        assert hit1 is True
        
        # Wait for expiration
        time.sleep(0.15)
        
        # Should miss now
        hit2, _ = cache.get("model-1", "prompt-1")
        assert hit2 is False
    
    def test_cache_lru_eviction(self):
        """Test LRU cache eviction."""
        from llmhive.app.orchestration.response_cache import ResponseCache
        
        cache = ResponseCache(max_size=2, ttl_seconds=60)
        
        cache.set("m", "p1", "v1")
        cache.set("m", "p2", "v2")
        cache.set("m", "p3", "v3")  # Should evict p1
        
        hit1, _ = cache.get("m", "p1")
        hit2, _ = cache.get("m", "p2")
        hit3, _ = cache.get("m", "p3")
        
        assert hit1 is False  # Evicted
        assert hit2 is True
        assert hit3 is True
    
    def test_cache_stats(self):
        """Test cache statistics."""
        from llmhive.app.orchestration.response_cache import ResponseCache
        
        cache = ResponseCache()
        
        cache.set("m", "p1", "v1")
        cache.get("m", "p1")  # Hit
        cache.get("m", "p1")  # Hit
        cache.get("m", "p2")  # Miss
        
        stats = cache.stats()
        
        assert stats["hits"] == 2
        assert stats["misses"] == 1
        assert stats["size"] == 1
        assert stats["hit_rate"] == 2 / 3
    
    def test_cache_invalidate(self):
        """Test cache invalidation."""
        from llmhive.app.orchestration.response_cache import ResponseCache
        
        cache = ResponseCache()
        
        cache.set("m1", "p1", "v1")
        cache.set("m2", "p2", "v2")
        
        # Invalidate specific model
        cache.invalidate(model_id="m1")
        
        hit1, _ = cache.get("m1", "p1")
        hit2, _ = cache.get("m2", "p2")
        
        assert hit1 is False  # Invalidated
        assert hit2 is True
    
    def test_cache_invalidate_all(self):
        """Test invalidating entire cache."""
        from llmhive.app.orchestration.response_cache import ResponseCache
        
        cache = ResponseCache()
        
        cache.set("m1", "p1", "v1")
        cache.set("m2", "p2", "v2")
        
        cache.invalidate()  # Invalidate all
        
        assert cache.stats()["size"] == 0


# ==============================================================================
# Integration Tests
# ==============================================================================

class TestSafeModeIntegration:
    """Integration tests for Safe Mode with guardrails."""
    
    def test_full_safe_mode_flow(self):
        """Test complete Safe Mode flow with input and output filtering."""
        from llmhive.app.routers.chat import validate_and_sanitize_input, filter_and_sanitize_output
        
        # Step 1: Validate input with PII
        input_text = "My email is user@test.com. What is 2+2?"
        sanitized_input, allowed, reason = validate_and_sanitize_input(input_text, True)
        
        assert allowed is True
        assert "user@test.com" not in sanitized_input
        
        # Step 2: Simulate clean model output
        model_output = "The answer to 2+2 is 4."
        filtered_output, was_filtered, issues = filter_and_sanitize_output(model_output, True)
        
        assert was_filtered is False
        assert filtered_output == model_output
    
    def test_harmful_input_blocked(self):
        """Test that harmful input is blocked."""
        from llmhive.app.routers.chat import validate_and_sanitize_input
        
        # These are the critical patterns that MUST be blocked
        harmful_inputs = [
            "How to make a bomb",
            "How to make explosives at home",
            "How to kill someone",
        ]
        
        for harmful_input in harmful_inputs:
            _, allowed, _ = validate_and_sanitize_input(harmful_input, True)
            assert allowed is False, f"Should block: {harmful_input}"


class TestDevModeIntegration:
    """Integration tests for Dev Mode tracing."""
    
    def test_dev_mode_check(self):
        """Test dev mode check function."""
        from llmhive.app.orchestration.dev_mode import is_dev_mode
        
        # Should return False by default (env var not set)
        result = is_dev_mode()
        # Just verify it returns a boolean
        assert isinstance(result, bool)
    
    def test_generate_explanation(self):
        """Test explanation generation."""
        from llmhive.app.orchestration.dev_mode import generate_explanation
        
        explanation = generate_explanation(
            final_answer="Paris is the capital of France.",
            strategy="expert_panel",
            agents_used=["researcher", "verifier"],
            tools_used=["web_search"],
            verification_passed=True
        )
        
        assert "How This Answer Was Generated" in explanation
        assert "Expert Panel" in explanation
        assert "researcher" in explanation
        assert "web_search" in explanation
        assert "✅" in explanation


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

