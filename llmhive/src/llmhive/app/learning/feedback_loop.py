"""Feedback Loop for Continuous Learning.

This module tracks user feedback (explicit and implicit) and uses it to:
- Mark regenerations as implicit negative feedback
- Store successful answers for future reference
- Update model weights based on feedback
- Identify patterns in failed queries
"""
from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from .performance_logger import get_performance_logger, PerformanceLogger
from .model_optimizer import get_model_optimizer, ModelOptimizer

logger = logging.getLogger(__name__)


class FeedbackType(str, Enum):
    """Types of feedback events."""
    # Explicit feedback
    THUMBS_UP = "thumbs_up"
    THUMBS_DOWN = "thumbs_down"
    RATING = "rating"  # 1-5 star rating
    CORRECTION = "correction"  # User corrected the answer
    
    # Implicit feedback
    REGENERATE = "regenerate"  # User asked to regenerate
    COPY = "copy"  # User copied the answer (positive)
    FOLLOW_UP = "follow_up"  # User asked follow-up (neutral/positive)
    ABANDON = "abandon"  # User abandoned conversation (negative)
    SHARE = "share"  # User shared the answer (very positive)


@dataclass
class FeedbackEvent:
    """A single feedback event."""
    id: str
    query_id: str
    feedback_type: FeedbackType
    value: Optional[float] = None  # Normalized 0-1 score
    model_name: Optional[str] = None  # Which model was being evaluated
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    
    @property
    def is_positive(self) -> bool:
        """Check if this is positive feedback."""
        if self.feedback_type in [FeedbackType.THUMBS_UP, FeedbackType.COPY, FeedbackType.SHARE]:
            return True
        if self.feedback_type == FeedbackType.RATING and self.value is not None:
            return self.value >= 0.6  # 3+ stars
        return False
    
    @property
    def is_negative(self) -> bool:
        """Check if this is negative feedback."""
        if self.feedback_type in [FeedbackType.THUMBS_DOWN, FeedbackType.REGENERATE, FeedbackType.ABANDON]:
            return True
        if self.feedback_type == FeedbackType.RATING and self.value is not None:
            return self.value < 0.4  # 1-2 stars
        return False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "query_id": self.query_id,
            "feedback_type": self.feedback_type.value,
            "value": self.value,
            "model_name": self.model_name,
            "session_id": self.session_id,
            "user_id": self.user_id,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "is_positive": self.is_positive,
            "is_negative": self.is_negative,
        }


class FeedbackLoop:
    """Main feedback loop for continuous learning.
    
    Tracks feedback events and uses them to:
    1. Update model weights based on success/failure patterns
    2. Mark queries for regeneration tracking
    3. Store successful answers in knowledge base
    4. Identify patterns in failed queries for improvement
    """
    
    def __init__(
        self,
        perf_logger: Optional[PerformanceLogger] = None,
        optimizer: Optional[ModelOptimizer] = None,
        knowledge_store: Optional[Any] = None,
    ):
        self.perf_logger = perf_logger or get_performance_logger()
        self.optimizer = optimizer or get_model_optimizer()
        self.knowledge_store = knowledge_store
        self._events: List[FeedbackEvent] = []
        self._session_feedback: Dict[str, List[FeedbackEvent]] = {}
        self._callbacks: List[Callable[[FeedbackEvent], None]] = []
        
        logger.info("FeedbackLoop initialized")
    
    def register_callback(self, callback: Callable[[FeedbackEvent], None]) -> None:
        """Register a callback to be called on each feedback event."""
        self._callbacks.append(callback)
    
    def record_feedback(
        self,
        query_id: str,
        feedback_type: FeedbackType,
        *,
        value: Optional[float] = None,
        model_name: Optional[str] = None,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> FeedbackEvent:
        """Record a feedback event.
        
        Args:
            query_id: ID of the query this feedback is for
            feedback_type: Type of feedback
            value: Optional normalized value (0-1 for ratings)
            model_name: Model being evaluated (if applicable)
            session_id: Session ID for grouping
            user_id: User ID for personalization
            metadata: Additional metadata
            
        Returns:
            The created FeedbackEvent
        """
        event = FeedbackEvent(
            id=str(uuid.uuid4())[:12],
            query_id=query_id,
            feedback_type=feedback_type,
            value=value,
            model_name=model_name,
            session_id=session_id,
            user_id=user_id,
            metadata=metadata or {},
        )
        
        self._events.append(event)
        
        # Track by session
        if session_id:
            if session_id not in self._session_feedback:
                self._session_feedback[session_id] = []
            self._session_feedback[session_id].append(event)
        
        # Process the feedback
        self._process_feedback(event)
        
        # Notify callbacks
        for callback in self._callbacks:
            try:
                callback(event)
            except Exception as e:
                logger.error("Feedback callback error: %s", e)
        
        logger.info(
            "Recorded feedback: type=%s, query=%s, positive=%s",
            feedback_type.value, query_id, event.is_positive
        )
        
        return event
    
    def record_regeneration(
        self,
        query_id: str,
        *,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> FeedbackEvent:
        """Record a regeneration (implicit negative feedback).
        
        This is called when a user asks to regenerate a response.
        """
        # Mark in performance logger
        self.perf_logger.mark_regeneration(query_id)
        
        return self.record_feedback(
            query_id,
            FeedbackType.REGENERATE,
            session_id=session_id,
            user_id=user_id,
            metadata={"implicit": True},
        )
    
    def record_thumbs_up(
        self,
        query_id: str,
        *,
        model_name: Optional[str] = None,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> FeedbackEvent:
        """Record positive thumbs up feedback."""
        return self.record_feedback(
            query_id,
            FeedbackType.THUMBS_UP,
            value=1.0,
            model_name=model_name,
            session_id=session_id,
            user_id=user_id,
        )
    
    def record_thumbs_down(
        self,
        query_id: str,
        *,
        model_name: Optional[str] = None,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> FeedbackEvent:
        """Record negative thumbs down feedback."""
        return self.record_feedback(
            query_id,
            FeedbackType.THUMBS_DOWN,
            value=0.0,
            model_name=model_name,
            session_id=session_id,
            user_id=user_id,
        )
    
    def record_rating(
        self,
        query_id: str,
        rating: int,  # 1-5 stars
        *,
        model_name: Optional[str] = None,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> FeedbackEvent:
        """Record a star rating (1-5)."""
        # Normalize to 0-1
        normalized = (rating - 1) / 4
        
        return self.record_feedback(
            query_id,
            FeedbackType.RATING,
            value=normalized,
            model_name=model_name,
            session_id=session_id,
            user_id=user_id,
            metadata={"stars": rating},
        )
    
    def record_copy(
        self,
        query_id: str,
        *,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> FeedbackEvent:
        """Record that user copied the answer (implicit positive)."""
        return self.record_feedback(
            query_id,
            FeedbackType.COPY,
            value=0.8,
            session_id=session_id,
            user_id=user_id,
            metadata={"implicit": True},
        )
    
    def _process_feedback(self, event: FeedbackEvent) -> None:
        """Process feedback event and update learning systems."""
        # Update performance logger
        if event.is_positive:
            self.perf_logger.record_feedback(event.query_id, "positive")
        elif event.is_negative:
            self.perf_logger.record_feedback(event.query_id, "negative")
        
        # Update model optimizer weights
        if event.model_name:
            self.optimizer.update_weights_from_feedback(
                event.model_name,
                positive=event.is_positive,
            )
        
        # Store successful answer in knowledge base
        if event.is_positive and event.value is not None and event.value >= 0.8:
            self._store_successful_answer(event)
    
    def _store_successful_answer(self, event: FeedbackEvent) -> None:
        """Store a highly-rated answer in the knowledge base for reuse."""
        if not self.knowledge_store:
            return
        
        try:
            # Get the answer from the query record
            # This would integrate with the answer_store
            logger.debug(
                "Would store successful answer for query %s (score=%.2f)",
                event.query_id, event.value or 0
            )
        except Exception as e:
            logger.error("Failed to store successful answer: %s", e)
    
    def get_session_feedback(self, session_id: str) -> List[FeedbackEvent]:
        """Get all feedback for a session."""
        return self._session_feedback.get(session_id, [])
    
    def get_session_satisfaction(self, session_id: str) -> float:
        """Calculate overall satisfaction score for a session.
        
        Returns a 0-1 score based on feedback events.
        """
        events = self.get_session_feedback(session_id)
        if not events:
            return 0.5  # Neutral if no feedback
        
        positive = sum(1 for e in events if e.is_positive)
        negative = sum(1 for e in events if e.is_negative)
        total = positive + negative
        
        if total == 0:
            return 0.5
        
        return positive / total
    
    def get_feedback_stats(self, days: int = 30) -> Dict[str, Any]:
        """Get aggregated feedback statistics."""
        # Filter recent events
        cutoff = time.time() - (days * 24 * 3600)
        recent = [
            e for e in self._events
            if datetime.fromisoformat(e.created_at.replace('Z', '+00:00')).timestamp() > cutoff
        ]
        
        if not recent:
            return {
                "period_days": days,
                "total_events": 0,
                "satisfaction_rate": 0.5,
            }
        
        positive = sum(1 for e in recent if e.is_positive)
        negative = sum(1 for e in recent if e.is_negative)
        regenerations = sum(1 for e in recent if e.feedback_type == FeedbackType.REGENERATE)
        
        by_type = {}
        for e in recent:
            ft = e.feedback_type.value
            by_type[ft] = by_type.get(ft, 0) + 1
        
        return {
            "period_days": days,
            "total_events": len(recent),
            "positive_count": positive,
            "negative_count": negative,
            "regeneration_count": regenerations,
            "satisfaction_rate": positive / (positive + negative) if (positive + negative) > 0 else 0.5,
            "by_type": by_type,
        }
    
    def identify_problem_patterns(self, min_occurrences: int = 3) -> List[Dict[str, Any]]:
        """Identify patterns in queries that receive negative feedback.
        
        Returns patterns that might indicate systematic issues.
        """
        negative_events = [e for e in self._events if e.is_negative]
        
        # Group by model
        model_failures: Dict[str, int] = {}
        for e in negative_events:
            if e.model_name:
                model_failures[e.model_name] = model_failures.get(e.model_name, 0) + 1
        
        patterns = []
        
        # Models with high failure rates
        for model, count in model_failures.items():
            if count >= min_occurrences:
                patterns.append({
                    "type": "model_failure",
                    "model": model,
                    "count": count,
                    "recommendation": f"Consider reducing weight for {model} or investigating issues",
                })
        
        # High regeneration rate
        regenerations = sum(1 for e in self._events if e.feedback_type == FeedbackType.REGENERATE)
        total = len(self._events)
        if total > 0 and regenerations / total > 0.15:
            patterns.append({
                "type": "high_regeneration",
                "rate": regenerations / total,
                "count": regenerations,
                "recommendation": "Consider enabling quality boost or consensus for more queries",
            })
        
        return patterns


# Global instance
_feedback_loop: Optional[FeedbackLoop] = None


def get_feedback_loop() -> FeedbackLoop:
    """Get the global feedback loop instance."""
    global _feedback_loop
    if _feedback_loop is None:
        _feedback_loop = FeedbackLoop()
    return _feedback_loop
