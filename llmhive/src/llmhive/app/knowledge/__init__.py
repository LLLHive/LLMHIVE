"""
Knowledge Base Module for LLMHive Orchestrator

Provides vector database-backed knowledge storage and retrieval
for orchestrator learning and RAG capabilities.

Includes:
- PineconeKnowledgeBase: General knowledge storage (answers, patterns, domain knowledge)
- ModelKnowledgeStore: Model intelligence storage (profiles, rankings, capabilities)
"""

from .pinecone_kb import (
    PineconeKnowledgeBase,
    KnowledgeRecord,
    RecordType,
    get_knowledge_base,
)

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
