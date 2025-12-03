"""
Pinecone Knowledge Base for LLMHive Orchestrator Learning

This module provides a vector database-backed knowledge base that stores:
1. Final answers from orchestration runs
2. Partial/intermediate answers from individual models
3. User queries and their context
4. Learned patterns and successful orchestration strategies

The knowledge base enables:
- RAG (Retrieval Augmented Generation) for context-aware responses
- Self-improvement by learning from successful orchestrations
- Cross-session memory and knowledge retention
"""

import os
import time
import hashlib
import logging
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)

# Check if Pinecone is available
try:
    from pinecone import Pinecone
    PINECONE_AVAILABLE = True
except ImportError:
    PINECONE_AVAILABLE = False
    logger.warning("Pinecone not installed. Knowledge base will use in-memory fallback.")


class RecordType(str, Enum):
    """Types of records stored in the knowledge base."""
    FINAL_ANSWER = "final_answer"
    PARTIAL_ANSWER = "partial_answer"
    USER_QUERY = "user_query"
    ORCHESTRATION_PATTERN = "orchestration_pattern"
    DOMAIN_KNOWLEDGE = "domain_knowledge"
    CORRECTION = "correction"


@dataclass
class KnowledgeRecord:
    """A record in the knowledge base."""
    id: str
    content: str
    record_type: RecordType
    metadata: Dict[str, Any] = field(default_factory=dict)
    score: float = 0.0
    timestamp: float = field(default_factory=time.time)


class PineconeKnowledgeBase:
    """
    Pinecone-backed knowledge base for orchestrator learning.
    
    Features:
    - Stores answers with integrated embeddings (llama-text-embed-v2)
    - Supports namespace isolation per user/project
    - Provides semantic search with reranking
    - Tracks answer quality and usage patterns
    """
    
    INDEX_NAME = "llmhive-orchestrator-kb"
    EMBEDDING_MODEL = "llama-text-embed-v2"
    RERANKER_MODEL = "bge-reranker-v2-m3"
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize the Pinecone knowledge base."""
        self.api_key = api_key or os.getenv("PINECONE_API_KEY")
        self.pc: Optional[Pinecone] = None
        self.index = None
        self._initialized = False
        self._fallback_store: Dict[str, List[KnowledgeRecord]] = {}
        
        if PINECONE_AVAILABLE and self.api_key:
            self._initialize_pinecone()
        else:
            logger.info("Using in-memory fallback for knowledge base")
    
    def _initialize_pinecone(self) -> None:
        """Initialize Pinecone client and ensure index exists."""
        try:
            self.pc = Pinecone(api_key=self.api_key)
            
            # Check if index exists, create if not
            if not self.pc.has_index(self.INDEX_NAME):
                logger.info(f"Creating Pinecone index: {self.INDEX_NAME}")
                self.pc.create_index_for_model(
                    name=self.INDEX_NAME,
                    cloud="aws",
                    region="us-east-1",
                    embed={
                        "model": self.EMBEDDING_MODEL,
                        "field_map": {"text": "content"}
                    }
                )
                # Wait for index to be ready
                time.sleep(5)
            
            self.index = self.pc.Index(self.INDEX_NAME)
            self._initialized = True
            logger.info("Pinecone knowledge base initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Pinecone: {e}")
            self._initialized = False
    
    def _generate_id(self, content: str, record_type: str, namespace: str) -> str:
        """Generate a unique ID for a record."""
        hash_input = f"{content[:200]}:{record_type}:{namespace}:{time.time()}"
        return hashlib.sha256(hash_input.encode()).hexdigest()[:16]
    
    def _get_namespace(self, user_id: Optional[str] = None, project_id: Optional[str] = None) -> str:
        """Get the namespace for storing/retrieving records."""
        if project_id:
            return f"project_{project_id}"
        elif user_id:
            return f"user_{user_id}"
        return "global"
    
    async def store_answer(
        self,
        query: str,
        answer: str,
        models_used: List[str],
        record_type: RecordType = RecordType.FINAL_ANSWER,
        quality_score: float = 0.0,
        domain: str = "default",
        user_id: Optional[str] = None,
        project_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        Store an answer in the knowledge base.
        
        Args:
            query: The original user query
            answer: The generated answer
            models_used: List of models that contributed
            record_type: Type of record (final, partial, etc.)
            quality_score: Quality score (0-1) if verified
            domain: Domain pack used
            user_id: Optional user ID for namespace
            project_id: Optional project ID for namespace
            metadata: Additional metadata
            
        Returns:
            Record ID if successful, None otherwise
        """
        namespace = self._get_namespace(user_id, project_id)
        record_id = self._generate_id(answer, record_type.value, namespace)
        
        record_metadata = {
            "record_type": record_type.value,
            "query": query[:500],  # Truncate for metadata size limits
            "models_used": ",".join(models_used),
            "quality_score": quality_score,
            "domain": domain,
            "timestamp": time.time(),
            "user_id": user_id or "",
            "project_id": project_id or "",
            **(metadata or {})
        }
        
        record = {
            "_id": record_id,
            "content": answer,  # Maps to text field for embedding
            **record_metadata
        }
        
        if self._initialized and self.index:
            try:
                self.index.upsert_records(namespace, [record])
                logger.debug(f"Stored answer in Pinecone: {record_id}")
                return record_id
            except Exception as e:
                logger.error(f"Failed to store in Pinecone: {e}")
        
        # Fallback to in-memory storage
        if namespace not in self._fallback_store:
            self._fallback_store[namespace] = []
        
        self._fallback_store[namespace].append(
            KnowledgeRecord(
                id=record_id,
                content=answer,
                record_type=record_type,
                metadata=record_metadata,
                score=quality_score
            )
        )
        return record_id
    
    async def store_orchestration_pattern(
        self,
        query_type: str,
        strategy_used: str,
        models_used: List[str],
        success: bool,
        latency_ms: int,
        quality_score: float,
        user_id: Optional[str] = None
    ) -> Optional[str]:
        """
        Store a successful orchestration pattern for learning.
        
        This helps the system learn which strategies work best for different query types.
        """
        content = f"""
Query Type: {query_type}
Strategy: {strategy_used}
Models: {', '.join(models_used)}
Success: {success}
Latency: {latency_ms}ms
Quality: {quality_score:.2f}
"""
        
        return await self.store_answer(
            query=f"Orchestration pattern for {query_type}",
            answer=content,
            models_used=models_used,
            record_type=RecordType.ORCHESTRATION_PATTERN,
            quality_score=quality_score if success else 0.0,
            user_id=user_id,
            metadata={
                "query_type": query_type,
                "strategy": strategy_used,
                "success": success,
                "latency_ms": latency_ms
            }
        )
    
    async def retrieve_context(
        self,
        query: str,
        top_k: int = 5,
        record_types: Optional[List[RecordType]] = None,
        domain: Optional[str] = None,
        user_id: Optional[str] = None,
        project_id: Optional[str] = None,
        min_quality_score: float = 0.0,
        rerank: bool = True
    ) -> List[KnowledgeRecord]:
        """
        Retrieve relevant context from the knowledge base.
        
        Args:
            query: The query to search for
            top_k: Number of results to return
            record_types: Filter by record types
            domain: Filter by domain
            user_id: Optional user ID for namespace
            project_id: Optional project ID for namespace
            min_quality_score: Minimum quality score filter
            rerank: Whether to rerank results
            
        Returns:
            List of relevant knowledge records
        """
        namespace = self._get_namespace(user_id, project_id)
        
        if self._initialized and self.index:
            try:
                # Build filter criteria
                filter_criteria = {}
                if record_types:
                    filter_criteria["record_type"] = {"$in": [rt.value for rt in record_types]}
                if domain:
                    filter_criteria["domain"] = {"$eq": domain}
                if min_quality_score > 0:
                    filter_criteria["quality_score"] = {"$gte": min_quality_score}
                
                # Build query
                search_query = {
                    "top_k": top_k * 2 if rerank else top_k,
                    "inputs": {"text": query}
                }
                
                if filter_criteria:
                    search_query["filter"] = filter_criteria
                
                # Execute search with optional reranking
                if rerank:
                    results = self.index.search(
                        namespace=namespace,
                        query=search_query,
                        rerank={
                            "model": self.RERANKER_MODEL,
                            "top_n": top_k,
                            "rank_fields": ["content"]
                        }
                    )
                else:
                    results = self.index.search(
                        namespace=namespace,
                        query=search_query
                    )
                
                # Convert to KnowledgeRecord objects
                records = []
                for hit in results.get("result", {}).get("hits", []):
                    fields = hit.get("fields", {})
                    records.append(KnowledgeRecord(
                        id=hit.get("_id", ""),
                        content=fields.get("content", ""),
                        record_type=RecordType(fields.get("record_type", "final_answer")),
                        metadata={
                            k: v for k, v in fields.items() 
                            if k not in ["content", "_id"]
                        },
                        score=hit.get("_score", 0.0)
                    ))
                
                return records
                
            except Exception as e:
                logger.error(f"Failed to retrieve from Pinecone: {e}")
        
        # Fallback to in-memory search (basic keyword matching)
        return self._fallback_search(query, namespace, top_k, record_types)
    
    def _fallback_search(
        self,
        query: str,
        namespace: str,
        top_k: int,
        record_types: Optional[List[RecordType]] = None
    ) -> List[KnowledgeRecord]:
        """Simple keyword-based fallback search."""
        records = self._fallback_store.get(namespace, [])
        
        # Filter by record types
        if record_types:
            records = [r for r in records if r.record_type in record_types]
        
        # Simple scoring based on keyword overlap
        query_words = set(query.lower().split())
        scored_records = []
        
        for record in records:
            content_words = set(record.content.lower().split())
            overlap = len(query_words & content_words)
            if overlap > 0:
                score = overlap / len(query_words)
                scored_records.append((record, score))
        
        # Sort by score and return top_k
        scored_records.sort(key=lambda x: x[1], reverse=True)
        return [r for r, _ in scored_records[:top_k]]
    
    async def get_best_strategy(
        self,
        query_type: str,
        user_id: Optional[str] = None
    ) -> Optional[Tuple[str, List[str]]]:
        """
        Get the best orchestration strategy for a query type based on past success.
        
        Returns:
            Tuple of (strategy_name, recommended_models) or None
        """
        records = await self.retrieve_context(
            query=f"Best strategy for {query_type}",
            top_k=10,
            record_types=[RecordType.ORCHESTRATION_PATTERN],
            user_id=user_id,
            min_quality_score=0.7
        )
        
        if not records:
            return None
        
        # Find the most successful strategy
        best_record = max(records, key=lambda r: r.score)
        strategy = best_record.metadata.get("strategy")
        models = best_record.metadata.get("models_used", "").split(",")
        
        return (strategy, models) if strategy else None
    
    async def augment_prompt(
        self,
        query: str,
        domain: str = "default",
        user_id: Optional[str] = None,
        project_id: Optional[str] = None,
        max_context_length: int = 2000
    ) -> str:
        """
        Augment a query with relevant context from the knowledge base.
        
        This implements RAG (Retrieval Augmented Generation) for the orchestrator.
        """
        # Retrieve relevant context
        records = await self.retrieve_context(
            query=query,
            top_k=3,
            record_types=[RecordType.FINAL_ANSWER, RecordType.DOMAIN_KNOWLEDGE],
            domain=domain,
            user_id=user_id,
            project_id=project_id,
            min_quality_score=0.5
        )
        
        if not records:
            return query
        
        # Build context string
        context_parts = []
        total_length = 0
        
        for record in records:
            if total_length + len(record.content) > max_context_length:
                break
            context_parts.append(f"[Relevant context: {record.content[:500]}...]")
            total_length += len(record.content)
        
        if not context_parts:
            return query
        
        # Create augmented prompt
        augmented = f"""Based on the following relevant context from previous interactions:

{chr(10).join(context_parts)}

Please answer the user's question:
{query}
"""
        return augmented
    
    async def learn_from_feedback(
        self,
        record_id: str,
        feedback_type: str,  # "positive", "negative", "correction"
        correction: Optional[str] = None,
        namespace: str = "global"
    ) -> bool:
        """
        Learn from user feedback on a previous answer.
        
        This allows the system to improve over time.
        """
        if feedback_type == "correction" and correction:
            # Store the correction as a new record
            await self.store_answer(
                query=f"Correction for {record_id}",
                answer=correction,
                models_used=["user_correction"],
                record_type=RecordType.CORRECTION,
                quality_score=1.0,  # User corrections are high quality
                metadata={"original_record_id": record_id}
            )
            return True
        
        # For positive/negative feedback, we could adjust quality scores
        # This would require fetching and updating the record
        # For now, we log the feedback
        logger.info(f"Received {feedback_type} feedback for record {record_id}")
        return True
    
    def get_stats(self, namespace: str = "global") -> Dict[str, Any]:
        """Get statistics about the knowledge base."""
        if self._initialized and self.index:
            try:
                stats = self.index.describe_index_stats()
                ns_stats = stats.get("namespaces", {}).get(namespace, {})
                return {
                    "total_vectors": stats.get("total_vector_count", 0),
                    "namespace_vectors": ns_stats.get("vector_count", 0),
                    "initialized": True,
                    "backend": "pinecone"
                }
            except Exception as e:
                logger.error(f"Failed to get Pinecone stats: {e}")
        
        # Fallback stats
        records = self._fallback_store.get(namespace, [])
        return {
            "total_vectors": sum(len(r) for r in self._fallback_store.values()),
            "namespace_vectors": len(records),
            "initialized": False,
            "backend": "in_memory"
        }


# Singleton instance
_knowledge_base: Optional[PineconeKnowledgeBase] = None


def get_knowledge_base() -> PineconeKnowledgeBase:
    """Get the singleton knowledge base instance."""
    global _knowledge_base
    if _knowledge_base is None:
        _knowledge_base = PineconeKnowledgeBase()
    return _knowledge_base

