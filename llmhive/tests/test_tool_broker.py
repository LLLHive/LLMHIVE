"""Unit tests for the ToolBroker module."""
from __future__ import annotations

import math
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from llmhive.src.llmhive.app.tool_broker import (
    ToolBroker,
    ToolDefinition,
    ToolRequest,
    ToolResult,
    ToolCategory,
    SafeCalculator,
    get_tool_broker,
    reset_tool_broker,
)


class TestSafeCalculator:
    """Tests for SafeCalculator."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.calc = SafeCalculator()
    
    def test_basic_addition(self):
        """Test basic addition."""
        assert self.calc.evaluate("2 + 3") == 5
    
    def test_basic_subtraction(self):
        """Test basic subtraction."""
        assert self.calc.evaluate("10 - 4") == 6
    
    def test_basic_multiplication(self):
        """Test basic multiplication."""
        assert self.calc.evaluate("5 * 7") == 35
    
    def test_basic_division(self):
        """Test basic division."""
        assert self.calc.evaluate("20 / 4") == 5.0
    
    def test_floor_division(self):
        """Test floor division."""
        assert self.calc.evaluate("17 // 5") == 3
    
    def test_modulo(self):
        """Test modulo operation."""
        assert self.calc.evaluate("17 % 5") == 2
    
    def test_power(self):
        """Test exponentiation."""
        assert self.calc.evaluate("2 ** 8") == 256
    
    def test_complex_expression(self):
        """Test complex expression."""
        result = self.calc.evaluate("(2 + 3) * 4 - 6 / 2")
        assert result == 17.0
    
    def test_negative_numbers(self):
        """Test negative numbers."""
        assert self.calc.evaluate("-5 + 3") == -2
        assert self.calc.evaluate("10 + (-3)") == 7
    
    def test_decimal_numbers(self):
        """Test decimal numbers."""
        result = self.calc.evaluate("3.14 * 2")
        assert abs(result - 6.28) < 0.001
    
    def test_math_constant_pi(self):
        """Test math constant pi."""
        result = self.calc.evaluate("pi * 2")
        assert abs(result - 2 * math.pi) < 0.0001
    
    def test_math_constant_e(self):
        """Test math constant e."""
        result = self.calc.evaluate("e")
        assert abs(result - math.e) < 0.0001
    
    def test_sqrt_function(self):
        """Test sqrt function."""
        assert self.calc.evaluate("sqrt(16)") == 4
    
    def test_sin_function(self):
        """Test sin function."""
        result = self.calc.evaluate("sin(0)")
        assert abs(result) < 0.0001
    
    def test_cos_function(self):
        """Test cos function."""
        result = self.calc.evaluate("cos(0)")
        assert abs(result - 1) < 0.0001
    
    def test_log_function(self):
        """Test log function."""
        result = self.calc.evaluate("log(e)")
        assert abs(result - 1) < 0.0001
    
    def test_abs_function(self):
        """Test abs function."""
        assert self.calc.evaluate("abs(-5)") == 5
    
    def test_min_function(self):
        """Test min function."""
        assert self.calc.evaluate("min(3, 1, 4, 1, 5)") == 1
    
    def test_max_function(self):
        """Test max function."""
        assert self.calc.evaluate("max(3, 1, 4, 1, 5)") == 5
    
    def test_round_function(self):
        """Test round function."""
        assert self.calc.evaluate("round(3.7)") == 4
    
    def test_factorial_function(self):
        """Test factorial function."""
        assert self.calc.evaluate("factorial(5)") == 120
    
    def test_division_by_zero(self):
        """Test division by zero returns error."""
        result = self.calc.evaluate("5 / 0")
        assert "Division by zero" in str(result)
    
    def test_syntax_error(self):
        """Test syntax error handling."""
        result = self.calc.evaluate("5 + * 3")
        assert "Syntax error" in str(result)
    
    def test_unknown_function(self):
        """Test unknown function returns error."""
        result = self.calc.evaluate("unknown(5)")
        assert "Unknown function" in str(result) or "error" in str(result).lower()
    
    def test_no_eval_abuse(self):
        """Test that dangerous operations are not allowed."""
        # These should not execute actual Python code
        result = self.calc.evaluate("__import__('os').system('ls')")
        assert "error" in str(result).lower() or "unsupported" in str(result).lower()


class TestToolBroker:
    """Tests for ToolBroker class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        reset_tool_broker()
        self.broker = ToolBroker(enable_sandbox=False)
    
    def test_list_tools_free_tier(self):
        """Test listing tools for free tier."""
        tools = self.broker.list_tools(user_tier="free")
        tool_names = [t["name"] for t in tools]
        
        assert "calculator" in tool_names
        assert "web_search" in tool_names
        # Python exec not available for free tier
        assert "python_exec" not in tool_names
    
    def test_list_tools_pro_tier(self):
        """Test listing tools for pro tier."""
        tools = self.broker.list_tools(user_tier="pro")
        tool_names = [t["name"] for t in tools]
        
        assert "calculator" in tool_names
        assert "web_search" in tool_names
        assert "python_exec" in tool_names
        assert "knowledge_lookup" in tool_names
    
    def test_list_tools_enterprise_tier(self):
        """Test listing tools for enterprise tier."""
        tools = self.broker.list_tools(user_tier="enterprise")
        tool_names = [t["name"] for t in tools]
        
        # Enterprise should have all tools
        assert len(tool_names) >= 4
    
    def test_is_tool_request_bracket_format(self):
        """Test detecting [TOOL:name] format."""
        assert self.broker.is_tool_request("[TOOL:calculator] 5 * 7") is True
        assert self.broker.is_tool_request("[TOOL:web_search] Python language") is True
        assert self.broker.is_tool_request("Regular text") is False
    
    def test_is_tool_request_json_format(self):
        """Test detecting JSON format."""
        assert self.broker.is_tool_request('{"tool": "calculator", "args": "5 * 7"}') is True
        assert self.broker.is_tool_request('{"not_a_tool": "value"}') is False
    
    def test_parse_tool_request_bracket_format(self):
        """Test parsing [TOOL:name] format."""
        request = self.broker.parse_tool_request("[TOOL:calculator] 5 * 7")
        
        assert request is not None
        assert request.tool_name == "calculator"
        assert request.arguments == "5 * 7"
    
    def test_parse_tool_request_json_format(self):
        """Test parsing JSON format."""
        request = self.broker.parse_tool_request('{"tool": "calculator", "args": "5 * 7"}')
        
        assert request is not None
        assert request.tool_name == "calculator"
        assert "5 * 7" in request.arguments
    
    def test_parse_tool_request_invalid(self):
        """Test parsing invalid request returns None."""
        request = self.broker.parse_tool_request("Just regular text")
        assert request is None
    
    def test_handle_calculator_request(self):
        """Test handling calculator request."""
        result = self.broker.handle_tool_request("[TOOL:calculator] 5 * 7")
        
        assert result.success is True
        assert result.tool_name == "calculator"
        assert "35" in result.result
    
    def test_handle_calculator_complex(self):
        """Test handling complex calculator request."""
        result = self.broker.handle_tool_request("[TOOL:calculator] (10 + 5) * 2 - 7")
        
        assert result.success is True
        assert "23" in result.result
    
    def test_handle_unknown_tool(self):
        """Test handling unknown tool."""
        result = self.broker.handle_tool_request("[TOOL:unknown_tool] args")
        
        assert result.success is False
        assert "Unknown tool" in result.error
    
    def test_handle_tier_restricted_tool(self):
        """Test handling tier-restricted tool."""
        result = self.broker.handle_tool_request(
            "[TOOL:python_exec] print('hello')",
            user_tier="free"
        )
        
        assert result.success is False
        assert "not available for tier" in result.error.lower() or "upgrade" in result.error.lower()
    
    def test_handle_tier_allowed_tool(self):
        """Test handling tool allowed for tier."""
        broker = ToolBroker(enable_sandbox=True)
        result = broker.handle_tool_request(
            "[TOOL:calculator] 2 + 2",
            user_tier="free"
        )
        
        assert result.success is True
    
    def test_datetime_tool(self):
        """Test datetime tool."""
        result = self.broker.handle_tool_request("[TOOL:datetime]")
        
        assert result.success is True
        # Should contain date/time info
        assert any(c.isdigit() for c in result.result)
    
    def test_datetime_tool_with_format(self):
        """Test datetime tool with format."""
        result = self.broker.handle_tool_request("[TOOL:datetime] %Y-%m-%d")
        
        assert result.success is True
        # Should match YYYY-MM-DD format
        import re
        assert re.match(r'\d{4}-\d{2}-\d{2}', result.result)
    
    def test_unit_convert_length(self):
        """Test unit conversion for length."""
        result = self.broker.handle_tool_request("[TOOL:convert] 100 km miles")
        
        assert result.success is True
        assert "62" in result.result  # 100 km ≈ 62 miles
    
    def test_unit_convert_temperature(self):
        """Test unit conversion for temperature."""
        result = self.broker.handle_tool_request("[TOOL:convert] 100 celsius fahrenheit")
        
        assert result.success is True
        assert "212" in result.result  # 100°C = 212°F
    
    def test_unit_convert_weight(self):
        """Test unit conversion for weight."""
        result = self.broker.handle_tool_request("[TOOL:convert] 1 kg pounds")
        
        assert result.success is True
        assert "2.2" in result.result  # 1 kg ≈ 2.2 lbs
    
    def test_register_custom_tool(self):
        """Test registering a custom tool."""
        def custom_tool(args: str) -> str:
            return f"Custom result: {args}"
        
        self.broker.register_tool(
            ToolDefinition(
                name="custom",
                description="Custom tool",
                category=ToolCategory.COMPUTE,
                handler=custom_tool,
            )
        )
        
        result = self.broker.handle_tool_request("[TOOL:custom] test args")
        
        assert result.success is True
        assert "Custom result: test args" in result.result
    
    def test_extract_tool_calls(self):
        """Test extracting multiple tool calls."""
        model_output = """
        Let me calculate that.
        [TOOL:calculator] 5 * 7
        And also:
        [TOOL:calculator] 10 + 3
        """
        
        tool_calls = self.broker.extract_tool_calls(model_output)
        
        assert len(tool_calls) == 2
        assert tool_calls[0][2].tool_name == "calculator"
        assert "5 * 7" in tool_calls[0][2].arguments
        assert tool_calls[1][2].tool_name == "calculator"
        assert "10 + 3" in tool_calls[1][2].arguments


class TestToolBrokerAsync:
    """Async tests for ToolBroker."""
    
    def setup_method(self):
        """Set up test fixtures."""
        reset_tool_broker()
        self.broker = ToolBroker(enable_sandbox=False)
    
    @pytest.mark.asyncio
    async def test_handle_calculator_async(self):
        """Test async calculator handling."""
        result = await self.broker.handle_tool_request_async("[TOOL:calculator] 5 * 7")
        
        assert result.success is True
        assert "35" in result.result
    
    @pytest.mark.asyncio
    async def test_handle_web_search_async(self):
        """Test async web search handling (mocked)."""
        # Mock web research
        mock_doc = MagicMock()
        mock_doc.title = "Python Programming"
        mock_doc.snippet = "Python is a programming language..."
        mock_doc.url = "https://python.org"
        
        self.broker.web_research = MagicMock()
        self.broker.web_research.search = AsyncMock(return_value=[mock_doc])
        
        result = await self.broker.handle_tool_request_async("[TOOL:web_search] Python programming")
        
        assert result.success is True
        assert "Python" in result.result
    
    @pytest.mark.asyncio
    async def test_process_model_output_with_tools(self):
        """Test processing model output with embedded tool calls."""
        model_output = """
        To solve this, I need to calculate:
        [TOOL:calculator] 5 * 7
        The result is above.
        """
        
        processed, results = await self.broker.process_model_output_with_tools(
            model_output,
            user_tier="free"
        )
        
        assert len(results) == 1
        assert results[0].success is True
        assert "[Tool Result (calculator)]" in processed
        assert "35" in processed
    
    @pytest.mark.asyncio
    async def test_process_multiple_tool_calls(self):
        """Test processing multiple tool calls."""
        model_output = """
        First: [TOOL:calculator] 10 + 5
        Second: [TOOL:calculator] 3 * 4
        """
        
        processed, results = await self.broker.process_model_output_with_tools(
            model_output,
            user_tier="free"
        )
        
        assert len(results) == 2
        assert all(r.success for r in results)
        assert "15" in processed
        assert "12" in processed
    
    @pytest.mark.asyncio
    async def test_process_no_tool_calls(self):
        """Test processing output with no tool calls."""
        model_output = "This is just regular text without any tool calls."
        
        processed, results = await self.broker.process_model_output_with_tools(
            model_output,
            user_tier="free"
        )
        
        assert len(results) == 0
        assert processed == model_output
    
    @pytest.mark.asyncio
    async def test_max_tool_calls_limit(self):
        """Test max tool calls limit."""
        model_output = """
        [TOOL:calculator] 1+1
        [TOOL:calculator] 2+2
        [TOOL:calculator] 3+3
        [TOOL:calculator] 4+4
        [TOOL:calculator] 5+5
        [TOOL:calculator] 6+6
        """
        
        processed, results = await self.broker.process_model_output_with_tools(
            model_output,
            user_tier="free",
            max_tool_calls=3
        )
        
        # Should only execute 3 tool calls
        assert len(results) == 3


class TestKnowledgeLookup:
    """Tests for knowledge lookup tool."""
    
    def setup_method(self):
        """Set up test fixtures."""
        reset_tool_broker()
        
        # Create mock memory manager
        self.mock_memory = MagicMock()
        self.mock_hit = MagicMock()
        self.mock_hit.text = "Paris is the capital of France"
        self.mock_hit.score = 0.9
        self.mock_memory.query_memory = MagicMock(return_value=[self.mock_hit])
        
        self.broker = ToolBroker(enable_sandbox=False, memory_manager=self.mock_memory)
    
    def test_knowledge_lookup_success(self):
        """Test knowledge lookup with results."""
        result = self.broker.handle_tool_request(
            "[TOOL:knowledge_lookup] capital of France",
            user_tier="pro"
        )
        
        assert result.success is True
        assert "Paris" in result.result or "capital" in result.result
    
    def test_knowledge_lookup_no_results(self):
        """Test knowledge lookup with no results."""
        self.mock_memory.query_memory = MagicMock(return_value=[])
        
        result = self.broker.handle_tool_request(
            "[TOOL:knowledge_lookup] obscure topic",
            user_tier="pro"
        )
        
        assert result.success is True
        assert "No relevant knowledge" in result.result
    
    def test_knowledge_lookup_free_tier_blocked(self):
        """Test knowledge lookup blocked for free tier."""
        result = self.broker.handle_tool_request(
            "[TOOL:knowledge_lookup] test query",
            user_tier="free"
        )
        
        assert result.success is False
        assert "not available" in result.error.lower()


class TestPythonExecution:
    """Tests for Python execution tool."""
    
    def setup_method(self):
        """Set up test fixtures."""
        reset_tool_broker()
        self.broker = ToolBroker(enable_sandbox=True)
    
    def test_python_exec_simple(self):
        """Test simple Python execution."""
        result = self.broker.handle_tool_request(
            "[TOOL:python_exec] print(2 + 2)",
            user_tier="pro"
        )
        
        # Result depends on sandbox availability
        assert result.tool_name == "python_exec"
    
    def test_python_exec_free_tier_blocked(self):
        """Test Python exec blocked for free tier."""
        result = self.broker.handle_tool_request(
            "[TOOL:python_exec] print('hello')",
            user_tier="free"
        )
        
        assert result.success is False
        assert "not available" in result.error.lower()


class TestGlobalToolBroker:
    """Tests for global tool broker instance."""
    
    def test_get_tool_broker(self):
        """Test getting global tool broker."""
        reset_tool_broker()
        broker1 = get_tool_broker()
        broker2 = get_tool_broker()
        
        assert broker1 is broker2
    
    def test_reset_tool_broker(self):
        """Test resetting global tool broker."""
        broker1 = get_tool_broker()
        reset_tool_broker()
        broker2 = get_tool_broker()
        
        assert broker1 is not broker2


class TestIntegrationScenarios:
    """Integration tests for tool broker scenarios."""
    
    def setup_method(self):
        """Set up test fixtures."""
        reset_tool_broker()
        self.broker = ToolBroker(enable_sandbox=False)
    
    def test_calculator_in_model_output(self):
        """Test calculator tool simulating model output."""
        # Simulate model output
        model_output = "[TOOL:calculator] 5*7"
        
        result = self.broker.handle_tool_request(model_output)
        
        assert result.success is True
        assert result.result == "35"
    
    def test_web_search_simulation(self):
        """Test web search tool simulation."""
        # Mock web research
        mock_doc = MagicMock()
        mock_doc.title = "Python - Wikipedia"
        mock_doc.snippet = "Python is a high-level programming language"
        mock_doc.url = "https://en.wikipedia.org/wiki/Python"
        
        self.broker.web_research = MagicMock()
        self.broker.web_research.search = AsyncMock(return_value=[mock_doc])
        
        # This would be called from async context
        # Just verify the tool exists
        assert "web_search" in [t["name"] for t in self.broker.list_tools()]
    
    @pytest.mark.asyncio
    async def test_full_pipeline(self):
        """Test full pipeline with tool processing."""
        # Model output with multiple tool calls
        model_output = """
        I'll help you with these calculations:
        
        First: [TOOL:calculator] 100 / 4
        
        Now let's add: [TOOL:calculator] 25 + 10
        
        The final answers are shown above.
        """
        
        processed, results = await self.broker.process_model_output_with_tools(
            model_output,
            user_tier="free"
        )
        
        # Should have processed both tool calls
        assert len(results) == 2
        assert all(r.success for r in results)
        
        # Results should be in output
        assert "[Tool Result (calculator)]" in processed
        assert "25" in processed
        assert "35" in processed


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

