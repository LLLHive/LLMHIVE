"""Domain-Plugin Router.

Integrates plugins with the adaptive routing system, ensuring
domain-specific queries are routed to appropriate plugins.

Features:
- Domain classification
- Plugin selection based on query
- Knowledge augmentation
- Tool recommendation

Usage:
    router = get_domain_router()
    
    # Get plugin for domain
    plugin = router.route_to_plugin(query, domain)
    
    # Augment query with plugin knowledge
    augmented = await router.augment_with_knowledge(query, domain)
"""
from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from .base import Plugin, PluginTool, PluginKnowledgeBase
from .manager import PluginManager, get_plugin_manager

logger = logging.getLogger(__name__)


# ==============================================================================
# Domain Classification
# ==============================================================================

# Domain keywords for classification
DOMAIN_KEYWORDS: Dict[str, List[str]] = {
    "medical": [
        "health", "medical", "doctor", "disease", "symptom", "treatment",
        "diagnosis", "medicine", "hospital", "patient", "clinical", "therapy",
        "prescription", "surgery", "vaccine", "illness", "condition",
    ],
    "legal": [
        "law", "legal", "court", "lawyer", "attorney", "contract", "sue",
        "lawsuit", "legislation", "statute", "regulation", "compliance",
        "rights", "liability", "tort", "criminal", "civil",
    ],
    "finance": [
        "finance", "financial", "stock", "market", "investment", "trading",
        "banking", "loan", "mortgage", "credit", "debt", "portfolio",
        "dividend", "interest", "budget", "tax", "accounting",
    ],
    "technology": [
        "technology", "software", "programming", "code", "developer", "api",
        "database", "server", "cloud", "algorithm", "machine learning", "ai",
        "artificial intelligence", "neural", "data science",
    ],
    "science": [
        "science", "scientific", "research", "experiment", "hypothesis",
        "physics", "chemistry", "biology", "astronomy", "geology",
        "laboratory", "theory", "quantum", "particle",
    ],
    "news": [
        "news", "latest", "current events", "today", "recent", "breaking",
        "update", "headline", "report", "announcement", "press",
    ],
    "weather": [
        "weather", "temperature", "forecast", "rain", "snow", "sunny",
        "cloudy", "humidity", "climate", "storm", "wind",
    ],
    "math": [
        "calculate", "math", "equation", "formula", "solve", "computation",
        "arithmetic", "algebra", "calculus", "statistics", "probability",
    ],
}


@dataclass(slots=True)
class DomainMatch:
    """Result of domain classification."""
    domain: str
    confidence: float
    keywords_matched: List[str]
    plugins_available: List[str]


# ==============================================================================
# Domain Router
# ==============================================================================

class DomainPluginRouter:
    """Routes queries to appropriate plugins based on domain.
    
    Features:
    - Domain classification from query text
    - Plugin matching and selection
    - Knowledge augmentation
    - Tool recommendation
    
    Usage:
        router = DomainPluginRouter()
        
        # Classify domain
        domain = router.classify_domain(query)
        
        # Get best plugin
        plugin = router.get_best_plugin(query, domain)
        
        # Augment query with knowledge
        augmented = await router.augment_query(query)
    """
    
    def __init__(
        self,
        plugin_manager: Optional[PluginManager] = None,
        domain_keywords: Optional[Dict[str, List[str]]] = None,
    ):
        self.plugin_manager = plugin_manager or get_plugin_manager()
        self.domain_keywords = domain_keywords or DOMAIN_KEYWORDS
    
    def classify_domain(
        self,
        query: str,
        threshold: float = 0.3,
    ) -> Optional[DomainMatch]:
        """Classify the domain of a query.
        
        Args:
            query: User query
            threshold: Minimum confidence threshold
            
        Returns:
            DomainMatch if domain detected, else None
        """
        query_lower = query.lower()
        best_domain = None
        best_score = 0.0
        best_keywords: List[str] = []
        
        for domain, keywords in self.domain_keywords.items():
            matched = [kw for kw in keywords if kw.lower() in query_lower]
            if matched:
                score = len(matched) / len(keywords)
                # Boost for multiple matches
                if len(matched) > 1:
                    score = min(score * 1.5, 1.0)
                
                if score > best_score:
                    best_score = score
                    best_domain = domain
                    best_keywords = matched
        
        if best_domain and best_score >= threshold:
            # Find available plugins for this domain
            plugins = self.plugin_manager.get_plugins_for_domain(best_domain)
            plugin_names = [p.name for p in plugins if p.is_active]
            
            return DomainMatch(
                domain=best_domain,
                confidence=best_score,
                keywords_matched=best_keywords,
                plugins_available=plugin_names,
            )
        
        return None
    
    def get_best_plugin(
        self,
        query: str,
        domain: Optional[str] = None,
        user_tier: str = "free",
    ) -> Optional[Plugin]:
        """Get the best plugin for a query.
        
        Args:
            query: User query
            domain: Optional pre-classified domain
            user_tier: User's subscription tier
            
        Returns:
            Best matching plugin or None
        """
        # Use plugin manager's matching
        return self.plugin_manager.get_best_plugin_for_query(
            query, domain, user_tier
        )
    
    def get_relevant_tools(
        self,
        query: str,
        domain: Optional[str] = None,
        user_tier: str = "free",
        max_tools: int = 5,
    ) -> List[PluginTool]:
        """Get tools relevant to a query.
        
        Args:
            query: User query
            domain: Optional domain filter
            user_tier: User tier
            max_tools: Maximum tools to return
            
        Returns:
            List of relevant PluginTools
        """
        # If no domain specified, classify
        if not domain:
            domain_match = self.classify_domain(query)
            if domain_match:
                domain = domain_match.domain
        
        # Get domain-specific tools
        if domain:
            tools = self.plugin_manager.get_tools_for_domain(domain, user_tier)
        else:
            tools = self.plugin_manager.get_all_tools(user_tier)
        
        # Score and rank tools
        scored_tools: List[Tuple[float, PluginTool]] = []
        query_lower = query.lower()
        
        for tool in tools:
            score = 0.0
            
            # Keyword match
            for kw in tool.trigger_keywords:
                if kw.lower() in query_lower:
                    score += 0.3
            
            # Name/description match
            if any(word in tool.description.lower() for word in query_lower.split()):
                score += 0.2
            
            scored_tools.append((score, tool))
        
        # Sort by score
        scored_tools.sort(key=lambda x: x[0], reverse=True)
        
        return [t for _, t in scored_tools[:max_tools]]
    
    async def augment_query(
        self,
        query: str,
        domain: Optional[str] = None,
        user_tier: str = "free",
        max_context_items: int = 3,
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """Augment query with plugin knowledge.
        
        Fetches relevant information from plugin knowledge bases
        and prepends it to the query.
        
        Args:
            query: Original query
            domain: Optional domain
            user_tier: User tier
            max_context_items: Max knowledge items to include
            
        Returns:
            (augmented_query, knowledge_items)
        """
        # Classify domain if needed
        if not domain:
            domain_match = self.classify_domain(query)
            if domain_match:
                domain = domain_match.domain
        
        # Query plugin knowledge
        knowledge_items = await self.plugin_manager.query_all_knowledge(
            query=query,
            domain=domain,
            user_tier=user_tier,
            top_k=max_context_items,
        )
        
        if not knowledge_items:
            return query, []
        
        # Build context string
        context_parts = []
        for item in knowledge_items[:max_context_items]:
            if isinstance(item, dict):
                content = item.get("content") or item.get("text") or str(item)
                source = item.get("source", "plugin knowledge")
                context_parts.append(f"[{source}] {content}")
            else:
                context_parts.append(str(item))
        
        if context_parts:
            context = "\n".join(context_parts)
            augmented = f"Relevant context:\n{context}\n\nUser question: {query}"
            return augmented, knowledge_items
        
        return query, []
    
    def get_routing_recommendation(
        self,
        query: str,
        user_tier: str = "free",
    ) -> Dict[str, Any]:
        """Get comprehensive routing recommendation.
        
        Args:
            query: User query
            user_tier: User tier
            
        Returns:
            Routing recommendation with plugin, tools, and knowledge
        """
        # Classify domain
        domain_match = self.classify_domain(query)
        domain = domain_match.domain if domain_match else None
        
        # Get best plugin
        plugin = self.get_best_plugin(query, domain, user_tier)
        
        # Get relevant tools
        tools = self.get_relevant_tools(query, domain, user_tier)
        
        recommendation = {
            "domain": domain,
            "domain_confidence": domain_match.confidence if domain_match else 0.0,
            "keywords_matched": domain_match.keywords_matched if domain_match else [],
            "recommended_plugin": plugin.name if plugin else None,
            "plugin_info": plugin.get_info() if plugin else None,
            "relevant_tools": [
                {
                    "name": t.name,
                    "description": t.description,
                    "domains": t.domains,
                }
                for t in tools
            ],
            "should_query_knowledge": bool(
                plugin and plugin.get_knowledge_bases()
            ),
        }
        
        return recommendation


# ==============================================================================
# Global Instance
# ==============================================================================

_domain_router: Optional[DomainPluginRouter] = None


def get_domain_router() -> DomainPluginRouter:
    """Get or create global domain router."""
    global _domain_router
    if _domain_router is None:
        _domain_router = DomainPluginRouter()
    return _domain_router

