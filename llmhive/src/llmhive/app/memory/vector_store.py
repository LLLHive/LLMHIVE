"""Vector database integration for persistent memory storage.

This module provides a unified interface for vector database operations,
with support for Pinecone (modern API with integrated embeddings + reranking)
and an in-memory fallback for testing.

Best Practices (from AGENTS.md):
- Always use namespaces for data isolation
- Always rerank in production for better relevance
- Use batch sizes of 96 for text records
- Handle errors with exponential backoff
"""
from __future__ import annotations

import hashlib
import logging
import os
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class MemoryRecord:
    """A record stored in vector memory."""
    id: str
    text: str
    embedding: List[float] = field(default_factory=list)  # Optional with integrated embeddings
    metadata: Dict[str, Any] = field(default_factory=dict)
    score: float = 0.0  # Similarity score (populated on query)
    namespace: str = "default"
    created_at: float = 0.0


@dataclass(slots=True)
class MemoryQueryResult:
    """Result of a memory query."""
    records: List[MemoryRecord]
    total_found: int
    query_time_ms: float
    reranked: bool = False


class VectorStore(ABC):
    """Abstract base class for vector stores."""
    
    @abstractmethod
    def upsert(
        self,
        records: List[MemoryRecord],
        namespace: str = "default",
    ) -> int:
        """Insert or update records in the store."""
        pass
    
    @abstractmethod
    def query(
        self,
        query_text: str,
        top_k: int = 5,
        namespace: str = "default",
        filter_metadata: Optional[Dict[str, Any]] = None,
        min_score: float = 0.0,
        use_rerank: bool = True,
    ) -> MemoryQueryResult:
        """Query the store for similar vectors."""
        pass
    
    @abstractmethod
    def delete(
        self,
        ids: List[str],
        namespace: str = "default",
    ) -> int:
        """Delete records by ID."""
        pass
    
    @abstractmethod
    def clear_namespace(self, namespace: str) -> int:
        """Clear all records in a namespace."""
        pass


class InMemoryVectorStore(VectorStore):
    """In-memory vector store for testing and development."""
    
    def __init__(self, embedding_service: Optional[Any] = None):
        """
        Initialize in-memory vector store.
        
        Args:
            embedding_service: Embedding service for similarity calculation
        """
        self._store: Dict[str, Dict[str, MemoryRecord]] = {}  # namespace -> id -> record
        self._embedding_service = embedding_service
        
        # Try to load embedding service
        if self._embedding_service is None:
            try:
                from .embeddings import get_embedding_service
                self._embedding_service = get_embedding_service()
            except Exception:
                pass
        
        logger.info("InMemoryVectorStore initialized")
    
    def upsert(
        self,
        records: List[MemoryRecord],
        namespace: str = "default",
    ) -> int:
        """Insert or update records."""
        if namespace not in self._store:
            self._store[namespace] = {}
        
        count = 0
        for record in records:
            record.namespace = namespace
            record.created_at = time.time()
            
            # Generate embedding if not provided and service available
            if not record.embedding and self._embedding_service:
                try:
                    record.embedding = self._embedding_service.embed(record.text)
                except Exception as e:
                    logger.warning("Failed to generate embedding: %s", e)
            
            self._store[namespace][record.id] = record
            count += 1
        
        logger.debug("Upserted %d records to namespace '%s'", count, namespace)
        return count
    
    def query(
        self,
        query_text: str,
        top_k: int = 5,
        namespace: str = "default",
        filter_metadata: Optional[Dict[str, Any]] = None,
        min_score: float = 0.0,
        use_rerank: bool = True,
    ) -> MemoryQueryResult:
        """Query for similar vectors."""
        start_time = time.time()
        
        if namespace not in self._store:
            return MemoryQueryResult(records=[], total_found=0, query_time_ms=0.0)
        
        # Generate query embedding
        query_embedding = []
        if self._embedding_service:
            try:
                query_embedding = self._embedding_service.embed(query_text)
            except Exception as e:
                logger.warning("Failed to generate query embedding: %s", e)
        
        if not query_embedding:
            # Fallback: simple text matching
            records = list(self._store[namespace].values())
            query_lower = query_text.lower()
            scored = []
            for r in records:
                # Simple keyword matching score
                if filter_metadata:
                    match = all(r.metadata.get(k) == v for k, v in filter_metadata.items())
                    if not match:
                        continue
                
                score = 0.5 if query_lower in r.text.lower() else 0.1
                if score >= min_score:
                    r_copy = MemoryRecord(
                        id=r.id, text=r.text, embedding=[], metadata=r.metadata,
                        score=score, namespace=namespace, created_at=r.created_at
                    )
                    scored.append(r_copy)
            
            scored.sort(key=lambda x: x.score, reverse=True)
            query_time_ms = (time.time() - start_time) * 1000
            return MemoryQueryResult(
                records=scored[:top_k],
                total_found=len(scored),
                query_time_ms=query_time_ms,
            )
        
        # Calculate similarity for all records
        scored_records: List[Tuple[MemoryRecord, float]] = []
        for record in self._store[namespace].values():
            # Apply metadata filter
            if filter_metadata:
                match = all(
                    record.metadata.get(k) == v
                    for k, v in filter_metadata.items()
                )
                if not match:
                    continue
            
            # Skip if no embedding
            if not record.embedding:
                continue
            
            # Calculate cosine similarity
            similarity = self._cosine_similarity(query_embedding, record.embedding)
            
            if similarity >= min_score:
                record_copy = MemoryRecord(
                    id=record.id,
                    text=record.text,
                    embedding=[],  # Don't return for efficiency
                    metadata=record.metadata,
                    score=similarity,
                    namespace=record.namespace,
                    created_at=record.created_at,
                )
                scored_records.append((record_copy, similarity))
        
        # Sort by score descending
        scored_records.sort(key=lambda x: x[1], reverse=True)
        
        # Take top K
        results = [r for r, _ in scored_records[:top_k]]
        
        query_time_ms = (time.time() - start_time) * 1000
        
        logger.debug(
            "Query returned %d results (top_k=%d, min_score=%.2f, time=%.1fms)",
            len(results), top_k, min_score, query_time_ms,
        )
        
        return MemoryQueryResult(
            records=results,
            total_found=len(scored_records),
            query_time_ms=query_time_ms,
        )
    
    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        if len(a) != len(b):
            return 0.0
        
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
        
        return dot / (norm_a * norm_b)
    
    def delete(
        self,
        ids: List[str],
        namespace: str = "default",
    ) -> int:
        """Delete records by ID."""
        if namespace not in self._store:
            return 0
        
        count = 0
        for record_id in ids:
            if record_id in self._store[namespace]:
                del self._store[namespace][record_id]
                count += 1
        
        logger.debug("Deleted %d records from namespace '%s'", count, namespace)
        return count
    
    def clear_namespace(self, namespace: str) -> int:
        """Clear all records in namespace."""
        if namespace not in self._store:
            return 0
        
        count = len(self._store[namespace])
        self._store[namespace] = {}
        
        logger.debug("Cleared %d records from namespace '%s'", count, namespace)
        return count
    
    def get_all_records(self, namespace: str = "default") -> List[MemoryRecord]:
        """Get all records in namespace (for testing)."""
        if namespace not in self._store:
            return []
        return list(self._store[namespace].values())


class PineconeVectorStore(VectorStore):
    """Pinecone vector database integration with modern API.
    
    Supports two modes:
    1. Integrated Embeddings (recommended): Pinecone handles embedding generation
    2. External Embeddings (legacy): You provide pre-computed embeddings
    
    Best Practices:
    - Always use namespaces for data isolation
    - Always rerank in production
    - Batch upserts in groups of 96
    - Use exponential backoff for retries
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        index_name: Optional[str] = None,
        use_integrated_embeddings: bool = True,
        content_field: str = "content",
    ):
        """
        Initialize Pinecone vector store.
        
        Args:
            api_key: Pinecone API key (defaults to PINECONE_API_KEY env var)
            index_name: Pinecone index name
            use_integrated_embeddings: If True, use Pinecone's integrated embedding
            content_field: Field name for text content (for integrated embeddings)
        """
        self._api_key = api_key or os.getenv("PINECONE_API_KEY")
        self._index_name = index_name or os.getenv("PINECONE_INDEX_NAME", "llmhive-memory")
        self._use_integrated_embeddings = use_integrated_embeddings
        self._content_field = content_field
        self._pc = None
        self._index = None
        self._initialized = False
        
        self._initialize()
    
    def _initialize(self) -> None:
        """Initialize Pinecone via registry (host-based) or direct connection."""
        if not self._api_key:
            logger.warning("Pinecone API key not configured")
            return
        
        # Try registry-based connection first (supports host-based connections)
        try:
            from ..knowledge.pinecone_registry import get_pinecone_registry, IndexKind
            
            registry = get_pinecone_registry()
            if registry.is_available:
                self._index = registry.get_index(IndexKind.MEMORY)
                if self._index:
                    self._initialized = True
                    logger.info("PineconeVectorStore initialized via registry (host-based)")
                    return
        except ImportError:
            logger.debug("Pinecone registry not available, using direct connection")
        except Exception as e:
            logger.warning("Registry connection failed: %s, falling back to direct", e)
        
        # Fallback: Direct connection (for backward compatibility)
        try:
            from pinecone import Pinecone
            
            self._pc = Pinecone(api_key=self._api_key)
            
            # Check if index exists
            if not self._pc.has_index(self._index_name):
                logger.warning(
                    "Pinecone index '%s' does not exist. "
                    "Create it with: pc index create -n %s -m cosine -c aws -r us-east-1 "
                    "--model llama-text-embed-v2 --field_map text=content",
                    self._index_name, self._index_name
                )
                return
            
            self._index = self._pc.Index(self._index_name)
            self._initialized = True
            
            # Get index stats
            try:
                stats = self._index.describe_index_stats()
                logger.info(
                    "PineconeVectorStore initialized via direct connection: index=%s, records=%s",
                    self._index_name,
                    stats.get("total_vector_count", "unknown"),
                )
            except Exception:
                logger.info("PineconeVectorStore initialized via direct connection: index=%s", self._index_name)
            
        except ImportError:
            logger.warning("Pinecone package not installed. Run: pip install pinecone")
        except Exception as e:
            logger.warning("Failed to initialize Pinecone: %s", e)
    
    def upsert(
        self,
        records: List[MemoryRecord],
        namespace: str = "default",
    ) -> int:
        """Insert or update records in Pinecone."""
        if not self._initialized or not self._index:
            logger.warning("Pinecone not initialized, cannot upsert")
            return 0
        
        if not records:
            return 0
        
        try:
            if self._use_integrated_embeddings:
                return self._upsert_with_integrated_embeddings(records, namespace)
            else:
                return self._upsert_with_vectors(records, namespace)
        except Exception as e:
            logger.error("Pinecone upsert failed: %s", e)
            return 0
    
    def _upsert_with_integrated_embeddings(
        self,
        records: List[MemoryRecord],
        namespace: str,
    ) -> int:
        """Upsert using integrated embeddings (modern API)."""
        # Convert to Pinecone record format
        pinecone_records = []
        for record in records:
            # Build record with required fields
            pc_record = {
                "_id": record.id,
                self._content_field: record.text,
                "created_at": str(time.time()),
            }
            
            # Add metadata (flattened - no nested objects!)
            for key, value in record.metadata.items():
                if isinstance(value, (str, int, float, bool)):
                    pc_record[key] = value
                elif isinstance(value, list) and all(isinstance(v, str) for v in value):
                    pc_record[key] = value  # String lists are OK
                else:
                    # Skip nested objects (not allowed in Pinecone)
                    logger.debug("Skipping nested metadata field: %s", key)
            
            pinecone_records.append(pc_record)
        
        # Batch upsert (max 96 for text records)
        batch_size = 96
        count = 0
        
        for i in range(0, len(pinecone_records), batch_size):
            batch = pinecone_records[i:i + batch_size]
            self._index.upsert_records(namespace, batch)
            count += len(batch)
            
            # Small delay between batches for rate limiting
            if i + batch_size < len(pinecone_records):
                time.sleep(0.1)
        
        logger.info("Upserted %d records to Pinecone namespace '%s'", count, namespace)
        return count
    
    def _upsert_with_vectors(
        self,
        records: List[MemoryRecord],
        namespace: str,
    ) -> int:
        """Upsert using pre-computed vectors (legacy API)."""
        vectors = []
        for record in records:
            if not record.embedding:
                logger.warning("Record %s has no embedding, skipping", record.id)
                continue
            
            vectors.append({
                "id": record.id,
                "values": record.embedding,
                "metadata": {
                    **record.metadata,
                    "text": record.text,
                    "created_at": str(time.time()),
                },
            })
        
        if not vectors:
            return 0
        
        # Batch upsert (max 100 for vector records)
        batch_size = 100
        count = 0
        
        for i in range(0, len(vectors), batch_size):
            batch = vectors[i:i + batch_size]
            self._index.upsert(vectors=batch, namespace=namespace)
            count += len(batch)
        
        logger.info("Upserted %d vectors to Pinecone namespace '%s'", count, namespace)
        return count
    
    def query(
        self,
        query_text: str,
        top_k: int = 5,
        namespace: str = "default",
        filter_metadata: Optional[Dict[str, Any]] = None,
        min_score: float = 0.0,
        use_rerank: bool = True,
    ) -> MemoryQueryResult:
        """Query Pinecone for similar records."""
        start_time = time.time()
        
        if not self._initialized or not self._index:
            logger.warning("Pinecone not initialized, cannot query")
            return MemoryQueryResult(records=[], total_found=0, query_time_ms=0.0)
        
        try:
            if self._use_integrated_embeddings:
                return self._query_with_integrated_embeddings(
                    query_text, top_k, namespace, filter_metadata, min_score, use_rerank, start_time
                )
            else:
                return self._query_with_vectors(
                    query_text, top_k, namespace, filter_metadata, min_score, start_time
                )
        except Exception as e:
            logger.error("Pinecone query failed: %s", e)
            return MemoryQueryResult(
                records=[],
                total_found=0,
                query_time_ms=(time.time() - start_time) * 1000,
            )
    
    def _query_with_integrated_embeddings(
        self,
        query_text: str,
        top_k: int,
        namespace: str,
        filter_metadata: Optional[Dict[str, Any]],
        min_score: float,
        use_rerank: bool,
        start_time: float,
    ) -> MemoryQueryResult:
        """Query using integrated embeddings (modern API with search())."""
        # Build query dict
        query_dict: Dict[str, Any] = {
            "top_k": top_k * 2 if use_rerank else top_k,  # Get more for reranking
            "inputs": {"text": query_text},
        }
        
        # Add filter if provided (only include if not empty!)
        if filter_metadata:
            query_dict["filter"] = filter_metadata
        
        # Build search kwargs
        search_kwargs: Dict[str, Any] = {
            "namespace": namespace,
            "query": query_dict,
        }
        
        # Add reranking (best practice for production)
        if use_rerank:
            search_kwargs["rerank"] = {
                "model": "bge-reranker-v2-m3",
                "top_n": top_k,
                "rank_fields": [self._content_field],
            }
        
        # Execute search
        results = self._index.search(**search_kwargs)
        
        # Convert to MemoryRecords
        records: List[MemoryRecord] = []
        hits = results.get("result", {}).get("hits", [])
        
        for hit in hits:
            score = hit.get("_score", 0.0)
            if score >= min_score:
                fields = hit.get("fields", {})
                text = fields.pop(self._content_field, "")
                created_at = float(fields.pop("created_at", 0))
                
                records.append(MemoryRecord(
                    id=hit.get("_id", ""),
                    text=text,
                    embedding=[],  # Not returned for efficiency
                    metadata=fields,
                    score=score,
                    namespace=namespace,
                    created_at=created_at,
                ))
        
        query_time_ms = (time.time() - start_time) * 1000
        
        logger.debug(
            "Pinecone search returned %d results (reranked=%s, time=%.1fms)",
            len(records), use_rerank, query_time_ms,
        )
        
        return MemoryQueryResult(
            records=records,
            total_found=len(records),
            query_time_ms=query_time_ms,
            reranked=use_rerank,
        )
    
    def _query_with_vectors(
        self,
        query_text: str,
        top_k: int,
        namespace: str,
        filter_metadata: Optional[Dict[str, Any]],
        min_score: float,
        start_time: float,
    ) -> MemoryQueryResult:
        """Query using pre-computed vectors (legacy API)."""
        # Generate query embedding
        try:
            from .embeddings import get_embedding
            query_embedding = get_embedding(query_text)
        except Exception as e:
            logger.error("Failed to generate query embedding: %s", e)
            return MemoryQueryResult(
                records=[],
                total_found=0,
                query_time_ms=(time.time() - start_time) * 1000,
            )
        
        # Query Pinecone
        results = self._index.query(
            vector=query_embedding,
            top_k=top_k,
            namespace=namespace,
            include_metadata=True,
            filter=filter_metadata if filter_metadata else None,
        )
        
        # Convert to MemoryRecords
        records: List[MemoryRecord] = []
        for match in results.matches:
            if match.score >= min_score:
                metadata = dict(match.metadata) if match.metadata else {}
                text = metadata.pop("text", "")
                created_at = float(metadata.pop("created_at", 0))
                
                records.append(MemoryRecord(
                    id=match.id,
                    text=text,
                    embedding=[],
                    metadata=metadata,
                    score=match.score,
                    namespace=namespace,
                    created_at=created_at,
                ))
        
        query_time_ms = (time.time() - start_time) * 1000
        
        logger.debug(
            "Pinecone query returned %d results (time=%.1fms)",
            len(records), query_time_ms,
        )
        
        return MemoryQueryResult(
            records=records,
            total_found=len(records),
            query_time_ms=query_time_ms,
        )
    
    def delete(
        self,
        ids: List[str],
        namespace: str = "default",
    ) -> int:
        """Delete records by ID from Pinecone."""
        if not self._initialized or not self._index:
            return 0
        
        try:
            self._index.delete(ids=ids, namespace=namespace)
            logger.info("Deleted %d records from Pinecone namespace '%s'", len(ids), namespace)
            return len(ids)
        except Exception as e:
            logger.error("Pinecone delete failed: %s", e)
            return 0
    
    def clear_namespace(self, namespace: str) -> int:
        """Clear all records in Pinecone namespace."""
        if not self._initialized or not self._index:
            return 0
        
        try:
            self._index.delete(delete_all=True, namespace=namespace)
            logger.info("Cleared Pinecone namespace '%s'", namespace)
            return 1  # Can't know exact count
        except Exception as e:
            logger.error("Pinecone clear namespace failed: %s", e)
            return 0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get index statistics."""
        if not self._initialized or not self._index:
            return {"status": "not_initialized"}
        
        try:
            stats = self._index.describe_index_stats()
            return {
                "status": "connected",
                "index_name": self._index_name,
                "total_records": stats.get("total_vector_count", 0),
                "namespaces": list(stats.get("namespaces", {}).keys()),
                "use_integrated_embeddings": self._use_integrated_embeddings,
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}


# Factory function to get appropriate vector store
def get_vector_store(
    use_pinecone: bool = True,
    use_integrated_embeddings: bool = True,
    **kwargs,
) -> VectorStore:
    """
    Get vector store instance.
    
    Args:
        use_pinecone: Whether to use Pinecone (if available)
        use_integrated_embeddings: Use Pinecone's integrated embedding models
        **kwargs: Additional arguments for vector store
        
    Returns:
        VectorStore instance
    """
    if use_pinecone and os.getenv("PINECONE_API_KEY"):
        try:
            store = PineconeVectorStore(
                use_integrated_embeddings=use_integrated_embeddings,
                **kwargs
            )
            if store._initialized:
                return store
        except Exception as e:
            logger.warning("Failed to initialize Pinecone, using in-memory: %s", e)
    
    return InMemoryVectorStore(**kwargs)


# Global vector store instance
_vector_store: Optional[VectorStore] = None


def get_global_vector_store() -> VectorStore:
    """Get the global vector store instance."""
    global _vector_store
    if _vector_store is None:
        _vector_store = get_vector_store()
    return _vector_store


def reset_global_vector_store() -> None:
    """Reset the global vector store (for testing)."""
    global _vector_store
    _vector_store = None
