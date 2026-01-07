"""Advanced Retrieval Engine with hybrid search, reranking, and HyDE.

This module implements state-of-the-art RAG optimizations:
1. Hybrid Semantic + Lexical (BM25) Retrieval
2. Cross-Encoder Reranking using MiniLM
3. HyDE (Hypothetical Document Embeddings) Fallback
4. Redis-backed Query Caching
5. Context Validation for RAG Quality
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import re
import time
from collections import Counter
from dataclasses import dataclass, field
from math import log
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class RetrievedDocument:
    """A document retrieved from the knowledge base."""
    content: str
    score: float
    doc_id: str
    source: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    rerank_score: Optional[float] = None
    retrieval_method: str = "semantic"  # semantic, lexical, hybrid, hyde


@dataclass
class RetrievalResult:
    """Result of a retrieval operation."""
    documents: List[RetrievedDocument]
    query: str
    method_used: str
    latency_ms: float
    cache_hit: bool = False
    hyde_used: bool = False
    reranked: bool = False


@dataclass
class RetrievalConfig:
    """Configuration for the retrieval engine."""
    # Hybrid search weights
    semantic_weight: float = 0.7
    lexical_weight: float = 0.3
    
    # Retrieval counts
    initial_candidates: int = 20  # Retrieve more for reranking
    final_top_k: int = 5
    
    # Reranking
    enable_reranking: bool = True
    rerank_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    
    # HyDE
    enable_hyde: bool = True
    hyde_threshold: float = 0.4  # Use HyDE if top score below this
    
    # Caching
    enable_cache: bool = True
    cache_ttl_seconds: int = 3600  # 1 hour
    
    # Context validation
    enable_validation: bool = True
    min_term_overlap: float = 0.2  # Minimum query term overlap


# =============================================================================
# BM25 Lexical Search
# =============================================================================

class BM25Index:
    """Simple BM25 index for lexical search.
    
    BM25 is a ranking function that scores documents based on term frequency
    and inverse document frequency, with saturation for term frequency.
    """
    
    def __init__(self, k1: float = 1.5, b: float = 0.75):
        """Initialize BM25 index.
        
        Args:
            k1: Term frequency saturation parameter (1.2-2.0 typical)
            b: Length normalization parameter (0.75 typical)
        """
        self.k1 = k1
        self.b = b
        self.doc_freqs: Dict[str, int] = {}  # term -> doc count
        self.doc_lengths: Dict[str, int] = {}  # doc_id -> length
        self.avg_doc_length: float = 0
        self.doc_term_freqs: Dict[str, Dict[str, int]] = {}  # doc_id -> {term: freq}
        self.doc_contents: Dict[str, str] = {}  # doc_id -> content
        self.total_docs: int = 0
    
    def add_documents(self, documents: List[Tuple[str, str]]) -> None:
        """Add documents to the index.
        
        Args:
            documents: List of (doc_id, content) tuples
        """
        for doc_id, content in documents:
            tokens = self._tokenize(content)
            self.doc_contents[doc_id] = content
            self.doc_lengths[doc_id] = len(tokens)
            
            # Count term frequencies
            term_freqs: Dict[str, int] = Counter(tokens)
            self.doc_term_freqs[doc_id] = term_freqs
            
            # Update document frequencies
            for term in set(tokens):
                self.doc_freqs[term] = self.doc_freqs.get(term, 0) + 1
        
        self.total_docs = len(self.doc_contents)
        if self.total_docs > 0:
            self.avg_doc_length = sum(self.doc_lengths.values()) / self.total_docs
    
    def search(self, query: str, top_k: int = 10) -> List[Tuple[str, float]]:
        """Search for documents matching the query.
        
        Args:
            query: Search query
            top_k: Number of results to return
            
        Returns:
            List of (doc_id, score) tuples sorted by score descending
        """
        query_tokens = self._tokenize(query)
        scores: Dict[str, float] = {}
        
        for doc_id in self.doc_contents:
            score = self._score_document(query_tokens, doc_id)
            if score > 0:
                scores[doc_id] = score
        
        # Sort by score descending
        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return sorted_scores[:top_k]
    
    def _score_document(self, query_tokens: List[str], doc_id: str) -> float:
        """Calculate BM25 score for a document.
        
        Args:
            query_tokens: Tokenized query
            doc_id: Document ID
            
        Returns:
            BM25 score
        """
        score = 0.0
        doc_length = self.doc_lengths.get(doc_id, 0)
        term_freqs = self.doc_term_freqs.get(doc_id, {})
        
        for term in query_tokens:
            if term not in term_freqs:
                continue
            
            tf = term_freqs[term]
            df = self.doc_freqs.get(term, 0)
            
            # IDF component
            idf = log((self.total_docs - df + 0.5) / (df + 0.5) + 1)
            
            # TF component with saturation
            tf_component = (tf * (self.k1 + 1)) / (
                tf + self.k1 * (1 - self.b + self.b * doc_length / self.avg_doc_length)
            )
            
            score += idf * tf_component
        
        return score
    
    def _tokenize(self, text: str) -> List[str]:
        """Tokenize text for BM25.
        
        Args:
            text: Text to tokenize
            
        Returns:
            List of tokens (lowercased words)
        """
        # Simple tokenization: lowercase, remove punctuation, split on whitespace
        text = text.lower()
        text = re.sub(r'[^\w\s]', ' ', text)
        tokens = text.split()
        
        # Remove stopwords (basic list)
        stopwords = {
            'a', 'an', 'the', 'is', 'are', 'was', 'were', 'be', 'been',
            'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
            'would', 'could', 'should', 'may', 'might', 'must', 'shall',
            'can', 'to', 'of', 'in', 'for', 'on', 'with', 'at', 'by',
            'from', 'as', 'into', 'through', 'during', 'before', 'after',
            'above', 'below', 'between', 'under', 'again', 'further',
            'then', 'once', 'here', 'there', 'when', 'where', 'why', 'how',
            'all', 'each', 'few', 'more', 'most', 'other', 'some', 'such',
            'no', 'nor', 'not', 'only', 'own', 'same', 'so', 'than', 'too',
            'very', 'just', 'and', 'but', 'if', 'or', 'because', 'until',
            'while', 'although', 'this', 'that', 'these', 'those', 'what',
        }
        
        return [t for t in tokens if t not in stopwords and len(t) > 1]


# =============================================================================
# Cross-Encoder Reranker
# =============================================================================

class CrossEncoderReranker:
    """Cross-encoder reranker for improved relevance scoring.
    
    Uses a transformer model to score query-document pairs together,
    capturing fine-grained semantic relationships.
    """
    
    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        """Initialize the reranker.
        
        Args:
            model_name: HuggingFace model name for cross-encoder
        """
        self.model_name = model_name
        self.model = None
        self._initialized = False
    
    def _lazy_init(self) -> bool:
        """Lazily initialize the model.
        
        Returns:
            True if model is available, False otherwise
        """
        if self._initialized:
            return self.model is not None
        
        self._initialized = True
        
        try:
            from sentence_transformers import CrossEncoder
            self.model = CrossEncoder(self.model_name)
            logger.info("Cross-encoder reranker initialized: %s", self.model_name)
            return True
        except ImportError:
            logger.warning(
                "sentence-transformers not installed. "
                "Install with: pip install sentence-transformers"
            )
            return False
        except Exception as e:
            logger.warning("Failed to load cross-encoder: %s", e)
            return False
    
    def rerank(
        self,
        query: str,
        documents: List[RetrievedDocument],
        top_k: int = 5,
    ) -> List[RetrievedDocument]:
        """Rerank documents using cross-encoder.
        
        Args:
            query: Search query
            documents: Documents to rerank
            top_k: Number of results to return
            
        Returns:
            Reranked documents with updated scores
        """
        if not documents:
            return []
        
        if not self._lazy_init():
            # Fall back to original ranking
            logger.debug("Cross-encoder not available, using original ranking")
            return documents[:top_k]
        
        try:
            # Prepare query-document pairs
            pairs = [(query, doc.content[:512]) for doc in documents]  # Truncate for efficiency
            
            # Get cross-encoder scores
            scores = self.model.predict(pairs)
            
            # Update documents with rerank scores
            for doc, score in zip(documents, scores):
                doc.rerank_score = float(score)
            
            # Sort by rerank score
            reranked = sorted(documents, key=lambda d: d.rerank_score or 0, reverse=True)
            
            return reranked[:top_k]
            
        except Exception as e:
            logger.error("Reranking failed: %s", e)
            return documents[:top_k]


# =============================================================================
# HyDE (Hypothetical Document Embeddings)
# =============================================================================

class HyDEGenerator:
    """Generate hypothetical documents for improved retrieval.
    
    HyDE works by having the LLM generate a hypothetical answer to the query,
    then using that answer's embedding to search for similar real documents.
    This bridges vocabulary gaps between queries and documents.
    """
    
    def __init__(self, llm_provider: Optional[Any] = None):
        """Initialize HyDE generator.
        
        Args:
            llm_provider: LLM provider for generating hypothetical documents
        """
        self.llm_provider = llm_provider
    
    async def generate_hypothetical_document(
        self,
        query: str,
        num_hypotheses: int = 1,
    ) -> List[str]:
        """Generate hypothetical documents for a query.
        
        Args:
            query: User query
            num_hypotheses: Number of hypothetical documents to generate
            
        Returns:
            List of hypothetical document texts
        """
        if not self.llm_provider:
            logger.debug("No LLM provider for HyDE, skipping")
            return []
        
        prompt = f"""Given this question, write a short passage that would directly answer it. 
Write as if you're providing factual information from a knowledge base.
Be specific and include relevant details.

Question: {query}

Passage:"""

        try:
            hypotheses = []
            for _ in range(num_hypotheses):
                result = await self.llm_provider.complete(
                    prompt,
                    model="gpt-4o-mini",
                    max_tokens=200,
                    temperature=0.7,
                )
                
                content = getattr(result, 'content', '') or getattr(result, 'text', '')
                if content:
                    hypotheses.append(content.strip())
            
            logger.info("HyDE generated %d hypothetical documents", len(hypotheses))
            return hypotheses
            
        except Exception as e:
            logger.error("HyDE generation failed: %s", e)
            return []


# =============================================================================
# Query Cache
# =============================================================================

class QueryCache:
    """Redis-backed query cache for repeated queries.
    
    Falls back to in-memory LRU cache if Redis is unavailable.
    """
    
    def __init__(
        self,
        redis_url: Optional[str] = None,
        ttl_seconds: int = 3600,
        max_memory_items: int = 1000,
    ):
        """Initialize query cache.
        
        Args:
            redis_url: Redis connection URL (optional)
            ttl_seconds: Cache TTL in seconds
            max_memory_items: Max items in memory cache
        """
        self.ttl_seconds = ttl_seconds
        self.max_memory_items = max_memory_items
        self.redis_client = None
        self._memory_cache: Dict[str, Tuple[Any, float]] = {}  # key -> (value, expiry)
        
        if redis_url:
            try:
                import redis
                self.redis_client = redis.from_url(redis_url)
                self.redis_client.ping()
                logger.info("Redis cache connected")
            except Exception as e:
                logger.warning("Redis not available, using memory cache: %s", e)
                self.redis_client = None
    
    def _make_key(self, query: str, config_hash: str) -> str:
        """Generate cache key from query and config."""
        combined = f"{query}:{config_hash}"
        return f"rag_cache:{hashlib.md5(combined.encode()).hexdigest()}"
    
    def get(self, query: str, config_hash: str = "") -> Optional[List[RetrievedDocument]]:
        """Get cached result.
        
        Args:
            query: Query string
            config_hash: Configuration hash for cache key
            
        Returns:
            Cached documents or None
        """
        key = self._make_key(query, config_hash)
        
        # Try Redis first
        if self.redis_client:
            try:
                import json
                data = self.redis_client.get(key)
                if data:
                    cached = json.loads(data)
                    return [RetrievedDocument(**doc) for doc in cached]
            except Exception as e:
                logger.debug("Redis cache get failed: %s", e)
        
        # Fall back to memory cache
        if key in self._memory_cache:
            value, expiry = self._memory_cache[key]
            if time.time() < expiry:
                return value
            else:
                del self._memory_cache[key]
        
        return None
    
    def set(
        self,
        query: str,
        documents: List[RetrievedDocument],
        config_hash: str = "",
    ) -> None:
        """Cache retrieval result.
        
        Args:
            query: Query string
            documents: Retrieved documents
            config_hash: Configuration hash for cache key
        """
        key = self._make_key(query, config_hash)
        
        # Serialize documents
        import json
        data = [
            {
                "content": doc.content,
                "score": doc.score,
                "doc_id": doc.doc_id,
                "source": doc.source,
                "metadata": doc.metadata,
                "rerank_score": doc.rerank_score,
                "retrieval_method": doc.retrieval_method,
            }
            for doc in documents
        ]
        
        # Try Redis first
        if self.redis_client:
            try:
                self.redis_client.setex(key, self.ttl_seconds, json.dumps(data))
                return
            except Exception as e:
                logger.debug("Redis cache set failed: %s", e)
        
        # Fall back to memory cache with LRU eviction
        if len(self._memory_cache) >= self.max_memory_items:
            # Evict oldest items
            sorted_items = sorted(
                self._memory_cache.items(),
                key=lambda x: x[1][1]  # Sort by expiry time
            )
            for old_key, _ in sorted_items[:100]:  # Remove 100 oldest
                del self._memory_cache[old_key]
        
        self._memory_cache[key] = (
            [RetrievedDocument(**d) for d in data],
            time.time() + self.ttl_seconds,
        )


# =============================================================================
# Context Validator
# =============================================================================

def validate_rag_context(
    query: str,
    documents: List[RetrievedDocument],
    min_term_overlap: float = 0.2,
) -> Tuple[bool, List[RetrievedDocument], str]:
    """Validate that retrieved context is relevant to the query.
    
    This sanity-check prevents feeding the LLM context that doesn't
    actually address the question.
    
    Args:
        query: Original query
        documents: Retrieved documents
        min_term_overlap: Minimum required term overlap ratio
        
    Returns:
        Tuple of (is_valid, filtered_documents, validation_message)
    """
    if not documents:
        return False, [], "No documents retrieved"
    
    # Extract query key terms
    query_lower = query.lower()
    query_terms = set(re.findall(r'\b\w{3,}\b', query_lower))
    
    # Remove common words
    common_words = {
        'what', 'when', 'where', 'who', 'how', 'why', 'which', 'the', 'and',
        'that', 'this', 'with', 'from', 'have', 'has', 'had', 'are', 'was',
        'were', 'been', 'being', 'about', 'into', 'through', 'during',
        'before', 'after', 'above', 'below', 'between', 'could', 'would',
        'should', 'does', 'did', 'can', 'will', 'just', 'more', 'also',
    }
    query_terms = query_terms - common_words
    
    if not query_terms:
        # Can't validate without query terms
        return True, documents, "No key terms to validate"
    
    valid_docs: List[RetrievedDocument] = []
    
    for doc in documents:
        doc_lower = doc.content.lower()
        doc_terms = set(re.findall(r'\b\w{3,}\b', doc_lower))
        
        # Calculate term overlap
        overlap = len(query_terms & doc_terms)
        overlap_ratio = overlap / len(query_terms)
        
        if overlap_ratio >= min_term_overlap:
            valid_docs.append(doc)
    
    if not valid_docs:
        return False, documents[:2], f"Low term overlap; using top {min(2, len(documents))} docs anyway"
    
    return True, valid_docs, f"Validated {len(valid_docs)}/{len(documents)} documents"


# =============================================================================
# Main Retrieval Engine
# =============================================================================

class RetrievalEngine:
    """Advanced retrieval engine with hybrid search, reranking, and HyDE.
    
    Implements state-of-the-art RAG optimizations:
    - Hybrid semantic + lexical (BM25) retrieval
    - Cross-encoder reranking
    - HyDE fallback for low-relevance cases
    - Query caching
    - Context validation
    """
    
    def __init__(
        self,
        semantic_search_fn: Optional[Callable] = None,
        embedding_fn: Optional[Callable] = None,
        llm_provider: Optional[Any] = None,
        config: Optional[RetrievalConfig] = None,
        redis_url: Optional[str] = None,
    ):
        """Initialize retrieval engine.
        
        Args:
            semantic_search_fn: Function for semantic search (query -> List[dict])
            embedding_fn: Function to embed text (text -> embedding)
            llm_provider: LLM provider for HyDE
            config: Retrieval configuration
            redis_url: Redis URL for caching
        """
        self.config = config or RetrievalConfig()
        self.semantic_search_fn = semantic_search_fn
        self.embedding_fn = embedding_fn
        
        # Initialize components
        self.bm25_index = BM25Index()
        self.reranker = CrossEncoderReranker(self.config.rerank_model)
        self.hyde_generator = HyDEGenerator(llm_provider)
        self.cache = QueryCache(
            redis_url=redis_url,
            ttl_seconds=self.config.cache_ttl_seconds,
        ) if self.config.enable_cache else None
        
        # Document store for BM25
        self._document_store: Dict[str, str] = {}
    
    def index_documents(self, documents: List[Tuple[str, str, Dict[str, Any]]]) -> None:
        """Index documents for BM25 search.
        
        Args:
            documents: List of (doc_id, content, metadata) tuples
        """
        for doc_id, content, metadata in documents:
            self._document_store[doc_id] = content
        
        # Build BM25 index
        self.bm25_index.add_documents([
            (doc_id, content) for doc_id, content, _ in documents
        ])
        
        logger.info("Indexed %d documents for BM25", len(documents))
    
    async def retrieve(
        self,
        query: str,
        user_id: Optional[str] = None,
        top_k: Optional[int] = None,
    ) -> RetrievalResult:
        """Retrieve relevant documents for a query.
        
        Args:
            query: Search query
            user_id: User ID for filtering (if applicable)
            top_k: Number of results (defaults to config)
            
        Returns:
            RetrievalResult with documents and metadata
        """
        start_time = time.time()
        top_k = top_k or self.config.final_top_k
        cache_hit = False
        hyde_used = False
        method_used = "hybrid"
        
        # Check cache
        config_hash = str(hash((self.config.semantic_weight, self.config.lexical_weight)))
        if self.cache:
            cached = self.cache.get(query, config_hash)
            if cached:
                logger.debug("Cache hit for query: %s", query[:50])
                return RetrievalResult(
                    documents=cached[:top_k],
                    query=query,
                    method_used="cached",
                    latency_ms=0,
                    cache_hit=True,
                )
        
        # Step 1: Semantic search
        semantic_docs = await self._semantic_search(query, user_id)
        
        # Step 2: Lexical search (BM25)
        lexical_docs = self._lexical_search(query)
        
        # Step 3: Hybrid fusion
        combined_docs = self._hybrid_fusion(semantic_docs, lexical_docs)
        
        # Step 4: Check if HyDE is needed
        top_score = combined_docs[0].score if combined_docs else 0
        if (
            self.config.enable_hyde
            and top_score < self.config.hyde_threshold
            and self.hyde_generator.llm_provider
        ):
            logger.info("Low relevance (%.2f), activating HyDE", top_score)
            hyde_docs = await self._hyde_search(query, user_id)
            if hyde_docs:
                combined_docs = self._merge_hyde_results(combined_docs, hyde_docs)
                hyde_used = True
                method_used = "hybrid+hyde"
        
        # Step 5: Rerank
        reranked = False
        if self.config.enable_reranking and combined_docs:
            combined_docs = self.reranker.rerank(
                query,
                combined_docs,
                top_k=top_k,
            )
            reranked = True
        else:
            combined_docs = combined_docs[:top_k]
        
        # Step 6: Validate context
        if self.config.enable_validation:
            is_valid, combined_docs, validation_msg = validate_rag_context(
                query, combined_docs, self.config.min_term_overlap
            )
            logger.debug("Context validation: %s", validation_msg)
        
        # Cache results
        if self.cache and combined_docs:
            self.cache.set(query, combined_docs, config_hash)
        
        latency_ms = (time.time() - start_time) * 1000
        
        return RetrievalResult(
            documents=combined_docs,
            query=query,
            method_used=method_used,
            latency_ms=latency_ms,
            cache_hit=cache_hit,
            hyde_used=hyde_used,
            reranked=reranked,
        )
    
    async def _semantic_search(
        self,
        query: str,
        user_id: Optional[str],
    ) -> List[RetrievedDocument]:
        """Perform semantic (dense) search.
        
        Args:
            query: Search query
            user_id: User ID for filtering
            
        Returns:
            List of retrieved documents
        """
        if not self.semantic_search_fn:
            return []
        
        try:
            # Call semantic search function
            if asyncio.iscoroutinefunction(self.semantic_search_fn):
                results = await self.semantic_search_fn(
                    query,
                    limit=self.config.initial_candidates,
                    user_id=user_id,
                )
            else:
                results = self.semantic_search_fn(
                    query,
                    limit=self.config.initial_candidates,
                    user_id=user_id,
                )
            
            # Convert to RetrievedDocument
            docs = []
            for r in results:
                if isinstance(r, dict):
                    docs.append(RetrievedDocument(
                        content=r.get('content', r.get('text', '')),
                        score=r.get('score', 0.0),
                        doc_id=r.get('id', r.get('doc_id', '')),
                        source=r.get('source'),
                        metadata=r.get('metadata', {}),
                        retrieval_method="semantic",
                    ))
                else:
                    docs.append(RetrievedDocument(
                        content=getattr(r, 'content', getattr(r, 'text', str(r))),
                        score=getattr(r, 'score', 0.0),
                        doc_id=getattr(r, 'id', getattr(r, 'doc_id', '')),
                        source=getattr(r, 'source', None),
                        metadata=getattr(r, 'metadata', {}),
                        retrieval_method="semantic",
                    ))
            
            return docs
            
        except Exception as e:
            logger.error("Semantic search failed: %s", e)
            return []
    
    def _lexical_search(self, query: str) -> List[RetrievedDocument]:
        """Perform lexical (BM25) search.
        
        Args:
            query: Search query
            
        Returns:
            List of retrieved documents
        """
        if not self._document_store:
            return []
        
        try:
            results = self.bm25_index.search(query, top_k=self.config.initial_candidates)
            
            docs = []
            for doc_id, score in results:
                content = self._document_store.get(doc_id, "")
                if content:
                    # Normalize BM25 score to 0-1 range (rough approximation)
                    normalized_score = min(1.0, score / 10.0)
                    docs.append(RetrievedDocument(
                        content=content,
                        score=normalized_score,
                        doc_id=doc_id,
                        retrieval_method="lexical",
                    ))
            
            return docs
            
        except Exception as e:
            logger.error("Lexical search failed: %s", e)
            return []
    
    def _hybrid_fusion(
        self,
        semantic_docs: List[RetrievedDocument],
        lexical_docs: List[RetrievedDocument],
    ) -> List[RetrievedDocument]:
        """Fuse semantic and lexical results using weighted combination.
        
        Args:
            semantic_docs: Documents from semantic search
            lexical_docs: Documents from lexical search
            
        Returns:
            Combined and sorted documents
        """
        # Create document map by content hash
        doc_map: Dict[str, RetrievedDocument] = {}
        
        # Process semantic results
        for doc in semantic_docs:
            content_hash = hashlib.md5(doc.content[:500].encode()).hexdigest()
            doc.score *= self.config.semantic_weight
            doc_map[content_hash] = doc
        
        # Process lexical results (merge or add)
        for doc in lexical_docs:
            content_hash = hashlib.md5(doc.content[:500].encode()).hexdigest()
            if content_hash in doc_map:
                # Merge scores
                existing = doc_map[content_hash]
                existing.score += doc.score * self.config.lexical_weight
                existing.retrieval_method = "hybrid"
            else:
                doc.score *= self.config.lexical_weight
                doc_map[content_hash] = doc
        
        # Sort by combined score
        combined = sorted(doc_map.values(), key=lambda d: d.score, reverse=True)
        
        return combined
    
    async def _hyde_search(
        self,
        query: str,
        user_id: Optional[str],
    ) -> List[RetrievedDocument]:
        """Perform HyDE-based search.
        
        Args:
            query: Original query
            user_id: User ID for filtering
            
        Returns:
            Documents retrieved using HyDE
        """
        # Generate hypothetical documents
        hypotheses = await self.hyde_generator.generate_hypothetical_document(query)
        
        if not hypotheses or not self.semantic_search_fn:
            return []
        
        # Search using hypothetical document embeddings
        all_docs: List[RetrievedDocument] = []
        
        for hypothesis in hypotheses:
            # Search using the hypothesis as query
            docs = await self._semantic_search(hypothesis, user_id)
            for doc in docs:
                doc.retrieval_method = "hyde"
            all_docs.extend(docs)
        
        # Deduplicate by content
        seen_content: set[str] = set()
        unique_docs: List[RetrievedDocument] = []
        
        for doc in all_docs:
            content_hash = hashlib.md5(doc.content[:500].encode()).hexdigest()
            if content_hash not in seen_content:
                seen_content.add(content_hash)
                unique_docs.append(doc)
        
        # Sort by score
        unique_docs.sort(key=lambda d: d.score, reverse=True)
        
        return unique_docs[:self.config.initial_candidates // 2]
    
    def _merge_hyde_results(
        self,
        original_docs: List[RetrievedDocument],
        hyde_docs: List[RetrievedDocument],
    ) -> List[RetrievedDocument]:
        """Merge HyDE results with original results.
        
        Args:
            original_docs: Original retrieval results
            hyde_docs: HyDE retrieval results
            
        Returns:
            Merged and deduplicated documents
        """
        # Create map of original docs
        doc_map: Dict[str, RetrievedDocument] = {}
        
        for doc in original_docs:
            content_hash = hashlib.md5(doc.content[:500].encode()).hexdigest()
            doc_map[content_hash] = doc
        
        # Add HyDE docs with boost
        for doc in hyde_docs:
            content_hash = hashlib.md5(doc.content[:500].encode()).hexdigest()
            if content_hash in doc_map:
                # Boost existing doc
                doc_map[content_hash].score = max(doc_map[content_hash].score, doc.score * 0.9)
            else:
                # Add new doc with slight penalty
                doc.score *= 0.85
                doc_map[content_hash] = doc
        
        # Sort by score
        merged = sorted(doc_map.values(), key=lambda d: d.score, reverse=True)
        
        return merged


# =============================================================================
# Factory Functions
# =============================================================================

_retrieval_engine: Optional[RetrievalEngine] = None


def get_retrieval_engine(
    semantic_search_fn: Optional[Callable] = None,
    llm_provider: Optional[Any] = None,
    config: Optional[RetrievalConfig] = None,
) -> RetrievalEngine:
    """Get or create the global retrieval engine instance.
    
    Args:
        semantic_search_fn: Semantic search function
        llm_provider: LLM provider for HyDE
        config: Configuration
        
    Returns:
        RetrievalEngine instance
    """
    global _retrieval_engine
    
    if _retrieval_engine is None:
        _retrieval_engine = RetrievalEngine(
            semantic_search_fn=semantic_search_fn,
            llm_provider=llm_provider,
            config=config,
        )
    
    return _retrieval_engine


def reset_retrieval_engine() -> None:
    """Reset the global retrieval engine instance."""
    global _retrieval_engine
    _retrieval_engine = None

