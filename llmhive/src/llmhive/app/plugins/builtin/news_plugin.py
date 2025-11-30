"""News Plugin for LLMHive.

Provides latest news from various RSS feeds and news APIs.

Features:
- Fetch latest news headlines
- Search news by topic
- Get news from specific sources
- Domain-specific news (tech, business, science)

Usage:
    plugin = NewsPlugin()
    await plugin.activate()
    
    # Get latest headlines
    news = await plugin.get_headlines()
    
    # Search news
    results = await plugin.search_news("artificial intelligence")
"""
from __future__ import annotations

import asyncio
import logging
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from xml.etree import ElementTree

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
class NewsArticle:
    """A news article."""
    title: str
    description: str
    url: str
    source: str
    published: Optional[datetime] = None
    category: Optional[str] = None


# ==============================================================================
# RSS Feed Sources
# ==============================================================================

RSS_FEEDS: Dict[str, Dict[str, str]] = {
    # General news
    "bbc": {
        "name": "BBC News",
        "url": "http://feeds.bbci.co.uk/news/rss.xml",
        "category": "general",
    },
    "reuters": {
        "name": "Reuters",
        "url": "https://www.reutersagency.com/feed/?best-topics=business-finance&post_type=best",
        "category": "general",
    },
    # Technology
    "techcrunch": {
        "name": "TechCrunch",
        "url": "https://techcrunch.com/feed/",
        "category": "technology",
    },
    "ars_technica": {
        "name": "Ars Technica",
        "url": "https://feeds.arstechnica.com/arstechnica/index",
        "category": "technology",
    },
    "hacker_news": {
        "name": "Hacker News",
        "url": "https://hnrss.org/frontpage",
        "category": "technology",
    },
    # Science
    "science_daily": {
        "name": "Science Daily",
        "url": "https://www.sciencedaily.com/rss/all.xml",
        "category": "science",
    },
    "nature": {
        "name": "Nature",
        "url": "https://www.nature.com/nature.rss",
        "category": "science",
    },
    # Business
    "wsj": {
        "name": "Wall Street Journal",
        "url": "https://feeds.a.dj.com/rss/RSSWorldNews.xml",
        "category": "business",
    },
}


# ==============================================================================
# RSS Client
# ==============================================================================

class RSSClient:
    """Client for fetching and parsing RSS feeds."""
    
    def __init__(self, timeout: int = 10):
        self.timeout = timeout
    
    async def fetch_feed(
        self,
        url: str,
        source_name: str,
        category: str = "general",
        limit: int = 10,
    ) -> List[NewsArticle]:
        """Fetch articles from an RSS feed."""
        try:
            import aiohttp
        except ImportError:
            logger.warning("aiohttp not available for RSS feeds")
            return []
        
        articles = []
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url, 
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as resp:
                    if resp.status == 200:
                        content = await resp.text()
                        articles = self._parse_rss(
                            content, source_name, category, limit
                        )
        except Exception as e:
            logger.warning("Failed to fetch RSS feed %s: %s", url, e)
        
        return articles
    
    def _parse_rss(
        self,
        content: str,
        source_name: str,
        category: str,
        limit: int,
    ) -> List[NewsArticle]:
        """Parse RSS XML content."""
        articles = []
        
        try:
            root = ElementTree.fromstring(content)
            
            # Handle both RSS and Atom feeds
            items = root.findall(".//item") or root.findall(
                ".//{http://www.w3.org/2005/Atom}entry"
            )
            
            for item in items[:limit]:
                # RSS format
                title = item.findtext("title") or item.findtext(
                    "{http://www.w3.org/2005/Atom}title"
                )
                description = (
                    item.findtext("description") or 
                    item.findtext("{http://www.w3.org/2005/Atom}summary") or
                    item.findtext("{http://www.w3.org/2005/Atom}content") or
                    ""
                )
                link = item.findtext("link")
                if not link:
                    link_elem = item.find("{http://www.w3.org/2005/Atom}link")
                    if link_elem is not None:
                        link = link_elem.get("href", "")
                
                pub_date = item.findtext("pubDate") or item.findtext(
                    "{http://www.w3.org/2005/Atom}published"
                )
                
                if title:
                    # Clean HTML from description
                    clean_desc = re.sub(r"<[^>]+>", "", description or "")
                    clean_desc = clean_desc[:500]  # Limit length
                    
                    articles.append(NewsArticle(
                        title=title.strip(),
                        description=clean_desc.strip(),
                        url=link or "",
                        source=source_name,
                        category=category,
                    ))
        except Exception as e:
            logger.warning("Failed to parse RSS: %s", e)
        
        return articles


# ==============================================================================
# News Plugin
# ==============================================================================

class NewsPlugin(Plugin):
    """News Plugin for LLMHive.
    
    Provides tools for fetching and searching latest news.
    
    Tools:
    - news_headlines: Get latest headlines from various sources
    - news_search: Search news by topic/keyword
    - news_by_category: Get news for a specific category
    """
    
    def __init__(self):
        config = PluginConfig(
            name="news",
            display_name="News",
            version="1.0.0",
            description="Get latest news and headlines from various sources",
            author="LLMHive",
            domains=["news", "current events", "headlines"],
            keywords=[
                "news", "latest", "headlines", "current events", "today",
                "recent", "breaking", "update", "what happened", "what's new",
            ],
            min_tier=PluginTier.FREE,
            capabilities=[PluginCapability.TOOLS, PluginCapability.KNOWLEDGE],
            enabled=True,
            auto_activate=True,
            priority=40,
        )
        super().__init__(config)
        
        self.rss_client = RSSClient()
        self.feeds = RSS_FEEDS
    
    async def initialize(self) -> bool:
        """Initialize News plugin."""
        logger.info("Initializing News plugin")
        return True
    
    def get_tools(self) -> List[PluginTool]:
        """Get news tools."""
        return [
            PluginTool(
                name="news_headlines",
                description="Get the latest news headlines from major sources. Can filter by category (general, technology, science, business).",
                handler=self._tool_headlines,
                parameters={
                    "type": "object",
                    "properties": {
                        "category": {
                            "type": "string",
                            "description": "News category",
                            "enum": ["general", "technology", "science", "business"],
                            "default": "general",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum articles (default: 10)",
                            "default": 10,
                        },
                    },
                },
                domains=["news", "current events"],
                trigger_keywords=["news", "headlines", "latest news", "what's happening"],
            ),
            PluginTool(
                name="news_search",
                description="Search news articles by keyword or topic.",
                handler=self._tool_search,
                parameters={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query (keyword or topic)",
                        },
                        "category": {
                            "type": "string",
                            "description": "News category filter",
                            "enum": ["general", "technology", "science", "business", "all"],
                            "default": "all",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum results",
                            "default": 10,
                        },
                    },
                    "required": ["query"],
                },
                domains=["news", "current events"],
                trigger_keywords=["search news", "news about", "find news"],
            ),
            PluginTool(
                name="news_tech",
                description="Get the latest technology news.",
                handler=self._tool_tech_news,
                parameters={
                    "type": "object",
                    "properties": {
                        "limit": {
                            "type": "integer",
                            "description": "Maximum articles",
                            "default": 10,
                        },
                    },
                },
                domains=["news", "technology"],
                trigger_keywords=["tech news", "technology news", "tech headlines"],
            ),
        ]
    
    def get_knowledge_bases(self) -> List[PluginKnowledgeBase]:
        """News provides dynamic knowledge via feeds."""
        return [
            PluginKnowledgeBase(
                name="news_feeds",
                description="Latest news from RSS feeds",
                kb_type="api",
                domains=["news", "current events"],
                query_handler=self._query_knowledge,
            )
        ]
    
    async def _query_knowledge(
        self,
        query: str,
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """Query news for knowledge."""
        # Fetch headlines and filter by query
        articles = await self._fetch_all_headlines(limit=20)
        
        # Simple keyword matching
        query_words = set(query.lower().split())
        
        relevant = []
        for article in articles:
            text = f"{article.title} {article.description}".lower()
            if any(word in text for word in query_words):
                relevant.append({
                    "content": f"{article.title}: {article.description}",
                    "source": f"News ({article.source})",
                    "url": article.url,
                    "confidence": 0.7,
                })
        
        return relevant[:top_k]
    
    async def _fetch_all_headlines(
        self,
        category: Optional[str] = None,
        limit: int = 10,
    ) -> List[NewsArticle]:
        """Fetch headlines from all feeds."""
        tasks = []
        
        for feed_id, feed_info in self.feeds.items():
            if category and feed_info["category"] != category:
                continue
            
            tasks.append(
                self.rss_client.fetch_feed(
                    feed_info["url"],
                    feed_info["name"],
                    feed_info["category"],
                    limit=limit,
                )
            )
        
        if not tasks:
            return []
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        articles = []
        for result in results:
            if isinstance(result, list):
                articles.extend(result)
        
        return articles[:limit]
    
    # -------------------------------------------------------------------------
    # Tool Handlers
    # -------------------------------------------------------------------------
    
    async def _tool_headlines(
        self,
        category: str = "general",
        limit: int = 10,
        **kwargs,
    ) -> Dict[str, Any]:
        """Handle news_headlines tool call."""
        articles = await self._fetch_all_headlines(category, limit)
        
        return {
            "success": True,
            "category": category,
            "articles": [
                {
                    "title": a.title,
                    "description": a.description,
                    "source": a.source,
                    "url": a.url,
                }
                for a in articles
            ],
            "count": len(articles),
        }
    
    async def _tool_search(
        self,
        query: str,
        category: str = "all",
        limit: int = 10,
        **kwargs,
    ) -> Dict[str, Any]:
        """Handle news_search tool call."""
        # Fetch from relevant categories
        cat_filter = None if category == "all" else category
        articles = await self._fetch_all_headlines(cat_filter, limit=50)
        
        # Filter by query
        query_lower = query.lower()
        matching = [
            a for a in articles
            if query_lower in a.title.lower() or query_lower in a.description.lower()
        ]
        
        return {
            "success": True,
            "query": query,
            "category": category,
            "articles": [
                {
                    "title": a.title,
                    "description": a.description,
                    "source": a.source,
                    "url": a.url,
                }
                for a in matching[:limit]
            ],
            "count": len(matching[:limit]),
        }
    
    async def _tool_tech_news(
        self,
        limit: int = 10,
        **kwargs,
    ) -> Dict[str, Any]:
        """Handle news_tech tool call."""
        return await self._tool_headlines(category="technology", limit=limit)


# Plugin manifest
PLUGIN_MANIFEST = {
    "name": "news",
    "display_name": "News",
    "version": "1.0.0",
    "description": "Get latest news and headlines from various sources",
    "author": "LLMHive",
    "domains": ["news", "current events", "headlines"],
    "keywords": ["news", "latest", "headlines", "current events", "today"],
    "min_tier": "free",
    "capabilities": ["tools", "knowledge"],
    "entry_point": "news_plugin.py",
    "plugin_class": "NewsPlugin",
    "enabled": True,
    "auto_activate": True,
    "priority": 40,
}

