"""Enhanced RAG retrieval with multi-hop, re-ranking, and source attribution."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence

from ..knowledge import KnowledgeBase, KnowledgeHit

logger = logging.getLogger(__name__)


@dataclass
class SourceAttribution:
    """Source metadata for retrieved knowledge."""
    
    title: Optional[str] = None
    url: Optional[str] = None
    document_id: Optional[str] = None
    domain: Optional[str] = None
    verified: bool = False
    timestamp: Optional[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class EnhancedKnowledgeHit(KnowledgeHit):
    """Enhanced knowledge hit with source attribution and re-ranking scores."""
    
    source: Optional[SourceAttribution] = None
    rerank_score: Optional[float] = None
    hop: int = 1  # Which retrieval hop this came from (1 = initial, 2+ = multi-hop)


class Reranker:
    """Re-ranks retrieved passages based on relevance."""
    
    def __init__(self, use_ml_reranker: bool = False):
        """
        Initialize re-ranker.
        
        Args:
            use_ml_reranker: Whether to use ML-based re-ranker (future enhancement)
        """
        self.use_ml_reranker = use_ml_reranker
    
    def rerank(
        self,
        query: str,
        hits: List[EnhancedKnowledgeHit],
        top_k: int = 5,
    ) -> List[EnhancedKnowledgeHit]:
        """
        Re-rank knowledge hits based on relevance to query.
        
        Args:
            query: Original query
            hits: List of knowledge hits to re-rank
            top_k: Number of top results to return
            
        Returns:
            Re-ranked list of hits
        """
        if not hits:
            return []
        
        # Simple cosine similarity re-ranking (can be enhanced with ML)
        query_lower = query.lower()
        query_words = set(query_lower.split())
        
        scored_hits: List[tuple[EnhancedKnowledgeHit, float]] = []
        for hit in hits:
            # Base score from vector similarity
            base_score = hit.score or 0.0
            
            # Keyword overlap boost
            content_lower = hit.content.lower()
            content_words = set(content_lower.split())
            overlap = len(query_words.intersection(content_words))
            keyword_boost = min(0.3, overlap * 0.05)  # Max 0.3 boost
            
            # Length penalty (prefer medium-length passages)
            length_penalty = 0.0
            content_length = len(hit.content)
            if content_length < 50:
                length_penalty = -0.1  # Too short
            elif content_length > 2000:
                length_penalty = -0.05  # Too long
            
            # Verified fact boost
            verified_boost = 0.1 if (hit.source and hit.source.verified) else 0.0
            
            # Calculate final score
            final_score = base_score + keyword_boost + verified_boost + length_penalty
            hit.rerank_score = final_score
            scored_hits.append((hit, final_score))
        
        # Sort by re-rank score
        scored_hits.sort(key=lambda x: x[1], reverse=True)
        
        # Return top K
        reranked = [hit for hit, _ in scored_hits[:top_k]]
        
        logger.debug(
            "Reranker: Re-ranked %d hits, returning top %d (score range: %.2f-%.2f)",
            len(hits),
            len(reranked),
            reranked[-1].rerank_score if reranked else 0.0,
            reranked[0].rerank_score if reranked else 0.0,
        )
        
        return reranked


class MultiHopRetrieval:
    """Multi-hop retrieval for complex queries requiring reasoning over multiple pieces of info."""
    
    def __init__(self, knowledge_base: KnowledgeBase, max_hops: int = 2):
        """
        Initialize multi-hop retrieval.
        
        Args:
            knowledge_base: Knowledge base instance
            max_hops: Maximum number of retrieval hops
        """
        self.knowledge_base = knowledge_base
        self.max_hops = max_hops
    
    async def retrieve(
        self,
        query: str,
        user_id: str,
        *,
        initial_limit: int = 5,
        hop_limit: int = 3,
        min_score: float = 0.5,
    ) -> List[EnhancedKnowledgeHit]:
        """
        Perform multi-hop retrieval.
        
        Args:
            query: Original query
            user_id: User ID for filtering
            initial_limit: Number of results from initial search
            hop_limit: Number of results per hop
            min_score: Minimum similarity score
            
        Returns:
            List of enhanced knowledge hits from all hops
        """
        all_hits: List[EnhancedKnowledgeHit] = []
        seen_content: set[str] = set()
        
        # Hop 1: Initial retrieval
        logger.info("Multi-hop Retrieval: Hop 1 - Initial search for '%s'", query[:50])
        initial_hits = self.knowledge_base.search(
            user_id=user_id,
            query=query,
            limit=initial_limit,
            min_score=min_score,
        )
        
        for hit in initial_hits:
            enhanced = self._enhance_hit(hit, hop=1)
            if enhanced.content not in seen_content:
                all_hits.append(enhanced)
                seen_content.add(enhanced.content[:200])  # Use first 200 chars as key
        
        # Hops 2+: Targeted retrieval based on initial results
        if self.max_hops > 1 and initial_hits:
            # Extract key terms or questions from initial results
            for hop in range(2, self.max_hops + 1):
                logger.info("Multi-hop Retrieval: Hop %d - Targeted search", hop)
                
                # Build follow-up query from initial results
                follow_up_query = self._build_followup_query(query, initial_hits)
                
                if not follow_up_query:
                    break
                
                # Search with follow-up query
                hop_hits = self.knowledge_base.search(
                    user_id=user_id,
                    query=follow_up_query,
                    limit=hop_limit,
                    min_score=min_score * 0.8,  # Slightly lower threshold for follow-ups
                )
                
                for hit in hop_hits:
                    enhanced = self._enhance_hit(hit, hop=hop)
                    # Avoid duplicates
                    if enhanced.content[:200] not in seen_content:
                        all_hits.append(enhanced)
                        seen_content.add(enhanced.content[:200])
                
                # If no new results, stop
                if not hop_hits:
                    break
        
        logger.info(
            "Multi-hop Retrieval: Completed %d hops, retrieved %d unique hits",
            min(self.max_hops, len([h for h in all_hits if h.hop > 1]) + 1),
            len(all_hits),
        )
        
        return all_hits
    
    def _enhance_hit(self, hit: KnowledgeHit, hop: int) -> EnhancedKnowledgeHit:
        """Convert KnowledgeHit to EnhancedKnowledgeHit with source attribution."""
        # Extract source information from metadata
        source = None
        if hit.metadata:
            source = SourceAttribution(
                title=hit.metadata.get("title"),
                url=hit.metadata.get("url"),
                document_id=hit.metadata.get("vector_id") or hit.metadata.get("document_id"),
                domain=hit.metadata.get("domain"),
                verified=hit.metadata.get("verified", False),
                timestamp=hit.metadata.get("timestamp"),
                metadata=hit.metadata,
            )
        
        return EnhancedKnowledgeHit(
            content=hit.content,
            metadata=hit.metadata,
            score=hit.score,
            source=source,
            hop=hop,
        )
    
    def _build_followup_query(self, original_query: str, initial_hits: List[KnowledgeHit]) -> Optional[str]:
        """Build a follow-up query based on initial results."""
        if not initial_hits:
            return None
        
        # Extract key information from initial results
        key_phrases: List[str] = []
        for hit in initial_hits[:2]:  # Use top 2 results
            # Extract first sentence or key phrase
            content = hit.content.strip()
            if content:
                # Take first sentence or first 100 chars
                first_sentence = content.split('.')[0][:100]
                if first_sentence:
                    key_phrases.append(first_sentence)
        
        if not key_phrases:
            return None
        
        # Combine original query with key phrases
        follow_up = f"{original_query} Related: {' '.join(key_phrases[:2])}"
        return follow_up[:500]  # Limit length


class EnhancedKnowledgeBase(KnowledgeBase):
    """Enhanced knowledge base with multi-hop retrieval, re-ranking, and source attribution."""
    
    def __init__(self, session, *, enable_multihop: bool = True, enable_reranking: bool = True):
        """
        Initialize enhanced knowledge base.
        
        Args:
            session: Database session
            enable_multihop: Enable multi-hop retrieval
            enable_reranking: Enable re-ranking
        """
        super().__init__(session)
        self.enable_multihop = enable_multihop
        self.enable_reranking = enable_reranking
        self.multihop = MultiHopRetrieval(self, max_hops=2) if enable_multihop else None
        self.reranker = Reranker() if enable_reranking else None
        self._retrieval_cache: Dict[str, List[EnhancedKnowledgeHit]] = {}  # Simple in-memory cache
    
    def search_enhanced(
        self,
        user_id: str,
        query: str,
        *,
        limit: int = 5,
        min_score: float = 0.5,
        use_multihop: Optional[bool] = None,
        use_reranking: Optional[bool] = None,
    ) -> List[EnhancedKnowledgeHit]:
        """
        Enhanced search with multi-hop retrieval and re-ranking.
        
        Args:
            user_id: User ID for filtering
            query: Search query
            limit: Maximum number of results
            min_score: Minimum similarity score
            use_multihop: Override default multi-hop setting
            use_reranking: Override default re-ranking setting
            
        Returns:
            List of enhanced knowledge hits with source attribution
        """
        # Check cache
        cache_key = f"{user_id}:{query}"
        if cache_key in self._retrieval_cache:
            logger.debug("Enhanced Knowledge Base: Using cached retrieval results")
            return self._retrieval_cache[cache_key]
        
        use_multihop = use_multihop if use_multihop is not None else self.enable_multihop
        use_reranking = use_reranking if use_reranking is not None else self.enable_reranking
        
        # Step 1: Retrieve (with multi-hop if enabled)
        if use_multihop and self.multihop:
            import asyncio
            try:
                # Run async multi-hop retrieval
                hits = asyncio.run(self.multihop.retrieve(
                    query=query,
                    user_id=user_id,
                    initial_limit=limit * 2,  # Get more for re-ranking
                    hop_limit=limit,
                    min_score=min_score,
                ))
            except Exception as exc:
                logger.warning("Enhanced Knowledge Base: Multi-hop retrieval failed, using single-hop: %s", exc)
                hits = self._single_hop_search(user_id, query, limit * 2, min_score)
        else:
            hits = self._single_hop_search(user_id, query, limit * 2, min_score)
        
        # Step 2: Re-rank if enabled
        if use_reranking and self.reranker and hits:
            hits = self.reranker.rerank(query, hits, top_k=limit)
        else:
            # Just take top K
            hits = hits[:limit]
        
        # Cache results (simple in-memory cache, could be enhanced)
        self._retrieval_cache[cache_key] = hits
        # Clear cache after some time (simple implementation)
        if len(self._retrieval_cache) > 100:
            self._retrieval_cache.clear()
        
        return hits
    
    def _single_hop_search(
        self,
        user_id: str,
        query: str,
        limit: int,
        min_score: float,
    ) -> List[EnhancedKnowledgeHit]:
        """Single-hop search with source attribution."""
        hits = self.search(user_id=user_id, query=query, limit=limit, min_score=min_score)
        
        enhanced_hits: List[EnhancedKnowledgeHit] = []
        for hit in hits:
            # Extract source information
            source = None
            if hit.metadata:
                source = SourceAttribution(
                    title=hit.metadata.get("title"),
                    url=hit.metadata.get("url"),
                    document_id=hit.metadata.get("vector_id") or hit.metadata.get("document_id"),
                    domain=hit.metadata.get("domain"),
                    verified=hit.metadata.get("verified", False),
                    timestamp=hit.metadata.get("timestamp"),
                    metadata=hit.metadata,
                )
            
            enhanced_hits.append(EnhancedKnowledgeHit(
                content=hit.content,
                metadata=hit.metadata,
                score=hit.score,
                source=source,
                hop=1,
            ))
        
        return enhanced_hits
    
    def get_sources(self, hits: List[EnhancedKnowledgeHit]) -> List[SourceAttribution]:
        """Extract source attributions from knowledge hits."""
        sources: List[SourceAttribution] = []
        seen_urls: set[str] = set()
        
        for hit in hits:
            if hit.source and hit.source.url and hit.source.url not in seen_urls:
                sources.append(hit.source)
                seen_urls.add(hit.source.url)
        
        return sources

