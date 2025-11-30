"""Feedback Collection for RLHF.

This module handles:
- User feedback collection (ratings, thumbs up/down)
- Feedback storage and retrieval
- Training data preparation

Usage:
    collector = get_feedback_collector()
    
    # Record feedback
    await collector.record_feedback(
        query="What is AI?",
        answer="AI is...",
        rating=5,
        user_id="user123",
    )
    
    # Get training data
    pairs = await collector.get_preference_pairs(min_count=100)
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import sqlite3
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ==============================================================================
# Types
# ==============================================================================

class FeedbackType(str, Enum):
    """Types of feedback."""
    THUMBS_UP = "thumbs_up"
    THUMBS_DOWN = "thumbs_down"
    RATING = "rating"
    PREFERENCE = "preference"  # A vs B comparison
    CORRECTION = "correction"  # User provided correction
    FLAG = "flag"  # Flagged as problematic


@dataclass(slots=True)
class FeedbackEntry:
    """A single feedback entry."""
    id: str
    query: str
    context: Optional[str]
    answer: str
    feedback_type: FeedbackType
    rating: float  # Normalized 0-1
    user_id: Optional[str]
    session_id: Optional[str]
    model_used: str
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Optional fields for preference learning
    alternative_answer: Optional[str] = None
    is_preferred: Optional[bool] = None
    correction_text: Optional[str] = None


@dataclass(slots=True)
class PreferencePair:
    """A preference pair for training."""
    query: str
    context: Optional[str]
    chosen: str  # Preferred answer
    rejected: str  # Non-preferred answer
    chosen_rating: float
    rejected_rating: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "context": self.context or "",
            "chosen": self.chosen,
            "rejected": self.rejected,
        }


@dataclass(slots=True)
class FeedbackStats:
    """Statistics about collected feedback."""
    total_entries: int
    positive_count: int
    negative_count: int
    average_rating: float
    unique_users: int
    unique_queries: int
    by_model: Dict[str, int]
    by_type: Dict[str, int]


# ==============================================================================
# Feedback Collector
# ==============================================================================

class FeedbackCollector:
    """Collects and manages user feedback for RLHF.
    
    Features:
    - Multiple feedback types (ratings, thumbs, preferences)
    - SQLite persistence
    - Training data generation
    - Statistics and analytics
    
    Usage:
        collector = FeedbackCollector(db_path="./data/feedback.db")
        
        # Record thumbs up
        await collector.record_feedback(
            query="What is ML?",
            answer="ML is...",
            feedback_type=FeedbackType.THUMBS_UP,
            model_used="gpt-4o",
        )
        
        # Get preference pairs for training
        pairs = await collector.get_preference_pairs()
    """
    
    def __init__(
        self,
        db_path: Optional[str] = None,
        min_rating_for_positive: float = 0.7,
    ):
        """
        Initialize feedback collector.
        
        Args:
            db_path: Path to SQLite database
            min_rating_for_positive: Minimum rating to consider as positive
        """
        self.db_path = db_path or os.getenv(
            "LLMHIVE_FEEDBACK_DB",
            "./data/feedback.db"
        )
        self.min_rating_for_positive = min_rating_for_positive
        
        self._ensure_db()
    
    def _ensure_db(self) -> None:
        """Ensure database and tables exist."""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS feedback (
                id TEXT PRIMARY KEY,
                query TEXT NOT NULL,
                context TEXT,
                answer TEXT NOT NULL,
                feedback_type TEXT NOT NULL,
                rating REAL NOT NULL,
                user_id TEXT,
                session_id TEXT,
                model_used TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                metadata TEXT,
                alternative_answer TEXT,
                is_preferred INTEGER,
                correction_text TEXT
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_feedback_rating 
            ON feedback(rating)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_feedback_model 
            ON feedback(model_used)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_feedback_user 
            ON feedback(user_id)
        """)
        
        conn.commit()
        conn.close()
        
        logger.info("Feedback database initialized: %s", self.db_path)
    
    def _generate_id(self, query: str, answer: str, timestamp: float) -> str:
        """Generate unique ID for feedback entry."""
        content = f"{query}|{answer}|{timestamp}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    async def record_feedback(
        self,
        query: str,
        answer: str,
        feedback_type: FeedbackType = FeedbackType.RATING,
        rating: Optional[float] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        model_used: str = "unknown",
        context: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        alternative_answer: Optional[str] = None,
        is_preferred: Optional[bool] = None,
        correction_text: Optional[str] = None,
    ) -> FeedbackEntry:
        """
        Record user feedback.
        
        Args:
            query: The user's question
            answer: The answer that was given
            feedback_type: Type of feedback
            rating: Rating value (0-1 or 1-5, will be normalized)
            user_id: User identifier
            session_id: Session identifier
            model_used: Model that generated the answer
            context: Conversation context
            metadata: Additional metadata
            alternative_answer: For preference feedback
            is_preferred: Whether this answer was preferred
            correction_text: User's correction
            
        Returns:
            FeedbackEntry that was recorded
        """
        timestamp = datetime.now(timezone.utc)
        
        # Normalize rating
        if rating is None:
            if feedback_type == FeedbackType.THUMBS_UP:
                rating = 1.0
            elif feedback_type == FeedbackType.THUMBS_DOWN:
                rating = 0.0
            else:
                rating = 0.5
        elif rating > 1.0:
            # Assume 1-5 scale, normalize to 0-1
            rating = (rating - 1) / 4.0
        
        entry_id = self._generate_id(query, answer, timestamp.timestamp())
        
        entry = FeedbackEntry(
            id=entry_id,
            query=query,
            context=context,
            answer=answer,
            feedback_type=feedback_type,
            rating=rating,
            user_id=user_id,
            session_id=session_id,
            model_used=model_used,
            timestamp=timestamp,
            metadata=metadata or {},
            alternative_answer=alternative_answer,
            is_preferred=is_preferred,
            correction_text=correction_text,
        )
        
        # Store in database
        await self._store_entry(entry)
        
        logger.info(
            "Recorded feedback: type=%s rating=%.2f model=%s",
            feedback_type.value, rating, model_used,
        )
        
        return entry
    
    async def _store_entry(self, entry: FeedbackEntry) -> None:
        """Store entry in database."""
        def _insert():
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO feedback 
                (id, query, context, answer, feedback_type, rating, user_id,
                 session_id, model_used, timestamp, metadata, alternative_answer,
                 is_preferred, correction_text)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                entry.id,
                entry.query,
                entry.context,
                entry.answer,
                entry.feedback_type.value,
                entry.rating,
                entry.user_id,
                entry.session_id,
                entry.model_used,
                entry.timestamp.isoformat(),
                json.dumps(entry.metadata),
                entry.alternative_answer,
                1 if entry.is_preferred else (0 if entry.is_preferred is False else None),
                entry.correction_text,
            ))
            
            conn.commit()
            conn.close()
        
        await asyncio.to_thread(_insert)
    
    async def get_feedback(
        self,
        limit: int = 1000,
        min_rating: Optional[float] = None,
        max_rating: Optional[float] = None,
        model_used: Optional[str] = None,
        feedback_type: Optional[FeedbackType] = None,
    ) -> List[FeedbackEntry]:
        """
        Get feedback entries with optional filters.
        
        Args:
            limit: Maximum entries to return
            min_rating: Minimum rating filter
            max_rating: Maximum rating filter
            model_used: Filter by model
            feedback_type: Filter by feedback type
            
        Returns:
            List of FeedbackEntry
        """
        def _query():
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            sql = "SELECT * FROM feedback WHERE 1=1"
            params = []
            
            if min_rating is not None:
                sql += " AND rating >= ?"
                params.append(min_rating)
            
            if max_rating is not None:
                sql += " AND rating <= ?"
                params.append(max_rating)
            
            if model_used:
                sql += " AND model_used = ?"
                params.append(model_used)
            
            if feedback_type:
                sql += " AND feedback_type = ?"
                params.append(feedback_type.value)
            
            sql += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)
            
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            conn.close()
            
            return [dict(row) for row in rows]
        
        rows = await asyncio.to_thread(_query)
        
        return [
            FeedbackEntry(
                id=row["id"],
                query=row["query"],
                context=row["context"],
                answer=row["answer"],
                feedback_type=FeedbackType(row["feedback_type"]),
                rating=row["rating"],
                user_id=row["user_id"],
                session_id=row["session_id"],
                model_used=row["model_used"],
                timestamp=datetime.fromisoformat(row["timestamp"]),
                metadata=json.loads(row["metadata"]) if row["metadata"] else {},
                alternative_answer=row["alternative_answer"],
                is_preferred=bool(row["is_preferred"]) if row["is_preferred"] is not None else None,
                correction_text=row["correction_text"],
            )
            for row in rows
        ]
    
    async def get_preference_pairs(
        self,
        min_rating_diff: float = 0.3,
        limit: int = 1000,
    ) -> List[PreferencePair]:
        """
        Get preference pairs for training.
        
        Creates pairs where one answer is clearly preferred over another.
        Uses the same query with different ratings.
        
        Args:
            min_rating_diff: Minimum rating difference for a valid pair
            limit: Maximum pairs to return
            
        Returns:
            List of PreferencePair for training
        """
        def _query():
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Get all feedback grouped by query hash
            cursor.execute("""
                SELECT query, context, answer, rating 
                FROM feedback 
                ORDER BY query, rating DESC
            """)
            
            rows = cursor.fetchall()
            conn.close()
            return [dict(row) for row in rows]
        
        rows = await asyncio.to_thread(_query)
        
        # Group by query
        by_query: Dict[str, List[Dict]] = {}
        for row in rows:
            query = row["query"]
            if query not in by_query:
                by_query[query] = []
            by_query[query].append(row)
        
        # Create preference pairs
        pairs: List[PreferencePair] = []
        
        for query, entries in by_query.items():
            if len(entries) < 2:
                continue
            
            # Sort by rating (descending)
            entries.sort(key=lambda x: x["rating"], reverse=True)
            
            # Create pairs from high-rated vs low-rated
            for i, high in enumerate(entries):
                for low in entries[i+1:]:
                    if high["rating"] - low["rating"] >= min_rating_diff:
                        pairs.append(PreferencePair(
                            query=query,
                            context=high.get("context") or low.get("context"),
                            chosen=high["answer"],
                            rejected=low["answer"],
                            chosen_rating=high["rating"],
                            rejected_rating=low["rating"],
                        ))
                        
                        if len(pairs) >= limit:
                            return pairs
        
        logger.info("Generated %d preference pairs", len(pairs))
        return pairs
    
    async def get_positive_examples(
        self,
        min_rating: Optional[float] = None,
        limit: int = 500,
    ) -> List[FeedbackEntry]:
        """Get high-rated examples for fine-tuning."""
        threshold = min_rating or self.min_rating_for_positive
        return await self.get_feedback(
            min_rating=threshold,
            limit=limit,
        )
    
    async def get_corrections(self, limit: int = 100) -> List[FeedbackEntry]:
        """Get user-corrected answers."""
        return await self.get_feedback(
            feedback_type=FeedbackType.CORRECTION,
            limit=limit,
        )
    
    async def get_stats(self) -> FeedbackStats:
        """Get feedback statistics."""
        def _query():
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Total entries
            cursor.execute("SELECT COUNT(*) FROM feedback")
            total = cursor.fetchone()[0]
            
            # Positive/negative
            cursor.execute(
                "SELECT COUNT(*) FROM feedback WHERE rating >= ?",
                (0.5,)
            )
            positive = cursor.fetchone()[0]
            
            # Average rating
            cursor.execute("SELECT AVG(rating) FROM feedback")
            avg_rating = cursor.fetchone()[0] or 0.0
            
            # Unique users
            cursor.execute("SELECT COUNT(DISTINCT user_id) FROM feedback WHERE user_id IS NOT NULL")
            unique_users = cursor.fetchone()[0]
            
            # Unique queries
            cursor.execute("SELECT COUNT(DISTINCT query) FROM feedback")
            unique_queries = cursor.fetchone()[0]
            
            # By model
            cursor.execute("""
                SELECT model_used, COUNT(*) as count 
                FROM feedback 
                GROUP BY model_used
            """)
            by_model = {row[0]: row[1] for row in cursor.fetchall()}
            
            # By type
            cursor.execute("""
                SELECT feedback_type, COUNT(*) as count 
                FROM feedback 
                GROUP BY feedback_type
            """)
            by_type = {row[0]: row[1] for row in cursor.fetchall()}
            
            conn.close()
            
            return {
                "total": total,
                "positive": positive,
                "avg_rating": avg_rating,
                "unique_users": unique_users,
                "unique_queries": unique_queries,
                "by_model": by_model,
                "by_type": by_type,
            }
        
        stats = await asyncio.to_thread(_query)
        
        return FeedbackStats(
            total_entries=stats["total"],
            positive_count=stats["positive"],
            negative_count=stats["total"] - stats["positive"],
            average_rating=stats["avg_rating"],
            unique_users=stats["unique_users"],
            unique_queries=stats["unique_queries"],
            by_model=stats["by_model"],
            by_type=stats["by_type"],
        )
    
    async def export_training_data(
        self,
        output_path: str,
        format: str = "jsonl",
    ) -> int:
        """
        Export training data to file.
        
        Args:
            output_path: Output file path
            format: Output format (jsonl, csv)
            
        Returns:
            Number of entries exported
        """
        entries = await self.get_feedback(limit=100000)
        
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        if format == "jsonl":
            with open(output_path, "w") as f:
                for entry in entries:
                    data = {
                        "query": entry.query,
                        "context": entry.context or "",
                        "answer": entry.answer,
                        "rating": entry.rating,
                        "model": entry.model_used,
                        "is_good": entry.rating >= self.min_rating_for_positive,
                    }
                    f.write(json.dumps(data) + "\n")
        
        elif format == "csv":
            import csv
            with open(output_path, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["query", "answer", "rating", "model", "is_good"])
                for entry in entries:
                    writer.writerow([
                        entry.query,
                        entry.answer,
                        entry.rating,
                        entry.model_used,
                        entry.rating >= self.min_rating_for_positive,
                    ])
        
        logger.info("Exported %d entries to %s", len(entries), output_path)
        return len(entries)


# ==============================================================================
# Global Instance
# ==============================================================================

_feedback_collector: Optional[FeedbackCollector] = None


def get_feedback_collector() -> FeedbackCollector:
    """Get or create global feedback collector."""
    global _feedback_collector
    if _feedback_collector is None:
        _feedback_collector = FeedbackCollector()
    return _feedback_collector


# ==============================================================================
# FastAPI Integration
# ==============================================================================

def setup_feedback_endpoints(app):
    """Setup feedback API endpoints."""
    from fastapi import HTTPException
    from pydantic import BaseModel
    
    class FeedbackRequest(BaseModel):
        query: str
        answer: str
        feedback_type: str = "rating"
        rating: Optional[float] = None
        model_used: str = "unknown"
        context: Optional[str] = None
        correction_text: Optional[str] = None
    
    @app.post("/api/feedback")
    async def submit_feedback(request: FeedbackRequest):
        """Submit feedback on an answer."""
        collector = get_feedback_collector()
        
        try:
            fb_type = FeedbackType(request.feedback_type)
        except ValueError:
            fb_type = FeedbackType.RATING
        
        entry = await collector.record_feedback(
            query=request.query,
            answer=request.answer,
            feedback_type=fb_type,
            rating=request.rating,
            model_used=request.model_used,
            context=request.context,
            correction_text=request.correction_text,
        )
        
        return {"status": "recorded", "id": entry.id}
    
    @app.get("/api/feedback/stats")
    async def get_feedback_stats():
        """Get feedback statistics."""
        collector = get_feedback_collector()
        stats = await collector.get_stats()
        
        return {
            "total_entries": stats.total_entries,
            "positive_count": stats.positive_count,
            "negative_count": stats.negative_count,
            "average_rating": round(stats.average_rating, 3),
            "unique_users": stats.unique_users,
            "unique_queries": stats.unique_queries,
            "by_model": stats.by_model,
            "by_type": stats.by_type,
        }
    
    logger.info("Feedback endpoints registered")

