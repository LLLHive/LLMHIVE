"""LLMHive Plugin System.

This module provides a comprehensive plugin architecture for domain-specific
knowledge integration and extensibility.

Features:
- Plugin discovery and loading
- Domain-specific knowledge bases
- Custom tools and API connectors
- Specialized prompt templates
- Tier-based access control
- Adaptive routing integration

Usage:
    from llmhive.app.plugins import PluginManager, get_plugin_manager
    
    # Get plugin manager
    pm = get_plugin_manager()
    
    # Load all plugins
    await pm.load_plugins()
    
    # Get tools from plugins
    tools = pm.get_all_tools()
    
    # Query plugin knowledge
    results = await pm.query_knowledge("medical", "What is hypertension?")
"""
from __future__ import annotations

# Base classes
try:
    from .base import (
        Plugin,
        PluginConfig,
        PluginManifest,
        PluginTool,
        PluginKnowledgeBase,
        PluginCapability,
        PluginStatus,
    )
    BASE_AVAILABLE = True
except ImportError:
    BASE_AVAILABLE = False
    Plugin = None  # type: ignore

# Plugin manager
try:
    from .manager import (
        PluginManager,
        PluginRegistry,
        get_plugin_manager,
    )
    MANAGER_AVAILABLE = True
except ImportError:
    MANAGER_AVAILABLE = False
    PluginManager = None  # type: ignore

# Domain router integration
try:
    from .domain_router import (
        DomainPluginRouter,
        get_domain_router,
    )
    DOMAIN_ROUTER_AVAILABLE = True
except ImportError:
    DOMAIN_ROUTER_AVAILABLE = False
    DomainPluginRouter = None  # type: ignore


__all__ = []

if BASE_AVAILABLE:
    __all__.extend([
        "Plugin",
        "PluginConfig",
        "PluginManifest",
        "PluginTool",
        "PluginKnowledgeBase",
        "PluginCapability",
        "PluginStatus",
    ])

if MANAGER_AVAILABLE:
    __all__.extend([
        "PluginManager",
        "PluginRegistry",
        "get_plugin_manager",
    ])

if DOMAIN_ROUTER_AVAILABLE:
    __all__.extend([
        "DomainPluginRouter",
        "get_domain_router",
    ])

