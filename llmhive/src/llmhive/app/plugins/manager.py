"""Plugin Manager for LLMHive.

Handles plugin discovery, loading, lifecycle, and coordination.

Features:
- Auto-discovery from plugins directory
- Manifest-based configuration
- Dependency resolution
- Tier-based access control
- Hot reload support

Usage:
    pm = get_plugin_manager()
    
    # Load all plugins
    await pm.load_plugins()
    
    # Get specific plugin
    wiki = pm.get_plugin("wiki")
    
    # Get all tools
    tools = pm.get_all_tools()
    
    # Query knowledge across plugins
    results = await pm.query_all_knowledge("medical condition")
"""
from __future__ import annotations

import asyncio
import importlib
import importlib.util
import json
import logging
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Type

from .base import (
    Plugin,
    PluginConfig,
    PluginManifest,
    PluginTool,
    PluginKnowledgeBase,
    PluginCapability,
    PluginStatus,
    PluginTier,
)

logger = logging.getLogger(__name__)


# ==============================================================================
# Plugin Registry
# ==============================================================================

@dataclass
class PluginRegistry:
    """Registry of all loaded plugins."""
    
    plugins: Dict[str, Plugin] = field(default_factory=dict)
    manifests: Dict[str, PluginManifest] = field(default_factory=dict)
    
    # Tool index
    tools_by_name: Dict[str, Tuple[str, PluginTool]] = field(default_factory=dict)
    tools_by_domain: Dict[str, List[Tuple[str, PluginTool]]] = field(default_factory=dict)
    
    # Knowledge index
    knowledge_by_domain: Dict[str, List[Tuple[str, PluginKnowledgeBase]]] = field(default_factory=dict)
    
    # Domain to plugin mapping
    domain_plugins: Dict[str, List[str]] = field(default_factory=dict)
    
    def register_plugin(self, plugin: Plugin, manifest: Optional[PluginManifest] = None) -> None:
        """Register a plugin in the registry."""
        self.plugins[plugin.name] = plugin
        if manifest:
            self.manifests[plugin.name] = manifest
        
        # Index tools
        for tool in plugin.get_tools():
            self.tools_by_name[tool.name] = (plugin.name, tool)
            for domain in tool.domains or plugin.config.domains:
                if domain not in self.tools_by_domain:
                    self.tools_by_domain[domain] = []
                self.tools_by_domain[domain].append((plugin.name, tool))
        
        # Index knowledge bases
        for kb in plugin.get_knowledge_bases():
            for domain in kb.domains or plugin.config.domains:
                if domain not in self.knowledge_by_domain:
                    self.knowledge_by_domain[domain] = []
                self.knowledge_by_domain[domain].append((plugin.name, kb))
        
        # Index domains
        for domain in plugin.config.domains:
            if domain not in self.domain_plugins:
                self.domain_plugins[domain] = []
            if plugin.name not in self.domain_plugins[domain]:
                self.domain_plugins[domain].append(plugin.name)
        
        logger.debug("Registered plugin: %s (tools=%d)", plugin.name, len(plugin.get_tools()))
    
    def unregister_plugin(self, name: str) -> Optional[Plugin]:
        """Remove a plugin from the registry."""
        plugin = self.plugins.pop(name, None)
        self.manifests.pop(name, None)
        
        if plugin:
            # Remove tools
            for tool in plugin.get_tools():
                self.tools_by_name.pop(tool.name, None)
            
            # Remove from domain mappings
            for domain in plugin.config.domains:
                if domain in self.domain_plugins:
                    self.domain_plugins[domain] = [
                        p for p in self.domain_plugins[domain] if p != name
                    ]
        
        return plugin
    
    def get_plugins_for_domain(self, domain: str) -> List[Plugin]:
        """Get all plugins that handle a domain."""
        plugin_names = self.domain_plugins.get(domain.lower(), [])
        return [self.plugins[n] for n in plugin_names if n in self.plugins]


# ==============================================================================
# Plugin Manager
# ==============================================================================

class PluginManager:
    """Central manager for LLMHive plugins.
    
    Handles:
    - Plugin discovery and loading
    - Lifecycle management
    - Tool and knowledge aggregation
    - Domain-based routing
    - Access control
    
    Usage:
        manager = PluginManager()
        
        # Load plugins from directory
        await manager.load_plugins()
        
        # Register a plugin programmatically
        manager.register(my_plugin)
        
        # Get tools for a domain
        tools = manager.get_tools_for_domain("medical")
    """
    
    def __init__(
        self,
        plugins_dir: Optional[str] = None,
        builtin_dir: Optional[str] = None,
    ):
        self.plugins_dir = Path(plugins_dir or os.getenv(
            "LLMHIVE_PLUGINS_DIR",
            "./plugins"
        ))
        self.builtin_dir = Path(builtin_dir) if builtin_dir else (
            Path(__file__).parent / "builtin"
        )
        
        self.registry = PluginRegistry()
        self._loaded = False
        self._loading_lock = asyncio.Lock()
    
    @property
    def plugins(self) -> Dict[str, Plugin]:
        return self.registry.plugins
    
    @property
    def is_loaded(self) -> bool:
        return self._loaded
    
    # -------------------------------------------------------------------------
    # Discovery
    # -------------------------------------------------------------------------
    
    def discover_plugins(self) -> List[PluginManifest]:
        """Discover all available plugins.
        
        Scans:
        1. Built-in plugins directory
        2. User plugins directory
        
        Returns:
            List of plugin manifests
        """
        manifests = []
        
        # Scan built-in plugins
        if self.builtin_dir.exists():
            manifests.extend(self._scan_directory(self.builtin_dir))
        
        # Scan user plugins
        if self.plugins_dir.exists():
            manifests.extend(self._scan_directory(self.plugins_dir))
        
        logger.info("Discovered %d plugins", len(manifests))
        return manifests
    
    def _scan_directory(self, directory: Path) -> List[PluginManifest]:
        """Scan a directory for plugin manifests."""
        manifests = []
        
        for item in directory.iterdir():
            if item.is_dir():
                manifest = self._load_manifest(item)
                if manifest:
                    manifests.append(manifest)
        
        return manifests
    
    def _load_manifest(self, plugin_dir: Path) -> Optional[PluginManifest]:
        """Load plugin manifest from directory."""
        # Try plugin.json
        json_path = plugin_dir / "plugin.json"
        if json_path.exists():
            try:
                with open(json_path) as f:
                    data = json.load(f)
                return PluginManifest.from_dict(data, plugin_dir)
            except Exception as e:
                logger.warning("Failed to load manifest %s: %s", json_path, e)
        
        # Try plugin.yaml
        yaml_path = plugin_dir / "plugin.yaml"
        if yaml_path.exists():
            try:
                import yaml
                with open(yaml_path) as f:
                    data = yaml.safe_load(f)
                return PluginManifest.from_dict(data, plugin_dir)
            except ImportError:
                logger.warning("YAML support not available")
            except Exception as e:
                logger.warning("Failed to load manifest %s: %s", yaml_path, e)
        
        return None
    
    # -------------------------------------------------------------------------
    # Loading
    # -------------------------------------------------------------------------
    
    async def load_plugins(
        self,
        filter_tier: Optional[str] = None,
    ) -> int:
        """Load all discovered plugins.
        
        Args:
            filter_tier: Only load plugins for this tier or lower
            
        Returns:
            Number of plugins loaded
        """
        async with self._loading_lock:
            if self._loaded:
                logger.debug("Plugins already loaded")
                return len(self.registry.plugins)
            
            manifests = self.discover_plugins()
            loaded = 0
            
            # Sort by priority
            manifests.sort(key=lambda m: m.config.priority)
            
            for manifest in manifests:
                if not manifest.config.enabled:
                    logger.debug("Skipping disabled plugin: %s", manifest.config.name)
                    continue
                
                # Check tier filter
                if filter_tier:
                    tier_order = {"free": 0, "pro": 1, "enterprise": 2}
                    if tier_order.get(manifest.config.min_tier.value, 0) > tier_order.get(filter_tier, 0):
                        logger.debug(
                            "Skipping plugin %s (requires %s tier)",
                            manifest.config.name, manifest.config.min_tier.value
                        )
                        continue
                
                try:
                    plugin = await self._load_plugin(manifest)
                    if plugin:
                        self.registry.register_plugin(plugin, manifest)
                        loaded += 1
                except Exception as e:
                    logger.error("Failed to load plugin %s: %s", manifest.config.name, e)
            
            self._loaded = True
            logger.info("Loaded %d/%d plugins", loaded, len(manifests))
            return loaded
    
    async def _load_plugin(self, manifest: PluginManifest) -> Optional[Plugin]:
        """Load a single plugin from manifest."""
        if not manifest.install_path:
            return None
        
        plugin_path = manifest.install_path / manifest.entry_point
        if not plugin_path.exists():
            logger.warning("Plugin entry point not found: %s", plugin_path)
            return None
        
        try:
            # Add plugin dir to path
            sys.path.insert(0, str(manifest.install_path))
            
            # Load module
            spec = importlib.util.spec_from_file_location(
                f"plugin_{manifest.config.name}",
                plugin_path
            )
            if not spec or not spec.loader:
                return None
            
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Get plugin class
            plugin_class = getattr(module, manifest.plugin_class, None)
            if not plugin_class:
                logger.warning("Plugin class not found: %s", manifest.plugin_class)
                return None
            
            # Instantiate
            plugin = plugin_class()
            
            # Initialize
            if manifest.config.auto_activate:
                success = await plugin.activate()
                if not success:
                    logger.warning("Plugin activation failed: %s", manifest.config.name)
                    return None
            
            return plugin
            
        except Exception as e:
            logger.error("Error loading plugin %s: %s", manifest.config.name, e)
            return None
        finally:
            # Remove from path
            if str(manifest.install_path) in sys.path:
                sys.path.remove(str(manifest.install_path))
    
    # -------------------------------------------------------------------------
    # Registration
    # -------------------------------------------------------------------------
    
    def register(self, plugin: Plugin) -> bool:
        """Register a plugin programmatically.
        
        Args:
            plugin: Plugin instance to register
            
        Returns:
            True if registered successfully
        """
        if plugin.name in self.registry.plugins:
            logger.warning("Plugin already registered: %s", plugin.name)
            return False
        
        self.registry.register_plugin(plugin)
        return True
    
    def unregister(self, name: str) -> bool:
        """Unregister a plugin.
        
        Args:
            name: Plugin name
            
        Returns:
            True if unregistered
        """
        plugin = self.registry.unregister_plugin(name)
        if plugin:
            # Try to schedule shutdown if there's a running loop
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(plugin.shutdown())
            except RuntimeError:
                # No running loop - shutdown synchronously is fine
                pass
            return True
        return False
    
    # -------------------------------------------------------------------------
    # Queries
    # -------------------------------------------------------------------------
    
    def get_plugin(self, name: str) -> Optional[Plugin]:
        """Get a plugin by name."""
        return self.registry.plugins.get(name)
    
    def get_active_plugins(self) -> List[Plugin]:
        """Get all active plugins."""
        return [p for p in self.registry.plugins.values() if p.is_active]
    
    def get_plugins_for_domain(self, domain: str) -> List[Plugin]:
        """Get plugins that handle a domain."""
        return self.registry.get_plugins_for_domain(domain)
    
    def get_best_plugin_for_query(
        self,
        query: str,
        domain: Optional[str] = None,
        user_tier: str = "free",
    ) -> Optional[Plugin]:
        """Find the best plugin to handle a query.
        
        Args:
            query: User query
            domain: Optional detected domain
            user_tier: User's tier
            
        Returns:
            Best matching plugin or None
        """
        best_plugin = None
        best_score = 0.0
        
        for plugin in self.get_active_plugins():
            # Check tier access
            if not plugin.check_tier_access(user_tier):
                continue
            
            score = plugin.can_handle_query(query, domain)
            if score > best_score:
                best_score = score
                best_plugin = plugin
        
        if best_score >= 0.3:  # Minimum threshold
            return best_plugin
        return None
    
    # -------------------------------------------------------------------------
    # Tools
    # -------------------------------------------------------------------------
    
    def get_all_tools(self, user_tier: str = "free") -> List[PluginTool]:
        """Get all tools from active plugins.
        
        Args:
            user_tier: Filter by tier access
            
        Returns:
            List of available tools
        """
        tools = []
        
        for plugin in self.get_active_plugins():
            if not plugin.check_tier_access(user_tier):
                continue
            
            for tool in plugin.get_tools():
                # Check tool-level tier
                tier_order = {"free": 0, "pro": 1, "enterprise": 2}
                if tier_order.get(tool.min_tier.value, 0) <= tier_order.get(user_tier, 0):
                    tools.append(tool)
        
        return tools
    
    def get_tools_for_domain(
        self,
        domain: str,
        user_tier: str = "free",
    ) -> List[PluginTool]:
        """Get tools for a specific domain."""
        tools = []
        
        for plugin_name, tool in self.registry.tools_by_domain.get(domain.lower(), []):
            plugin = self.registry.plugins.get(plugin_name)
            if plugin and plugin.is_active and plugin.check_tier_access(user_tier):
                tools.append(tool)
        
        return tools
    
    def get_tool(self, name: str) -> Optional[Tuple[Plugin, PluginTool]]:
        """Get a specific tool by name."""
        result = self.registry.tools_by_name.get(name)
        if result:
            plugin_name, tool = result
            plugin = self.registry.plugins.get(plugin_name)
            if plugin and plugin.is_active:
                return plugin, tool
        return None
    
    # -------------------------------------------------------------------------
    # Knowledge
    # -------------------------------------------------------------------------
    
    async def query_all_knowledge(
        self,
        query: str,
        domain: Optional[str] = None,
        user_tier: str = "free",
        top_k: int = 10,
    ) -> List[Dict[str, Any]]:
        """Query knowledge bases across all plugins.
        
        Args:
            query: Search query
            domain: Optional domain filter
            user_tier: User tier for access control
            top_k: Max results per plugin
            
        Returns:
            Combined results from all relevant plugins
        """
        results = []
        
        # Determine which plugins to query
        if domain:
            plugins = self.get_plugins_for_domain(domain)
        else:
            plugins = self.get_active_plugins()
        
        # Query each plugin
        tasks = []
        for plugin in plugins:
            if plugin.check_tier_access(user_tier):
                tasks.append(plugin.query_knowledge(query, top_k=top_k))
        
        if tasks:
            all_results = await asyncio.gather(*tasks, return_exceptions=True)
            for r in all_results:
                if isinstance(r, list):
                    results.extend(r)
        
        return results
    
    # -------------------------------------------------------------------------
    # Lifecycle
    # -------------------------------------------------------------------------
    
    async def reload_plugin(self, name: str) -> bool:
        """Reload a specific plugin."""
        manifest = self.registry.manifests.get(name)
        if not manifest:
            return False
        
        # Shutdown existing
        plugin = self.registry.unregister_plugin(name)
        if plugin:
            await plugin.shutdown()
        
        # Reload
        new_plugin = await self._load_plugin(manifest)
        if new_plugin:
            self.registry.register_plugin(new_plugin, manifest)
            return True
        
        return False
    
    async def shutdown_all(self) -> None:
        """Shutdown all plugins."""
        for plugin in list(self.registry.plugins.values()):
            try:
                await plugin.shutdown()
            except Exception as e:
                logger.error("Error shutting down plugin %s: %s", plugin.name, e)
        
        self.registry = PluginRegistry()
        self._loaded = False
        logger.info("All plugins shutdown")
    
    # -------------------------------------------------------------------------
    # Info
    # -------------------------------------------------------------------------
    
    def get_stats(self) -> Dict[str, Any]:
        """Get plugin system statistics."""
        active = [p for p in self.registry.plugins.values() if p.is_active]
        
        return {
            "total_plugins": len(self.registry.plugins),
            "active_plugins": len(active),
            "total_tools": len(self.registry.tools_by_name),
            "domains_covered": list(self.registry.domain_plugins.keys()),
            "plugins": [p.get_info() for p in self.registry.plugins.values()],
        }


# ==============================================================================
# Global Instance
# ==============================================================================

_plugin_manager: Optional[PluginManager] = None


def get_plugin_manager() -> PluginManager:
    """Get or create global plugin manager."""
    global _plugin_manager
    if _plugin_manager is None:
        _plugin_manager = PluginManager()
    return _plugin_manager


async def initialize_plugins(
    plugins_dir: Optional[str] = None,
    filter_tier: Optional[str] = None,
) -> PluginManager:
    """Initialize and load plugins.
    
    Args:
        plugins_dir: Custom plugins directory
        filter_tier: Only load plugins for this tier
        
    Returns:
        Initialized PluginManager
    """
    global _plugin_manager
    _plugin_manager = PluginManager(plugins_dir=plugins_dir)
    await _plugin_manager.load_plugins(filter_tier=filter_tier)
    return _plugin_manager

