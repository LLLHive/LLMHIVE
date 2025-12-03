"""Persistent Memory Module for LLMHive Orchestrator.

Implements vector-based persistent memory using FAISS for:
- Conversation history storage and retrieval
- Reference document embedding
- Organization-wide knowledge sharing
- Context-aware retrieval for RAG

Features:
- FAISS-based vector store
- Embedding generation (OpenAI or local)
- Multi-source context merging
- Memory prioritization and trimming
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Try to import FAISS
try:
    import faiss
    import numpy as np
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False
    logger.info("FAISS not available, using simple memory store")


@dataclass
class MemoryEntry:
    """A single memory entry."""
    id: str
    content: str
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    source: str = "conversation"
    relevance_score: float = 1.0


@dataclass
class MemorySearchResult:
    """Result from memory search."""
    entries: List[MemoryEntry]
    total_matches: int
    search_time_ms: float


class EmbeddingProvider:
    """Handles embedding generation."""
    
    def __init__(
        self,
        providers: Optional[Dict[str, Any]] = None,
        model: str = "text-embedding-3-small",
    ):
        self.providers = providers or {}
        self.model = model
        self._dimension = 1536  # OpenAI default
    
    @property
    def dimension(self) -> int:
        return self._dimension
    
    async def embed(self, text: str) -> List[float]:
        """Generate embedding for text."""
        if "openai" in self.providers:
            try:
                return await self._embed_openai(text)
            except Exception as e:
                logger.warning("OpenAI embedding failed: %s", e)
        
        # Fallback to simple hash-based embedding (not semantic!)
        return self._simple_embed(text)
    
    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        tasks = [self.embed(text) for text in texts]
        return await asyncio.gather(*tasks)
    
    async def _embed_openai(self, text: str) -> List[float]:
        """Use OpenAI for embeddings."""
        provider = self.providers["openai"]
        
        # Truncate to avoid token limits
        text = text[:8000]
        
        result = await provider.create_embedding(text, model=self.model)
        return result.embedding
    
    def _simple_embed(self, text: str) -> List[float]:
        """Simple hash-based embedding (fallback)."""
        # This is NOT semantic - just for testing
        import hashlib
        
        # Create consistent hash
        text_hash = hashlib.sha256(text.encode()).digest()
        
        # Expand to dimension
        embedding = []
        for i in range(self._dimension):
            byte_idx = i % len(text_hash)
            embedding.append((text_hash[byte_idx] - 128) / 128.0)
        
        return embedding


class VectorStore:
    """FAISS-based vector store."""
    
    def __init__(self, dimension: int = 1536):
        self.dimension = dimension
        self._entries: Dict[str, MemoryEntry] = {}
        self._id_to_idx: Dict[str, int] = {}
        self._idx_to_id: Dict[int, str] = {}
        
        if FAISS_AVAILABLE:
            self._index = faiss.IndexFlatIP(dimension)  # Inner product (cosine after norm)
        else:
            self._index = None
            self._vectors: List[Tuple[str, List[float]]] = []
    
    def add(self, entry: MemoryEntry) -> None:
        """Add an entry to the store."""
        if entry.embedding is None:
            return
        
        self._entries[entry.id] = entry
        
        if FAISS_AVAILABLE and self._index is not None:
            # Normalize for cosine similarity
            vec = np.array([entry.embedding], dtype=np.float32)
            faiss.normalize_L2(vec)
            
            idx = self._index.ntotal
            self._index.add(vec)
            self._id_to_idx[entry.id] = idx
            self._idx_to_id[idx] = entry.id
        else:
            self._vectors.append((entry.id, entry.embedding))
    
    def search(
        self,
        query_embedding: List[float],
        k: int = 5,
    ) -> List[Tuple[str, float]]:
        """Search for similar entries."""
        if FAISS_AVAILABLE and self._index is not None and self._index.ntotal > 0:
            # Normalize query
            query = np.array([query_embedding], dtype=np.float32)
            faiss.normalize_L2(query)
            
            # Search
            k = min(k, self._index.ntotal)
            scores, indices = self._index.search(query, k)
            
            results = []
            for score, idx in zip(scores[0], indices[0]):
                if idx >= 0 and idx in self._idx_to_id:
                    entry_id = self._idx_to_id[idx]
                    results.append((entry_id, float(score)))
            
            return results
        else:
            # Simple cosine similarity fallback
            return self._simple_search(query_embedding, k)
    
    def _simple_search(
        self,
        query: List[float],
        k: int,
    ) -> List[Tuple[str, float]]:
        """Simple search without FAISS."""
        scores = []
        
        for entry_id, embedding in self._vectors:
            # Cosine similarity
            dot = sum(a * b for a, b in zip(query, embedding))
            norm_q = sum(a * a for a in query) ** 0.5
            norm_e = sum(a * a for a in embedding) ** 0.5
            
            if norm_q > 0 and norm_e > 0:
                score = dot / (norm_q * norm_e)
                scores.append((entry_id, score))
        
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:k]
    
    def get(self, entry_id: str) -> Optional[MemoryEntry]:
        """Get entry by ID."""
        return self._entries.get(entry_id)
    
    def delete(self, entry_id: str) -> bool:
        """Delete entry by ID."""
        if entry_id in self._entries:
            del self._entries[entry_id]
            # Note: FAISS doesn't support deletion easily
            # In production, would need to rebuild index periodically
            return True
        return False


class PersistentMemory:
    """Manages persistent memory with vector search.
    
    Stores conversation turns, reference documents, and shared
    knowledge with semantic retrieval capabilities.
    """
    
    def __init__(
        self,
        providers: Optional[Dict[str, Any]] = None,
        storage_path: Optional[str] = None,
        max_entries: int = 10000,
    ):
        """Initialize persistent memory.
        
        Args:
            providers: LLM providers (for embeddings)
            storage_path: Path for persistent storage
            max_entries: Maximum number of entries to keep
        """
        self.embedding_provider = EmbeddingProvider(providers)
        self.vector_store = VectorStore(self.embedding_provider.dimension)
        self.storage_path = storage_path
        self.max_entries = max_entries
        
        if storage_path:
            self._load_from_disk()
    
    async def add_memory(
        self,
        content: str,
        *,
        source: str = "conversation",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Add a memory entry.
        
        Args:
            content: Text content to store
            source: Source type (conversation, document, shared)
            metadata: Optional metadata
            
        Returns:
            Entry ID
        """
        # Generate ID
        entry_id = hashlib.sha256(
            f"{content[:100]}{time.time()}".encode()
        ).hexdigest()[:16]
        
        # Generate embedding
        embedding = await self.embedding_provider.embed(content)
        
        # Create entry
        entry = MemoryEntry(
            id=entry_id,
            content=content,
            embedding=embedding,
            metadata=metadata or {},
            source=source,
        )
        
        # Add to store
        self.vector_store.add(entry)
        
        # Check limits
        self._enforce_limits()
        
        return entry_id
    
    async def search_memory(
        self,
        query: str,
        k: int = 5,
        source_filter: Optional[str] = None,
    ) -> MemorySearchResult:
        """Search memory for relevant entries.
        
        Args:
            query: Search query
            k: Number of results
            source_filter: Optional source type filter
            
        Returns:
            MemorySearchResult with matching entries
        """
        start_time = time.time()
        
        # Embed query
        query_embedding = await self.embedding_provider.embed(query)
        
        # Search
        results = self.vector_store.search(query_embedding, k * 2)  # Over-fetch for filtering
        
        # Collect entries
        entries = []
        for entry_id, score in results:
            entry = self.vector_store.get(entry_id)
            if entry:
                # Apply source filter
                if source_filter and entry.source != source_filter:
                    continue
                
                entry.relevance_score = score
                entries.append(entry)
                
                if len(entries) >= k:
                    break
        
        return MemorySearchResult(
            entries=entries,
            total_matches=len(entries),
            search_time_ms=(time.time() - start_time) * 1000,
        )
    
    async def get_relevant_context(
        self,
        query: str,
        *,
        max_tokens: int = 1000,
        include_conversation: bool = True,
        include_documents: bool = True,
        include_shared: bool = True,
    ) -> str:
        """Get relevant context for a query.
        
        Args:
            query: The query to find context for
            max_tokens: Maximum tokens in context
            include_conversation: Include conversation history
            include_documents: Include reference documents
            include_shared: Include shared knowledge
            
        Returns:
            Formatted context string
        """
        all_entries = []
        
        # Search each source
        sources_to_search = []
        if include_conversation:
            sources_to_search.append("conversation")
        if include_documents:
            sources_to_search.append("document")
        if include_shared:
            sources_to_search.append("shared")
        
        for source in sources_to_search:
            result = await self.search_memory(query, k=3, source_filter=source)
            all_entries.extend(result.entries)
        
        # Sort by relevance
        all_entries.sort(key=lambda e: e.relevance_score, reverse=True)
        
        # Build context with token limit
        context_parts = []
        total_chars = 0
        max_chars = max_tokens * 4  # Rough estimate
        
        for entry in all_entries:
            if total_chars + len(entry.content) > max_chars:
                # Truncate or skip
                remaining = max_chars - total_chars
                if remaining > 100:
                    context_parts.append(entry.content[:remaining] + "...")
                break
            
            context_parts.append(entry.content)
            total_chars += len(entry.content)
        
        if not context_parts:
            return ""
        
        return "\n\n---\n\n".join(context_parts)
    
    def _enforce_limits(self) -> None:
        """Enforce memory limits by removing old entries."""
        if len(self.vector_store._entries) <= self.max_entries:
            return
        
        # Remove oldest entries
        entries = sorted(
            self.vector_store._entries.values(),
            key=lambda e: e.timestamp
        )
        
        to_remove = len(entries) - self.max_entries
        for entry in entries[:to_remove]:
            self.vector_store.delete(entry.id)
    
    def _load_from_disk(self) -> None:
        """Load memory from disk."""
        if not self.storage_path:
            return
        
        path = Path(self.storage_path)
        if not path.exists():
            return
        
        try:
            with open(path, 'r') as f:
                data = json.load(f)
            
            for entry_data in data.get("entries", []):
                entry = MemoryEntry(
                    id=entry_data["id"],
                    content=entry_data["content"],
                    embedding=entry_data.get("embedding"),
                    metadata=entry_data.get("metadata", {}),
                    timestamp=entry_data.get("timestamp", time.time()),
                    source=entry_data.get("source", "conversation"),
                )
                if entry.embedding:
                    self.vector_store.add(entry)
            
            logger.info("Loaded %d memory entries from %s", 
                       len(self.vector_store._entries), path)
        except Exception as e:
            logger.error("Failed to load memory: %s", e)
    
    def save_to_disk(self) -> None:
        """Save memory to disk."""
        if not self.storage_path:
            return
        
        path = Path(self.storage_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            "entries": [
                {
                    "id": e.id,
                    "content": e.content,
                    "embedding": e.embedding,
                    "metadata": e.metadata,
                    "timestamp": e.timestamp,
                    "source": e.source,
                }
                for e in self.vector_store._entries.values()
            ]
        }
        
        try:
            with open(path, 'w') as f:
                json.dump(data, f)
            logger.info("Saved %d memory entries to %s", len(data["entries"]), path)
        except Exception as e:
            logger.error("Failed to save memory: %s", e)


class SharedMemoryManager:
    """Manages organization-wide shared knowledge.
    
    Placeholder for future integration with organizational
    knowledge bases and shared context.
    """
    
    def __init__(self):
        self._shared_facts: List[str] = []
    
    def add_shared_fact(self, fact: str) -> None:
        """Add a shared fact."""
        self._shared_facts.append(fact)
    
    def get_shared_context(self, query: str) -> str:
        """Get relevant shared context for a query."""
        # Placeholder - would use semantic search in production
        return ""


# ==============================================================================
# Convenience Functions
# ==============================================================================

# Global memory instance
_memory: Optional[PersistentMemory] = None


def get_memory(
    providers: Optional[Dict[str, Any]] = None,
) -> PersistentMemory:
    """Get or create the global memory instance."""
    global _memory
    if _memory is None:
        _memory = PersistentMemory(providers=providers)
    return _memory


async def remember(
    content: str,
    source: str = "conversation",
) -> str:
    """Convenience function to add memory."""
    memory = get_memory()
    return await memory.add_memory(content, source=source)


async def recall(
    query: str,
    k: int = 5,
) -> List[str]:
    """Convenience function to recall memories."""
    memory = get_memory()
    result = await memory.search_memory(query, k=k)
    return [e.content for e in result.entries]
