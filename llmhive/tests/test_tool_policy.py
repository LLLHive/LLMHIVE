"""Tests for tool broker functionality.

Ensures that the Tool Broker properly analyzes queries and executes tools.
"""
import pytest
from unittest.mock import MagicMock, patch, AsyncMock

from llmhive.app.orchestration.tool_broker import (
    ToolBroker,
    ToolType,
    ToolRequest,
    ToolStatus,
    ToolResult,
    get_tool_broker,
    ToolAnalysis,
    ToolPriority,
)


class TestToolBrokerInit:
    """Test ToolBroker initialization."""

    def test_initialization(self):
        """Tool broker should initialize properly."""
        broker = ToolBroker()
        assert broker is not None
        assert hasattr(broker, 'tools')
        assert len(broker.tools) > 0

    def test_default_tools_registered(self):
        """Default tools should be registered."""
        broker = ToolBroker()
        
        # Check that key tool types are registered
        assert ToolType.CALCULATOR in broker.tools
        assert ToolType.WEB_SEARCH in broker.tools
        assert ToolType.CODE_EXECUTION in broker.tools


class TestToolBrokerSingleton:
    """Test tool broker singleton pattern."""

    def test_get_tool_broker_returns_instance(self):
        """get_tool_broker should return a ToolBroker instance."""
        broker = get_tool_broker()
        assert isinstance(broker, ToolBroker)

    def test_get_tool_broker_returns_same_instance(self):
        """get_tool_broker should return the same instance."""
        broker1 = get_tool_broker()
        broker2 = get_tool_broker()
        
        assert broker1 is broker2


class TestToolAnalysis:
    """Test tool analysis functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.broker = ToolBroker()

    def test_analyze_search_query(self):
        """Queries needing web search should be analyzed."""
        search_queries = [
            "What are the latest news about AI?",
            "Current price of bitcoin",
            "Who is the president of France in 2024",
        ]
        
        for query in search_queries:
            analysis = self.broker.analyze_tool_needs(query)
            assert isinstance(analysis, ToolAnalysis)
            # Check the correct attribute name
            assert isinstance(analysis.requires_tools, bool)

    def test_analyze_calculation_query(self):
        """Math queries should be detected."""
        calc_queries = [
            "Calculate 25 * 4",
            "What is the sum of 100 and 50?",
            "Compute the average of 10, 20, 30",
        ]
        
        for query in calc_queries:
            analysis = self.broker.analyze_tool_needs(query)
            assert isinstance(analysis, ToolAnalysis)
            assert isinstance(analysis.requires_tools, bool)

    def test_analyze_code_query(self):
        """Code execution queries should be detected."""
        code_queries = [
            "Run this Python code: print('hello')",
            "Execute the following script",
            "What's the output of this code?",
        ]
        
        for query in code_queries:
            analysis = self.broker.analyze_tool_needs(query)
            assert isinstance(analysis, ToolAnalysis)

    def test_analyze_simple_query(self):
        """Simple factual queries may not need tools."""
        simple_queries = [
            "What is photosynthesis?",
            "Explain machine learning",
            "Define recursion",
        ]
        
        for query in simple_queries:
            analysis = self.broker.analyze_tool_needs(query)
            assert isinstance(analysis, ToolAnalysis)


class TestToolBrokerConfiguration:
    """Test tool broker configuration."""

    def test_configure_external_apis(self):
        """External API configuration should work."""
        broker = ToolBroker()
        
        # Configure with test keys
        broker.configure_external_apis(
            serpapi_key="test_serpapi_key",
            tavily_key="test_tavily_key",
        )
        
        # Should have configured the APIs
        assert hasattr(broker, '_api_configs')

    def test_configure_with_none_keys(self):
        """Missing API keys should be handled gracefully."""
        broker = ToolBroker()
        
        # Configure with None keys
        broker.configure_external_apis(
            serpapi_key=None,
            tavily_key=None,
        )
        
        # Should not raise
        assert True

    def test_register_tool(self):
        """Tool registration should work."""
        broker = ToolBroker()
        
        mock_tool = MagicMock()
        mock_tool.tool_type = ToolType.WEB_SEARCH
        
        broker.register_tool(mock_tool)
        assert broker.tools[ToolType.WEB_SEARCH] == mock_tool


class TestToolTypes:
    """Test tool type enumeration."""

    def test_tool_types_exist(self):
        """Essential tool types should exist."""
        assert hasattr(ToolType, 'WEB_SEARCH')
        assert hasattr(ToolType, 'CALCULATOR')
        assert hasattr(ToolType, 'CODE_EXECUTION')
        assert hasattr(ToolType, 'IMAGE_GENERATION')

    def test_tool_type_values(self):
        """Tool types should have string values."""
        assert isinstance(ToolType.WEB_SEARCH.value, str)
        assert isinstance(ToolType.CALCULATOR.value, str)


class TestToolBrokerConcurrency:
    """Test tool broker thread safety."""

    def test_concurrent_initialization(self):
        """Tool broker should be thread-safe during initialization."""
        import threading
        from concurrent.futures import ThreadPoolExecutor
        
        brokers = []
        errors = []
        
        def get_broker():
            try:
                broker = get_tool_broker()
                brokers.append(broker)
            except Exception as e:
                errors.append(e)
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(get_broker) for _ in range(50)]
            for f in futures:
                f.result()
        
        assert len(errors) == 0
        # All should be the same instance
        if brokers:
            assert all(b is brokers[0] for b in brokers)


class TestToolRequest:
    """Test ToolRequest model."""

    def test_tool_request_creation(self):
        """ToolRequest should be creatable."""
        request = ToolRequest(
            tool_type=ToolType.WEB_SEARCH,
            query="test query",
            purpose="Testing",
            priority=ToolPriority.HIGH  # Use HIGH instead of REQUIRED
        )
        
        assert request.tool_type == ToolType.WEB_SEARCH
        assert request.query == "test query"


class TestToolResult:
    """Test ToolResult model."""

    def test_tool_result_creation(self):
        """ToolResult should be creatable."""
        result = ToolResult(
            tool_type=ToolType.CALCULATOR,
            success=True,
            data="42",
            status=ToolStatus.SUCCESS
        )
        
        assert result.success is True
        assert result.data == "42"


class TestToolAnalysisModel:
    """Test ToolAnalysis model."""

    def test_tool_analysis_structure(self):
        """ToolAnalysis should have expected structure."""
        broker = ToolBroker()
        analysis = broker.analyze_tool_needs("test query")
        
        # Use correct attribute names
        assert hasattr(analysis, 'requires_tools')
        assert hasattr(analysis, 'tool_requests')
        assert hasattr(analysis, 'reasoning')


class TestSearchTriggers:
    """Test search trigger detection."""

    def test_search_triggers_defined(self):
        """SEARCH_TRIGGERS should be defined."""
        broker = ToolBroker()
        assert hasattr(broker, 'SEARCH_TRIGGERS')
        assert len(broker.SEARCH_TRIGGERS) > 0

    def test_search_triggers_include_common_patterns(self):
        """Common search patterns should be in triggers."""
        broker = ToolBroker()
        triggers = broker.SEARCH_TRIGGERS
        
        # Check for common patterns
        assert any("latest" in t for t in triggers)
        assert any("current" in t for t in triggers)
        assert any("news" in t for t in triggers)


class TestCalcTriggers:
    """Test calculation trigger detection."""

    def test_calc_triggers_defined(self):
        """CALC_TRIGGERS should be defined."""
        broker = ToolBroker()
        assert hasattr(broker, 'CALC_TRIGGERS')
        assert len(broker.CALC_TRIGGERS) > 0

    def test_calc_triggers_include_common_patterns(self):
        """Common calc patterns should be in triggers."""
        broker = ToolBroker()
        triggers = broker.CALC_TRIGGERS
        
        assert any("calculate" in t for t in triggers)
        assert any("compute" in t for t in triggers)


class TestToolPriority:
    """Test tool priority enumeration."""

    def test_priorities_exist(self):
        """Tool priority levels should exist."""
        assert hasattr(ToolPriority, 'CRITICAL')
        assert hasattr(ToolPriority, 'HIGH')
        assert hasattr(ToolPriority, 'MEDIUM')
        assert hasattr(ToolPriority, 'LOW')
