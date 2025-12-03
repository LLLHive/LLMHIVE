"""Memory Module for LLMHive Orchestrator.

This package provides persistent memory capabilities including:
- Vector-based semantic storage (FAISS)
- Conversation history
- Reference documents
- Organization-wide shared knowledge
"""
from .persistent_memory import (
    PersistentMemory,
    SharedMemoryManager,
    MemoryEntry,
    MemorySearchResult,
    VectorStore,
    get_memory,
    remember,
    recall,
)

__all__ = [
    "PersistentMemory",
    "SharedMemoryManager",
    "MemoryEntry",
    "MemorySearchResult",
    "VectorStore",
    "get_memory",
    "remember",
    "recall",
]
