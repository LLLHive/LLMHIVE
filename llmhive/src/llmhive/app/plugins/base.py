"""Plugin Base Classes and Types.

Defines the core abstractions for the plugin system:
- Plugin: Base class for all plugins
- PluginConfig: Configuration for plugin behavior
- PluginManifest: Plugin metadata and requirements
- PluginTool: Tool definition within a plugin
- PluginKnowledgeBase: Domain-specific knowledge

Usage:
    from llmhive.app.plugins.base import Plugin, PluginConfig
    
    class MyPlugin(Plugin):
        def __init__(self):
            super().__init__(
                config=PluginConfig(
                    name="my_plugin",
                    display_name="My Plugin",
                    version="1.0.0",
                    domains=["custom"],
                )
            )
        
        async def initialize(self) -> bool:
            # Setup plugin resources
            return True
        
        def get_tools(self) -> List[PluginTool]:
            return [my_tool]
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

logger = logging.getLogger(__name__)


# ==============================================================================
# Enums
# ==============================================================================

class PluginStatus(str, Enum):
    """Plugin lifecycle status."""
    UNLOADED = "unloaded"
    LOADING = "loading"
    ACTIVE = "active"
    ERROR = "error"
    DISABLED = "disabled"


class PluginCapability(str, Enum):
    """Capabilities a plugin can provide."""
    TOOLS = "tools"
    KNOWLEDGE = "knowledge"
    PROMPTS = "prompts"
    MODELS = "models"
    MIDDLEWARE = "middleware"


class PluginTier(str, Enum):
    """Tier requirements for plugins."""
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


# ==============================================================================
# Data Classes
# ==============================================================================

@dataclass(slots=True)
class PluginConfig:
    """Configuration for a plugin."""
    name: str
    display_name: str
    version: str
    description: str = ""
    author: str = ""
    
    # Domain configuration
    domains: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    
    # Access control
    min_tier: PluginTier = PluginTier.FREE
    required_permissions: List[str] = field(default_factory=list)
    
    # Capabilities
    capabilities: List[PluginCapability] = field(default_factory=list)
    
    # Dependencies
    dependencies: List[str] = field(default_factory=list)  # Other plugin names
    python_packages: List[str] = field(default_factory=list)
    
    # Settings
    enabled: bool = True
    auto_activate: bool = True
    priority: int = 100  # Lower = higher priority
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "display_name": self.display_name,
            "version": self.version,
            "description": self.description,
            "author": self.author,
            "domains": self.domains,
            "keywords": self.keywords,
            "min_tier": self.min_tier.value,
            "capabilities": [c.value for c in self.capabilities],
            "enabled": self.enabled,
            "priority": self.priority,
        }


@dataclass(slots=True)
class PluginManifest:
    """Full manifest for a plugin (from plugin.json/yaml)."""
    config: PluginConfig
    entry_point: str = "plugin.py"
    plugin_class: str = "Plugin"
    
    # Resource paths
    tools_file: Optional[str] = None
    knowledge_dir: Optional[str] = None
    prompts_file: Optional[str] = None
    
    # Runtime info
    install_path: Optional[Path] = None
    checksum: Optional[str] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any], install_path: Optional[Path] = None) -> "PluginManifest":
        """Create manifest from dictionary."""
        config = PluginConfig(
            name=data.get("name", "unknown"),
            display_name=data.get("display_name", data.get("name", "Unknown")),
            version=data.get("version", "0.0.0"),
            description=data.get("description", ""),
            author=data.get("author", ""),
            domains=data.get("domains", []),
            keywords=data.get("keywords", []),
            min_tier=PluginTier(data.get("min_tier", "free")),
            required_permissions=data.get("required_permissions", []),
            capabilities=[PluginCapability(c) for c in data.get("capabilities", [])],
            dependencies=data.get("dependencies", []),
            python_packages=data.get("python_packages", []),
            enabled=data.get("enabled", True),
            auto_activate=data.get("auto_activate", True),
            priority=data.get("priority", 100),
        )
        
        return cls(
            config=config,
            entry_point=data.get("entry_point", "plugin.py"),
            plugin_class=data.get("plugin_class", "Plugin"),
            tools_file=data.get("tools_file"),
            knowledge_dir=data.get("knowledge_dir"),
            prompts_file=data.get("prompts_file"),
            install_path=install_path,
        )


@dataclass(slots=True)
class PluginTool:
    """A tool provided by a plugin."""
    name: str
    description: str
    handler: Callable
    
    # Parameters schema (JSON Schema)
    parameters: Dict[str, Any] = field(default_factory=dict)
    
    # Access control
    min_tier: PluginTier = PluginTier.FREE
    requires_api_key: Optional[str] = None
    
    # Domain hints
    domains: List[str] = field(default_factory=list)
    trigger_keywords: List[str] = field(default_factory=list)
    
    # Rate limiting
    rate_limit_per_minute: int = 60
    
    def to_tool_definition(self) -> Dict[str, Any]:
        """Convert to tool broker format."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
            "handler": self.handler,
        }


@dataclass(slots=True)
class PluginKnowledgeBase:
    """Knowledge base provided by a plugin."""
    name: str
    description: str
    
    # Type of knowledge base
    kb_type: str = "vector"  # vector, sql, graph, documents
    
    # Connection/path info
    connection_string: Optional[str] = None
    index_path: Optional[str] = None
    namespace: Optional[str] = None
    
    # Domain info
    domains: List[str] = field(default_factory=list)
    
    # Query interface
    query_handler: Optional[Callable] = None
    
    # Stats
    document_count: int = 0
    last_updated: Optional[datetime] = None


@dataclass(slots=True)
class PluginPromptTemplate:
    """Prompt template provided by a plugin."""
    name: str
    description: str
    template: str
    
    # When to use
    domains: List[str] = field(default_factory=list)
    use_for_roles: List[str] = field(default_factory=list)  # HRM roles
    
    # Variables
    variables: List[str] = field(default_factory=list)


# ==============================================================================
# Plugin Base Class
# ==============================================================================

class Plugin(ABC):
    """Base class for all LLMHive plugins.
    
    Plugins extend LLMHive with:
    - Domain-specific tools
    - Knowledge bases
    - Prompt templates
    - Custom models
    
    Lifecycle:
    1. __init__: Set up config and basic state
    2. initialize(): Async setup (load resources, connect to APIs)
    3. activate(): Enable plugin for use
    4. deactivate(): Disable plugin temporarily
    5. shutdown(): Clean up resources
    
    Example:
        class WeatherPlugin(Plugin):
            def __init__(self):
                super().__init__(
                    config=PluginConfig(
                        name="weather",
                        display_name="Weather Plugin",
                        version="1.0.0",
                        domains=["weather", "climate"],
                        capabilities=[PluginCapability.TOOLS],
                    )
                )
            
            async def initialize(self) -> bool:
                self.api_key = os.getenv("WEATHER_API_KEY")
                return bool(self.api_key)
            
            def get_tools(self) -> List[PluginTool]:
                return [
                    PluginTool(
                        name="get_weather",
                        description="Get current weather",
                        handler=self._get_weather,
                        parameters={...}
                    )
                ]
    """
    
    def __init__(self, config: PluginConfig):
        self.config = config
        self._status = PluginStatus.UNLOADED
        self._error: Optional[str] = None
        self._initialized_at: Optional[datetime] = None
        
        # Cached resources
        self._tools: List[PluginTool] = []
        self._knowledge_bases: List[PluginKnowledgeBase] = []
        self._prompt_templates: List[PluginPromptTemplate] = []
    
    @property
    def name(self) -> str:
        return self.config.name
    
    @property
    def status(self) -> PluginStatus:
        return self._status
    
    @property
    def is_active(self) -> bool:
        return self._status == PluginStatus.ACTIVE
    
    @property
    def error(self) -> Optional[str]:
        return self._error
    
    # -------------------------------------------------------------------------
    # Lifecycle Methods
    # -------------------------------------------------------------------------
    
    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize plugin resources.
        
        Called once when plugin is first loaded. Use this to:
        - Load configuration
        - Connect to external APIs
        - Initialize knowledge bases
        - Set up any required state
        
        Returns:
            True if initialization succeeded
        """
        pass
    
    async def activate(self) -> bool:
        """Activate the plugin for use.
        
        Called when plugin should start handling requests.
        Override to perform activation-specific logic.
        
        Returns:
            True if activation succeeded
        """
        if self._status == PluginStatus.UNLOADED:
            success = await self.initialize()
            if not success:
                return False
        
        self._status = PluginStatus.ACTIVE
        self._initialized_at = datetime.now(timezone.utc)
        logger.info("Plugin activated: %s", self.name)
        return True
    
    async def deactivate(self) -> None:
        """Deactivate the plugin temporarily.
        
        Plugin resources remain loaded but won't be used.
        """
        self._status = PluginStatus.DISABLED
        logger.info("Plugin deactivated: %s", self.name)
    
    async def shutdown(self) -> None:
        """Clean up plugin resources.
        
        Called when plugin is being unloaded.
        Override to clean up connections, files, etc.
        """
        self._status = PluginStatus.UNLOADED
        self._tools = []
        self._knowledge_bases = []
        self._prompt_templates = []
        logger.info("Plugin shutdown: %s", self.name)
    
    def set_error(self, error: str) -> None:
        """Set plugin to error state."""
        self._status = PluginStatus.ERROR
        self._error = error
        logger.error("Plugin error [%s]: %s", self.name, error)
    
    # -------------------------------------------------------------------------
    # Capability Methods
    # -------------------------------------------------------------------------
    
    def get_tools(self) -> List[PluginTool]:
        """Get tools provided by this plugin.
        
        Override to provide custom tools.
        
        Returns:
            List of PluginTool definitions
        """
        return self._tools
    
    def get_knowledge_bases(self) -> List[PluginKnowledgeBase]:
        """Get knowledge bases provided by this plugin.
        
        Override to provide domain-specific knowledge.
        
        Returns:
            List of PluginKnowledgeBase definitions
        """
        return self._knowledge_bases
    
    def get_prompt_templates(self) -> List[PluginPromptTemplate]:
        """Get prompt templates provided by this plugin.
        
        Override to provide domain-specific prompts.
        
        Returns:
            List of PluginPromptTemplate definitions
        """
        return self._prompt_templates
    
    async def query_knowledge(
        self,
        query: str,
        kb_name: Optional[str] = None,
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """Query plugin's knowledge bases.
        
        Args:
            query: Search query
            kb_name: Specific KB to query (or all if None)
            top_k: Number of results
            
        Returns:
            List of relevant documents/facts
        """
        results = []
        
        for kb in self._knowledge_bases:
            if kb_name and kb.name != kb_name:
                continue
            
            if kb.query_handler:
                try:
                    kb_results = await kb.query_handler(query, top_k)
                    results.extend(kb_results)
                except Exception as e:
                    logger.warning(
                        "Knowledge query failed [%s/%s]: %s",
                        self.name, kb.name, e
                    )
        
        return results
    
    # -------------------------------------------------------------------------
    # Domain Matching
    # -------------------------------------------------------------------------
    
    def matches_domain(self, domain: str) -> bool:
        """Check if plugin handles the given domain."""
        return domain.lower() in [d.lower() for d in self.config.domains]
    
    def matches_keywords(self, text: str) -> float:
        """Score how well text matches plugin keywords.
        
        Returns:
            Score from 0-1
        """
        if not self.config.keywords:
            return 0.0
        
        text_lower = text.lower()
        matches = sum(1 for kw in self.config.keywords if kw.lower() in text_lower)
        return min(matches / len(self.config.keywords), 1.0)
    
    def can_handle_query(self, query: str, domain: Optional[str] = None) -> float:
        """Score how well plugin can handle a query.
        
        Args:
            query: The user's query
            domain: Optional detected domain
            
        Returns:
            Score from 0-1 (higher = better fit)
        """
        score = 0.0
        
        # Domain match
        if domain and self.matches_domain(domain):
            score += 0.5
        
        # Keyword match
        keyword_score = self.matches_keywords(query)
        score += keyword_score * 0.5
        
        return min(score, 1.0)
    
    # -------------------------------------------------------------------------
    # Access Control
    # -------------------------------------------------------------------------
    
    def check_tier_access(self, user_tier: str) -> bool:
        """Check if user tier can access this plugin.
        
        Args:
            user_tier: User's subscription tier
            
        Returns:
            True if access is allowed
        """
        tier_order = {
            PluginTier.FREE: 0,
            PluginTier.PRO: 1,
            PluginTier.ENTERPRISE: 2,
        }
        
        user_level = tier_order.get(PluginTier(user_tier.lower()), 0)
        required_level = tier_order.get(self.config.min_tier, 0)
        
        return user_level >= required_level
    
    # -------------------------------------------------------------------------
    # Info
    # -------------------------------------------------------------------------
    
    def get_info(self) -> Dict[str, Any]:
        """Get plugin information."""
        return {
            "name": self.config.name,
            "display_name": self.config.display_name,
            "version": self.config.version,
            "description": self.config.description,
            "status": self._status.value,
            "error": self._error,
            "domains": self.config.domains,
            "capabilities": [c.value for c in self.config.capabilities],
            "min_tier": self.config.min_tier.value,
            "tools_count": len(self.get_tools()),
            "kb_count": len(self.get_knowledge_bases()),
            "initialized_at": self._initialized_at.isoformat() if self._initialized_at else None,
        }


# ==============================================================================
# Convenience Classes
# ==============================================================================

class SimplePlugin(Plugin):
    """Simplified plugin for quick implementations.
    
    Use when you just need to add tools without complex lifecycle.
    
    Example:
        plugin = SimplePlugin(
            name="my_tools",
            display_name="My Tools",
            version="1.0.0",
            tools=[my_tool1, my_tool2],
        )
    """
    
    def __init__(
        self,
        name: str,
        display_name: str,
        version: str = "1.0.0",
        description: str = "",
        domains: Optional[List[str]] = None,
        tools: Optional[List[PluginTool]] = None,
        min_tier: PluginTier = PluginTier.FREE,
    ):
        config = PluginConfig(
            name=name,
            display_name=display_name,
            version=version,
            description=description,
            domains=domains or [],
            capabilities=[PluginCapability.TOOLS] if tools else [],
            min_tier=min_tier,
        )
        super().__init__(config)
        self._tools = tools or []
    
    async def initialize(self) -> bool:
        return True

