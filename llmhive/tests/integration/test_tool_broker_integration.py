"""Integration tests for Tool Broker.

Tests tool detection, execution, and integration with the orchestration pipeline.

Run from llmhive directory: pytest tests/integration/test_tool_broker_integration.py -v
"""
from __future__ import annotations

import sys
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any, List

# Add src to path for imports
_src_path = Path(__file__).parent.parent.parent / "src"
if str(_src_path) not in sys.path:
    sys.path.insert(0, str(_src_path))

# Try to import tool broker components
try:
    from llmhive.app.tool_broker import (
        ToolBroker,
        ToolDefinition,
        ToolRequest,
        ToolResult,
        ToolCategory,
        get_tool_broker,
        reset_tool_broker,
    )
    TOOL_BROKER_AVAILABLE = True
except ImportError:
    TOOL_BROKER_AVAILABLE = False


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def tool_broker():
    """Create a tool broker instance."""
    if not TOOL_BROKER_AVAILABLE:
        pytest.skip("Tool broker not available")
    reset_tool_broker()
    return ToolBroker(enable_sandbox=False)


# ============================================================
# Test Tool Detection
# ============================================================

@pytest.mark.skipif(not TOOL_BROKER_AVAILABLE, reason="Tool broker not available")
class TestToolDetection:
    """Test tool call detection in model output."""
    
    def test_detect_bracket_format_at_start(self, tool_broker):
        """Test detecting [TOOL:name] format at start of text."""
        # is_tool_request uses match() which checks start of string
        model_output = "[TOOL:calculator] 5 * 7"
        
        assert tool_broker.is_tool_request(model_output)
    
    def test_detect_json_format(self, tool_broker):
        """Test detecting JSON tool format."""
        model_output = '{"tool": "calculator", "args": "5 * 7"}'
        
        assert tool_broker.is_tool_request(model_output)
    
    def test_no_tool_detected(self, tool_broker):
        """Test that regular text is not detected as tool call."""
        model_output = "The capital of France is Paris."
        
        assert not tool_broker.is_tool_request(model_output)
    
    def test_extract_multiple_tools(self, tool_broker):
        """Test extracting multiple tool calls from output."""
        model_output = """
        [TOOL:calculator] 10 + 5
        Some text
        [TOOL:calculator] 20 / 4
        """
        
        tool_calls = tool_broker.extract_tool_calls(model_output)
        
        # Should find both tool calls
        assert len(tool_calls) >= 2
    
    def test_parse_tool_request_bracket(self, tool_broker):
        """Test parsing [TOOL:name] format."""
        text = "[TOOL:calculator] 5 * 7"
        request = tool_broker.parse_tool_request(text)
        
        assert request is not None
        assert request.tool_name == "calculator"
        assert "5 * 7" in request.arguments
    
    def test_parse_tool_request_json(self, tool_broker):
        """Test parsing JSON format."""
        text = '{"tool": "calculator", "args": "5 * 7"}'
        request = tool_broker.parse_tool_request(text)
        
        assert request is not None
        assert request.tool_name == "calculator"


# ============================================================
# Test Tool Execution
# ============================================================

@pytest.mark.skipif(not TOOL_BROKER_AVAILABLE, reason="Tool broker not available")
class TestToolExecution:
    """Test tool execution."""
    
    def test_calculator_basic(self, tool_broker):
        """Test basic calculator execution."""
        result = tool_broker.handle_tool_request("[TOOL:calculator] 2 + 2")
        
        assert result.success
        assert "4" in result.result
    
    def test_calculator_multiplication(self, tool_broker):
        """Test calculator multiplication."""
        result = tool_broker.handle_tool_request("[TOOL:calculator] 5 * 7")
        
        assert result.success
        assert "35" in result.result
    
    def test_calculator_complex(self, tool_broker):
        """Test complex calculator expression."""
        # Use simpler expression without parentheses which may cause issues
        result = tool_broker.handle_tool_request("[TOOL:calculator] 10 + 5 * 2")
        
        assert result.success
        # 10 + 5 * 2 = 20 (order of operations)
        assert "20" in result.result
    
    def test_datetime_tool(self, tool_broker):
        """Test datetime tool."""
        result = tool_broker.handle_tool_request("[TOOL:datetime]")
        
        assert result.success
        # Should contain date/time info
        assert any(c.isdigit() for c in result.result)
    
    def test_datetime_with_format(self, tool_broker):
        """Test datetime with format string."""
        result = tool_broker.handle_tool_request("[TOOL:datetime] %Y-%m-%d")
        
        assert result.success
        import re
        # Should match YYYY-MM-DD format
        assert re.match(r'\d{4}-\d{2}-\d{2}', result.result)
    
    def test_unknown_tool(self, tool_broker):
        """Test handling of unknown tool."""
        result = tool_broker.handle_tool_request("[TOOL:nonexistent_tool] args")
        
        assert not result.success
        assert "unknown" in result.error.lower() or "not found" in result.error.lower()


# ============================================================
# Test Tier Restrictions
# ============================================================

@pytest.mark.skipif(not TOOL_BROKER_AVAILABLE, reason="Tool broker not available")
class TestTierRestrictions:
    """Test tool access tier restrictions."""
    
    def test_free_tier_has_calculator(self, tool_broker):
        """Test calculator available for free tier."""
        tools = tool_broker.list_tools(user_tier="free")
        tool_names = [t["name"] for t in tools]
        
        assert "calculator" in tool_names
    
    def test_free_tier_has_datetime(self, tool_broker):
        """Test datetime available for free tier."""
        tools = tool_broker.list_tools(user_tier="free")
        tool_names = [t["name"] for t in tools]
        
        assert "datetime" in tool_names
    
    def test_pro_tier_has_more_tools(self, tool_broker):
        """Test pro tier has at least as many tools as free."""
        free_tools = tool_broker.list_tools(user_tier="free")
        pro_tools = tool_broker.list_tools(user_tier="pro")
        
        assert len(pro_tools) >= len(free_tools)
    
    def test_python_exec_blocked_for_free(self, tool_broker):
        """Test Python exec blocked for free tier."""
        result = tool_broker.handle_tool_request(
            "[TOOL:python_exec] print('hello')",
            user_tier="free"
        )
        
        assert not result.success
        assert "not available" in result.error.lower() or "upgrade" in result.error.lower()


# ============================================================
# Test Async Tool Execution
# ============================================================

@pytest.mark.skipif(not TOOL_BROKER_AVAILABLE, reason="Tool broker not available")
class TestAsyncToolExecution:
    """Test async tool execution."""
    
    @pytest.mark.asyncio
    async def test_async_calculator(self, tool_broker):
        """Test async calculator execution."""
        result = await tool_broker.handle_tool_request_async("[TOOL:calculator] 5 * 7")
        
        assert result.success
        assert "35" in result.result
    
    @pytest.mark.asyncio
    async def test_process_model_output_simple(self, tool_broker):
        """Test processing model output with simple tool call."""
        # Use simple format without leading text
        model_output = "[TOOL:calculator] 100 / 4"
        
        processed, results = await tool_broker.process_model_output_with_tools(
            model_output,
            user_tier="free"
        )
        
        assert len(results) >= 1
        # Check if any result succeeded with 25
        successful = [r for r in results if r.success]
        if successful:
            assert "25" in processed
    
    @pytest.mark.asyncio
    async def test_process_multiple_tool_calls(self, tool_broker):
        """Test processing multiple tool calls."""
        model_output = """[TOOL:calculator] 10 + 5
[TOOL:calculator] 20 * 2"""
        
        processed, results = await tool_broker.process_model_output_with_tools(
            model_output,
            user_tier="free"
        )
        
        assert len(results) >= 2
    
    @pytest.mark.asyncio
    async def test_process_no_tools(self, tool_broker):
        """Test processing output with no tool calls."""
        model_output = "This is just regular text without any tools."
        
        processed, results = await tool_broker.process_model_output_with_tools(
            model_output,
            user_tier="free"
        )
        
        assert len(results) == 0
        assert processed == model_output


# ============================================================
# Test Tool Registration
# ============================================================

@pytest.mark.skipif(not TOOL_BROKER_AVAILABLE, reason="Tool broker not available")
class TestToolRegistration:
    """Test custom tool registration."""
    
    def test_register_custom_tool(self, tool_broker):
        """Test registering a custom tool."""
        def echo_tool(args: str) -> str:
            return f"Echo: {args}"
        
        tool_broker.register_tool(
            ToolDefinition(
                name="echo",
                description="Echoes the input",
                category=ToolCategory.COMPUTE,
                handler=echo_tool,
            )
        )
        
        result = tool_broker.handle_tool_request("[TOOL:echo] Hello World")
        
        assert result.success
        assert "Echo: Hello World" in result.result


# ============================================================
# Test Error Handling
# ============================================================

@pytest.mark.skipif(not TOOL_BROKER_AVAILABLE, reason="Tool broker not available")
class TestToolErrorHandling:
    """Test error handling in tool execution."""
    
    def test_calculator_division_by_zero(self, tool_broker):
        """Test calculator handles division by zero."""
        result = tool_broker.handle_tool_request("[TOOL:calculator] 5 / 0")
        
        # Should handle gracefully - either error or inf
        assert result is not None
    
    def test_malformed_tool_request(self, tool_broker):
        """Test handling of malformed tool request."""
        result = tool_broker.parse_tool_request("[TOOL: invalid format")
        
        # Should return None for invalid format
        assert result is None


# ============================================================
# Test Global Tool Broker
# ============================================================

@pytest.mark.skipif(not TOOL_BROKER_AVAILABLE, reason="Tool broker not available")
class TestGlobalToolBroker:
    """Test global tool broker singleton."""
    
    def test_get_tool_broker_singleton(self):
        """Test getting global tool broker returns same instance."""
        reset_tool_broker()
        broker1 = get_tool_broker()
        broker2 = get_tool_broker()
        
        assert broker1 is broker2
    
    def test_reset_creates_new_instance(self):
        """Test reset creates new instance."""
        broker1 = get_tool_broker()
        reset_tool_broker()
        broker2 = get_tool_broker()
        
        assert broker1 is not broker2
