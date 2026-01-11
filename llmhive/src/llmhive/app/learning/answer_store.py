"""Answer Store for Continuous Learning.

This module stores successful answers for reuse on similar future queries:
- Caches high-quality answers with their queries
- Enables semantic search for similar past queries
- Integrates with Pinecone for vector similarity search
- Falls back to SQLite for local-only deployments
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import sqlite3
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from typing import Any, Dict, Iterator, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Try to import Pinecone
try:
    from pinecone import Pinecone
    PINECONE_AVAILABLE = True
except ImportError:
    PINECONE_AVAILABLE = False
    Pinecone = None
    logger.debug("Pinecone not available - using SQLite fallback for answer store")


@dataclass
class StoredAnswer:
    """A stored answer for potential reuse."""
    id: str
    query_hash: str
    query_text: str
    answer_text: str
    
    # Quality indicators
    quality_score: float  # 0-1
    feedback_score: Optional[float] = None
    times_reused: int = 0
    
    # Context
    domain: str = "general"
    complexity: str = "moderate"
    models_used: List[str] = field(default_factory=list)
    consensus_method: Optional[str] = None
    
    # Metadata
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_reused_at: Optional[str] = None
    
    @property
    def relevance_score(self) -> float:
        """Calculate relevance score for ranking."""
        base = self.quality_score
        if self.feedback_score is not None:
            base = (base + self.feedback_score) / 2
        
        # Boost for successful reuse
        reuse_bonus = min(self.times_reused * 0.05, 0.2)
        
        return min(base + reuse_bonus, 1.0)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "query_hash": self.query_hash,
            "query_text": self.query_text,
            "answer_text": self.answer_text,
            "quality_score": self.quality_score,
            "feedback_score": self.feedback_score,
            "times_reused": self.times_reused,
            "domain": self.domain,
            "complexity": self.complexity,
            "models_used": self.models_used,
            "consensus_method": self.consensus_method,
            "session_id": self.session_id,
            "user_id": self.user_id,
            "created_at": self.created_at,
            "last_reused_at": self.last_reused_at,
            "relevance_score": self.relevance_score,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StoredAnswer":
        return cls(
            id=data["id"],
            query_hash=data["query_hash"],
            query_text=data["query_text"],
            answer_text=data["answer_text"],
            quality_score=data.get("quality_score", 0.5),
            feedback_score=data.get("feedback_score"),
            times_reused=data.get("times_reused", 0),
            domain=data.get("domain", "general"),
            complexity=data.get("complexity", "moderate"),
            models_used=data.get("models_used", []),
            consensus_method=data.get("consensus_method"),
            session_id=data.get("session_id"),
            user_id=data.get("user_id"),
            created_at=data.get("created_at", datetime.now(timezone.utc).isoformat()),
            last_reused_at=data.get("last_reused_at"),
        )


class SQLiteAnswerStore:
    """SQLite-based answer storage for local deployments."""
    
    SCHEMA = """
    CREATE TABLE IF NOT EXISTS stored_answers (
        id TEXT PRIMARY KEY,
        query_hash TEXT,
        query_text TEXT,
        answer_text TEXT,
        quality_score REAL,
        feedback_score REAL,
        times_reused INTEGER DEFAULT 0,
        domain TEXT,
        complexity TEXT,
        models_used TEXT,
        consensus_method TEXT,
        session_id TEXT,
        user_id TEXT,
        created_at TEXT,
        last_reused_at TEXT
    );
    
    CREATE INDEX IF NOT EXISTS idx_query_hash ON stored_answers(query_hash);
    CREATE INDEX IF NOT EXISTS idx_domain ON stored_answers(domain);
    CREATE INDEX IF NOT EXISTS idx_quality ON stored_answers(quality_score DESC);
    CREATE INDEX IF NOT EXISTS idx_created_at ON stored_answers(created_at DESC);
    
    -- Simple text search using FTS5 (if available)
    CREATE VIRTUAL TABLE IF NOT EXISTS answer_fts USING fts5(
        id,
        query_text,
        answer_text,
        content=stored_answers,
        content_rowid=rowid
    );
    """
    
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or os.getenv(
            "ANSWER_STORE_PATH",
            str(Path.home() / ".llmhive" / "answers.db")
        )
        self._lock = RLock()
        self._ensure_db()
    
    def _ensure_db(self) -> None:
        """Ensure database and tables exist."""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        with self._get_connection() as conn:
            try:
                conn.executescript(self.SCHEMA)
            except sqlite3.OperationalError as e:
                # FTS5 might not be available, create without it
                if "fts5" in str(e).lower():
                    logger.warning("FTS5 not available, creating basic tables only")
                    conn.execute("""
                        CREATE TABLE IF NOT EXISTS stored_answers (
                            id TEXT PRIMARY KEY,
                            query_hash TEXT,
                            query_text TEXT,
                            answer_text TEXT,
                            quality_score REAL,
                            feedback_score REAL,
                            times_reused INTEGER DEFAULT 0,
                            domain TEXT,
                            complexity TEXT,
                            models_used TEXT,
                            consensus_method TEXT,
                            session_id TEXT,
                            user_id TEXT,
                            created_at TEXT,
                            last_reused_at TEXT
                        )
                    """)
                else:
                    raise
    
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
    
    def store(self, answer: StoredAnswer) -> None:
        """Store an answer."""
        with self._lock:
            with self._get_connection() as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO stored_answers
                    (id, query_hash, query_text, answer_text, quality_score,
                     feedback_score, times_reused, domain, complexity, models_used,
                     consensus_method, session_id, user_id, created_at, last_reused_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        answer.id, answer.query_hash, answer.query_text,
                        answer.answer_text, answer.quality_score,
                        answer.feedback_score, answer.times_reused,
                        answer.domain, answer.complexity,
                        json.dumps(answer.models_used), answer.consensus_method,
                        answer.session_id, answer.user_id,
                        answer.created_at, answer.last_reused_at
                    )
                )
    
    def find_by_hash(self, query_hash: str, limit: int = 5) -> List[StoredAnswer]:
        """Find answers by exact query hash."""
        with self._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT * FROM stored_answers
                WHERE query_hash = ?
                ORDER BY quality_score DESC
                LIMIT ?
                """,
                (query_hash, limit)
            ).fetchall()
            
            return [self._row_to_answer(row) for row in rows]
    
    def search(
        self,
        query: str,
        domain: Optional[str] = None,
        min_quality: float = 0.5,
        limit: int = 5,
    ) -> List[Tuple[StoredAnswer, float]]:
        """Search for similar answers.
        
        Returns list of (answer, similarity_score) tuples.
        """
        with self._get_connection() as conn:
            # First try exact hash match
            query_hash = self._hash_query(query)
            exact_matches = self.find_by_hash(query_hash, limit=1)
            
            if exact_matches:
                # Found exact match
                return [(exact_matches[0], 1.0)]
            
            # Fall back to keyword search
            keywords = query.lower().split()[:5]  # Top 5 keywords
            
            conditions = ["quality_score >= ?"]
            params: List[Any] = [min_quality]
            
            if domain:
                conditions.append("domain = ?")
                params.append(domain)
            
            if keywords:
                keyword_conditions = " OR ".join(
                    "query_text LIKE ?" for _ in keywords
                )
                conditions.append(f"({keyword_conditions})")
                params.extend([f"%{kw}%" for kw in keywords])
            
            where_clause = " AND ".join(conditions)
            
            rows = conn.execute(
                f"""
                SELECT * FROM stored_answers
                WHERE {where_clause}
                ORDER BY quality_score DESC, times_reused DESC
                LIMIT ?
                """,
                params + [limit]
            ).fetchall()
            
            results = []
            for row in rows:
                answer = self._row_to_answer(row)
                # Calculate simple similarity score based on keyword overlap
                score = self._calculate_similarity(query, answer.query_text)
                results.append((answer, score))
            
            # Sort by similarity
            results.sort(key=lambda x: x[1], reverse=True)
            return results
    
    def mark_reused(self, answer_id: str) -> None:
        """Mark an answer as reused."""
        with self._get_connection() as conn:
            conn.execute(
                """
                UPDATE stored_answers
                SET times_reused = times_reused + 1,
                    last_reused_at = ?
                WHERE id = ?
                """,
                (datetime.now(timezone.utc).isoformat(), answer_id)
            )
    
    def update_feedback(self, answer_id: str, feedback_score: float) -> None:
        """Update the feedback score for an answer."""
        with self._get_connection() as conn:
            conn.execute(
                """
                UPDATE stored_answers
                SET feedback_score = ?
                WHERE id = ?
                """,
                (feedback_score, answer_id)
            )
    
    def get_stats(self) -> Dict[str, Any]:
        """Get storage statistics."""
        with self._get_connection() as conn:
            row = conn.execute(
                """
                SELECT
                    COUNT(*) as total_answers,
                    AVG(quality_score) as avg_quality,
                    SUM(times_reused) as total_reuses,
                    AVG(times_reused) as avg_reuses,
                    COUNT(DISTINCT domain) as unique_domains
                FROM stored_answers
                """
            ).fetchone()
            
            return dict(row) if row else {}
    
    def _row_to_answer(self, row: sqlite3.Row) -> StoredAnswer:
        """Convert a database row to StoredAnswer."""
        models_used = json.loads(row["models_used"]) if row["models_used"] else []
        
        return StoredAnswer(
            id=row["id"],
            query_hash=row["query_hash"],
            query_text=row["query_text"],
            answer_text=row["answer_text"],
            quality_score=row["quality_score"] or 0.5,
            feedback_score=row["feedback_score"],
            times_reused=row["times_reused"] or 0,
            domain=row["domain"] or "general",
            complexity=row["complexity"] or "moderate",
            models_used=models_used,
            consensus_method=row["consensus_method"],
            session_id=row["session_id"],
            user_id=row["user_id"],
            created_at=row["created_at"],
            last_reused_at=row["last_reused_at"],
        )
    
    def _hash_query(self, query: str) -> str:
        """Create a hash of the query."""
        normalized = query.lower().strip()
        return hashlib.md5(normalized.encode()).hexdigest()[:16]
    
    def _calculate_similarity(self, query1: str, query2: str) -> float:
        """Calculate simple word overlap similarity."""
        words1 = set(query1.lower().split())
        words2 = set(query2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1 & words2
        union = words1 | words2
        
        return len(intersection) / len(union) if union else 0.0


class PineconeAnswerStore:
    """Pinecone-based answer storage for semantic search.
    
    Uses the ORCHESTRATOR_KB index with a dedicated namespace for answer caching.
    This avoids needing a separate index while maintaining isolation.
    """
    
    # Reuse orchestrator-kb index with a dedicated namespace
    INDEX_NAME = "llmhive-orchestrator-kb"  # Changed from llmhive-answer-cache
    NAMESPACE = "answer_cache"  # Dedicated namespace for answer caching
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("PINECONE_API_KEY")
        self.pc: Optional[Pinecone] = None
        self.index = None
        self._initialized = False
        
        if PINECONE_AVAILABLE and self.api_key:
            self._initialize_pinecone()
    
    def _initialize_pinecone(self) -> None:
        """Initialize Pinecone via registry (host-based) or direct connection."""
        # Try registry-based connection first (supports host-based connections)
        try:
            from ..knowledge.pinecone_registry import get_pinecone_registry, IndexKind
            
            registry = get_pinecone_registry()
            if registry.is_available:
                # Use ANSWER_CACHE kind which maps to ORCHESTRATOR_KB host
                self.index = registry.get_index(IndexKind.ANSWER_CACHE)
                if self.index:
                    self._initialized = True
                    logger.info("Pinecone answer store initialized via registry (host-based)")
                    return
        except ImportError:
            logger.debug("Pinecone registry not available, using direct connection")
        except Exception as e:
            logger.warning("Registry connection failed: %s, falling back to direct", e)
        
        # Fallback: Direct connection (for backward compatibility)
        try:
            self.pc = Pinecone(api_key=self.api_key)
            
            if not self.pc.has_index(self.INDEX_NAME):
                # Don't create - just warn, as we're reusing orchestrator-kb
                logger.warning("Orchestrator KB index not found, answer store will be disabled")
                return
            
            self.index = self.pc.Index(self.INDEX_NAME)
            self._initialized = True
            logger.info("Pinecone answer store initialized via direct connection")
            
        except Exception as e:
            logger.error("Failed to initialize Pinecone: %s", e)
            self._initialized = False
    
    def store(self, answer: StoredAnswer) -> None:
        """Store an answer with embeddings."""
        if not self._initialized:
            return
        
        try:
            record = {
                "_id": answer.id,
                "query_text": answer.query_text,
                "answer_text": answer.answer_text[:5000],  # Limit size
                "query_hash": answer.query_hash,
                "quality_score": answer.quality_score,
                "domain": answer.domain,
                "complexity": answer.complexity,
                "created_at": answer.created_at,
            }
            
            self.index.upsert_records(self.NAMESPACE, [record])
            logger.debug("Stored answer %s in Pinecone", answer.id)
            
        except Exception as e:
            logger.error("Failed to store answer in Pinecone: %s", e)
    
    def search(
        self,
        query: str,
        domain: Optional[str] = None,
        min_quality: float = 0.5,
        limit: int = 5,
    ) -> List[Tuple[StoredAnswer, float]]:
        """Search for similar answers using semantic search."""
        if not self._initialized:
            return []
        
        try:
            # Build filter
            filter_dict = {"quality_score": {"$gte": min_quality}}
            if domain:
                filter_dict["domain"] = {"$eq": domain}
            
            results = self.index.search(
                namespace=self.NAMESPACE,
                query={
                    "top_k": limit,
                    "inputs": {"text": query},
                    "filter": filter_dict,
                },
                rerank={
                    "model": "bge-reranker-v2-m3",
                    "top_n": limit,
                    "rank_fields": ["query_text"],
                }
            )
            
            answers = []
            for hit in results.get("result", {}).get("hits", []):
                score = hit.get("_score", 0)
                fields = hit.get("fields", {})
                
                answer = StoredAnswer(
                    id=hit["_id"],
                    query_hash=fields.get("query_hash", ""),
                    query_text=fields.get("query_text", ""),
                    answer_text=fields.get("answer_text", ""),
                    quality_score=fields.get("quality_score", 0.5),
                    domain=fields.get("domain", "general"),
                    complexity=fields.get("complexity", "moderate"),
                    created_at=fields.get("created_at", ""),
                )
                answers.append((answer, score))
            
            return answers
            
        except Exception as e:
            logger.error("Pinecone search failed: %s", e)
            return []


class AnswerStore:
    """Main answer store with fallback support.
    
    Uses Pinecone for semantic search when available, falls back to SQLite.
    """
    
    def __init__(
        self,
        pinecone_api_key: Optional[str] = None,
        sqlite_path: Optional[str] = None,
    ):
        # Always use SQLite as primary storage
        self.sqlite_store = SQLiteAnswerStore(sqlite_path)
        
        # Use Pinecone for semantic search if available
        self.pinecone_store: Optional[PineconeAnswerStore] = None
        if PINECONE_AVAILABLE and (pinecone_api_key or os.getenv("PINECONE_API_KEY")):
            self.pinecone_store = PineconeAnswerStore(pinecone_api_key)
        
        logger.info(
            "AnswerStore initialized (pinecone=%s)",
            self.pinecone_store is not None and self.pinecone_store._initialized
        )
    
    def store(
        self,
        query_text: str,
        answer_text: str,
        *,
        quality_score: float = 0.5,
        domain: str = "general",
        complexity: str = "moderate",
        models_used: Optional[List[str]] = None,
        consensus_method: Optional[str] = None,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> StoredAnswer:
        """Store a new answer.
        
        Returns the created StoredAnswer.
        """
        import uuid
        
        answer = StoredAnswer(
            id=str(uuid.uuid4())[:12],
            query_hash=self._hash_query(query_text),
            query_text=query_text,
            answer_text=answer_text,
            quality_score=quality_score,
            domain=domain,
            complexity=complexity,
            models_used=models_used or [],
            consensus_method=consensus_method,
            session_id=session_id,
            user_id=user_id,
        )
        
        # Store in SQLite
        self.sqlite_store.store(answer)
        
        # Also store in Pinecone for semantic search
        if self.pinecone_store and self.pinecone_store._initialized:
            self.pinecone_store.store(answer)
        
        logger.info(
            "Stored answer %s (quality=%.2f, domain=%s)",
            answer.id, quality_score, domain
        )
        
        return answer
    
    def find_similar(
        self,
        query: str,
        *,
        domain: Optional[str] = None,
        min_quality: float = 0.5,
        min_similarity: float = 0.7,
        limit: int = 5,
    ) -> List[Tuple[StoredAnswer, float]]:
        """Find similar answers for potential reuse.
        
        Args:
            query: The query to find similar answers for
            domain: Optional domain filter
            min_quality: Minimum quality score
            min_similarity: Minimum similarity score
            limit: Maximum number of results
            
        Returns:
            List of (answer, similarity_score) tuples
        """
        results = []
        
        # Try Pinecone first for semantic search
        if self.pinecone_store and self.pinecone_store._initialized:
            results = self.pinecone_store.search(
                query, domain=domain, min_quality=min_quality, limit=limit
            )
        
        # Fall back to SQLite if no Pinecone results
        if not results:
            results = self.sqlite_store.search(
                query, domain=domain, min_quality=min_quality, limit=limit
            )
        
        # Filter by minimum similarity
        results = [(a, s) for a, s in results if s >= min_similarity]
        
        return results
    
    def find_best_match(
        self,
        query: str,
        *,
        domain: Optional[str] = None,
        min_quality: float = 0.7,
        min_similarity: float = 0.85,
    ) -> Optional[StoredAnswer]:
        """Find the single best matching answer for reuse.
        
        Returns the best answer if one meets the quality/similarity thresholds.
        """
        results = self.find_similar(
            query,
            domain=domain,
            min_quality=min_quality,
            min_similarity=min_similarity,
            limit=1,
        )
        
        if results:
            answer, score = results[0]
            # Mark as reused
            self.sqlite_store.mark_reused(answer.id)
            logger.info(
                "Found reusable answer %s (similarity=%.2f, quality=%.2f)",
                answer.id, score, answer.quality_score
            )
            return answer
        
        return None
    
    def update_feedback(self, answer_id: str, feedback_score: float) -> None:
        """Update feedback score for an answer."""
        self.sqlite_store.update_feedback(answer_id, feedback_score)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get storage statistics."""
        return self.sqlite_store.get_stats()
    
    def _hash_query(self, query: str) -> str:
        """Create a hash of the query."""
        normalized = query.lower().strip()
        return hashlib.md5(normalized.encode()).hexdigest()[:16]


# Global instance
_answer_store: Optional[AnswerStore] = None


def get_answer_store() -> AnswerStore:
    """Get the global answer store instance."""
    global _answer_store
    if _answer_store is None:
        _answer_store = AnswerStore()
    return _answer_store
