"""Web Research Service using Tavily API.

This module provides web search capabilities for the orchestrator
to retrieve current, real-time information from the internet.

Features:
- Search the web using Tavily API
- Extract relevant snippets and content
- Handle rate limiting and errors gracefully
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import List, Optional, Dict, Any

logger = logging.getLogger(__name__)

# Check for Tavily availability
try:
    from tavily import TavilyClient
    TAVILY_AVAILABLE = True
except ImportError:
    TAVILY_AVAILABLE = False
    TavilyClient = None
    logger.warning("Tavily not installed. Run: pip install tavily-python")


@dataclass
class SearchResult:
    """A single search result."""
    title: str
    url: str
    snippet: Optional[str] = None
    content: Optional[str] = None
    score: float = 0.0
    published_date: Optional[str] = None


class WebResearchClient:
    """Client for web research using Tavily API.
    
    Tavily is specifically designed for LLM applications and provides
    high-quality, relevant search results optimized for AI consumption.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize the web research client.
        
        Args:
            api_key: Tavily API key. If not provided, reads from TAVILY_API_KEY env var.
        """
        self._api_key = api_key or os.getenv("TAVILY_API_KEY")
        self._client: Optional[TavilyClient] = None
        
        if not self._api_key:
            logger.warning("TAVILY_API_KEY not set. Web search will not be available.")
        elif TAVILY_AVAILABLE:
            try:
                self._client = TavilyClient(api_key=self._api_key)
                logger.info("Tavily web search client initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Tavily client: {e}")
    
    @property
    def is_available(self) -> bool:
        """Check if web search is available."""
        return self._client is not None
    
    async def search(
        self,
        query: str,
        max_results: int = 10,  # Increased for list queries
        search_depth: str = "advanced",  # Thorough search for better results
        include_domains: Optional[List[str]] = None,
        exclude_domains: Optional[List[str]] = None,
        days: Optional[int] = None,  # Limit to recent results (days)
        topic: str = "general",  # "general" or "news"
    ) -> List[SearchResult]:
        """Search the web for information.
        
        Args:
            query: The search query
            max_results: Maximum number of results (default: 10)
            search_depth: "basic" for faster results, "advanced" for more thorough (default: advanced)
            include_domains: Only search these domains (optional)
            exclude_domains: Exclude these domains (optional)
            days: Only return results from the last N days (optional, for fresh data)
            topic: "general" for broad search, "news" for news articles
            
        Returns:
            List of SearchResult objects
        """
        if not self._client:
            logger.warning("Web search not available - Tavily client not initialized")
            return []
        
        try:
            logger.info(f"Web search: query='{query[:50]}...', max_results={max_results}, days={days}, topic={topic}")
            
            # Build search params
            search_params = {
                "query": query,
                "max_results": max_results,
                "search_depth": search_depth,
                "include_domains": include_domains or [],
                "exclude_domains": exclude_domains or [],
                "include_answer": True,  # Synthesize answer from sources
                "topic": topic,
            }
            
            # Add days filter for recency if specified
            if days:
                search_params["days"] = days
            
            # Call Tavily API
            response = self._client.search(**search_params)
            
            results = []
            
            # Include synthesized answer as first result if available
            if response.get("answer"):
                results.append(SearchResult(
                    title="Synthesized Answer",
                    url="tavily-answer",
                    snippet=response["answer"],
                    content=response["answer"],
                    score=1.0,
                ))
                logger.info("Tavily provided synthesized answer")
            
            for item in response.get("results", []):
                results.append(SearchResult(
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    snippet=item.get("snippet", item.get("content", "")[:500]),
                    content=item.get("content"),
                    score=item.get("score", 0.0),
                    published_date=item.get("published_date"),
                ))
            
            logger.info(f"Web search returned {len(results)} results")
            return results
            
        except Exception as e:
            logger.error(f"Web search failed: {e}")
            return []
    
    async def search_news(
        self,
        query: str,
        max_results: int = 5,
        days: int = 7,
    ) -> List[SearchResult]:
        """Search for recent news articles.
        
        Args:
            query: The search query
            max_results: Maximum number of results
            days: How many days back to search (default: 7)
            
        Returns:
            List of SearchResult objects
        """
        if not self._client:
            return []
        
        try:
            # Add time context to query for recency
            enhanced_query = f"{query} latest news {days} days"
            return await self.search(
                query=enhanced_query,
                max_results=max_results,
                search_depth="advanced",
            )
        except Exception as e:
            logger.error(f"News search failed: {e}")
            return []
    
    async def get_answer(
        self,
        query: str,
        max_results: int = 5,
    ) -> Dict[str, Any]:
        """Get a direct answer with supporting sources.
        
        Uses Tavily's answer endpoint which provides a synthesized
        answer along with the source URLs.
        
        Args:
            query: The question to answer
            max_results: Number of sources to include
            
        Returns:
            Dict with 'answer' and 'sources' keys
        """
        if not self._client:
            return {"answer": None, "sources": [], "error": "Web search not available"}
        
        try:
            response = self._client.search(
                query=query,
                max_results=max_results,
                search_depth="advanced",
                include_answer=True,
            )
            
            return {
                "answer": response.get("answer"),
                "sources": [
                    {"title": r.get("title"), "url": r.get("url")}
                    for r in response.get("results", [])
                ],
            }
        except Exception as e:
            logger.error(f"Answer search failed: {e}")
            return {"answer": None, "sources": [], "error": str(e)}


# Global instance
_web_research_client: Optional[WebResearchClient] = None


def get_web_research_client() -> WebResearchClient:
    """Get or create the global web research client."""
    global _web_research_client
    if _web_research_client is None:
        _web_research_client = WebResearchClient()
    return _web_research_client


async def web_search(
    query: str, 
    max_results: int = 10,
    days: Optional[int] = None,
    topic: str = "general",
    **kwargs,
) -> List[SearchResult]:
    """Convenience function for web search.
    
    Args:
        query: Search query
        max_results: Maximum results
        days: Limit to last N days (for current data)
        topic: "general" or "news"
        
    Returns:
        List of SearchResult objects
    """
    client = get_web_research_client()
    return await client.search(query, max_results=max_results, days=days, topic=topic)


async def web_search_formatted(
    query: str, 
    max_results: int = 10,
    days: Optional[int] = None,
    topic: str = "general",
    **kwargs,
) -> str:
    """Search and return formatted results for LLM consumption.
    
    Args:
        query: Search query
        max_results: Maximum results
        days: Limit to last N days (for current data)
        topic: "general" or "news"
        
    Returns:
        Formatted string with search results
    """
    results = await web_search(query, max_results, days=days, topic=topic)
    
    if not results:
        # Return empty string when no results - orchestrator will handle fallback
        return ""
    
    # Add current date context and recency info
    from datetime import datetime
    current_date = datetime.now().strftime("%B %d, %Y")
    
    formatted = f"Web Search Results for: '{query}'\n"
    formatted += f"Search Date: {current_date}\n"
    if days:
        formatted += f"Recency Filter: Last {days} days\n"
    formatted += "=" * 50 + "\n\n"
    
    for i, result in enumerate(results, 1):
        formatted += f"{i}. {result.title}\n"
        formatted += f"   URL: {result.url}\n"
        if result.snippet:
            formatted += f"   Summary: {result.snippet}\n"
        if result.published_date:
            formatted += f"   Date: {result.published_date}\n"
        formatted += "\n"
    
    return formatted
