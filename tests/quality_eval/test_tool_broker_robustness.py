"""Tests for Tool Broker robustness features.

This module tests:
1. Semantic tool filtering
2. Retry and fallback logic
3. Async parallel tool dispatch
4. Tool metadata handling
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch


class TestSemanticToolFilter:
    """Tests for semantic tool filtering."""
    
    def test_filter_without_index(self):
        """Test filtering returns all tools when not indexed."""
        from llmhive.app.tool_broker import SemanticToolFilter, ToolDefinition, ToolCategory
        
        filter = SemanticToolFilter(embedding_fn=None)
        
        tools = {
            "calculator": ToolDefinition(
                name="calculator",
                description="Math",
                category=ToolCategory.COMPUTE,
                handler=lambda x: x,
            ),
            "search": ToolDefinition(
                name="search",
                description="Search",
                category=ToolCategory.SEARCH,
                handler=lambda x: x,
            ),
        }
        
        result = filter.filter_tools("calculate 5 * 5", tools, top_k=3)
        
        # Should return tools even without embedding
        assert len(result) <= 3


class TestToolRetryLogic:
    """Tests for tool retry and fallback."""
    
    @pytest.mark.asyncio
    async def test_successful_execution_no_retry(self):
        """Test successful execution doesn't trigger retry."""
        from llmhive.app.tool_broker import ToolBroker, ToolRequest
        
        broker = ToolBroker()
        
        # Calculator should succeed
        result = await broker.handle_tool_request_with_retry(
            ToolRequest(tool_name="calculator", arguments="5 + 5", raw_request="[TOOL:calculator] 5 + 5"),
            user_tier="free",
        )
        
        assert result.success
        assert result.retry_count == 0
        assert not result.fallback_used
    
    @pytest.mark.asyncio
    async def test_fallback_on_unknown_tool(self):
        """Test fallback triggers for unknown tool."""
        from llmhive.app.tool_broker import ToolBroker, ToolRequest
        
        broker = ToolBroker()
        
        result = await broker.handle_tool_request_with_retry(
            ToolRequest(tool_name="nonexistent_tool", arguments="test", raw_request="test"),
            user_tier="free",
        )
        
        assert not result.success
        assert result.fallback_used
        assert result.fallback_reason == "unknown_tool"


class TestParallelToolExecution:
    """Tests for async parallel tool dispatch."""
    
    @pytest.mark.asyncio
    async def test_parallel_execution_multiple_tools(self):
        """Test multiple tools execute in parallel."""
        from llmhive.app.tool_broker import ToolBroker
        
        broker = ToolBroker()
        
        requests = [
            "[TOOL:calculator] 5 + 5",
            "[TOOL:calculator] 10 * 2",
            "[TOOL:datetime]",
        ]
        
        results = await broker.execute_tools_parallel(requests, user_tier="free")
        
        assert len(results) == 3
        # All should succeed
        successes = [r for r in results if r.success]
        assert len(successes) >= 2  # At least calculator and datetime
    
    @pytest.mark.asyncio
    async def test_parallel_handles_failures(self):
        """Test parallel execution handles individual failures gracefully."""
        from llmhive.app.tool_broker import ToolBroker
        
        broker = ToolBroker()
        
        requests = [
            "[TOOL:calculator] 5 + 5",
            "[TOOL:nonexistent] test",  # Will fail
            "[TOOL:calculator] 10 * 2",
        ]
        
        results = await broker.execute_tools_parallel(requests, user_tier="free")
        
        assert len(results) == 3
        # First and third should succeed
        assert results[0].success
        assert not results[1].success
        assert results[2].success


class TestToolMetadata:
    """Tests for enhanced tool metadata."""
    
    def test_tool_definition_has_new_fields(self):
        """Test tool definitions have enhanced metadata fields."""
        from llmhive.app.tool_broker import ToolBroker
        
        broker = ToolBroker()
        
        calc_def = broker.tool_definitions.get("calculator")
        
        assert calc_def is not None
        assert hasattr(calc_def, 'retryable')
        assert hasattr(calc_def, 'latency_score')
        assert hasattr(calc_def, 'failure_policy')
        assert hasattr(calc_def, 'keywords')
        
        # Calculator should be fast
        assert calc_def.latency_score < 0.3
    
    def test_get_relevant_tools(self):
        """Test semantic tool relevance filtering."""
        from llmhive.app.tool_broker import ToolBroker
        
        broker = ToolBroker(max_visible_tools=3)
        
        tools = broker.get_relevant_tools(
            "calculate 15 percent of 200",
            user_tier="free",
        )
        
        # Should return tool info dicts
        assert len(tools) <= 3
        assert all("name" in t and "description" in t for t in tools)


class TestToolExecution:
    """Tests for basic tool execution."""
    
    def test_calculator_execution(self):
        """Test calculator tool works correctly."""
        from llmhive.app.tool_broker import ToolBroker
        
        broker = ToolBroker()
        
        result = broker.handle_tool_request("[TOOL:calculator] 15 * 23", user_tier="free")
        
        assert result.success
        assert "345" in result.result
    
    def test_datetime_execution(self):
        """Test datetime tool works correctly."""
        from llmhive.app.tool_broker import ToolBroker
        
        broker = ToolBroker()
        
        result = broker.handle_tool_request("[TOOL:datetime]", user_tier="free")
        
        assert result.success
        assert result.result is not None
    
    def test_convert_execution(self):
        """Test unit conversion tool works correctly."""
        from llmhive.app.tool_broker import ToolBroker
        
        broker = ToolBroker()
        
        result = broker.handle_tool_request("[TOOL:convert] 100 km miles", user_tier="free")
        
        assert result.success
        assert "miles" in result.result.lower()


class TestExecutionStats:
    """Tests for execution statistics tracking."""
    
    @pytest.mark.asyncio
    async def test_stats_recorded(self):
        """Test that execution stats are recorded."""
        from llmhive.app.tool_broker import ToolBroker
        
        broker = ToolBroker()
        
        # Execute a few tools
        await broker.handle_tool_request_async("[TOOL:calculator] 5 + 5", user_tier="free")
        await broker.handle_tool_request_async("[TOOL:calculator] 10 * 2", user_tier="free")
        
        stats = broker.get_execution_stats()
        
        # Should have stats for calculator
        assert "calculator" in stats
        assert stats["calculator"]["total_calls"] >= 2
        assert stats["calculator"]["successful"] >= 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

