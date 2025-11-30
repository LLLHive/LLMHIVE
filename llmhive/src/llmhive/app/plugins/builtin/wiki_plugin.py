"""Wikipedia Plugin for LLMHive.

Provides Wikipedia search and article retrieval capabilities.

Features:
- Search Wikipedia for articles
- Get article summaries
- Retrieve full article content
- Domain-specific knowledge augmentation

Usage:
    plugin = WikiPlugin()
    await plugin.activate()
    
    # Search Wikipedia
    results = await plugin.search("artificial intelligence")
    
    # Get summary
    summary = await plugin.get_summary("Machine learning")
"""
from __future__ import annotations

import asyncio
import logging
import os
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from urllib.parse import quote

from ..base import (
    Plugin,
    PluginConfig,
    PluginTool,
    PluginKnowledgeBase,
    PluginCapability,
    PluginTier,
)

logger = logging.getLogger(__name__)


# ==============================================================================
# Types
# ==============================================================================

@dataclass
class WikiArticle:
    """Wikipedia article summary."""
    title: str
    summary: str
    url: str
    page_id: int
    categories: List[str]


@dataclass
class WikiSearchResult:
    """Wikipedia search result."""
    title: str
    snippet: str
    page_id: int
    url: str


# ==============================================================================
# Wikipedia API Client
# ==============================================================================

class WikipediaClient:
    """Client for Wikipedia API."""
    
    BASE_URL = "https://en.wikipedia.org/w/api.php"
    
    def __init__(self, language: str = "en"):
        self.language = language
        self.base_url = f"https://{language}.wikipedia.org/w/api.php"
    
    async def search(
        self,
        query: str,
        limit: int = 5,
    ) -> List[WikiSearchResult]:
        """Search Wikipedia for articles."""
        try:
            import aiohttp
        except ImportError:
            logger.warning("aiohttp not available for Wikipedia search")
            return []
        
        params = {
            "action": "query",
            "list": "search",
            "srsearch": query,
            "srlimit": limit,
            "format": "json",
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.base_url, params=params) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        results = []
                        for item in data.get("query", {}).get("search", []):
                            # Clean snippet
                            snippet = re.sub(r"<[^>]+>", "", item.get("snippet", ""))
                            results.append(WikiSearchResult(
                                title=item.get("title", ""),
                                snippet=snippet,
                                page_id=item.get("pageid", 0),
                                url=f"https://{self.language}.wikipedia.org/wiki/{quote(item.get('title', ''))}",
                            ))
                        return results
        except Exception as e:
            logger.error("Wikipedia search failed: %s", e)
        
        return []
    
    async def get_summary(
        self,
        title: str,
        sentences: int = 3,
    ) -> Optional[WikiArticle]:
        """Get article summary."""
        try:
            import aiohttp
        except ImportError:
            return None
        
        params = {
            "action": "query",
            "titles": title,
            "prop": "extracts|info|categories",
            "exintro": True,
            "explaintext": True,
            "exsentences": sentences,
            "inprop": "url",
            "format": "json",
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.base_url, params=params) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        pages = data.get("query", {}).get("pages", {})
                        
                        for page_id, page in pages.items():
                            if page_id == "-1":
                                continue
                            
                            categories = [
                                c.get("title", "").replace("Category:", "")
                                for c in page.get("categories", [])
                            ]
                            
                            return WikiArticle(
                                title=page.get("title", title),
                                summary=page.get("extract", ""),
                                url=page.get("fullurl", ""),
                                page_id=int(page_id),
                                categories=categories,
                            )
        except Exception as e:
            logger.error("Wikipedia get_summary failed: %s", e)
        
        return None
    
    async def get_content(
        self,
        title: str,
        max_chars: int = 5000,
    ) -> Optional[str]:
        """Get full article content."""
        try:
            import aiohttp
        except ImportError:
            return None
        
        params = {
            "action": "query",
            "titles": title,
            "prop": "extracts",
            "explaintext": True,
            "format": "json",
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.base_url, params=params) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        pages = data.get("query", {}).get("pages", {})
                        
                        for page_id, page in pages.items():
                            if page_id != "-1":
                                content = page.get("extract", "")
                                return content[:max_chars] if content else None
        except Exception as e:
            logger.error("Wikipedia get_content failed: %s", e)
        
        return None


# ==============================================================================
# Wikipedia Plugin
# ==============================================================================

class WikiPlugin(Plugin):
    """Wikipedia Plugin for LLMHive.
    
    Provides tools for searching and retrieving Wikipedia content.
    
    Tools:
    - wiki_search: Search Wikipedia for articles
    - wiki_summary: Get article summary
    - wiki_content: Get full article content
    """
    
    def __init__(self, language: str = "en"):
        config = PluginConfig(
            name="wiki",
            display_name="Wikipedia",
            version="1.0.0",
            description="Search and retrieve information from Wikipedia",
            author="LLMHive",
            domains=["general", "encyclopedia", "knowledge", "facts", "education"],
            keywords=[
                "wikipedia", "wiki", "what is", "who is", "define", "explain",
                "tell me about", "information", "facts", "history", "biography",
            ],
            min_tier=PluginTier.FREE,
            capabilities=[PluginCapability.TOOLS, PluginCapability.KNOWLEDGE],
            enabled=True,
            auto_activate=True,
            priority=50,
        )
        super().__init__(config)
        
        self.language = language
        self.client = WikipediaClient(language)
    
    async def initialize(self) -> bool:
        """Initialize Wikipedia plugin."""
        logger.info("Initializing Wikipedia plugin")
        return True
    
    def get_tools(self) -> List[PluginTool]:
        """Get Wikipedia tools."""
        return [
            PluginTool(
                name="wiki_search",
                description="Search Wikipedia for articles matching a query. Returns titles, snippets, and URLs.",
                handler=self._tool_search,
                parameters={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum results (default: 5)",
                            "default": 5,
                        },
                    },
                    "required": ["query"],
                },
                domains=["general", "encyclopedia", "knowledge"],
                trigger_keywords=["wikipedia", "search wikipedia", "wiki search"],
            ),
            PluginTool(
                name="wiki_summary",
                description="Get a summary of a Wikipedia article by title.",
                handler=self._tool_summary,
                parameters={
                    "type": "object",
                    "properties": {
                        "title": {
                            "type": "string",
                            "description": "Article title (e.g., 'Machine learning')",
                        },
                        "sentences": {
                            "type": "integer",
                            "description": "Number of sentences (default: 3)",
                            "default": 3,
                        },
                    },
                    "required": ["title"],
                },
                domains=["general", "encyclopedia", "knowledge"],
                trigger_keywords=["wikipedia", "wiki", "summary", "what is"],
            ),
            PluginTool(
                name="wiki_content",
                description="Get the full content of a Wikipedia article.",
                handler=self._tool_content,
                parameters={
                    "type": "object",
                    "properties": {
                        "title": {
                            "type": "string",
                            "description": "Article title",
                        },
                        "max_chars": {
                            "type": "integer",
                            "description": "Maximum characters (default: 5000)",
                            "default": 5000,
                        },
                    },
                    "required": ["title"],
                },
                domains=["general", "encyclopedia", "knowledge"],
                trigger_keywords=["wikipedia full", "wiki article", "full article"],
                min_tier=PluginTier.PRO,  # Full content for Pro+
            ),
        ]
    
    def get_knowledge_bases(self) -> List[PluginKnowledgeBase]:
        """Wikipedia provides dynamic knowledge via API."""
        return [
            PluginKnowledgeBase(
                name="wikipedia",
                description="Wikipedia encyclopedia - dynamic search",
                kb_type="api",
                domains=["general", "encyclopedia", "knowledge"],
                query_handler=self._query_knowledge,
            )
        ]
    
    async def _query_knowledge(
        self,
        query: str,
        top_k: int = 3,
    ) -> List[Dict[str, Any]]:
        """Query Wikipedia for knowledge."""
        results = []
        
        # Search for articles
        search_results = await self.client.search(query, limit=top_k)
        
        for sr in search_results[:top_k]:
            # Get summary for each result
            article = await self.client.get_summary(sr.title, sentences=2)
            if article:
                results.append({
                    "content": article.summary,
                    "source": f"Wikipedia: {article.title}",
                    "url": article.url,
                    "confidence": 0.9,  # Wikipedia is reliable
                })
        
        return results
    
    # -------------------------------------------------------------------------
    # Tool Handlers
    # -------------------------------------------------------------------------
    
    async def _tool_search(
        self,
        query: str,
        limit: int = 5,
        **kwargs,
    ) -> Dict[str, Any]:
        """Handle wiki_search tool call."""
        results = await self.client.search(query, limit)
        
        return {
            "success": True,
            "query": query,
            "results": [
                {
                    "title": r.title,
                    "snippet": r.snippet,
                    "url": r.url,
                }
                for r in results
            ],
            "count": len(results),
        }
    
    async def _tool_summary(
        self,
        title: str,
        sentences: int = 3,
        **kwargs,
    ) -> Dict[str, Any]:
        """Handle wiki_summary tool call."""
        article = await self.client.get_summary(title, sentences)
        
        if article:
            return {
                "success": True,
                "title": article.title,
                "summary": article.summary,
                "url": article.url,
                "categories": article.categories[:5],
            }
        
        return {
            "success": False,
            "error": f"Article not found: {title}",
        }
    
    async def _tool_content(
        self,
        title: str,
        max_chars: int = 5000,
        **kwargs,
    ) -> Dict[str, Any]:
        """Handle wiki_content tool call."""
        content = await self.client.get_content(title, max_chars)
        
        if content:
            return {
                "success": True,
                "title": title,
                "content": content,
                "truncated": len(content) >= max_chars,
            }
        
        return {
            "success": False,
            "error": f"Article not found: {title}",
        }


# Create plugin manifest for auto-discovery
PLUGIN_MANIFEST = {
    "name": "wiki",
    "display_name": "Wikipedia",
    "version": "1.0.0",
    "description": "Search and retrieve information from Wikipedia",
    "author": "LLMHive",
    "domains": ["general", "encyclopedia", "knowledge", "facts", "education"],
    "keywords": ["wikipedia", "wiki", "what is", "who is", "define", "explain"],
    "min_tier": "free",
    "capabilities": ["tools", "knowledge"],
    "entry_point": "wiki_plugin.py",
    "plugin_class": "WikiPlugin",
    "enabled": True,
    "auto_activate": True,
    "priority": 50,
}

