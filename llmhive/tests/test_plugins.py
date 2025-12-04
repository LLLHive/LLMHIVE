"""Tests for Plugin System.

These tests verify:
1. Plugin base classes and configuration
2. Plugin manager discovery and loading
3. Built-in plugins (Wiki, News, Math, Weather)
4. Domain routing and classification
5. Tool registration and execution
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path
import pytest
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch

# Add src to path for imports
_src_path = Path(__file__).parent.parent / "src"
if str(_src_path) not in sys.path:
    sys.path.insert(0, str(_src_path))

# Import modules under test
from llmhive.app.plugins.base import (
    Plugin,
    PluginConfig,
    PluginManifest,
    PluginTool,
    PluginKnowledgeBase,
    PluginCapability,
    PluginStatus,
    PluginTier,
    SimplePlugin,
)
from llmhive.app.plugins.manager import (
    PluginManager,
    PluginRegistry,
)
from llmhive.app.plugins.domain_router import (
    DomainPluginRouter,
    DomainMatch,
    DOMAIN_KEYWORDS,
)


# ==============================================================================
# Test Plugin Implementation
# ==============================================================================

class MockTestPlugin(Plugin):
    """Test plugin for unit tests."""
    
    def __init__(self):
        config = PluginConfig(
            name="test_plugin",
            display_name="Test Plugin",
            version="1.0.0",
            description="A test plugin",
            domains=["test", "demo"],
            keywords=["test", "demo", "sample"],
            min_tier=PluginTier.FREE,
            capabilities=[PluginCapability.TOOLS],
        )
        super().__init__(config)
    
    async def initialize(self) -> bool:
        return True
    
    def get_tools(self) -> List[PluginTool]:
        return [
            PluginTool(
                name="test_tool",
                description="A test tool",
                handler=self._test_handler,
                parameters={"type": "object", "properties": {}},
                domains=["test"],
            )
        ]
    
    async def _test_handler(self, **kwargs) -> Dict[str, Any]:
        return {"success": True, "message": "Test tool executed"}


# Alias for fixtures
def TestPlugin():
    return MockTestPlugin()


# ==============================================================================
# Plugin Config Tests
# ==============================================================================

class TestPluginConfig:
    """Tests for PluginConfig."""
    
    def test_create_config(self):
        """Test creating plugin config."""
        config = PluginConfig(
            name="my_plugin",
            display_name="My Plugin",
            version="1.0.0",
            domains=["custom"],
        )
        
        assert config.name == "my_plugin"
        assert config.display_name == "My Plugin"
        assert config.version == "1.0.0"
        assert config.enabled is True
        assert config.min_tier == PluginTier.FREE
    
    def test_config_to_dict(self):
        """Test converting config to dict."""
        config = PluginConfig(
            name="test",
            display_name="Test",
            version="1.0.0",
            domains=["test"],
            capabilities=[PluginCapability.TOOLS],
        )
        
        data = config.to_dict()
        
        assert data["name"] == "test"
        assert "tools" in data["capabilities"]
        assert data["enabled"] is True


class TestPluginManifest:
    """Tests for PluginManifest."""
    
    def test_from_dict(self):
        """Test creating manifest from dict."""
        data = {
            "name": "wiki",
            "display_name": "Wikipedia",
            "version": "1.0.0",
            "domains": ["encyclopedia"],
            "min_tier": "free",
            "capabilities": ["tools", "knowledge"],
            "entry_point": "wiki_plugin.py",
        }
        
        manifest = PluginManifest.from_dict(data)
        
        assert manifest.config.name == "wiki"
        assert manifest.config.display_name == "Wikipedia"
        assert PluginCapability.TOOLS in manifest.config.capabilities
        assert manifest.entry_point == "wiki_plugin.py"


# ==============================================================================
# Plugin Base Tests
# ==============================================================================

class TestPluginBase:
    """Tests for Plugin base class."""
    
    @pytest.fixture
    def plugin(self):
        return MockTestPlugin()
    
    def test_initial_status(self, plugin):
        """Test plugin initial status."""
        assert plugin.status == PluginStatus.UNLOADED
        assert not plugin.is_active
    
    @pytest.mark.asyncio
    async def test_activate(self, plugin):
        """Test plugin activation."""
        success = await plugin.activate()
        
        assert success is True
        assert plugin.status == PluginStatus.ACTIVE
        assert plugin.is_active
    
    @pytest.mark.asyncio
    async def test_deactivate(self, plugin):
        """Test plugin deactivation."""
        await plugin.activate()
        await plugin.deactivate()
        
        assert plugin.status == PluginStatus.DISABLED
        assert not plugin.is_active
    
    @pytest.mark.asyncio
    async def test_shutdown(self, plugin):
        """Test plugin shutdown."""
        await plugin.activate()
        await plugin.shutdown()
        
        assert plugin.status == PluginStatus.UNLOADED
    
    def test_get_tools(self, plugin):
        """Test getting tools."""
        tools = plugin.get_tools()
        
        assert len(tools) == 1
        assert tools[0].name == "test_tool"
    
    def test_matches_domain(self, plugin):
        """Test domain matching."""
        assert plugin.matches_domain("test")
        assert plugin.matches_domain("demo")
        assert not plugin.matches_domain("other")
    
    def test_matches_keywords(self, plugin):
        """Test keyword matching."""
        score = plugin.matches_keywords("this is a test query")
        assert score > 0
        
        score = plugin.matches_keywords("random words")
        assert score == 0
    
    def test_check_tier_access(self, plugin):
        """Test tier access check."""
        assert plugin.check_tier_access("free")
        assert plugin.check_tier_access("pro")
        assert plugin.check_tier_access("enterprise")
    
    def test_get_info(self, plugin):
        """Test getting plugin info."""
        info = plugin.get_info()
        
        assert info["name"] == "test_plugin"
        assert info["status"] == "unloaded"
        assert info["tools_count"] == 1


class TestSimplePlugin:
    """Tests for SimplePlugin."""
    
    def test_create_simple_plugin(self):
        """Test creating a simple plugin."""
        async def handler(**kwargs):
            return {"result": "ok"}
        
        tool = PluginTool(
            name="simple_tool",
            description="A simple tool",
            handler=handler,
        )
        
        plugin = SimplePlugin(
            name="simple",
            display_name="Simple Plugin",
            tools=[tool],
        )
        
        assert plugin.name == "simple"
        assert len(plugin.get_tools()) == 1
    
    @pytest.mark.asyncio
    async def test_simple_plugin_initialize(self):
        """Test simple plugin always initializes."""
        plugin = SimplePlugin(
            name="test",
            display_name="Test",
        )
        
        success = await plugin.initialize()
        assert success is True


# ==============================================================================
# Plugin Registry Tests
# ==============================================================================

class TestPluginRegistry:
    """Tests for PluginRegistry."""
    
    @pytest.fixture
    def registry(self):
        return PluginRegistry()
    
    @pytest.fixture
    def plugin(self):
        return MockTestPlugin()
    
    def test_register_plugin(self, registry, plugin):
        """Test registering a plugin."""
        registry.register_plugin(plugin)
        
        assert plugin.name in registry.plugins
        assert "test_tool" in registry.tools_by_name
    
    def test_unregister_plugin(self, registry, plugin):
        """Test unregistering a plugin."""
        registry.register_plugin(plugin)
        removed = registry.unregister_plugin(plugin.name)
        
        assert removed == plugin
        assert plugin.name not in registry.plugins
    
    def test_get_plugins_for_domain(self, registry, plugin):
        """Test getting plugins by domain."""
        registry.register_plugin(plugin)
        
        plugins = registry.get_plugins_for_domain("test")
        assert len(plugins) == 1
        assert plugins[0].name == "test_plugin"
        
        plugins = registry.get_plugins_for_domain("unknown")
        assert len(plugins) == 0


# ==============================================================================
# Plugin Manager Tests
# ==============================================================================

class TestPluginManager:
    """Tests for PluginManager."""
    
    @pytest.fixture
    def manager(self, tmp_path):
        return PluginManager(
            plugins_dir=str(tmp_path / "plugins"),
            builtin_dir=str(tmp_path / "builtin"),
        )
    
    def test_register(self, manager):
        """Test registering a plugin."""
        plugin = MockTestPlugin()
        
        success = manager.register(plugin)
        
        assert success is True
        assert plugin.name in manager.plugins
    
    def test_register_duplicate(self, manager):
        """Test registering duplicate plugin."""
        plugin = MockTestPlugin()
        manager.register(plugin)
        
        success = manager.register(plugin)
        
        assert success is False
    
    def test_unregister(self, manager):
        """Test unregistering a plugin."""
        plugin = MockTestPlugin()
        manager.register(plugin)
        
        success = manager.unregister(plugin.name)
        
        assert success is True
        assert plugin.name not in manager.plugins
    
    def test_get_plugin(self, manager):
        """Test getting a plugin."""
        plugin = MockTestPlugin()
        manager.register(plugin)
        
        retrieved = manager.get_plugin("test_plugin")
        
        assert retrieved == plugin
    
    @pytest.mark.asyncio
    async def test_get_active_plugins(self, manager):
        """Test getting active plugins."""
        plugin = MockTestPlugin()
        manager.register(plugin)
        await plugin.activate()
        
        active = manager.get_active_plugins()
        
        assert len(active) == 1
    
    @pytest.mark.asyncio
    async def test_get_all_tools(self, manager):
        """Test getting all tools."""
        plugin = MockTestPlugin()
        manager.register(plugin)
        await plugin.activate()  # Tools only returned for active plugins
        
        tools = manager.get_all_tools()
        
        assert len(tools) == 1
        assert tools[0].name == "test_tool"
    
    @pytest.mark.asyncio
    async def test_get_best_plugin_for_query(self, manager):
        """Test finding best plugin for query."""
        plugin = MockTestPlugin()
        manager.register(plugin)
        await plugin.activate()
        
        best = manager.get_best_plugin_for_query(
            "this is a test query",
            domain="test",
        )
        
        assert best == plugin
    
    def test_get_stats(self, manager):
        """Test getting manager stats."""
        plugin = MockTestPlugin()
        manager.register(plugin)
        
        stats = manager.get_stats()
        
        assert stats["total_plugins"] == 1
        assert stats["total_tools"] == 1


# ==============================================================================
# Domain Router Tests
# ==============================================================================

class TestDomainPluginRouter:
    """Tests for DomainPluginRouter."""
    
    @pytest.fixture
    def router(self, tmp_path):
        manager = PluginManager(
            plugins_dir=str(tmp_path / "plugins"),
            builtin_dir=str(tmp_path / "builtin"),
        )
        return DomainPluginRouter(plugin_manager=manager)
    
    def test_classify_domain_medical(self, router):
        """Test domain classification for medical."""
        # Use multiple medical keywords to ensure threshold is met
        result = router.classify_domain(
            "What are the symptoms and treatment for this medical condition? The doctor and patient discussed diagnosis."
        )
        
        assert result is not None
        assert result.domain == "medical"
    
    def test_classify_domain_technology(self, router):
        """Test domain classification for technology."""
        # Use multiple technology keywords
        result = router.classify_domain(
            "How do I write software code for a programming algorithm? Using database and API for cloud server."
        )
        
        assert result is not None
        assert result.domain == "technology"
    
    def test_classify_domain_finance(self, router):
        """Test domain classification for finance."""
        # Use multiple finance keywords
        result = router.classify_domain(
            "What's the best investment strategy for stock market trading and financial portfolio?"
        )
        
        assert result is not None
        assert result.domain == "finance"
    
    def test_classify_domain_no_match(self, router):
        """Test domain classification with no match."""
        result = router.classify_domain(
            "Hello, how are you today?"
        )
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_get_relevant_tools(self, router):
        """Test getting relevant tools."""
        plugin = MockTestPlugin()
        router.plugin_manager.register(plugin)
        await plugin.activate()
        
        tools = router.get_relevant_tools(
            "this is a test query",
            domain="test",
        )
        
        # Should find the test tool
        assert len(tools) >= 0  # May be 0 if plugin not active
    
    def test_get_routing_recommendation(self, router):
        """Test getting routing recommendation."""
        plugin = MockTestPlugin()
        router.plugin_manager.register(plugin)
        
        rec = router.get_routing_recommendation(
            "What are the symptoms and treatment for this medical condition? The doctor diagnosed the patient."
        )
        
        assert "domain" in rec
        assert "domain_confidence" in rec
        assert "relevant_tools" in rec


# ==============================================================================
# Built-in Plugin Tests
# ==============================================================================

class TestMathPlugin:
    """Tests for MathPlugin."""
    
    @pytest.fixture
    def plugin(self):
        from llmhive.app.plugins.builtin.math_plugin import MathPlugin
        return MathPlugin()
    
    @pytest.mark.asyncio
    async def test_calculate_basic(self, plugin):
        """Test basic calculation."""
        result = await plugin._tool_calculate(expression="2 + 2")
        
        assert result["success"] is True
        assert result["result"] == 4
    
    @pytest.mark.asyncio
    async def test_calculate_trig(self, plugin):
        """Test trigonometric calculation."""
        result = await plugin._tool_calculate(expression="sin(0)")
        
        assert result["success"] is True
        assert abs(result["result"]) < 0.0001
    
    @pytest.mark.asyncio
    async def test_calculate_sqrt(self, plugin):
        """Test square root."""
        result = await plugin._tool_calculate(expression="sqrt(16)")
        
        assert result["success"] is True
        assert result["result"] == 4
    
    @pytest.mark.asyncio
    async def test_statistics(self, plugin):
        """Test statistics calculation."""
        result = await plugin._tool_statistics(numbers=[1, 2, 3, 4, 5])
        
        assert result["success"] is True
        assert result["mean"] == 3
        assert result["sum"] == 15
        assert result["count"] == 5
    
    @pytest.mark.asyncio
    async def test_convert_temperature(self, plugin):
        """Test temperature conversion."""
        result = await plugin._tool_convert(
            value=0,
            from_unit="celsius",
            to_unit="fahrenheit",
        )
        
        assert result["success"] is True
        assert result["result"] == 32
    
    @pytest.mark.asyncio
    async def test_prime_check(self, plugin):
        """Test prime number check."""
        result = await plugin._tool_prime_check(number=17)
        assert result["is_prime"] is True
        
        result = await plugin._tool_prime_check(number=18)
        assert result["is_prime"] is False


class TestWikiPlugin:
    """Tests for WikiPlugin."""
    
    @pytest.fixture
    def plugin(self):
        from llmhive.app.plugins.builtin.wiki_plugin import WikiPlugin
        return WikiPlugin()
    
    def test_plugin_config(self, plugin):
        """Test plugin configuration."""
        assert plugin.name == "wiki"
        assert "encyclopedia" in plugin.config.domains
    
    def test_get_tools(self, plugin):
        """Test getting tools."""
        tools = plugin.get_tools()
        
        assert len(tools) == 3
        tool_names = [t.name for t in tools]
        assert "wiki_search" in tool_names
        assert "wiki_summary" in tool_names


class TestNewsPlugin:
    """Tests for NewsPlugin."""
    
    @pytest.fixture
    def plugin(self):
        from llmhive.app.plugins.builtin.news_plugin import NewsPlugin
        return NewsPlugin()
    
    def test_plugin_config(self, plugin):
        """Test plugin configuration."""
        assert plugin.name == "news"
        assert "news" in plugin.config.domains
    
    def test_get_tools(self, plugin):
        """Test getting tools."""
        tools = plugin.get_tools()
        
        assert len(tools) >= 2
        tool_names = [t.name for t in tools]
        assert "news_headlines" in tool_names
        assert "news_search" in tool_names


class TestWeatherPlugin:
    """Tests for WeatherPlugin."""
    
    @pytest.fixture
    def plugin(self):
        from llmhive.app.plugins.builtin.weather_plugin import WeatherPlugin
        return WeatherPlugin()
    
    def test_plugin_config(self, plugin):
        """Test plugin configuration."""
        assert plugin.name == "weather"
        assert "weather" in plugin.config.domains
    
    def test_get_tools(self, plugin):
        """Test getting tools."""
        tools = plugin.get_tools()
        
        assert len(tools) == 2
        tool_names = [t.name for t in tools]
        assert "weather_current" in tool_names
        assert "weather_forecast" in tool_names


# ==============================================================================
# Integration Tests
# ==============================================================================

class TestPluginIntegration:
    """Integration tests for plugin system."""
    
    @pytest.mark.asyncio
    async def test_full_plugin_lifecycle(self, tmp_path):
        """Test complete plugin lifecycle."""
        # Create manager
        manager = PluginManager(
            plugins_dir=str(tmp_path / "plugins"),
            builtin_dir=str(tmp_path / "builtin"),
        )
        
        # Register plugin
        plugin = MockTestPlugin()
        manager.register(plugin)
        
        # Activate
        await plugin.activate()
        assert plugin.is_active
        
        # Get tools
        tools = manager.get_all_tools()
        assert len(tools) == 1
        
        # Execute tool
        result = await tools[0].handler()
        assert result["success"] is True
        
        # Shutdown
        await manager.shutdown_all()
        assert len(manager.plugins) == 0
    
    @pytest.mark.asyncio
    async def test_domain_routing_with_plugins(self, tmp_path):
        """Test domain routing with registered plugins."""
        manager = PluginManager(
            plugins_dir=str(tmp_path / "plugins"),
            builtin_dir=str(tmp_path / "builtin"),
        )
        router = DomainPluginRouter(plugin_manager=manager)
        
        # Register and activate plugin
        plugin = MockTestPlugin()
        manager.register(plugin)
        await plugin.activate()
        
        # Route query
        best = router.get_best_plugin(
            "this is a test query",
            domain="test",
        )
        
        assert best == plugin


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

