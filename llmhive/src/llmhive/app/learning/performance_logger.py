"""Performance Logger for Continuous Learning.

This module tracks detailed performance metrics for each query, including:
- Which models contributed to each answer
- Latency per model
- Token usage per model
- Quality scores and verification results
- Domain classification

Data is stored in SQLite (local) or Firestore (production) for persistence.
"""
from __future__ import annotations

import json
import logging
import os
import sqlite3
import time
import uuid
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from typing import Any, Dict, Iterator, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ModelContribution:
    """A single model's contribution to a query response."""
    model_name: str
    provider: str
    latency_ms: float
    tokens_input: int = 0
    tokens_output: int = 0
    quality_score: Optional[float] = None
    was_selected: bool = False  # Whether this model's answer was used in final
    verification_passed: Optional[bool] = None
    task_type: Optional[str] = None  # e.g., "research", "analysis", "synthesis"
    error: Optional[str] = None
    
    @property
    def total_tokens(self) -> int:
        return self.tokens_input + self.tokens_output
    
    @property
    def success(self) -> bool:
        return self.error is None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "model_name": self.model_name,
            "provider": self.provider,
            "latency_ms": self.latency_ms,
            "tokens_input": self.tokens_input,
            "tokens_output": self.tokens_output,
            "quality_score": self.quality_score,
            "was_selected": self.was_selected,
            "verification_passed": self.verification_passed,
            "task_type": self.task_type,
            "error": self.error,
        }


@dataclass
class QueryPerformance:
    """Performance record for a complete query execution."""
    query_id: str
    query_hash: str  # For finding similar queries
    query_text: str
    query_domain: str  # e.g., "coding", "research", "general"
    query_complexity: str  # "simple", "moderate", "complex"
    
    # Timing
    start_time: float
    end_time: float
    total_latency_ms: float
    
    # Model contributions
    contributions: List[ModelContribution] = field(default_factory=list)
    
    # Final result
    final_answer_length: int = 0
    final_model: Optional[str] = None  # Primary model in final answer
    consensus_method: Optional[str] = None  # e.g., "fusion", "debate", "majority"
    
    # Quality indicators
    user_regenerated: bool = False  # Implicit negative feedback
    user_feedback: Optional[str] = None  # "positive", "negative", None
    verification_score: Optional[float] = None
    
    # Session context
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    
    # Metadata
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate of model contributions."""
        if not self.contributions:
            return 0.0
        successful = sum(1 for c in self.contributions if c.success)
        return successful / len(self.contributions)
    
    @property
    def total_tokens(self) -> int:
        """Total tokens used across all models."""
        return sum(c.total_tokens for c in self.contributions)
    
    @property
    def models_used(self) -> List[str]:
        """List of unique models used."""
        return list(set(c.model_name for c in self.contributions))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "query_id": self.query_id,
            "query_hash": self.query_hash,
            "query_text": self.query_text,
            "query_domain": self.query_domain,
            "query_complexity": self.query_complexity,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "total_latency_ms": self.total_latency_ms,
            "contributions": [c.to_dict() for c in self.contributions],
            "final_answer_length": self.final_answer_length,
            "final_model": self.final_model,
            "consensus_method": self.consensus_method,
            "user_regenerated": self.user_regenerated,
            "user_feedback": self.user_feedback,
            "verification_score": self.verification_score,
            "session_id": self.session_id,
            "user_id": self.user_id,
            "created_at": self.created_at,
            "total_tokens": self.total_tokens,
            "models_used": self.models_used,
        }


class SQLiteStorage:
    """SQLite-based storage for performance logs."""
    
    SCHEMA = """
    CREATE TABLE IF NOT EXISTS query_performance (
        query_id TEXT PRIMARY KEY,
        query_hash TEXT,
        query_text TEXT,
        query_domain TEXT,
        query_complexity TEXT,
        total_latency_ms REAL,
        total_tokens INTEGER,
        final_model TEXT,
        consensus_method TEXT,
        user_regenerated INTEGER,
        user_feedback TEXT,
        verification_score REAL,
        session_id TEXT,
        user_id TEXT,
        created_at TEXT,
        data JSON
    );
    
    CREATE INDEX IF NOT EXISTS idx_query_hash ON query_performance(query_hash);
    CREATE INDEX IF NOT EXISTS idx_domain ON query_performance(query_domain);
    CREATE INDEX IF NOT EXISTS idx_created_at ON query_performance(created_at);
    CREATE INDEX IF NOT EXISTS idx_user_id ON query_performance(user_id);
    
    CREATE TABLE IF NOT EXISTS model_contributions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        query_id TEXT,
        model_name TEXT,
        provider TEXT,
        latency_ms REAL,
        tokens_input INTEGER,
        tokens_output INTEGER,
        quality_score REAL,
        was_selected INTEGER,
        verification_passed INTEGER,
        task_type TEXT,
        error TEXT,
        created_at TEXT,
        FOREIGN KEY (query_id) REFERENCES query_performance(query_id)
    );
    
    CREATE INDEX IF NOT EXISTS idx_model_name ON model_contributions(model_name);
    CREATE INDEX IF NOT EXISTS idx_contributions_query ON model_contributions(query_id);
    """
    
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or os.getenv(
            "LEARNING_DB_PATH",
            str(Path.home() / ".llmhive" / "learning.db")
        )
        self._lock = RLock()
        self._ensure_db()
    
    def _ensure_db(self) -> None:
        """Ensure database and tables exist."""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        with self._get_connection() as conn:
            conn.executescript(self.SCHEMA)
    
    @contextmanager
    def _get_connection(self) -> Iterator[sqlite3.Connection]:
        """Get a database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def save_query_performance(self, perf: QueryPerformance) -> None:
        """Save a query performance record."""
        with self._lock:
            with self._get_connection() as conn:
                # Save main record
                conn.execute(
                    """
                    INSERT OR REPLACE INTO query_performance
                    (query_id, query_hash, query_text, query_domain, query_complexity,
                     total_latency_ms, total_tokens, final_model, consensus_method,
                     user_regenerated, user_feedback, verification_score,
                     session_id, user_id, created_at, data)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        perf.query_id, perf.query_hash, perf.query_text[:1000],
                        perf.query_domain, perf.query_complexity,
                        perf.total_latency_ms, perf.total_tokens,
                        perf.final_model, perf.consensus_method,
                        int(perf.user_regenerated), perf.user_feedback,
                        perf.verification_score, perf.session_id, perf.user_id,
                        perf.created_at, json.dumps(perf.to_dict())
                    )
                )
                
                # Delete existing contributions for this query
                conn.execute(
                    "DELETE FROM model_contributions WHERE query_id = ?",
                    (perf.query_id,)
                )
                
                # Save model contributions
                for contrib in perf.contributions:
                    conn.execute(
                        """
                        INSERT INTO model_contributions
                        (query_id, model_name, provider, latency_ms, tokens_input,
                         tokens_output, quality_score, was_selected, verification_passed,
                         task_type, error, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            perf.query_id, contrib.model_name, contrib.provider,
                            contrib.latency_ms, contrib.tokens_input, contrib.tokens_output,
                            contrib.quality_score, int(contrib.was_selected),
                            int(contrib.verification_passed) if contrib.verification_passed is not None else None,
                            contrib.task_type, contrib.error, perf.created_at
                        )
                    )
    
    def get_model_stats(
        self,
        model_name: str,
        domain: Optional[str] = None,
        days: int = 30,
    ) -> Dict[str, Any]:
        """Get aggregated stats for a model."""
        with self._get_connection() as conn:
            query = """
                SELECT
                    model_name,
                    COUNT(*) as total_queries,
                    AVG(latency_ms) as avg_latency_ms,
                    SUM(tokens_input + tokens_output) as total_tokens,
                    SUM(CASE WHEN was_selected = 1 THEN 1 ELSE 0 END) as times_selected,
                    SUM(CASE WHEN verification_passed = 1 THEN 1 ELSE 0 END) as verification_passes,
                    SUM(CASE WHEN error IS NULL THEN 1 ELSE 0 END) as successful_calls,
                    AVG(quality_score) as avg_quality
                FROM model_contributions mc
                JOIN query_performance qp ON mc.query_id = qp.query_id
                WHERE mc.model_name = ?
                  AND datetime(mc.created_at) > datetime('now', ?)
            """
            params: List[Any] = [model_name, f'-{days} days']
            
            if domain:
                query += " AND qp.query_domain = ?"
                params.append(domain)
            
            query += " GROUP BY model_name"
            
            row = conn.execute(query, params).fetchone()
            
            if not row:
                return {"model_name": model_name, "total_queries": 0}
            
            return dict(row)
    
    def get_all_model_stats(self, days: int = 30) -> List[Dict[str, Any]]:
        """Get stats for all models."""
        with self._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT
                    model_name,
                    COUNT(*) as total_queries,
                    AVG(latency_ms) as avg_latency_ms,
                    SUM(tokens_input + tokens_output) as total_tokens,
                    SUM(CASE WHEN was_selected = 1 THEN 1 ELSE 0 END) as times_selected,
                    SUM(CASE WHEN verification_passed = 1 THEN 1 ELSE 0 END) as verification_passes,
                    SUM(CASE WHEN error IS NULL THEN 1 ELSE 0 END) as successful_calls,
                    AVG(quality_score) as avg_quality
                FROM model_contributions mc
                JOIN query_performance qp ON mc.query_id = qp.query_id
                WHERE datetime(mc.created_at) > datetime('now', ?)
                GROUP BY model_name
                ORDER BY total_queries DESC
                """,
                (f'-{days} days',)
            ).fetchall()
            
            return [dict(row) for row in rows]
    
    def get_domain_stats(self, domain: str, days: int = 30) -> Dict[str, Any]:
        """Get stats for a specific domain."""
        with self._get_connection() as conn:
            row = conn.execute(
                """
                SELECT
                    query_domain,
                    COUNT(*) as total_queries,
                    AVG(total_latency_ms) as avg_latency_ms,
                    AVG(total_tokens) as avg_tokens,
                    SUM(CASE WHEN user_regenerated = 0 THEN 1 ELSE 0 END) as successful_queries,
                    AVG(verification_score) as avg_verification
                FROM query_performance
                WHERE query_domain = ?
                  AND datetime(created_at) > datetime('now', ?)
                GROUP BY query_domain
                """,
                (domain, f'-{days} days')
            ).fetchone()
            
            return dict(row) if row else {"query_domain": domain, "total_queries": 0}
    
    def get_regeneration_rate(self, days: int = 30) -> float:
        """Get the rate of regenerations (implicit negative feedback)."""
        with self._get_connection() as conn:
            row = conn.execute(
                """
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN user_regenerated = 1 THEN 1 ELSE 0 END) as regenerated
                FROM query_performance
                WHERE datetime(created_at) > datetime('now', ?)
                """,
                (f'-{days} days',)
            ).fetchone()
            
            if not row or row['total'] == 0:
                return 0.0
            return row['regenerated'] / row['total']


class PerformanceLogger:
    """Main performance logger for continuous learning.
    
    Tracks model contributions, latencies, and quality metrics for each query.
    Data is persisted to SQLite locally or Firestore in production.
    """
    
    def __init__(self, storage: Optional[SQLiteStorage] = None):
        self.storage = storage or SQLiteStorage()
        self._current_query: Optional[QueryPerformance] = None
        self._lock = RLock()
        logger.info("PerformanceLogger initialized with storage at %s", self.storage.db_path)
    
    def start_query(
        self,
        query_text: str,
        *,
        domain: str = "general",
        complexity: str = "moderate",
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> str:
        """Start tracking a new query.
        
        Returns the query_id for reference.
        """
        query_id = str(uuid.uuid4())[:12]
        query_hash = self._hash_query(query_text)
        
        with self._lock:
            self._current_query = QueryPerformance(
                query_id=query_id,
                query_hash=query_hash,
                query_text=query_text,
                query_domain=domain,
                query_complexity=complexity,
                start_time=time.time(),
                end_time=0,
                total_latency_ms=0,
                session_id=session_id,
                user_id=user_id,
            )
        
        logger.debug(
            "Started tracking query %s (domain=%s, complexity=%s)",
            query_id, domain, complexity
        )
        return query_id
    
    def record_contribution(
        self,
        model_name: str,
        provider: str,
        latency_ms: float,
        *,
        tokens_input: int = 0,
        tokens_output: int = 0,
        quality_score: Optional[float] = None,
        was_selected: bool = False,
        verification_passed: Optional[bool] = None,
        task_type: Optional[str] = None,
        error: Optional[str] = None,
    ) -> None:
        """Record a model's contribution to the current query."""
        if not self._current_query:
            logger.warning("No active query to record contribution for")
            return
        
        contribution = ModelContribution(
            model_name=model_name,
            provider=provider,
            latency_ms=latency_ms,
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            quality_score=quality_score,
            was_selected=was_selected,
            verification_passed=verification_passed,
            task_type=task_type,
            error=error,
        )
        
        with self._lock:
            self._current_query.contributions.append(contribution)
        
        logger.debug(
            "Recorded contribution from %s: %.0fms, %d tokens, selected=%s",
            model_name, latency_ms, contribution.total_tokens, was_selected
        )
    
    def end_query(
        self,
        *,
        final_answer_length: int = 0,
        final_model: Optional[str] = None,
        consensus_method: Optional[str] = None,
        verification_score: Optional[float] = None,
    ) -> Optional[QueryPerformance]:
        """End tracking for the current query and persist the data.
        
        Returns the completed QueryPerformance record.
        """
        if not self._current_query:
            logger.warning("No active query to end")
            return None
        
        with self._lock:
            self._current_query.end_time = time.time()
            self._current_query.total_latency_ms = (
                self._current_query.end_time - self._current_query.start_time
            ) * 1000
            self._current_query.final_answer_length = final_answer_length
            self._current_query.final_model = final_model
            self._current_query.consensus_method = consensus_method
            self._current_query.verification_score = verification_score
            
            result = self._current_query
            self._current_query = None
        
        # Persist to storage
        try:
            self.storage.save_query_performance(result)
            logger.info(
                "Saved query %s: %.0fms, %d models, %d tokens",
                result.query_id, result.total_latency_ms,
                len(result.contributions), result.total_tokens
            )
        except Exception as e:
            logger.error("Failed to persist query performance: %s", e)
        
        return result
    
    def mark_regeneration(self, query_id: str) -> None:
        """Mark a query as regenerated (implicit negative feedback)."""
        try:
            with self.storage._get_connection() as conn:
                conn.execute(
                    "UPDATE query_performance SET user_regenerated = 1 WHERE query_id = ?",
                    (query_id,)
                )
            logger.info("Marked query %s as regenerated", query_id)
        except Exception as e:
            logger.error("Failed to mark regeneration: %s", e)
    
    def record_feedback(self, query_id: str, feedback: str) -> None:
        """Record explicit user feedback for a query."""
        try:
            with self.storage._get_connection() as conn:
                conn.execute(
                    "UPDATE query_performance SET user_feedback = ? WHERE query_id = ?",
                    (feedback, query_id)
                )
            logger.info("Recorded feedback '%s' for query %s", feedback, query_id)
        except Exception as e:
            logger.error("Failed to record feedback: %s", e)
    
    def get_model_stats(
        self,
        model_name: str,
        domain: Optional[str] = None,
        days: int = 30,
    ) -> Dict[str, Any]:
        """Get aggregated stats for a model."""
        return self.storage.get_model_stats(model_name, domain, days)
    
    def get_all_model_stats(self, days: int = 30) -> List[Dict[str, Any]]:
        """Get stats for all models."""
        return self.storage.get_all_model_stats(days)
    
    def get_domain_stats(self, domain: str, days: int = 30) -> Dict[str, Any]:
        """Get stats for a specific domain."""
        return self.storage.get_domain_stats(domain, days)
    
    def get_regeneration_rate(self, days: int = 30) -> float:
        """Get the regeneration rate (implicit negative feedback rate)."""
        return self.storage.get_regeneration_rate(days)
    
    def _hash_query(self, query: str) -> str:
        """Create a hash of the query for similarity matching."""
        import hashlib
        # Normalize query for hashing
        normalized = query.lower().strip()
        return hashlib.md5(normalized.encode()).hexdigest()[:16]


# Global instance
_performance_logger: Optional[PerformanceLogger] = None


def get_performance_logger() -> PerformanceLogger:
    """Get the global performance logger instance."""
    global _performance_logger
    if _performance_logger is None:
        _performance_logger = PerformanceLogger()
    return _performance_logger
