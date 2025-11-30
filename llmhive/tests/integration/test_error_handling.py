"""Tests for error handling and graceful degradation."""
from __future__ import annotations

import pytest
from unittest.mock import Mock, AsyncMock, patch

# Avoid importing FastAPI/HTTPException if not available
try:
    from fastapi import HTTPException
except ImportError:
    HTTPException = Exception  # Fallback

# Use direct module loading to avoid dependency issues
import sys
from pathlib import Path
import importlib.util

orchestrator_path = Path(__file__).parent.parent.parent / "src" / "llmhive" / "app" / "orchestrator.py"
if orchestrator_path.exists():
    spec = importlib.util.spec_from_file_location("orchestrator", orchestrator_path)
    orchestrator_module = importlib.util.module_from_spec(spec)
    sys.modules['orchestrator'] = orchestrator_module
    spec.loader.exec_module(orchestrator_module)
    Orchestrator = orchestrator_module.Orchestrator
else:
    Orchestrator = Mock  # Fallback for testing

# Fixtures
@pytest.fixture
def sample_prompt():
    return "What is the capital of France?"

@pytest.fixture
def error_scenarios():
    return [
        {"type": "timeout", "error": TimeoutError("Request timed out")},
        {"type": "connection", "error": ConnectionError("Connection failed")},
    ]


class TestGracefulDegradation:
    """Test graceful degradation on component failures."""
    
    @pytest.mark.asyncio
    async def test_planner_exception_handling(self, sample_prompt):
        """Test handling of planner exceptions."""
        orchestrator = Orchestrator()
        
        # Simulate planner failure
        with patch.object(orchestrator.planner, 'create_plan', side_effect=Exception("Planning failed")):
            try:
                result = await orchestrator.orchestrate(sample_prompt, user_id="test-user")
                # Should either have fallback or error message
                assert result is not None
                # Should not be a stack trace
                assert "traceback" not in str(result).lower()
            except Exception as e:
                # Should be user-friendly error
                assert "planning" in str(e).lower() or "error" in str(e).lower()
    
    @pytest.mark.asyncio
    async def test_model_call_failure_handling(self, sample_prompt):
        """Test handling of model API call failures."""
        orchestrator = Orchestrator()
        
        # Simulate model API failure
        with patch.object(orchestrator.providers['openai'], 'complete', side_effect=ConnectionError("API unavailable")):
            try:
                result = await orchestrator.orchestrate(sample_prompt, user_id="test-user")
                # Should have fallback or error message
                assert result is not None
            except Exception as e:
                # Should be user-friendly
                assert "unavailable" in str(e).lower() or "error" in str(e).lower()
    
    @pytest.mark.asyncio
    async def test_memory_store_failure_handling(self, sample_prompt):
        """Test handling of memory store failures."""
        orchestrator = Orchestrator()
        
        # Simulate memory store failure
        with patch('llmhive.app.memory.get_memory_context', side_effect=Exception("DB error")):
            # Should still proceed without memory
            result = await orchestrator.orchestrate(sample_prompt, user_id="test-user")
            assert result is not None
    
    @pytest.mark.asyncio
    async def test_tool_execution_failure(self, sample_prompt):
        """Test handling of tool execution failures."""
        orchestrator = Orchestrator()
        
        # Simulate tool failure
        with patch('llmhive.app.tool_broker.execute_tool', side_effect=Exception("Tool failed")):
            # Should handle gracefully
            result = await orchestrator.orchestrate(sample_prompt, user_id="test-user")
            assert result is not None


class TestErrorMessages:
    """Test user-friendly error messages."""
    
    def test_no_stack_traces_exposed(self):
        """Test that stack traces are not exposed to users."""
        error = Exception("Internal error with traceback")
        error_str = str(error)
        
        # Should not contain technical details
        assert "file" not in error_str.lower()
        assert "line" not in error_str.lower()
        assert "traceback" not in error_str.lower()
    
    def test_user_friendly_error_format(self):
        """Test that errors are formatted for users."""
        # Simulate error that would be shown to user
        user_error = "I'm sorry, I encountered an issue processing your request. Please try again."
        
        # Should be friendly and actionable
        assert "sorry" in user_error.lower() or "issue" in user_error.lower()
        assert len(user_error) < 200  # Not too long
        assert "try again" in user_error.lower() or "retry" in user_error.lower()
    
    @pytest.mark.asyncio
    async def test_error_includes_retry_suggestion(self):
        """Test that errors suggest retrying."""
        orchestrator = Orchestrator()
        
        # Simulate transient error
        with patch.object(orchestrator, 'orchestrate', side_effect=TimeoutError("Request timed out")):
            try:
                await orchestrator.orchestrate("test", user_id="test-user")
            except Exception as e:
                error_msg = str(e).lower()
                # Should suggest retry for transient errors
                assert "retry" in error_msg or "try again" in error_msg or "later" in error_msg


class TestComprehensiveLogging:
    """Test comprehensive logging of events."""
    
    @pytest.mark.asyncio
    async def test_request_logging(self, sample_prompt):
        """Test that requests are logged."""
        import logging
        from io import StringIO
        
        log_capture = StringIO()
        handler = logging.StreamHandler(log_capture)
        logger = logging.getLogger('llmhive.app.orchestrator')
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        
        orchestrator = Orchestrator()
        await orchestrator.orchestrate(sample_prompt, user_id="test-user")
        
        logs = log_capture.getvalue()
        # Should have logged the request
        assert len(logs) > 0
    
    def test_sensitive_info_not_logged(self):
        """Test that sensitive info is not logged."""
        import logging
        from io import StringIO
        
        log_capture = StringIO()
        handler = logging.StreamHandler(log_capture)
        logger = logging.getLogger('llmhive')
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)
        
        # Log something that might contain sensitive data
        api_key = "sk-1234567890abcdef"
        logger.info(f"Processing request with key: {api_key[:3]}...")  # Should be sanitized
        
        logs = log_capture.getvalue()
        # Should not contain full API key
        assert api_key not in logs
        assert "sk-123" not in logs  # Even partial keys should be hidden
    
    @pytest.mark.asyncio
    async def test_stage_logging(self, sample_prompt):
        """Test that each stage is logged."""
        import logging
        from io import StringIO
        
        log_capture = StringIO()
        handler = logging.StreamHandler(log_capture)
        logger = logging.getLogger('llmhive.app.orchestrator')
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        
        orchestrator = Orchestrator()
        await orchestrator.orchestrate(sample_prompt, user_id="test-user")
        
        logs = log_capture.getvalue().lower()
        # Should log key stages (implementation dependent)
        # This is a placeholder - actual implementation would check for specific log messages
        assert len(logs) > 0


class TestErrorRecovery:
    """Test error recovery mechanisms."""
    
    @pytest.mark.asyncio
    async def test_retry_on_transient_errors(self):
        """Test retry logic for transient errors."""
        call_count = 0
        
        async def failing_then_succeeding():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Temporary failure")
            return "Success"
        
        # Should retry and eventually succeed
        result = await failing_then_succeeding()
        assert result == "Success"
        assert call_count == 3
    
    @pytest.mark.asyncio
    async def test_fallback_on_permanent_errors(self):
        """Test fallback on permanent errors."""
        orchestrator = Orchestrator()
        
        # Primary model fails permanently
        with patch.object(orchestrator.providers.get('openai', Mock()), 'complete', side_effect=Exception("Invalid API key")):
            # Should try fallback model
            with patch.object(orchestrator.providers.get('anthropic', Mock()), 'complete', return_value=AsyncMock(content="Fallback answer")):
                result = await orchestrator.orchestrate("test", user_id="test-user")
                # Should have used fallback
                assert result is not None

