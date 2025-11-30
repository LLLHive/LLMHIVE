"""Vector database integration for persistent memory storage.

This module provides a unified interface for vector database operations,
with support for Pinecone and an in-memory fallback for testing.
"""
from __future__ import annotations

import hashlib
import logging
import os
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .embeddings import get_embedding_service, EmbeddingService

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class MemoryRecord:
    """A record stored in vector memory."""
    id: str
    text: str
    embedding: List[float]
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
        query_embedding: List[float],
        top_k: int = 5,
        namespace: str = "default",
        filter_metadata: Optional[Dict[str, Any]] = None,
        min_score: float = 0.0,
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
    
    def __init__(self, embedding_service: Optional[EmbeddingService] = None):
        """
        Initialize in-memory vector store.
        
        Args:
            embedding_service: Embedding service for similarity calculation
        """
        self._store: Dict[str, Dict[str, MemoryRecord]] = {}  # namespace -> id -> record
        self._embedding_service = embedding_service or get_embedding_service()
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
            self._store[namespace][record.id] = record
            count += 1
        
        logger.debug("Upserted %d records to namespace '%s'", count, namespace)
        return count
    
    def query(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        namespace: str = "default",
        filter_metadata: Optional[Dict[str, Any]] = None,
        min_score: float = 0.0,
    ) -> MemoryQueryResult:
        """Query for similar vectors."""
        start_time = time.time()
        
        if namespace not in self._store:
            return MemoryQueryResult(records=[], total_found=0, query_time_ms=0.0)
        
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
            
            # Calculate cosine similarity
            similarity = self._embedding_service.cosine_similarity(
                query_embedding,
                record.embedding,
            )
            
            if similarity >= min_score:
                record_copy = MemoryRecord(
                    id=record.id,
                    text=record.text,
                    embedding=record.embedding,
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
            len(results),
            top_k,
            min_score,
            query_time_ms,
        )
        
        return MemoryQueryResult(
            records=results,
            total_found=len(scored_records),
            query_time_ms=query_time_ms,
        )
    
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
    """Pinecone vector database integration."""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        environment: Optional[str] = None,
        index_name: Optional[str] = None,
        embedding_service: Optional[EmbeddingService] = None,
    ):
        """
        Initialize Pinecone vector store.
        
        Args:
            api_key: Pinecone API key
            environment: Pinecone environment
            index_name: Pinecone index name
            embedding_service: Embedding service
        """
        from ..config import settings
        
        self._api_key = api_key or settings.pinecone_api_key
        self._environment = environment or settings.pinecone_environment
        self._index_name = index_name or settings.pinecone_index_name
        self._embedding_service = embedding_service or get_embedding_service()
        self._index = None
        self._initialized = False
        
        self._initialize()
    
    def _initialize(self) -> None:
        """Initialize Pinecone connection."""
        if not self._api_key:
            logger.warning("Pinecone API key not configured, using fallback")
            return
        
        try:
            from pinecone import Pinecone
            
            pc = Pinecone(api_key=self._api_key)
            self._index = pc.Index(self._index_name)
            self._initialized = True
            
            logger.info(
                "PineconeVectorStore initialized: index=%s, env=%s",
                self._index_name,
                self._environment,
            )
        except ImportError:
            logger.warning("Pinecone package not installed, using fallback")
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
        
        try:
            vectors = []
            for record in records:
                vectors.append({
                    "id": record.id,
                    "values": record.embedding,
                    "metadata": {
                        **record.metadata,
                        "text": record.text,
                        "created_at": time.time(),
                    },
                })
            
            # Upsert in batches of 100
            batch_size = 100
            count = 0
            for i in range(0, len(vectors), batch_size):
                batch = vectors[i:i + batch_size]
                self._index.upsert(vectors=batch, namespace=namespace)
                count += len(batch)
            
            logger.info("Upserted %d records to Pinecone namespace '%s'", count, namespace)
            return count
            
        except Exception as e:
            logger.error("Pinecone upsert failed: %s", e)
            return 0
    
    def query(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        namespace: str = "default",
        filter_metadata: Optional[Dict[str, Any]] = None,
        min_score: float = 0.0,
    ) -> MemoryQueryResult:
        """Query Pinecone for similar vectors."""
        start_time = time.time()
        
        if not self._initialized or not self._index:
            logger.warning("Pinecone not initialized, cannot query")
            return MemoryQueryResult(records=[], total_found=0, query_time_ms=0.0)
        
        try:
            # Build filter
            pinecone_filter = None
            if filter_metadata:
                pinecone_filter = filter_metadata
            
            # Query Pinecone
            results = self._index.query(
                vector=query_embedding,
                top_k=top_k,
                namespace=namespace,
                include_metadata=True,
                filter=pinecone_filter,
            )
            
            # Convert to MemoryRecords
            records: List[MemoryRecord] = []
            for match in results.matches:
                if match.score >= min_score:
                    metadata = match.metadata or {}
                    text = metadata.pop("text", "")
                    created_at = metadata.pop("created_at", 0.0)
                    
                    records.append(MemoryRecord(
                        id=match.id,
                        text=text,
                        embedding=[],  # Don't return embedding for efficiency
                        metadata=metadata,
                        score=match.score,
                        namespace=namespace,
                        created_at=created_at,
                    ))
            
            query_time_ms = (time.time() - start_time) * 1000
            
            logger.debug(
                "Pinecone query returned %d results (time=%.1fms)",
                len(records),
                query_time_ms,
            )
            
            return MemoryQueryResult(
                records=records,
                total_found=len(records),
                query_time_ms=query_time_ms,
            )
            
        except Exception as e:
            logger.error("Pinecone query failed: %s", e)
            return MemoryQueryResult(
                records=[],
                total_found=0,
                query_time_ms=(time.time() - start_time) * 1000,
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


# Factory function to get appropriate vector store
def get_vector_store(
    use_pinecone: bool = True,
    **kwargs,
) -> VectorStore:
    """
    Get vector store instance.
    
    Args:
        use_pinecone: Whether to use Pinecone (if available)
        **kwargs: Additional arguments for vector store
        
    Returns:
        VectorStore instance
    """
    from ..config import settings
    
    if use_pinecone and settings.pinecone_api_key:
        try:
            store = PineconeVectorStore(**kwargs)
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

