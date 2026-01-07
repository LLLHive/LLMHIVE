"""Query Router for LLMHive RAG System.

This module routes queries to appropriate retrieval strategies:
1. Factoid Fast-Path - Direct answers without clarification
2. Complex Query Router - Multi-hop retrieval for complex queries
3. Tool-Required Detection - Queries needing external tools
4. RAG-Dependent Queries - Standard retrieval path
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class QueryRoute(str, Enum):
    """Possible query routing destinations."""
    FACTOID_FAST = "factoid_fast"       # Simple factual, skip clarification
    COMPLEX_MULTIHOP = "complex_multihop"  # Multi-hop retrieval needed
    TOOL_REQUIRED = "tool_required"     # External tools needed
    RAG_STANDARD = "rag_standard"       # Standard RAG retrieval
    DIRECT_LLM = "direct_llm"           # No retrieval needed
    CLARIFICATION = "clarification"     # Genuine clarification needed


@dataclass
class RoutingDecision:
    """Result of query routing analysis."""
    route: QueryRoute
    confidence: float
    reasoning: str
    suggested_tools: List[str] = field(default_factory=list)
    skip_clarification: bool = False
    use_multihop: bool = False
    use_verification: bool = False
    estimated_complexity: float = 0.5


# =============================================================================
# Pattern Definitions
# =============================================================================

# Factoid patterns - simple questions with known answer types
FACTOID_PATTERNS = [
    # Who/What/When/Where questions
    (r"^who (?:is|was|discovered|invented|wrote|painted|created|founded|won)\b", 0.95),
    (r"^what (?:is|was|are|were) (?:the|a|an)?\s*\w+(?:\s+\w+){0,3}\??$", 0.9),
    (r"^what (?:is|are) (?:the )?\w+ (?:of|for|in) ", 0.85),
    (r"^when (?:did|was|is|were)\b", 0.9),
    (r"^where (?:is|was|are|were)\b", 0.9),
    (r"^which (?:is|was|are|were)\b", 0.85),
    
    # Measurement questions
    (r"^how (?:much|many|old|long|far|tall|big|large|wide|deep)\b", 0.85),
    
    # Definition questions
    (r"^define\b", 0.9),
    (r"^what does .+ mean", 0.9),
    
    # Capital/discovery/invention questions
    (r"(?:capital|discovered|invented|founded|born|died|wrote|painted)\b.*\?$", 0.85),
]

# Complex query patterns - require multi-step reasoning
COMPLEX_PATTERNS = [
    (r"\b(?:analyze|compare|contrast|evaluate|assess|examine)\b", 0.8),
    (r"\bpros and cons\b", 0.85),
    (r"\badvantages and disadvantages\b", 0.85),
    (r"\b(?:step by step|in detail|comprehensive|thorough)\b", 0.7),
    (r"[,;].*[,;].*[,;]", 0.75),  # Multiple clauses
    (r"\b\d+\.\s+\w+.*\b\d+\.\s+\w+", 0.8),  # Numbered lists
    (r"\b(?:how can|how should|how would)\b.*\b(?:and|while|also)\b", 0.75),
]

# Tool-required patterns - need external data or computation
TOOL_REQUIRED_PATTERNS = [
    (r"\b(?:current|today|now|latest|recent|live)\b", ["web_search"], 0.8),
    (r"\b(?:price|stock|weather|news|score)\b", ["web_search"], 0.85),
    (r"\b(?:calculate|compute|solve|what is \d+)\b", ["calculator"], 0.9),
    (r"\b(?:search|look up|find|google)\b", ["web_search"], 0.75),
    (r"\b(?:run|execute|code|program|script)\b", ["python_exec"], 0.7),
    (r"\b(?:convert|conversion)\b.*\b(?:to|into)\b", ["convert", "calculator"], 0.8),
]

# Truly ambiguous patterns - need clarification
AMBIGUOUS_PATTERNS = [
    (r"^(?:it|this|that|they|them)\b", 0.9),
    (r"^tell me about it\b", 0.95),
    (r"^continue\b", 0.9),
    (r"^more\b", 0.85),
    (r"^what about\b", 0.8),
    (r"^how about\b", 0.8),
    (r"^(?:the same|that one|this thing)\b", 0.85),
]

# Direct LLM patterns - no retrieval needed
DIRECT_LLM_PATTERNS = [
    (r"^(?:hello|hi|hey|greetings|good morning|good evening)\b", 0.95),
    (r"^(?:thank you|thanks|appreciate)\b", 0.95),
    (r"^(?:write|create|compose|draft|generate)\b.*\b(?:poem|story|essay|letter|email)\b", 0.8),
    (r"^(?:translate|rewrite|paraphrase|summarize)\b", 0.75),
]


# =============================================================================
# Query Router
# =============================================================================

class QueryRouter:
    """Routes queries to appropriate handling strategies.
    
    This router analyzes incoming queries and determines:
    1. Whether clarification should be skipped (factoid fast-path)
    2. Which retrieval strategy to use
    3. Which tools might be needed
    4. Whether multi-hop retrieval is required
    """
    
    def __init__(self):
        """Initialize the query router."""
        self.factoid_patterns = [(re.compile(p, re.IGNORECASE), c) for p, c in FACTOID_PATTERNS]
        self.complex_patterns = [(re.compile(p, re.IGNORECASE), c) for p, c in COMPLEX_PATTERNS]
        self.tool_patterns = [(re.compile(p, re.IGNORECASE), t, c) for p, t, c in TOOL_REQUIRED_PATTERNS]
        self.ambiguous_patterns = [(re.compile(p, re.IGNORECASE), c) for p, c in AMBIGUOUS_PATTERNS]
        self.direct_patterns = [(re.compile(p, re.IGNORECASE), c) for p, c in DIRECT_LLM_PATTERNS]
    
    def route(self, query: str, context: Optional[Dict[str, Any]] = None) -> RoutingDecision:
        """Route a query to the appropriate handling strategy.
        
        Args:
            query: User query
            context: Optional context (conversation history, user info, etc.)
            
        Returns:
            RoutingDecision with route and metadata
        """
        query = query.strip()
        query_lower = query.lower()
        word_count = len(query.split())
        
        # Check for direct LLM (no retrieval) first
        for pattern, confidence in self.direct_patterns:
            if pattern.search(query_lower):
                return RoutingDecision(
                    route=QueryRoute.DIRECT_LLM,
                    confidence=confidence,
                    reasoning="Direct LLM response (greeting/creative/translation)",
                    skip_clarification=True,
                )
        
        # Check for truly ambiguous queries (need clarification)
        if self._needs_context_resolution(query_lower, context):
            for pattern, confidence in self.ambiguous_patterns:
                if pattern.search(query_lower):
                    return RoutingDecision(
                        route=QueryRoute.CLARIFICATION,
                        confidence=confidence,
                        reasoning="Ambiguous reference requiring clarification",
                        skip_clarification=False,
                    )
        
        # Check for tool-required queries
        suggested_tools: List[str] = []
        tool_confidence = 0.0
        for pattern, tools, confidence in self.tool_patterns:
            if pattern.search(query_lower):
                suggested_tools.extend(tools)
                tool_confidence = max(tool_confidence, confidence)
        
        if suggested_tools:
            return RoutingDecision(
                route=QueryRoute.TOOL_REQUIRED,
                confidence=tool_confidence,
                reasoning=f"Query requires tools: {', '.join(set(suggested_tools))}",
                suggested_tools=list(set(suggested_tools)),
                skip_clarification=True,  # Tool queries don't need clarification
            )
        
        # Check for factoid fast-path
        for pattern, confidence in self.factoid_patterns:
            if pattern.search(query_lower):
                # Additional check: query should be reasonably short
                if word_count <= 15:
                    return RoutingDecision(
                        route=QueryRoute.FACTOID_FAST,
                        confidence=confidence,
                        reasoning="Simple factoid question - fast path enabled",
                        skip_clarification=True,
                        use_verification=word_count > 8,  # Verify longer factoids
                    )
        
        # Check for complex multi-hop queries
        for pattern, confidence in self.complex_patterns:
            if pattern.search(query_lower):
                return RoutingDecision(
                    route=QueryRoute.COMPLEX_MULTIHOP,
                    confidence=confidence,
                    reasoning="Complex query requiring multi-hop retrieval",
                    skip_clarification=True,  # Complex != ambiguous
                    use_multihop=True,
                    use_verification=True,
                    estimated_complexity=0.8,
                )
        
        # Default: standard RAG
        return RoutingDecision(
            route=QueryRoute.RAG_STANDARD,
            confidence=0.7,
            reasoning="Standard RAG retrieval path",
            skip_clarification=True,  # Default to not asking clarification
            estimated_complexity=self._estimate_complexity(query),
        )
    
    def _needs_context_resolution(
        self,
        query: str,
        context: Optional[Dict[str, Any]],
    ) -> bool:
        """Check if query has unresolved references.
        
        Args:
            query: Query string
            context: Conversation context
            
        Returns:
            True if query has dangling references
        """
        # If we have conversation context, references might be resolvable
        if context and context.get("has_history"):
            return False
        
        # Check for pronouns/references at start
        dangling_refs = ["it", "this", "that", "they", "them", "the same", "that one"]
        query_words = query.lower().split()
        
        if query_words and query_words[0] in dangling_refs:
            return True
        
        return False
    
    def _estimate_complexity(self, query: str) -> float:
        """Estimate query complexity on 0-1 scale.
        
        Args:
            query: Query string
            
        Returns:
            Complexity score
        """
        # Factors that increase complexity
        complexity = 0.3  # Base
        
        # Word count
        word_count = len(query.split())
        if word_count > 20:
            complexity += 0.2
        elif word_count > 10:
            complexity += 0.1
        
        # Multiple sentences/clauses
        if query.count('.') > 1 or query.count(';') > 0:
            complexity += 0.15
        
        # Multiple question marks
        if query.count('?') > 1:
            complexity += 0.2
        
        # Technical/domain terms
        technical_terms = [
            "algorithm", "architecture", "implementation", "framework",
            "infrastructure", "optimization", "performance", "scalability",
            "integration", "configuration", "deployment", "methodology",
        ]
        for term in technical_terms:
            if term in query.lower():
                complexity += 0.05
        
        return min(1.0, complexity)
    
    def is_factoid(self, query: str) -> bool:
        """Quick check if query is a simple factoid.
        
        Args:
            query: Query string
            
        Returns:
            True if query is a simple factoid
        """
        decision = self.route(query)
        return decision.route == QueryRoute.FACTOID_FAST
    
    def should_skip_clarification(self, query: str) -> Tuple[bool, str]:
        """Check if clarification should be skipped for this query.
        
        This is the main entry point for the factoid fast-path.
        
        Args:
            query: Query string
            
        Returns:
            Tuple of (should_skip, reason)
        """
        decision = self.route(query)
        return decision.skip_clarification, decision.reasoning


# =============================================================================
# Factoid Fast-Path Handler
# =============================================================================

class FactoidFastPath:
    """Handler for factoid queries that skips unnecessary clarification.
    
    This ensures simple factual questions like "Who discovered penicillin?"
    are answered directly without asking for clarification.
    """
    
    def __init__(
        self,
        router: Optional[QueryRouter] = None,
        retrieval_engine: Optional[Any] = None,
        llm_provider: Optional[Any] = None,
    ):
        """Initialize factoid fast-path.
        
        Args:
            router: Query router
            retrieval_engine: Retrieval engine for knowledge lookup
            llm_provider: LLM provider for answering
        """
        self.router = router or QueryRouter()
        self.retrieval_engine = retrieval_engine
        self.llm_provider = llm_provider
    
    async def handle_if_factoid(
        self,
        query: str,
        user_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Handle query if it's a factoid, otherwise return None.
        
        Args:
            query: User query
            user_id: User ID for retrieval
            
        Returns:
            Response dict if handled, None if not a factoid
        """
        decision = self.router.route(query)
        
        if decision.route != QueryRoute.FACTOID_FAST:
            return None
        
        logger.info("Factoid fast-path: handling '%s'", query[:50])
        
        # Retrieve relevant context if available
        context = ""
        if self.retrieval_engine:
            try:
                result = await self.retrieval_engine.retrieve(query, user_id, top_k=3)
                if result.documents:
                    context = "\n\n".join([doc.content for doc in result.documents[:3]])
            except Exception as e:
                logger.warning("Retrieval failed for factoid: %s", e)
        
        # Generate answer
        if self.llm_provider:
            answer = await self._generate_factoid_answer(query, context)
        else:
            # No LLM, return context directly
            answer = context if context else "I don't have information about that."
        
        return {
            "answer": answer,
            "route": "factoid_fast",
            "confidence": decision.confidence,
            "skip_clarification": True,
            "retrieval_used": bool(context),
        }
    
    async def _generate_factoid_answer(self, query: str, context: str) -> str:
        """Generate a direct answer to a factoid question.
        
        Args:
            query: Factoid question
            context: Retrieved context
            
        Returns:
            Answer string
        """
        if not self.llm_provider:
            return "Cannot generate answer without LLM provider."
        
        system_prompt = """You are a helpful assistant that answers factual questions directly and concisely.
- Answer the question directly without asking for clarification
- Be factual and accurate
- If you're not sure, say so but still provide your best answer
- Keep the answer concise but complete"""

        if context:
            user_prompt = f"""Based on this information:

{context[:2000]}

Question: {query}

Answer directly and concisely:"""
        else:
            user_prompt = f"""Question: {query}

Answer directly and concisely based on your knowledge:"""

        try:
            result = await self.llm_provider.complete(
                user_prompt,
                system=system_prompt,
                model="gpt-4o-mini",
                temperature=0,
                max_tokens=300,
            )
            return getattr(result, 'content', '') or getattr(result, 'text', '')
        except Exception as e:
            logger.error("Factoid answer generation failed: %s", e)
            return f"I encountered an error answering: {str(e)[:100]}"


# =============================================================================
# Factory Functions
# =============================================================================

_query_router: Optional[QueryRouter] = None
_factoid_handler: Optional[FactoidFastPath] = None


def get_query_router() -> QueryRouter:
    """Get global query router instance."""
    global _query_router
    if _query_router is None:
        _query_router = QueryRouter()
    return _query_router


def get_factoid_handler(
    retrieval_engine: Optional[Any] = None,
    llm_provider: Optional[Any] = None,
) -> FactoidFastPath:
    """Get global factoid handler instance."""
    global _factoid_handler
    if _factoid_handler is None:
        _factoid_handler = FactoidFastPath(
            router=get_query_router(),
            retrieval_engine=retrieval_engine,
            llm_provider=llm_provider,
        )
    return _factoid_handler


def reset_query_router() -> None:
    """Reset global instances."""
    global _query_router, _factoid_handler
    _query_router = None
    _factoid_handler = None

