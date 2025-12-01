"""Pinecone-integrated RLHF Feedback Storage.

This module stores user feedback in Pinecone for:
- Semantic similarity search of past feedback
- RLHF training data retrieval  
- Finding similar good/bad answers for model improvement

No Vertex AI needed - uses Pinecone's integrated embeddings.
"""
from __future__ import annotations

import hashlib
import logging
import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Try to import Pinecone
try:
    from pinecone import Pinecone
    PINECONE_AVAILABLE = True
except ImportError:
    PINECONE_AVAILABLE = False
    Pinecone = None  # type: ignore
    logger.warning("pinecone not installed. Run: pip install pinecone")


class FeedbackType(str, Enum):
    """Types of feedback."""
    THUMBS_UP = "thumbs_up"
    THUMBS_DOWN = "thumbs_down"
    RATING = "rating"
    CORRECTION = "correction"


@dataclass
class FeedbackRecord:
    """A feedback record stored in Pinecone."""
    id: str
    query: str
    answer: str
    feedback_type: str
    rating: float  # 0-1 normalized
    user_id: Optional[str]
    model_used: Optional[str]
    created_at: str
    is_positive: bool
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "query": self.query,
            "answer": self.answer,
            "feedback_type": self.feedback_type,
            "rating": self.rating,
            "user_id": self.user_id or "",
            "model_used": self.model_used or "",
            "created_at": self.created_at,
            "is_positive": self.is_positive,
        }


class PineconeFeedbackStore:
    """Store and retrieve RLHF feedback using Pinecone.
    
    Uses Pinecone's integrated embeddings (llama-text-embed-v2) so we don't
    need external embedding APIs like Vertex AI.
    
    Usage:
        store = PineconeFeedbackStore()
        
        # Record feedback
        await store.record_feedback(
            query="What is AI?",
            answer="AI is...",
            feedback_type="thumbs_up",
            user_id="user123",
        )
        
        # Find similar positive examples
        examples = await store.find_similar_feedback(
            query="Tell me about artificial intelligence",
            positive_only=True,
            limit=5,
        )
    """
    
    INDEX_NAME = "llmhive-rlhf-feedback"
    NAMESPACE = "feedback"
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        index_name: Optional[str] = None,
    ):
        """Initialize Pinecone feedback store.
        
        Args:
            api_key: Pinecone API key (or use PINECONE_API_KEY env var)
            index_name: Index name (default: llmhive-rlhf-feedback)
        """
        self.api_key = api_key or os.getenv("PINECONE_API_KEY")
        self.index_name = index_name or self.INDEX_NAME
        
        self._pc: Optional[Any] = None
        self._index: Optional[Any] = None
        self._initialized = False
    
    def _ensure_initialized(self) -> bool:
        """Ensure Pinecone client is initialized."""
        if self._initialized:
            return True
        
        if not PINECONE_AVAILABLE:
            logger.error("Pinecone SDK not available")
            return False
        
        if not self.api_key:
            logger.error("PINECONE_API_KEY not set")
            return False
        
        try:
            self._pc = Pinecone(api_key=self.api_key)
            
            # Check if index exists
            if not self._pc.has_index(self.index_name):
                logger.info("Creating Pinecone index: %s", self.index_name)
                # Create index with integrated embeddings
                self._pc.create_index_for_model(
                    name=self.index_name,
                    cloud="aws",
                    region="us-east-1",
                    embed={
                        "model": "llama-text-embed-v2",
                        "field_map": {"text": "content"}
                    }
                )
                # Wait for index to be ready
                time.sleep(5)
            
            self._index = self._pc.Index(self.index_name)
            self._initialized = True
            logger.info("Pinecone feedback store initialized: %s", self.index_name)
            return True
            
        except Exception as e:
            logger.error("Failed to initialize Pinecone: %s", e)
            return False
    
    def _generate_id(self, query: str, answer: str) -> str:
        """Generate unique ID for feedback."""
        content = f"{query}|{answer}|{time.time()}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def _normalize_rating(self, rating: Optional[float], feedback_type: str) -> float:
        """Normalize rating to 0-1 scale."""
        if rating is None:
            if feedback_type == "thumbs_up":
                return 1.0
            elif feedback_type == "thumbs_down":
                return 0.0
            else:
                return 0.5
        elif rating > 1.0:
            # Assume 1-5 scale, normalize to 0-1
            return (rating - 1) / 4.0
        return rating
    
    async def record_feedback(
        self,
        query: str,
        answer: str,
        feedback_type: str = "rating",
        rating: Optional[float] = None,
        user_id: Optional[str] = None,
        model_used: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> Optional[FeedbackRecord]:
        """Record user feedback in Pinecone.
        
        Args:
            query: The user's question
            answer: The answer that was given
            feedback_type: Type of feedback (thumbs_up, thumbs_down, rating, correction)
            rating: Rating value (0-1 or 1-5, will be normalized)
            user_id: User identifier
            model_used: Model that generated the answer
            session_id: Session identifier
            
        Returns:
            FeedbackRecord that was stored, or None if failed
        """
        if not self._ensure_initialized():
            logger.warning("Cannot record feedback - Pinecone not initialized")
            return None
        
        try:
            normalized_rating = self._normalize_rating(rating, feedback_type)
            is_positive = normalized_rating >= 0.7
            
            record_id = self._generate_id(query, answer)
            created_at = datetime.now(timezone.utc).isoformat()
            
            # Create content for embedding (combine query + answer for semantic search)
            content = f"Query: {query}\n\nAnswer: {answer}"
            
            # Create record for Pinecone
            record = {
                "_id": record_id,
                "content": content,  # This field is embedded by Pinecone
                "query": query,
                "answer": answer,
                "feedback_type": feedback_type,
                "rating": normalized_rating,
                "is_positive": is_positive,
                "user_id": user_id or "",
                "model_used": model_used or "",
                "session_id": session_id or "",
                "created_at": created_at,
            }
            
            # Upsert to Pinecone
            self._index.upsert_records(self.NAMESPACE, [record])
            
            logger.info(
                "Recorded feedback: type=%s rating=%.2f positive=%s",
                feedback_type, normalized_rating, is_positive,
            )
            
            return FeedbackRecord(
                id=record_id,
                query=query,
                answer=answer,
                feedback_type=feedback_type,
                rating=normalized_rating,
                user_id=user_id,
                model_used=model_used,
                created_at=created_at,
                is_positive=is_positive,
            )
            
        except Exception as e:
            logger.error("Failed to record feedback: %s", e)
            return None
    
    async def find_similar_feedback(
        self,
        query: str,
        positive_only: bool = False,
        negative_only: bool = False,
        limit: int = 5,
        min_score: float = 0.5,
    ) -> List[FeedbackRecord]:
        """Find similar past feedback using semantic search.
        
        Args:
            query: Query to search for
            positive_only: Only return positive feedback
            negative_only: Only return negative feedback
            limit: Maximum results
            min_score: Minimum similarity score
            
        Returns:
            List of similar FeedbackRecord
        """
        if not self._ensure_initialized():
            return []
        
        try:
            # Build filter
            filter_dict = None
            if positive_only:
                filter_dict = {"is_positive": {"$eq": True}}
            elif negative_only:
                filter_dict = {"is_positive": {"$eq": False}}
            
            # Build query
            query_params = {
                "top_k": limit * 2,  # Get more for reranking
                "inputs": {"text": query},
            }
            if filter_dict:
                query_params["filter"] = filter_dict
            
            # Search with reranking
            results = self._index.search(
                namespace=self.NAMESPACE,
                query=query_params,
                rerank={
                    "model": "bge-reranker-v2-m3",
                    "top_n": limit,
                    "rank_fields": ["content"],
                }
            )
            
            # Convert to FeedbackRecord
            records = []
            for hit in results.get("result", {}).get("hits", []):
                if hit.get("_score", 0) >= min_score:
                    fields = hit.get("fields", {})
                    records.append(FeedbackRecord(
                        id=hit.get("_id", ""),
                        query=fields.get("query", ""),
                        answer=fields.get("answer", ""),
                        feedback_type=fields.get("feedback_type", "rating"),
                        rating=fields.get("rating", 0.5),
                        user_id=fields.get("user_id"),
                        model_used=fields.get("model_used"),
                        created_at=fields.get("created_at", ""),
                        is_positive=fields.get("is_positive", False),
                    ))
            
            logger.debug("Found %d similar feedback records", len(records))
            return records
            
        except Exception as e:
            logger.error("Failed to search feedback: %s", e)
            return []
    
    async def get_training_examples(
        self,
        query: str,
        num_positive: int = 3,
        num_negative: int = 2,
    ) -> Dict[str, List[FeedbackRecord]]:
        """Get positive and negative examples for a query.
        
        Useful for RLHF training - finds similar past queries with
        known good and bad answers.
        
        Args:
            query: Query to find examples for
            num_positive: Number of positive examples
            num_negative: Number of negative examples
            
        Returns:
            Dict with "positive" and "negative" example lists
        """
        positive = await self.find_similar_feedback(
            query=query,
            positive_only=True,
            limit=num_positive,
        )
        
        negative = await self.find_similar_feedback(
            query=query,
            negative_only=True,
            limit=num_negative,
        )
        
        return {
            "positive": positive,
            "negative": negative,
        }
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get feedback statistics."""
        if not self._ensure_initialized():
            return {"error": "Pinecone not initialized"}
        
        try:
            stats = self._index.describe_index_stats()
            ns_stats = stats.get("namespaces", {}).get(self.NAMESPACE, {})
            
            return {
                "total_feedback": ns_stats.get("record_count", 0),
                "index_name": self.index_name,
                "namespace": self.NAMESPACE,
            }
            
        except Exception as e:
            logger.error("Failed to get stats: %s", e)
            return {"error": str(e)}


# ==============================================================================
# Global Instance
# ==============================================================================

_feedback_store: Optional[PineconeFeedbackStore] = None


def get_pinecone_feedback_store() -> PineconeFeedbackStore:
    """Get or create global Pinecone feedback store."""
    global _feedback_store
    if _feedback_store is None:
        _feedback_store = PineconeFeedbackStore()
    return _feedback_store


# ==============================================================================
# FastAPI Integration
# ==============================================================================

def create_feedback_router():
    """Create FastAPI router for feedback endpoints."""
    from fastapi import APIRouter, HTTPException
    from pydantic import BaseModel
    from typing import Optional
    
    router = APIRouter()
    
    class FeedbackRequest(BaseModel):
        query: str
        answer: str
        feedback_type: str = "rating"  # thumbs_up, thumbs_down, rating
        rating: Optional[float] = None  # 1-5 or 0-1
        model_used: Optional[str] = None
        session_id: Optional[str] = None
    
    class FeedbackResponse(BaseModel):
        success: bool
        feedback_id: Optional[str] = None
        message: str
    
    @router.post("/feedback", response_model=FeedbackResponse)
    async def submit_feedback(request: FeedbackRequest):
        """Submit feedback on an answer.
        
        This feedback is stored in Pinecone for RLHF training.
        """
        store = get_pinecone_feedback_store()
        
        record = await store.record_feedback(
            query=request.query,
            answer=request.answer,
            feedback_type=request.feedback_type,
            rating=request.rating,
            model_used=request.model_used,
            session_id=request.session_id,
        )
        
        if record:
            return FeedbackResponse(
                success=True,
                feedback_id=record.id,
                message="Feedback recorded successfully",
            )
        else:
            return FeedbackResponse(
                success=False,
                message="Failed to record feedback - Pinecone may not be configured",
            )
    
    @router.get("/feedback/similar")
    async def find_similar(
        query: str,
        positive_only: bool = False,
        limit: int = 5,
    ):
        """Find similar past feedback for a query."""
        store = get_pinecone_feedback_store()
        
        records = await store.find_similar_feedback(
            query=query,
            positive_only=positive_only,
            limit=limit,
        )
        
        return {
            "query": query,
            "results": [r.to_dict() for r in records],
            "count": len(records),
        }
    
    @router.get("/feedback/examples")
    async def get_examples(
        query: str,
        num_positive: int = 3,
        num_negative: int = 2,
    ):
        """Get positive and negative examples for RLHF training."""
        store = get_pinecone_feedback_store()
        
        examples = await store.get_training_examples(
            query=query,
            num_positive=num_positive,
            num_negative=num_negative,
        )
        
        return {
            "query": query,
            "positive": [r.to_dict() for r in examples["positive"]],
            "negative": [r.to_dict() for r in examples["negative"]],
        }
    
    @router.get("/feedback/stats")
    async def get_stats():
        """Get feedback statistics."""
        store = get_pinecone_feedback_store()
        return await store.get_stats()
    
    return router

