"""Memory management module for LLMHive.

This module provides:
- Persistent memory with vector database storage (Pinecone)
- Short-term scratchpad for within-query data sharing
- Enhanced memory with summarization and relevance filtering
- Secure memory with encryption
"""
from __future__ import annotations

# Embedding service
try:
    from .embeddings import (
        EmbeddingService,
        get_embedding_service,
        get_embedding,
    )
    EMBEDDINGS_AVAILABLE = True
except ImportError:
    EMBEDDINGS_AVAILABLE = False
    EmbeddingService = None  # type: ignore
    get_embedding_service = None  # type: ignore
    get_embedding = None  # type: ignore

# Vector store
try:
    from .vector_store import (
        VectorStore,
        InMemoryVectorStore,
        PineconeVectorStore,
        MemoryRecord,
        MemoryQueryResult,
        get_vector_store,
        get_global_vector_store,
    )
    VECTOR_STORE_AVAILABLE = True
except ImportError:
    VECTOR_STORE_AVAILABLE = False
    VectorStore = None  # type: ignore
    InMemoryVectorStore = None  # type: ignore
    PineconeVectorStore = None  # type: ignore
    MemoryRecord = None  # type: ignore
    MemoryQueryResult = None  # type: ignore

# Persistent memory
try:
    from .persistent_memory import (
        PersistentMemoryManager,
        MemoryHit,
        Scratchpad,
        get_persistent_memory,
        get_scratchpad,
        query_scratchpad,
        add_to_memory,
        query_memory,
    )
    PERSISTENT_MEMORY_AVAILABLE = True
except ImportError:
    PERSISTENT_MEMORY_AVAILABLE = False
    PersistentMemoryManager = None  # type: ignore
    MemoryHit = None  # type: ignore
    Scratchpad = None  # type: ignore

# Enhanced memory
try:
    from .enhanced_memory import (
        EnhancedMemoryManager,
        SummarizedContext,
    )
    ENHANCED_MEMORY_AVAILABLE = True
except ImportError:
    ENHANCED_MEMORY_AVAILABLE = False
    EnhancedMemoryManager = None  # type: ignore
    SummarizedContext = None  # type: ignore

# Secure memory
try:
    from .secure_memory import SecureMemoryManager
    SECURE_MEMORY_AVAILABLE = True
except ImportError:
    SECURE_MEMORY_AVAILABLE = False
    SecureMemoryManager = None  # type: ignore

__all__ = []

if EMBEDDINGS_AVAILABLE:
    __all__.extend([
        "EmbeddingService",
        "get_embedding_service",
        "get_embedding",
    ])

if VECTOR_STORE_AVAILABLE:
    __all__.extend([
        "VectorStore",
        "InMemoryVectorStore",
        "PineconeVectorStore",
        "MemoryRecord",
        "MemoryQueryResult",
        "get_vector_store",
        "get_global_vector_store",
    ])

if PERSISTENT_MEMORY_AVAILABLE:
    __all__.extend([
        "PersistentMemoryManager",
        "MemoryHit",
        "Scratchpad",
        "get_persistent_memory",
        "get_scratchpad",
        "query_scratchpad",
        "add_to_memory",
        "query_memory",
    ])

if ENHANCED_MEMORY_AVAILABLE:
    __all__.extend([
        "EnhancedMemoryManager",
        "SummarizedContext",
    ])

if SECURE_MEMORY_AVAILABLE:
    __all__.extend([
        "SecureMemoryManager",
    ])

