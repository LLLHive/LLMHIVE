"""
Knowledge Base Module for LLMHive Orchestrator

Provides vector database-backed knowledge storage and retrieval
for orchestrator learning and RAG capabilities.
"""

from .pinecone_kb import (
    PineconeKnowledgeBase,
    KnowledgeRecord,
    RecordType,
    get_knowledge_base,
)

__all__ = [
    "PineconeKnowledgeBase",
    "KnowledgeRecord",
    "RecordType",
    "get_knowledge_base",
]
