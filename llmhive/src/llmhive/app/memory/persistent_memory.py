"""Persistent memory management for LLMHive.

This module provides long-term memory storage and retrieval using vector databases,
enabling the system to remember and reuse verified answers and facts across sessions.
"""
from __future__ import annotations

import hashlib
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from contextlib import contextmanager

from .embeddings import get_embedding_service, get_embedding, EmbeddingService
from .vector_store import (
    VectorStore,
    MemoryRecord,
    MemoryQueryResult,
    get_global_vector_store,
    InMemoryVectorStore,
)

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class MemoryHit:
    """A memory retrieval result."""
    text: str
    score: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    record_id: str = ""
    created_at: float = 0.0
    
    @property
    def is_verified(self) -> bool:
        """Check if this memory was verified."""
        return self.metadata.get("verified", False)
    
    @property
    def domain(self) -> Optional[str]:
        """Get the domain tag if available."""
        tags = self.metadata.get("tags", [])
        return tags[0] if tags else None


class Scratchpad:
    """Short-term scratchpad for within-query data sharing.
    
    This allows different roles/agents to share intermediate results
    during a single query processing lifecycle.
    """
    
    def __init__(self):
        """Initialize empty scratchpad."""
        self._data: Dict[str, Any] = {}
        self._timestamps: Dict[str, float] = {}
    
    def write(self, key: str, value: Any) -> None:
        """
        Write a value to the scratchpad.
        
        Args:
            key: Key to store the value under
            value: Value to store
        """
        self._data[key] = value
        self._timestamps[key] = time.time()
        logger.debug("Scratchpad: wrote key '%s'", key)
    
    def read(self, key: str, default: Any = None) -> Any:
        """
        Read a value from the scratchpad.
        
        Args:
            key: Key to read
            default: Default value if key not found
            
        Returns:
            Stored value or default
        """
        return self._data.get(key, default)
    
    def get_all(self) -> Dict[str, Any]:
        """Get all scratchpad data."""
        return dict(self._data)
    
    def clear(self) -> None:
        """Clear all scratchpad data."""
        self._data.clear()
        self._timestamps.clear()
        logger.debug("Scratchpad: cleared")
    
    def remove(self, key: str) -> bool:
        """
        Remove a key from the scratchpad.
        
        Args:
            key: Key to remove
            
        Returns:
            True if key was found and removed
        """
        if key in self._data:
            del self._data[key]
            del self._timestamps[key]
            return True
        return False
    
    def keys(self) -> List[str]:
        """Get all keys in the scratchpad."""
        return list(self._data.keys())
    
    def has(self, key: str) -> bool:
        """Check if a key exists in the scratchpad."""
        return key in self._data
    
    def append_to_list(self, key: str, value: Any) -> None:
        """
        Append a value to a list in the scratchpad.
        Creates the list if it doesn't exist.
        
        Args:
            key: Key for the list
            value: Value to append
        """
        if key not in self._data:
            self._data[key] = []
        if isinstance(self._data[key], list):
            self._data[key].append(value)
            self._timestamps[key] = time.time()
    
    def get_context_string(self) -> str:
        """
        Get scratchpad contents as a formatted context string.
        
        Returns:
            Formatted string of scratchpad contents
        """
        if not self._data:
            return ""
        
        parts = []
        for key, value in self._data.items():
            if isinstance(value, str):
                parts.append(f"[{key}]: {value[:500]}")
            elif isinstance(value, list):
                list_str = ", ".join(str(v)[:100] for v in value[:5])
                parts.append(f"[{key}]: [{list_str}]")
            else:
                parts.append(f"[{key}]: {str(value)[:200]}")
        
        return "\n".join(parts)


class PersistentMemoryManager:
    """Manages persistent long-term memory using vector database.
    
    Provides add_to_memory and query_memory functions for storing and
    retrieving verified answers and facts across sessions.
    """
    
    def __init__(
        self,
        vector_store: Optional[VectorStore] = None,
        embedding_service: Optional[EmbeddingService] = None,
        namespace_per_user: bool = True,
        global_namespace: str = "global",
    ):
        """
        Initialize persistent memory manager.
        
        Args:
            vector_store: Vector store backend
            embedding_service: Embedding service
            namespace_per_user: Use separate namespace per user
            global_namespace: Name for global/shared namespace
        """
        self._vector_store = vector_store or get_global_vector_store()
        self._embedding_service = embedding_service or get_embedding_service()
        self._namespace_per_user = namespace_per_user
        self._global_namespace = global_namespace
        
        logger.info(
            "PersistentMemoryManager initialized: per_user=%s, global_ns=%s",
            namespace_per_user,
            global_namespace,
        )
    
    def _get_namespace(self, user_id: Optional[str] = None) -> str:
        """Get the appropriate namespace for a user."""
        if not user_id or not self._namespace_per_user:
            return self._global_namespace
        return f"user_{user_id}"
    
    def _generate_id(self, uid: str, text: str) -> str:
        """Generate a unique ID for a memory record."""
        combined = f"{uid}|{text}"
        return hashlib.sha256(combined.encode()).hexdigest()[:32]
    
    def add_to_memory(
        self,
        uid: str,
        text: str,
        metadata: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
    ) -> str:
        """
        Add text to persistent memory.
        
        Args:
            uid: Unique identifier (e.g., session_id + query)
            text: Text to store
            metadata: Optional metadata (e.g., {'verified': True, 'tags': ['medical']})
            user_id: Optional user ID for namespace
            
        Returns:
            Record ID
        """
        if not text or not text.strip():
            logger.warning("add_to_memory: Empty text, skipping")
            return ""
        
        # Generate embedding
        embedding = self._embedding_service.get_embedding(text)
        
        # Generate record ID
        record_id = self._generate_id(uid, text)
        
        # Build metadata
        record_metadata = metadata or {}
        record_metadata.setdefault("uid", uid)
        record_metadata.setdefault("verified", False)
        record_metadata.setdefault("tags", [])
        
        # Create record
        record = MemoryRecord(
            id=record_id,
            text=text,
            embedding=embedding,
            metadata=record_metadata,
        )
        
        # Get namespace
        namespace = self._get_namespace(user_id)
        
        # Upsert to vector store
        count = self._vector_store.upsert([record], namespace=namespace)
        
        if count > 0:
            logger.info(
                "add_to_memory: Stored record %s in namespace '%s' (verified=%s)",
                record_id[:8],
                namespace,
                record_metadata.get("verified"),
            )
        
        return record_id
    
    def query_memory(
        self,
        query_text: str,
        top_k: int = 5,
        user_id: Optional[str] = None,
        min_score: float = 0.7,
        filter_verified: bool = False,
        filter_tags: Optional[List[str]] = None,
        include_global: bool = True,
    ) -> List[MemoryHit]:
        """
        Query persistent memory for relevant stored items.
        
        Args:
            query_text: Query text to search for
            top_k: Maximum number of results
            user_id: Optional user ID for namespace
            min_score: Minimum similarity score
            filter_verified: Only return verified memories
            filter_tags: Filter by tags
            include_global: Also search global namespace
            
        Returns:
            List of MemoryHit objects sorted by score
        """
        if not query_text or not query_text.strip():
            return []
        
        # Generate query embedding
        query_embedding = self._embedding_service.get_embedding(query_text)
        
        # Build metadata filter
        filter_metadata = None
        if filter_verified or filter_tags:
            filter_metadata = {}
            if filter_verified:
                filter_metadata["verified"] = True
            # Note: Tag filtering might need special handling in Pinecone
        
        all_hits: List[MemoryHit] = []
        
        # Query user namespace
        namespace = self._get_namespace(user_id)
        result = self._vector_store.query(
            query_embedding=query_embedding,
            top_k=top_k,
            namespace=namespace,
            filter_metadata=filter_metadata,
            min_score=min_score,
        )
        
        for record in result.records:
            all_hits.append(MemoryHit(
                text=record.text,
                score=record.score,
                metadata=record.metadata,
                record_id=record.id,
                created_at=record.created_at,
            ))
        
        # Also query global namespace if different
        if include_global and namespace != self._global_namespace:
            global_result = self._vector_store.query(
                query_embedding=query_embedding,
                top_k=top_k,
                namespace=self._global_namespace,
                filter_metadata=filter_metadata,
                min_score=min_score,
            )
            
            for record in global_result.records:
                all_hits.append(MemoryHit(
                    text=record.text,
                    score=record.score,
                    metadata=record.metadata,
                    record_id=record.id,
                    created_at=record.created_at,
                ))
        
        # Filter by tags if specified (post-query filter)
        if filter_tags:
            all_hits = [
                h for h in all_hits
                if any(tag in h.metadata.get("tags", []) for tag in filter_tags)
            ]
        
        # Sort by score descending and deduplicate
        seen_ids = set()
        unique_hits = []
        for hit in sorted(all_hits, key=lambda h: h.score, reverse=True):
            if hit.record_id not in seen_ids:
                unique_hits.append(hit)
                seen_ids.add(hit.record_id)
        
        # Return top K
        results = unique_hits[:top_k]
        
        logger.info(
            "query_memory: Found %d results for query (min_score=%.2f, namespace=%s)",
            len(results),
            min_score,
            namespace,
        )
        
        return results
    
    def store_verified_answer(
        self,
        session_id: str,
        query: str,
        answer: str,
        domain: Optional[str] = None,
        user_id: Optional[str] = None,
        additional_metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Store a verified Q&A pair in memory.
        
        This is called after fact verification passes.
        
        Args:
            session_id: Session identifier
            query: Original query
            answer: Verified answer
            domain: Domain classification (e.g., 'medical', 'legal')
            user_id: User ID
            additional_metadata: Additional metadata to store
            
        Returns:
            Record ID
        """
        # Combine query and answer for storage
        combined_text = f"Q: {query}\nA: {answer}"
        
        # Build metadata
        metadata = {
            "verified": True,
            "query": query[:500],  # Store original query
            "session_id": session_id,
            "type": "qa_pair",
        }
        
        if domain:
            metadata["tags"] = [domain]
            metadata["domain"] = domain
        
        if additional_metadata:
            metadata.update(additional_metadata)
        
        # Generate unique ID from session + query
        uid = f"{session_id}|{query}"
        
        return self.add_to_memory(
            uid=uid,
            text=combined_text,
            metadata=metadata,
            user_id=user_id,
        )
    
    def get_relevant_context(
        self,
        query: str,
        user_id: Optional[str] = None,
        max_context_length: int = 2000,
        top_k: int = 3,
    ) -> Tuple[str, List[MemoryHit]]:
        """
        Get relevant context from memory to prepend to query.
        
        Args:
            query: User query
            user_id: User ID
            max_context_length: Maximum context length in characters
            top_k: Number of memory hits to consider
            
        Returns:
            Tuple of (context_string, memory_hits)
        """
        hits = self.query_memory(
            query_text=query,
            top_k=top_k,
            user_id=user_id,
            min_score=0.75,  # Higher threshold for context injection
            filter_verified=True,  # Only use verified memories
        )
        
        if not hits:
            return "", []
        
        # Build context string
        context_parts = []
        total_length = 0
        selected_hits = []
        
        for hit in hits:
            hit_text = f"[Relevant prior knowledge (score: {hit.score:.2f})]\n{hit.text}"
            
            if total_length + len(hit_text) > max_context_length:
                break
            
            context_parts.append(hit_text)
            total_length += len(hit_text)
            selected_hits.append(hit)
        
        if not context_parts:
            return "", []
        
        context = "\n\n".join(context_parts)
        context = f"--- Relevant Context from Memory ---\n{context}\n--- End Context ---\n\n"
        
        logger.info(
            "get_relevant_context: Built context with %d memory hits (%d chars)",
            len(selected_hits),
            len(context),
        )
        
        return context, selected_hits
    
    def delete_memory(
        self,
        record_ids: List[str],
        user_id: Optional[str] = None,
    ) -> int:
        """
        Delete memories by ID.
        
        Args:
            record_ids: List of record IDs to delete
            user_id: User ID for namespace
            
        Returns:
            Number of records deleted
        """
        namespace = self._get_namespace(user_id)
        return self._vector_store.delete(record_ids, namespace=namespace)
    
    def clear_user_memory(self, user_id: str) -> int:
        """
        Clear all memories for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            Number of records cleared
        """
        namespace = self._get_namespace(user_id)
        return self._vector_store.clear_namespace(namespace)


# Global instances
_persistent_memory: Optional[PersistentMemoryManager] = None
_scratchpad: Optional[Scratchpad] = None


def get_persistent_memory() -> PersistentMemoryManager:
    """Get the global persistent memory manager."""
    global _persistent_memory
    if _persistent_memory is None:
        _persistent_memory = PersistentMemoryManager()
    return _persistent_memory


def get_scratchpad() -> Scratchpad:
    """Get the global scratchpad instance."""
    global _scratchpad
    if _scratchpad is None:
        _scratchpad = Scratchpad()
    return _scratchpad


@contextmanager
def query_scratchpad():
    """Context manager for a query-scoped scratchpad.
    
    Creates a fresh scratchpad for the duration of a query,
    then clears it when done.
    
    Usage:
        with query_scratchpad() as scratchpad:
            scratchpad.write("model1_output", output1)
            ...
    """
    scratchpad = Scratchpad()
    try:
        yield scratchpad
    finally:
        scratchpad.clear()


# Convenience functions
def add_to_memory(
    uid: str,
    text: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> str:
    """Add text to global memory."""
    return get_persistent_memory().add_to_memory(uid, text, metadata)


def query_memory(
    query_text: str,
    top_k: int = 5,
    user_id: Optional[str] = None,
) -> List[MemoryHit]:
    """Query global memory."""
    return get_persistent_memory().query_memory(
        query_text,
        top_k=top_k,
        user_id=user_id,
    )

