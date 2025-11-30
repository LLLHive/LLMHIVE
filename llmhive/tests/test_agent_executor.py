"""Tests for AgentExecutor and autonomous task execution.

These tests verify:
1. Basic agent execution loop
2. Tool integration and result handling
3. Tier-based limits and stopping criteria
4. Multi-step task planning
5. Scratchpad state management
"""
from __future__ import annotations

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Any, Dict

# Import modules under test
from llmhive.src.llmhive.app.agent_executor import (
    AgentExecutor,
    AgentExecutionResult,
    AgentStep,
    AgentAction,
    AgentStatus,
    AgentScratchpad,
    AGENT_TIER_LIMITS,
    build_tool_descriptions,
)


# ==============================================================================
# Test Fixtures
# ==============================================================================

@pytest.fixture
def mock_tool_broker():
    """Create a mock ToolBroker."""
    broker = MagicMock()
    
    # Tool definitions
    broker.tool_definitions = {
        "calculator": MagicMock(
            description="Calculate mathematical expressions",
            parameters={"expression": "Math expression to evaluate"},
        ),
        "web_search": MagicMock(
            description="Search the web for information",
            parameters={"query": "Search query"},
        ),
        "knowledge_lookup": MagicMock(
            description="Look up information in knowledge base",
            parameters={"query": "Query to search"},
        ),
    }
    
    # Mock tool execution
    async def mock_handle_request(request, user_tier):
        result = MagicMock()
        result.success = True
        
        if request.tool_name == "calculator":
            # Simple calculation mock
            args = request.arguments
            if "factorial(5)" in args or "5!" in args:
                result.result = "124"  # 5! + sqrt(16) = 120 + 4 = 124
            elif "sqrt" in args:
                result.result = "4"
            else:
                result.result = "42"
        elif request.tool_name == "web_search":
            result.result = "France population: 1900: 40.6M, 1950: 41.8M, 2000: 60.9M"
        else:
            result.result = "Tool result"
        
        return result
    
    broker.handle_tool_request_async = mock_handle_request
    
    return broker


@pytest.fixture
def mock_provider():
    """Create a mock LLM provider."""
    provider = MagicMock()
    call_count = 0
    
    async def mock_generate(prompt: str, model: str = "test", **kwargs):
        nonlocal call_count
        call_count += 1
        result = MagicMock()
        
        # Simulate agent behavior based on prompt content
        if "Calculate" in prompt or "factorial" in prompt.lower():
            if call_count == 1:
                # First call: use calculator
                result.content = "I need to calculate this. [TOOL:calculator] factorial(5) + sqrt(16)"
            else:
                # Second call: provide answer
                result.content = "[ANSWER] The result is 124. This is calculated as 5! (120) plus sqrt(16) (4)."
        
        elif "Research" in prompt or "population" in prompt.lower():
            if "Result from web_search" in prompt:
                # Already have results, provide answer
                result.content = "[ANSWER] Based on my research:\n- 1900: 40.6 million\n- 1950: 41.8 million\n- 2000: 60.9 million"
            else:
                # First call: search for info
                result.content = "Let me search for population data. [TOOL:web_search] France population 1900 1950 2000"
        
        else:
            # Default behavior
            result.content = "[ANSWER] Here is your answer based on the available information."
        
        result.tokens_used = 100
        return result
    
    provider.generate = mock_generate
    return provider


@pytest.fixture
def mock_providers(mock_provider):
    """Create dict of mock providers."""
    return {
        "openai": mock_provider,
        "anthropic": mock_provider,
        "stub": mock_provider,
    }


# ==============================================================================
# AgentScratchpad Tests
# ==============================================================================

class TestAgentScratchpad:
    """Tests for AgentScratchpad."""
    
    def test_init(self):
        """Test scratchpad initialization."""
        scratchpad = AgentScratchpad("Test task")
        assert scratchpad.task == "Test task"
        assert len(scratchpad.thoughts) == 0
        assert len(scratchpad.actions) == 0
    
    def test_add_thought(self):
        """Test adding thoughts."""
        scratchpad = AgentScratchpad("Test")
        scratchpad.add_thought("I need to calculate this")
        
        assert len(scratchpad.thoughts) == 1
        assert "calculate" in scratchpad.thoughts[0]
        assert "Thought:" in scratchpad.context_accumulator[0]
    
    def test_add_action(self):
        """Test adding actions."""
        scratchpad = AgentScratchpad("Test")
        scratchpad.add_action("tool_call", "calculator", "5 + 3")
        
        assert len(scratchpad.actions) == 1
        assert scratchpad.actions[0]["tool"] == "calculator"
    
    def test_add_tool_result(self):
        """Test adding tool results."""
        scratchpad = AgentScratchpad("Test")
        scratchpad.add_tool_result("calculator", "8")
        
        assert len(scratchpad.tool_results) == 1
        assert "calculator" in list(scratchpad.tool_results.keys())[0]
    
    def test_set_and_get_variable(self):
        """Test variable storage."""
        scratchpad = AgentScratchpad("Test")
        scratchpad.set_variable("result1", 42)
        
        assert scratchpad.get_variable("result1") == 42
        assert scratchpad.get_variable("nonexistent") is None
    
    def test_get_context(self):
        """Test context accumulation."""
        scratchpad = AgentScratchpad("Test")
        scratchpad.add_thought("First thought")
        scratchpad.add_action("tool_call", "calculator", "2+2")
        scratchpad.add_tool_result("calculator", "4")
        
        context = scratchpad.get_context()
        assert "Thought: First thought" in context
        assert "calculator" in context
        assert "Result from calculator: 4" in context
    
    def test_get_summary(self):
        """Test summary generation."""
        scratchpad = AgentScratchpad("Test task")
        scratchpad.add_thought("Thought 1")
        scratchpad.add_thought("Thought 2")
        scratchpad.add_tool_result("tool1", "result1")
        
        summary = scratchpad.get_summary()
        assert summary["task"] == "Test task"
        assert summary["num_thoughts"] == 2
        assert summary["num_tool_results"] == 1
    
    def test_clear(self):
        """Test clearing scratchpad."""
        scratchpad = AgentScratchpad("Test")
        scratchpad.add_thought("Thought")
        scratchpad.add_tool_result("tool", "result")
        
        scratchpad.clear()
        
        assert len(scratchpad.thoughts) == 0
        assert len(scratchpad.tool_results) == 0
        # Task should remain
        assert scratchpad.task == "Test"


# ==============================================================================
# AgentExecutor Tests
# ==============================================================================

class TestAgentExecutor:
    """Tests for AgentExecutor."""
    
    @pytest.mark.asyncio
    async def test_basic_execution(self, mock_providers, mock_tool_broker):
        """Test basic agent execution."""
        executor = AgentExecutor(mock_providers, mock_tool_broker)
        
        result = await executor.execute(
            "What is 2 + 2?",
            user_tier="free",
        )
        
        assert isinstance(result, AgentExecutionResult)
        assert result.final_answer is not None
        assert len(result.steps) > 0
    
    @pytest.mark.asyncio
    async def test_tool_call_execution(self, mock_providers, mock_tool_broker):
        """Test execution with tool calls."""
        executor = AgentExecutor(mock_providers, mock_tool_broker)
        
        result = await executor.execute(
            "Calculate factorial(5) + sqrt(16)",
            user_tier="pro",
        )
        
        assert result.success
        assert result.total_tool_calls >= 1
        # Should have used calculator
        tool_calls = result.tool_calls_made
        assert any(tc["tool"] == "calculator" for tc in tool_calls)
    
    @pytest.mark.asyncio
    async def test_multi_step_research(self, mock_providers, mock_tool_broker):
        """Test multi-step research task."""
        executor = AgentExecutor(mock_providers, mock_tool_broker)
        
        result = await executor.execute(
            "Research the population of France in 1900, 1950, and 2000",
            user_tier="pro",
        )
        
        assert result.success
        assert "population" in result.final_answer.lower() or result.total_tool_calls > 0
    
    @pytest.mark.asyncio
    async def test_tier_limits_free(self, mock_providers, mock_tool_broker):
        """Test free tier limits."""
        # Modify provider to always request tools
        provider = mock_providers["openai"]
        call_count = 0
        
        async def always_tool(prompt, model="test", **kwargs):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            result.content = f"[TOOL:calculator] {call_count} + {call_count}"
            result.tokens_used = 50
            return result
        
        provider.generate = always_tool
        
        executor = AgentExecutor(mock_providers, mock_tool_broker)
        
        result = await executor.execute(
            "Keep calculating",
            user_tier="free",
            max_iterations=10,  # Allow many iterations
        )
        
        # Free tier: max 2 tool calls
        assert result.total_tool_calls <= AGENT_TIER_LIMITS["free"]["max_tool_calls"]
    
    @pytest.mark.asyncio
    async def test_max_iterations_limit(self, mock_providers, mock_tool_broker):
        """Test max iterations limit."""
        # Provider that never gives an answer
        provider = mock_providers["openai"]
        
        async def endless_thinking(prompt, model="test", **kwargs):
            result = MagicMock()
            result.content = "Let me think more about this..."
            result.tokens_used = 50
            return result
        
        provider.generate = endless_thinking
        
        executor = AgentExecutor(mock_providers, mock_tool_broker)
        
        result = await executor.execute(
            "Think forever",
            user_tier="free",
            max_iterations=3,
        )
        
        assert result.total_iterations == 3
        assert result.status in (AgentStatus.MAX_ITERATIONS, AgentStatus.COMPLETED)
    
    @pytest.mark.asyncio
    async def test_step_callback(self, mock_providers, mock_tool_broker):
        """Test step callback."""
        executor = AgentExecutor(mock_providers, mock_tool_broker)
        
        steps_received = []
        
        def on_step(step):
            steps_received.append(step)
        
        result = await executor.execute(
            "Calculate 5 + 5",
            user_tier="free",
            on_step=on_step,
        )
        
        assert len(steps_received) > 0
        assert all(isinstance(s, AgentStep) for s in steps_received)
    
    @pytest.mark.asyncio
    async def test_disallowed_tool_for_tier(self, mock_providers, mock_tool_broker):
        """Test that disallowed tools are blocked."""
        # Free tier should not have access to advanced tools
        provider = mock_providers["openai"]
        
        async def request_advanced_tool(prompt, model="test", **kwargs):
            result = MagicMock()
            result.content = "[TOOL:python_exec] print('hello')"
            result.tokens_used = 50
            return result
        
        provider.generate = request_advanced_tool
        
        executor = AgentExecutor(mock_providers, mock_tool_broker)
        
        result = await executor.execute(
            "Execute python code",
            user_tier="free",
            max_iterations=2,
        )
        
        # Tool should be blocked
        for step in result.steps:
            if step.tool_name == "python_exec":
                assert "not available" in (step.tool_result or "").lower()


# ==============================================================================
# Agent Parsing Tests
# ==============================================================================

class TestAgentParsing:
    """Tests for agent response parsing."""
    
    def test_parse_tool_request(self, mock_providers, mock_tool_broker):
        """Test parsing tool requests."""
        executor = AgentExecutor(mock_providers, mock_tool_broker)
        
        response = "[TOOL:calculator] 5 + 3"
        action, parsed = executor._parse_response(response)
        
        assert action == AgentAction.TOOL_CALL
        assert parsed["tool_name"] == "calculator"
        assert "5 + 3" in parsed["tool_args"]
    
    def test_parse_answer(self, mock_providers, mock_tool_broker):
        """Test parsing final answer."""
        executor = AgentExecutor(mock_providers, mock_tool_broker)
        
        response = "[ANSWER] The result is 42."
        action, parsed = executor._parse_response(response)
        
        assert action == AgentAction.ANSWER
        assert "42" in parsed["answer"]
    
    def test_parse_thought(self, mock_providers, mock_tool_broker):
        """Test parsing thoughts."""
        executor = AgentExecutor(mock_providers, mock_tool_broker)
        
        response = "Thought: I need to analyze this problem first."
        action, parsed = executor._parse_response(response)
        
        assert action == AgentAction.THINK
        assert "analyze" in parsed["thought"].lower()
    
    def test_looks_like_answer(self, mock_providers, mock_tool_broker):
        """Test answer detection."""
        executor = AgentExecutor(mock_providers, mock_tool_broker)
        
        assert executor._looks_like_answer("The answer is 42.") is True
        assert executor._looks_like_answer("Therefore, the result is correct.") is True
        assert executor._looks_like_answer("[TOOL:calculator] 5 + 3") is False
        assert executor._looks_like_answer("Let me think...") is False


# ==============================================================================
# Tier Limits Configuration Tests
# ==============================================================================

class TestTierLimits:
    """Tests for tier-based limits."""
    
    def test_free_tier_limits(self):
        """Test free tier has restrictive limits."""
        limits = AGENT_TIER_LIMITS["free"]
        
        assert limits["max_iterations"] <= 5
        assert limits["max_tool_calls"] <= 3
        assert "calculator" in limits["allowed_tools"]
        assert "python_exec" not in limits["allowed_tools"]
    
    def test_pro_tier_limits(self):
        """Test pro tier has more generous limits."""
        limits = AGENT_TIER_LIMITS["pro"]
        
        assert limits["max_iterations"] > AGENT_TIER_LIMITS["free"]["max_iterations"]
        assert limits["max_tool_calls"] > AGENT_TIER_LIMITS["free"]["max_tool_calls"]
        assert "python_exec" in limits["allowed_tools"]
    
    def test_enterprise_tier_limits(self):
        """Test enterprise tier has highest limits."""
        limits = AGENT_TIER_LIMITS["enterprise"]
        
        assert limits["max_iterations"] >= 20
        assert limits["max_tool_calls"] >= 15
        assert "advanced_search" in limits["allowed_tools"]


# ==============================================================================
# Tool Description Tests
# ==============================================================================

class TestToolDescriptions:
    """Tests for tool description building."""
    
    def test_build_tool_descriptions(self, mock_tool_broker):
        """Test building tool descriptions."""
        descriptions = build_tool_descriptions(mock_tool_broker)
        
        assert "calculator" in descriptions
        assert "web_search" in descriptions
        assert "Calculate" in descriptions


# ==============================================================================
# AgentExecutionResult Tests
# ==============================================================================

class TestAgentExecutionResult:
    """Tests for AgentExecutionResult."""
    
    def test_tool_calls_made(self):
        """Test tool_calls_made property."""
        steps = [
            AgentStep(
                step_number=1,
                action=AgentAction.TOOL_CALL,
                content="",
                tool_name="calculator",
                tool_args="5 + 3",
                tool_result="8",
            ),
            AgentStep(
                step_number=2,
                action=AgentAction.ANSWER,
                content="The answer is 8",
            ),
        ]
        
        result = AgentExecutionResult(
            success=True,
            final_answer="The answer is 8",
            status=AgentStatus.COMPLETED,
            steps=steps,
        )
        
        tool_calls = result.tool_calls_made
        assert len(tool_calls) == 1
        assert tool_calls[0]["tool"] == "calculator"
        assert tool_calls[0]["result"] == "8"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

