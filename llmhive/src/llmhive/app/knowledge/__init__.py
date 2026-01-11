"""
Knowledge Base Module for LLMHive Orchestrator

Provides vector database-backed knowledge storage and retrieval
for orchestrator learning and RAG capabilities.

Includes:
- PineconeKnowledgeBase: General knowledge storage (answers, patterns, domain knowledge)
- ModelKnowledgeStore: Model intelligence storage (profiles, rankings, capabilities)
- PineconeRegistry: Centralized connection management for all Pinecone indexes
"""

from .pinecone_kb import (
    PineconeKnowledgeBase,
    KnowledgeRecord,
    RecordType,
    get_knowledge_base,
)

# Pinecone Registry for centralized connection management
try:
    from .pinecone_registry import (
        PineconeRegistry,
        IndexKind,
        INDEX_CONFIGS,
        get_pinecone_registry,
        get_index,
        is_pinecone_available,
    )
    PINECONE_REGISTRY_AVAILABLE = True
except ImportError:
    PINECONE_REGISTRY_AVAILABLE = False
    PineconeRegistry = None  # type: ignore
    IndexKind = None  # type: ignore
    get_pinecone_registry = None  # type: ignore

# Model Knowledge Store for orchestration intelligence
try:
    from .model_knowledge_store import (
        ModelKnowledgeStore,
        ModelProfile,
        ModelKnowledgeRecord,
        ModelKnowledgeType,
        get_model_knowledge_store,
    )
    from .model_knowledge_sync import (
        ModelKnowledgeSync,
        sync_openrouter_to_knowledge,
    )
    MODEL_KNOWLEDGE_AVAILABLE = True
except ImportError:
    MODEL_KNOWLEDGE_AVAILABLE = False
    ModelKnowledgeStore = None  # type: ignore
    ModelProfile = None  # type: ignore
    get_model_knowledge_store = None  # type: ignore

__all__ = [
    # General knowledge base
    "PineconeKnowledgeBase",
    "KnowledgeRecord",
    "RecordType",
    "get_knowledge_base",
    # Model knowledge store
    "ModelKnowledgeStore",
    "ModelProfile",
    "ModelKnowledgeRecord",
    "ModelKnowledgeType",
    "get_model_knowledge_store",
    "ModelKnowledgeSync",
    "sync_openrouter_to_knowledge",
    "MODEL_KNOWLEDGE_AVAILABLE",
]
