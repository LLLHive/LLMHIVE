"""Tests for OpenTelemetry distributed tracing.

Tests verify:
- Tracing initialization
- Span creation for orchestration, agents, tools, model calls
- Attribute recording
- Context propagation
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock

import pytest

# Add src to path for imports
_src_path = Path(__file__).parent.parent / "src"
if str(_src_path) not in sys.path:
    sys.path.insert(0, str(_src_path))

# Try to import tracing module
try:
    from llmhive.app.telemetry.tracing import (
        init_tracing,
        get_tracer,
        trace_orchestration,
        trace_agent,
        trace_tool,
        trace_model_call,
        get_current_span,
        add_span_attributes,
        record_exception,
        TracingConfig,
        OTEL_AVAILABLE,
        traced,
        get_trace_context,
    )
    TRACING_AVAILABLE = True
except ImportError:
    TRACING_AVAILABLE = False


# ==============================================================================
# Fixtures
# ==============================================================================

@pytest.fixture
def tracing_config():
    """Create a test tracing configuration."""
    return TracingConfig(
        service_name="llmhive-test",
        service_version="0.0.1",
        environment="test",
        otlp_endpoint=None,
        use_console_exporter=False,
        trace_orchestration=True,
        trace_agents=True,
        trace_tools=True,
        trace_model_calls=True,
    )


@pytest.fixture
def mock_tracer():
    """Create a mock tracer."""
    tracer = MagicMock()
    mock_span = MagicMock()
    mock_span.__enter__ = MagicMock(return_value=mock_span)
    mock_span.__exit__ = MagicMock(return_value=False)
    tracer.start_as_current_span.return_value = mock_span
    return tracer


# ==============================================================================
# TracingConfig Tests
# ==============================================================================

@pytest.mark.skipif(not TRACING_AVAILABLE, reason="Tracing module not available")
class TestTracingConfig:
    """Tests for TracingConfig dataclass."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = TracingConfig()
        
        assert config.service_name == "llmhive-orchestrator"
        assert config.service_version == "1.0.0"
        assert config.trace_orchestration is True
        assert config.trace_agents is True
        assert config.trace_tools is True
        assert config.trace_model_calls is True
        assert config.max_attribute_length == 1024
    
    def test_custom_config(self, tracing_config):
        """Test custom configuration values."""
        assert tracing_config.service_name == "llmhive-test"
        assert tracing_config.environment == "test"
    
    def test_config_from_env(self):
        """Test configuration from environment variables."""
        import os
        
        with patch.dict(os.environ, {
            "ENVIRONMENT": "production",
            "OTEL_EXPORTER_OTLP_ENDPOINT": "http://localhost:4317",
            "OTEL_CONSOLE_EXPORT": "true",
        }):
            config = TracingConfig()
            assert config.environment == "production"
            assert config.otlp_endpoint == "http://localhost:4317"
            assert config.use_console_exporter is True


# ==============================================================================
# Tracing Initialization Tests
# ==============================================================================

@pytest.mark.skipif(not TRACING_AVAILABLE, reason="Tracing module not available")
class TestTracingInitialization:
    """Tests for tracing initialization."""
    
    def test_init_without_otel(self):
        """Test initialization when OpenTelemetry is not available."""
        with patch("llmhive.app.telemetry.tracing.OTEL_AVAILABLE", False):
            result = init_tracing()
            assert result is False
    
    def test_init_with_config(self, tracing_config):
        """Test initialization with custom config."""
        # Reset global state
        import llmhive.app.telemetry.tracing as tracing_module
        tracing_module._initialized = False
        tracing_module._tracer = None
        
        if OTEL_AVAILABLE:
            result = init_tracing(tracing_config)
            assert result is True
    
    def test_double_initialization(self, tracing_config):
        """Test that double initialization is handled gracefully."""
        import llmhive.app.telemetry.tracing as tracing_module
        tracing_module._initialized = False
        tracing_module._tracer = None
        
        if OTEL_AVAILABLE:
            first_result = init_tracing(tracing_config)
            second_result = init_tracing(tracing_config)
            # Both should succeed (second is a no-op)
            assert first_result is True
            assert second_result is True


# ==============================================================================
# Span Creation Tests
# ==============================================================================

@pytest.mark.skipif(not TRACING_AVAILABLE, reason="Tracing module not available")
class TestSpanCreation:
    """Tests for span creation functions."""
    
    def test_trace_orchestration_context_manager(self, tracing_config):
        """Test trace_orchestration as context manager."""
        import llmhive.app.telemetry.tracing as tracing_module
        tracing_module._initialized = False
        init_tracing(tracing_config)
        
        with trace_orchestration(
            prompt="Test prompt",
            reasoning_mode="standard",
            domain_pack="default",
            agent_mode="team",
            accuracy_level=3,
            models=["gpt-4o", "claude-3"],
        ) as span:
            # Span may be None if OTEL not fully available
            # The important thing is it doesn't raise
            pass
    
    def test_trace_agent_context_manager(self, tracing_config):
        """Test trace_agent as context manager."""
        import llmhive.app.telemetry.tracing as tracing_module
        tracing_module._initialized = False
        init_tracing(tracing_config)
        
        with trace_agent(
            agent_type="qa",
            task_type="analyze",
            agent_id="qa-001",
        ) as span:
            pass
    
    def test_trace_tool_context_manager(self, tracing_config):
        """Test trace_tool as context manager."""
        import llmhive.app.telemetry.tracing as tracing_module
        tracing_module._initialized = False
        init_tracing(tracing_config)
        
        with trace_tool(
            tool_name="calculator",
            tool_type="compute",
            input_preview="2 + 2",
        ) as span:
            pass
    
    def test_trace_model_call_context_manager(self, tracing_config):
        """Test trace_model_call as context manager."""
        import llmhive.app.telemetry.tracing as tracing_module
        tracing_module._initialized = False
        init_tracing(tracing_config)
        
        with trace_model_call(
            model="gpt-4o",
            provider="openai",
            prompt_tokens=100,
            temperature=0.7,
            max_tokens=1000,
        ) as span:
            pass
    
    def test_tracing_disabled_graceful(self):
        """Test that tracing functions work gracefully when disabled."""
        import llmhive.app.telemetry.tracing as tracing_module
        tracing_module._initialized = False
        tracing_module._config = None
        
        # Should not raise even when not initialized
        with trace_orchestration(prompt="Test") as span:
            assert span is None
        
        with trace_agent(agent_type="test", task_type="test") as span:
            assert span is None


# ==============================================================================
# Decorator Tests
# ==============================================================================

@pytest.mark.skipif(not TRACING_AVAILABLE, reason="Tracing module not available")
class TestTracedDecorator:
    """Tests for the @traced decorator."""
    
    def test_traced_sync_function(self, tracing_config):
        """Test @traced decorator on sync function."""
        init_tracing(tracing_config)
        
        @traced(span_name="test.sync_function")
        def sync_function(x, y):
            return x + y
        
        result = sync_function(2, 3)
        assert result == 5
    
    @pytest.mark.asyncio
    async def test_traced_async_function(self, tracing_config):
        """Test @traced decorator on async function."""
        init_tracing(tracing_config)
        
        @traced(span_name="test.async_function")
        async def async_function(x, y):
            return x * y
        
        result = await async_function(2, 3)
        assert result == 6
    
    def test_traced_with_attributes(self, tracing_config):
        """Test @traced decorator with static attributes."""
        init_tracing(tracing_config)
        
        @traced(
            span_name="test.with_attrs",
            attributes={"custom.attr": "value"},
        )
        def func_with_attrs():
            return "done"
        
        result = func_with_attrs()
        assert result == "done"


# ==============================================================================
# Span Attributes Tests
# ==============================================================================

@pytest.mark.skipif(not TRACING_AVAILABLE, reason="Tracing module not available")
class TestSpanAttributes:
    """Tests for span attribute functions."""
    
    def test_add_span_attributes_no_span(self):
        """Test adding attributes when no span is active."""
        import llmhive.app.telemetry.tracing as tracing_module
        tracing_module._initialized = False
        
        # Should not raise
        add_span_attributes({"key": "value"})
    
    def test_add_span_attributes_with_span(self, tracing_config):
        """Test adding attributes to active span."""
        init_tracing(tracing_config)
        
        with trace_orchestration(prompt="Test") as span:
            add_span_attributes({
                "custom.attribute": "custom_value",
                "custom.count": 42,
            })
    
    def test_record_exception_no_span(self):
        """Test recording exception when no span is active."""
        import llmhive.app.telemetry.tracing as tracing_module
        tracing_module._initialized = False
        
        # Should not raise
        record_exception(ValueError("Test error"))


# ==============================================================================
# Context Propagation Tests
# ==============================================================================

@pytest.mark.skipif(not TRACING_AVAILABLE, reason="Tracing module not available")
class TestContextPropagation:
    """Tests for trace context propagation."""
    
    def test_get_trace_context_not_initialized(self):
        """Test getting context when tracing not initialized."""
        import llmhive.app.telemetry.tracing as tracing_module
        tracing_module._initialized = False
        
        context = get_trace_context()
        assert context == {}
    
    def test_get_trace_context_with_span(self, tracing_config):
        """Test getting context with active span."""
        init_tracing(tracing_config)
        
        with trace_orchestration(prompt="Test") as span:
            context = get_trace_context()
            # Context should be a dict (may be empty if no propagation)
            assert isinstance(context, dict)


# ==============================================================================
# Integration Tests
# ==============================================================================

@pytest.mark.skipif(not TRACING_AVAILABLE, reason="Tracing module not available")
class TestTracingIntegration:
    """Integration tests for tracing."""
    
    def test_nested_spans(self, tracing_config):
        """Test nested span creation."""
        init_tracing(tracing_config)
        
        with trace_orchestration(prompt="Outer") as outer:
            with trace_agent(agent_type="qa", task_type="analyze") as inner:
                with trace_model_call(model="gpt-4o", provider="openai") as model:
                    pass
    
    def test_exception_recording(self, tracing_config):
        """Test that exceptions are recorded in spans."""
        init_tracing(tracing_config)
        
        with pytest.raises(ValueError):
            with trace_orchestration(prompt="Test") as span:
                raise ValueError("Test error")
    
    @pytest.mark.asyncio
    async def test_async_tracing(self, tracing_config):
        """Test tracing in async context."""
        init_tracing(tracing_config)
        
        async def async_operation():
            with trace_orchestration(prompt="Async test") as span:
                with trace_model_call(model="gpt-4o", provider="openai") as model:
                    return "result"
        
        result = await async_operation()
        assert result == "result"
    
    def test_full_pipeline_tracing(self, tracing_config):
        """Test tracing through a simulated orchestration pipeline."""
        init_tracing(tracing_config)
        
        with trace_orchestration(
            prompt="Explain quantum computing",
            reasoning_mode="deep",
            models=["gpt-4o", "claude-3"],
        ) as orch_span:
            # Agent phase
            with trace_agent(agent_type="research", task_type="gather") as agent:
                # Tool usage
                with trace_tool(tool_name="web_search", tool_type="search") as tool:
                    pass
            
            # Model calls
            with trace_model_call(model="gpt-4o", provider="openai", prompt_tokens=500) as m1:
                pass
            
            with trace_model_call(model="claude-3", provider="anthropic", prompt_tokens=500) as m2:
                pass
            
            # Add final attributes
            add_span_attributes({
                "llmhive.result.tokens": 1000,
                "llmhive.result.latency_ms": 2500,
            })


# ==============================================================================
# Edge Cases
# ==============================================================================

@pytest.mark.skipif(not TRACING_AVAILABLE, reason="Tracing module not available")
class TestTracingEdgeCases:
    """Test edge cases in tracing."""
    
    def test_empty_prompt(self, tracing_config):
        """Test tracing with empty prompt."""
        init_tracing(tracing_config)
        
        with trace_orchestration(prompt="") as span:
            pass
    
    def test_very_long_prompt(self, tracing_config):
        """Test tracing with very long prompt (should truncate)."""
        init_tracing(tracing_config)
        
        long_prompt = "x" * 10000
        with trace_orchestration(prompt=long_prompt) as span:
            pass
    
    def test_none_values(self, tracing_config):
        """Test tracing with None values."""
        init_tracing(tracing_config)
        
        with trace_model_call(
            model="test",
            provider="test",
            prompt_tokens=None,
            temperature=None,
            max_tokens=None,
        ) as span:
            pass
    
    def test_special_characters_in_names(self, tracing_config):
        """Test tracing with special characters in names."""
        init_tracing(tracing_config)
        
        with trace_tool(
            tool_name="tool/with/slashes",
            tool_type="special-type",
            input_preview="Input with 'quotes' and \"double quotes\"",
        ) as span:
            pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
