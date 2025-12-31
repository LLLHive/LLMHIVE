"""
Memory Router - Handles conversation memory storage and retrieval.

This router provides endpoints for:
- Syncing user conversations to vector memory
- Storing individual Q&A pairs for RAG
- Retrieving relevant context for new queries
"""

import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from ..feature_flags import is_feature_enabled, FeatureFlags
from ..memory.vector_store import get_global_vector_store, MemoryRecord

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/memory", tags=["memory"])


class MessageData(BaseModel):
    role: str
    content: str
    timestamp: Optional[str] = None


class ConversationData(BaseModel):
    id: str
    title: str
    messages: List[MessageData]
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class SyncRequest(BaseModel):
    user_id: str
    conversations: List[ConversationData]


class StoreRequest(BaseModel):
    user_id: str
    conversation_id: str
    title: str
    messages: List[MessageData]


class QueryRequest(BaseModel):
    user_id: str
    query: str
    top_k: int = 5


class MemoryEntry(BaseModel):
    id: str
    content: str
    metadata: dict
    score: Optional[float] = None


class SyncResponse(BaseModel):
    success: bool
    records_stored: int
    message: str


class QueryResponse(BaseModel):
    results: List[MemoryEntry]
    count: int


@router.post("/sync", response_model=SyncResponse)
async def sync_conversations(request: SyncRequest):
    """
    Sync user conversations to vector memory for RAG.
    
    This endpoint:
    1. Processes each conversation's Q&A pairs
    2. Generates embeddings for answers
    3. Stores in Pinecone with user namespace isolation
    """
    if not is_feature_enabled(FeatureFlags.VECTOR_MEMORY):
        return SyncResponse(
            success=True,
            records_stored=0,
            message="Vector memory feature is disabled"
        )
    
    try:
        vector_store = get_global_vector_store()
        namespace = f"user_{request.user_id}"
        records_stored = 0
        
        for conv in request.conversations:
            # Extract Q&A pairs from messages
            messages = conv.messages
            for i in range(len(messages) - 1):
                if messages[i].role == "user" and messages[i + 1].role == "assistant":
                    question = messages[i].content
                    answer = messages[i + 1].content
                    
                    # Create memory record
                    record = MemoryRecord(
                        id=f"{conv.id}_{i}",
                        content=answer,
                        metadata={
                            "conversation_id": conv.id,
                            "conversation_title": conv.title,
                            "question": question[:500],  # Truncate for metadata limits
                            "user_id": request.user_id,
                            "type": "qa_pair",
                        }
                    )
                    
                    # Store in vector database
                    await vector_store.upsert(record, namespace=namespace)
                    records_stored += 1
        
        logger.info(
            "Synced %d records for user %s",
            records_stored, request.user_id[:8]
        )
        
        return SyncResponse(
            success=True,
            records_stored=records_stored,
            message=f"Synced {records_stored} Q&A pairs to memory"
        )
        
    except Exception as e:
        logger.error("Memory sync error: %s", e)
        return SyncResponse(
            success=False,
            records_stored=0,
            message=f"Sync failed: {str(e)}"
        )


@router.post("/store", response_model=SyncResponse)
async def store_conversation(request: StoreRequest):
    """
    Store a single conversation's Q&A pairs to memory.
    """
    if not is_feature_enabled(FeatureFlags.VECTOR_MEMORY):
        return SyncResponse(
            success=True,
            records_stored=0,
            message="Vector memory feature is disabled"
        )
    
    try:
        vector_store = get_global_vector_store()
        namespace = f"user_{request.user_id}"
        records_stored = 0
        
        messages = request.messages
        for i in range(len(messages) - 1):
            if messages[i].role == "user" and messages[i + 1].role == "assistant":
                question = messages[i].content
                answer = messages[i + 1].content
                
                record = MemoryRecord(
                    id=f"{request.conversation_id}_{i}",
                    content=answer,
                    metadata={
                        "conversation_id": request.conversation_id,
                        "conversation_title": request.title,
                        "question": question[:500],
                        "user_id": request.user_id,
                        "type": "qa_pair",
                    }
                )
                
                await vector_store.upsert(record, namespace=namespace)
                records_stored += 1
        
        logger.info(
            "Stored %d records for conversation %s",
            records_stored, request.conversation_id[:8]
        )
        
        return SyncResponse(
            success=True,
            records_stored=records_stored,
            message=f"Stored {records_stored} Q&A pairs"
        )
        
    except Exception as e:
        logger.error("Memory store error: %s", e)
        return SyncResponse(
            success=False,
            records_stored=0,
            message=f"Store failed: {str(e)}"
        )


@router.post("/query", response_model=QueryResponse)
async def query_memory(request: QueryRequest):
    """
    Query user's conversation memory for relevant context.
    
    Used by RAG to find relevant past Q&A pairs.
    """
    if not is_feature_enabled(FeatureFlags.VECTOR_MEMORY):
        return QueryResponse(results=[], count=0)
    
    try:
        vector_store = get_global_vector_store()
        namespace = f"user_{request.user_id}"
        
        results = await vector_store.search(
            query=request.query,
            namespace=namespace,
            top_k=request.top_k,
            filter={"user_id": request.user_id}
        )
        
        entries = [
            MemoryEntry(
                id=r.id,
                content=r.content,
                metadata=r.metadata,
                score=r.score
            )
            for r in results
        ]
        
        logger.debug(
            "Memory query returned %d results for user %s",
            len(entries), request.user_id[:8]
        )
        
        return QueryResponse(results=entries, count=len(entries))
        
    except Exception as e:
        logger.error("Memory query error: %s", e)
        return QueryResponse(results=[], count=0)


@router.get("/stats/{user_id}")
async def get_memory_stats(user_id: str):
    """
    Get memory statistics for a user.
    """
    if not is_feature_enabled(FeatureFlags.VECTOR_MEMORY):
        return {"enabled": False, "total_records": 0}
    
    try:
        vector_store = get_global_vector_store()
        namespace = f"user_{user_id}"
        
        stats = await vector_store.get_stats(namespace=namespace)
        
        return {
            "enabled": True,
            "namespace": namespace,
            **stats
        }
        
    except Exception as e:
        logger.error("Memory stats error: %s", e)
        return {"enabled": True, "error": str(e)}

