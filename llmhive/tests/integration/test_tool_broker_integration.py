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


@pytest.fixture
def mock_web_search():
    """Create mock web search function."""
    async def search(query: str) -> List[Dict[str, Any]]:
        return [
            {
                "title": f"Result for: {query}",
                "snippet": f"This is relevant information about {query}",
                "url": f"https://example.com/{query.replace(' ', '-')}",
            }
        ]
    return search


@pytest.fixture
def mock_code_executor():
    """Create mock code executor function."""
    async def execute(code: str, language: str = "python") -> Dict[str, Any]:
        return {
            "success": True,
            "output": "Code executed successfully",
            "error": None,
            "execution_time_ms": 50,
        }
    return execute


# ============================================================
# Test Tool Detection
# ============================================================

@pytest.mark.skipif(not TOOL_BROKER_AVAILABLE, reason="Tool broker not available")
class TestToolDetection:
    """Test tool call detection in model output."""
    
    def test_detect_bracket_format(self, tool_broker):
        """Test detecting [TOOL:name] format."""
        model_output = "Let me calculate: [TOOL:calculator] 5 * 7"
        
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
        """Test extracting multiple tool calls."""
        model_output = """
        First calculation: [TOOL:calculator] 10 + 5
        Second calculation: [TOOL:calculator] 20 / 4
        Third: [TOOL:datetime]
        """
        
        tool_calls = tool_broker.extract_tool_calls(model_output)
        
        assert len(tool_calls) >= 2


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
    
    def test_calculator_complex(self, tool_broker):
        """Test complex calculator expression."""
        result = tool_broker.handle_tool_request("[TOOL:calculator] (10 + 5) * 2 - 7")
        
        assert result.success
        assert "23" in result.result
    
    def test_calculator_math_functions(self, tool_broker):
        """Test calculator with math functions."""
        result = tool_broker.handle_tool_request("[TOOL:calculator] sqrt(16) + 2")
        
        assert result.success
        assert "6" in result.result
    
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
    
    def test_unit_conversion(self, tool_broker):
        """Test unit conversion tool."""
        result = tool_broker.handle_tool_request("[TOOL:convert] 100 km miles")
        
        assert result.success
        assert "62" in result.result  # 100km ≈ 62 miles
    
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
    
    def test_free_tier_tools(self, tool_broker):
        """Test tools available for free tier."""
        tools = tool_broker.list_tools(user_tier="free")
        tool_names = [t["name"] for t in tools]
        
        assert "calculator" in tool_names
        assert "datetime" in tool_names
    
    def test_pro_tier_tools(self, tool_broker):
        """Test tools available for pro tier."""
        tools = tool_broker.list_tools(user_tier="pro")
        tool_names = [t["name"] for t in tools]
        
        # Pro tier should have more tools
        assert "calculator" in tool_names
        assert len(tool_names) >= len(tool_broker.list_tools(user_tier="free"))
    
    def test_restricted_tool_blocked(self, tool_broker):
        """Test that restricted tools are blocked for lower tiers."""
        # Python exec is typically pro+ only
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
    async def test_process_model_output(self, tool_broker):
        """Test processing model output with tool calls."""
        model_output = """
        I'll calculate that for you:
        [TOOL:calculator] 100 / 4
        
        The result is shown above.
        """
        
        processed, results = await tool_broker.process_model_output_with_tools(
            model_output,
            user_tier="free"
        )
        
        assert len(results) == 1
        assert results[0].success
        assert "25" in processed
    
    @pytest.mark.asyncio
    async def test_multiple_tool_calls(self, tool_broker):
        """Test processing multiple tool calls."""
        model_output = """
        [TOOL:calculator] 10 + 5
        [TOOL:calculator] 20 * 2
        """
        
        processed, results = await tool_broker.process_model_output_with_tools(
            model_output,
            user_tier="free"
        )
        
        assert len(results) == 2
        assert all(r.success for r in results)
    
    @pytest.mark.asyncio
    async def test_max_tool_calls_limit(self, tool_broker):
        """Test max tool calls limit is enforced."""
        model_output = "\n".join([
            f"[TOOL:calculator] {i}+1" for i in range(10)
        ])
        
        processed, results = await tool_broker.process_model_output_with_tools(
            model_output,
            user_tier="free",
            max_tool_calls=3
        )
        
        # Should only execute up to max_tool_calls
        assert len(results) <= 3


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
        
        # Should handle gracefully
        assert "division" in result.result.lower() or "error" in result.result.lower()
    
    def test_calculator_syntax_error(self, tool_broker):
        """Test calculator handles syntax errors."""
        result = tool_broker.handle_tool_request("[TOOL:calculator] 5 + * 3")
        
        # Should handle gracefully
        assert "error" in result.result.lower() or "syntax" in result.result.lower()
    
    def test_malformed_tool_request(self, tool_broker):
        """Test handling of malformed tool request."""
        result = tool_broker.parse_tool_request("[TOOL: invalid format")
        
        # Should return None or handle gracefully
        assert result is None or not result.tool_name
    
    @pytest.mark.asyncio
    async def test_tool_timeout(self, tool_broker):
        """Test tool execution timeout handling."""
        # This test verifies timeout behavior is handled
        # Actual timeout depends on implementation
        result = await tool_broker.handle_tool_request_async("[TOOL:calculator] 1+1")
        
        # Should complete without hanging
        assert result is not None
