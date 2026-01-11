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
from collections import Counter
import math
import re
import os
import pickle

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
    
    Now uses centralized PineconeRegistry for host-based connections.
    """
    
    INDEX_NAME = "llmhive-orchestrator-kb"
    EMBEDDING_MODEL = "llama-text-embed-v2"
    RERANKER_MODEL = "bge-reranker-v2-m3"
    
    def __init__(self, api_key: Optional[str] = None, use_local_only: bool = False):
        """Initialize the Pinecone knowledge base."""
        self.api_key = api_key or os.getenv("PINECONE_API_KEY")
        self.pc: Optional[Pinecone] = None
        self.index = None
        self._initialized = False
        self._fallback_store: Dict[str, List[KnowledgeRecord]] = {}
        self._local_store = LocalVectorStore()
        self._faiss_store = FaissVectorStore()
        
        if not use_local_only and PINECONE_AVAILABLE and self.api_key:
            self._initialize_pinecone()
        else:
            logger.info("Using local in-memory vector store for knowledge base")
    
    def _initialize_pinecone(self) -> None:
        """Initialize Pinecone via registry (host-based) or direct connection."""
        # Try registry-based connection first (supports host-based connections)
        try:
            from .pinecone_registry import get_pinecone_registry, IndexKind
            
            registry = get_pinecone_registry()
            if registry.is_available:
                self.index = registry.get_index(IndexKind.ORCHESTRATOR_KB)
                if self.index:
                    self._initialized = True
                    logger.info("Pinecone knowledge base initialized via registry (host-based)")
                    return
        except ImportError:
            logger.debug("Pinecone registry not available, using direct connection")
        except Exception as e:
            logger.warning("Registry connection failed: %s, falling back to direct", e)
        
        # Fallback: Direct connection (for backward compatibility)
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
            logger.info("Pinecone knowledge base initialized via direct connection")
            
        except Exception as e:
            logger.error(f"Failed to initialize Pinecone: {e}")
            self._initialized = False
    
    def _generate_id(self, content: str, record_type: str, namespace: str) -> str:
        """Generate a unique ID for a record."""
        hash_input = f"{content[:200]}:{record_type}:{namespace}:{time.time()}"
        return hashlib.sha256(hash_input.encode()).hexdigest()[:16]
    
    def _get_namespace(self, user_id: Optional[str] = None, project_id: Optional[str] = None, org_id: Optional[str] = None) -> str:
        """Get the namespace for storing/retrieving records."""
        if org_id:
            return f"org_{org_id}"
        if project_id:
            return f"project_{project_id}"
        if user_id:
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
        org_id: Optional[str] = None,
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
        namespace = self._get_namespace(user_id, project_id, org_id)
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
            "org_id": org_id or "",
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
        
        # Fallback to local/FAISS vector store
        self._local_store.add(
            namespace=namespace,
            record=KnowledgeRecord(
                id=record_id,
                content=answer,
                record_type=record_type,
                metadata=record_metadata,
                score=quality_score
            )
        )
        self._faiss_store.add(namespace=namespace, record=record_metadata, content=answer)
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
        top_k: int = 8,
        record_types: Optional[List[RecordType]] = None,
        domain: Optional[str] = None,
        user_id: Optional[str] = None,
        project_id: Optional[str] = None,
        org_id: Optional[str] = None,
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
        namespace = self._get_namespace(user_id, project_id, org_id)
        
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
                
                records.sort(key=lambda r: r.score, reverse=True)
                return records[:top_k]
                
            except Exception as e:
                logger.error(f"Failed to retrieve from Pinecone: {e}")
        
        # Try FAISS store first
        faiss_records = self._faiss_store.search(
            query=query,
            namespace=namespace,
            top_k=top_k,
            record_types=record_types,
            domain=domain,
            min_quality_score=min_quality_score,
        )
        if faiss_records:
            return faiss_records
        
        # Fallback to local vector search (bag-of-words)
        return self._local_store.search(
            query=query,
            namespace=namespace,
            top_k=top_k,
            record_types=record_types,
            domain=domain,
            min_quality_score=min_quality_score,
        )
    
    def _fallback_search(
        self,
        query: str,
        namespace: str,
        top_k: int,
        record_types: Optional[List[RecordType]] = None
    ) -> List[KnowledgeRecord]:
        """Keyword fallback (kept for legacy)."""
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
            top_k=5,
            record_types=[RecordType.FINAL_ANSWER, RecordType.DOMAIN_KNOWLEDGE, RecordType.PARTIAL_ANSWER],
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
            snippet = record.content[:600]
            if total_length + len(snippet) > max_context_length:
                break
            context_parts.append(f"[Relevant context ({record.metadata.get('domain','')} | score={record.score:.2f})]: {snippet}")
            total_length += len(snippet)
        
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
    
    async def delete_record(
        self,
        record_id: str,
        user_id: Optional[str] = None,
        project_id: Optional[str] = None,
    ) -> bool:
        """Delete a record from the KB."""
        namespace = self._get_namespace(user_id, project_id)
        if self._initialized and self.index:
            try:
                self.index.delete(ids=[record_id], namespace=namespace)
                logger.info("Deleted record %s from Pinecone", record_id)
                return True
            except Exception as e:
                logger.warning("Failed to delete record in Pinecone: %s", e)
        # Remove from local store
        self._local_store.delete(namespace, record_id)
        if namespace in self._fallback_store:
            self._fallback_store[namespace] = [
                r for r in self._fallback_store[namespace] if r.id != record_id
            ]
        return True
    
    def export_data(
        self,
        record_types: Optional[List[RecordType]] = None,
        output_path: str = "knowledge_export.jsonl",
        namespace: str = "global",
    ) -> str:
        """
        Export stored records (local store) to JSONL for offline fine-tuning.
        
        Note: For Pinecone-backed data this exports what is present in the local
        cache; use Pinecone export tools for full remote data if needed.
        """
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        exported = 0
        with open(output_path, "w", encoding="utf-8") as f:
            records = self._local_store.store.get(namespace, [])
            for record, _vec in records:
                if record_types and record.record_type not in record_types:
                    continue
                f.write(json.dumps({
                    "id": record.id,
                    "record_type": record.record_type.value,
                    "query": record.metadata.get("query", ""),
                    "answer": record.content,
                    "quality_score": record.metadata.get("quality_score", 0.0),
                    "models_used": record.metadata.get("models_used", ""),
                    "domain": record.metadata.get("domain", ""),
                    "timestamp": record.metadata.get("timestamp", 0),
                }) + "\n")
                exported += 1
        logger.info("Exported %d records to %s", exported, output_path)
        return output_path
    
    async def store_document(
        self,
        document_text: str,
        doc_id: str,
        domain: str = "default",
        user_id: Optional[str] = None,
        project_id: Optional[str] = None,
        org_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        chunk_size: int = 800,
    ) -> List[str]:
        """Ingest a document by chunking and storing as domain knowledge."""
        namespace = self._get_namespace(user_id, project_id, org_id)
        record_ids: List[str] = []
        words = document_text.split()
        chunks = []
        current = []
        for w in words:
            current.append(w)
            if len(current) >= chunk_size:
                chunks.append(" ".join(current))
                current = []
        if current:
            chunks.append(" ".join(current))
        
        for idx, chunk in enumerate(chunks):
            meta = {
                "record_type": RecordType.DOMAIN_KNOWLEDGE.value,
                "doc_id": doc_id,
                "chunk_id": idx,
                "domain": domain,
                "user_id": user_id or "",
                "project_id": project_id or "",
                "timestamp": time.time(),
                **(metadata or {}),
            }
            record_id = self._generate_id(chunk, RecordType.DOMAIN_KNOWLEDGE.value, namespace)
            record = {
                "_id": record_id,
                "content": chunk,
                **meta,
            }
            # Try Pinecone, else local
            if self._initialized and self.index:
                try:
                    self.index.upsert_records(namespace, [record])
                    record_ids.append(record_id)
                    continue
                except Exception as e:
                    logger.warning("Failed to store doc chunk in Pinecone: %s", e)
            self._local_store.add(
                namespace=namespace,
                record=KnowledgeRecord(
                    id=record_id,
                    content=chunk,
                    record_type=RecordType.DOMAIN_KNOWLEDGE,
                    metadata=meta,
                    score=1.0,
                ),
            )
            self._faiss_store.add(namespace=namespace, record=meta, content=chunk)
            record_ids.append(record_id)
        return record_ids
    
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
        records = self._local_store.store.get(namespace, [])
        return {
            "total_vectors": sum(len(v) for v in self._local_store.store.values()),
            "namespace_vectors": len(records),
            "initialized": False,
            "backend": "faiss" if self._faiss_store.is_available else "local_vector",
        }


class LocalVectorStore:
    """Lightweight local vector store with bag-of-words cosine similarity."""
    
    def __init__(self):
        self.store: Dict[str, List[Tuple[KnowledgeRecord, Dict[str, float]]]] = {}
    
    def _embed(self, text: str) -> Dict[str, float]:
        words = [w for w in text.lower().split() if w.isalpha()]
        counts = Counter(words)
        norm = math.sqrt(sum(v * v for v in counts.values())) or 1.0
        return {k: v / norm for k, v in counts.items()}
    
    def add(self, namespace: str, record: KnowledgeRecord) -> None:
        vec = self._embed(record.content)
        if namespace not in self.store:
            self.store[namespace] = []
        self.store[namespace].append((record, vec))
    
    def delete(self, namespace: str, record_id: str) -> None:
        if namespace in self.store:
            self.store[namespace] = [
                (r, v) for (r, v) in self.store[namespace] if r.id != record_id
            ]
    
    def _sim(self, v1: Dict[str, float], v2: Dict[str, float]) -> float:
        # Cosine on sparse dicts
        return sum(v1.get(k, 0.0) * v2.get(k, 0.0) for k in v1.keys())
    
    def search(
        self,
        query: str,
        namespace: str,
        top_k: int,
        record_types: Optional[List[RecordType]] = None,
        domain: Optional[str] = None,
        min_quality_score: float = 0.0,
    ) -> List[KnowledgeRecord]:
        if namespace not in self.store:
            return []
        qv = self._embed(query)
        scored: List[Tuple[KnowledgeRecord, float]] = []
        now = time.time()
        for record, vec in self.store[namespace]:
            if record_types and record.record_type not in record_types:
                continue
            if domain and record.metadata.get("domain") and record.metadata.get("domain") != domain:
                continue
            if record.metadata.get("quality_score", 0.0) < min_quality_score:
                continue
            base = self._sim(qv, vec)
            # recency boost (up to +0.1)
            ts = record.metadata.get("timestamp", record.timestamp)
            recency = max(0.0, 1.0 - ((now - ts) / (60 * 60 * 24 * 30)))  # ~1 month decay
            score = base + 0.1 * recency
            scored.append((record, score))
        scored.sort(key=lambda x: x[1], reverse=True)
        return [r for r, _ in scored[:top_k]]


class FaissVectorStore:
    """Optional FAISS-backed local vector store (if faiss + sentence-transformers available)."""
    
    def __init__(self):
        try:
            import faiss  # type: ignore
            from sentence_transformers import SentenceTransformer  # type: ignore
            self._faiss = faiss
            model_name = os.getenv("KB_EMBED_MODEL_LOCAL", "all-MiniLM-L6-v2")
            self._model = SentenceTransformer(model_name)
            self._indexes: Dict[str, Any] = {}
            self._id_maps: Dict[str, List[str]] = {}
            self._meta_maps: Dict[str, Dict[str, Dict[str, Any]]] = {}
            self._base_path = os.getenv("KB_FAISS_PATH", ".kb_faiss")
            self.is_available = True
            # Attempt to load persisted indexes/metadata
            self._load_all()
        except Exception as e:
            logger.info("FAISS store unavailable: %s", e)
            self.is_available = False
    
    def add(self, namespace: str, record: Dict[str, Any], content: str) -> None:
        if not self.is_available:
            return
        import numpy as np
        vec = self._model.encode(content).astype("float32")
        index = self._indexes.get(namespace)
        if index is None:
            index = self._faiss.IndexFlatIP(len(vec))
            self._indexes[namespace] = index
            self._id_maps[namespace] = []
            self._meta_maps[namespace] = {}
        index.add(np.expand_dims(vec, axis=0))
        rid = record.get("_id") or record.get("id") or ""
        self._id_maps[namespace].append(rid)
        # Persist minimal metadata and content for retrieval
        self._meta_maps[namespace][rid] = {
            "record_type": record.get("record_type", RecordType.FINAL_ANSWER.value),
            "metadata": record,
            "content": content,
        }
        self._save(namespace)
    
    def delete(self, namespace: str, record_id: str) -> None:
        if not self.is_available or namespace not in self._indexes:
            return
        # Rebuild without the deleted vector
        ids = self._id_maps[namespace]
        if record_id not in ids:
            return
        del_idx = ids.index(record_id)
        ids.pop(del_idx)
        if namespace in self._meta_maps:
            self._meta_maps[namespace].pop(record_id, None)
        import numpy as np
        index = self._indexes[namespace]
        if index.ntotal == 0:
            return
        vecs = []
        for i in range(index.ntotal):
            v = np.zeros((index.d,), dtype="float32")
            index.reconstruct(i, v)
            vecs.append(v)
        if vecs:
            vecs.pop(del_idx)
        new_index = self._faiss.IndexFlatIP(index.d)
        if vecs:
            new_index.add(np.array(vecs))
        self._indexes[namespace] = new_index
        self._save(namespace)
    
    def search(
        self,
        query: str,
        namespace: str,
        top_k: int,
        record_types: Optional[List[RecordType]] = None,
        domain: Optional[str] = None,
        min_quality_score: float = 0.0,
    ) -> List[KnowledgeRecord]:
        if not self.is_available or namespace not in self._indexes:
            return []
        import numpy as np
        index = self._indexes[namespace]
        ids = self._id_maps[namespace]
        qvec = self._model.encode(query).astype("float32")
        D, I = index.search(np.expand_dims(qvec, axis=0), top_k)
        records: List[KnowledgeRecord] = []
        for score, idx in zip(D[0], I[0]):
            if idx == -1 or idx >= len(ids):
                continue
            meta = self._meta_maps.get(namespace, {}).get(ids[idx], {})
            records.append(KnowledgeRecord(
                id=ids[idx],
                content=meta.get("content", ""),
                record_type=RecordType(meta.get("record_type", RecordType.FINAL_ANSWER.value)),
                metadata=meta.get("metadata", {"score": float(score)}),
                score=float(score),
            ))
        return records

    def _ns_paths(self, namespace: str) -> Tuple[str, str]:
        os.makedirs(self._base_path, exist_ok=True)
        return (
            os.path.join(self._base_path, f"{namespace}.index"),
            os.path.join(self._base_path, f"{namespace}.meta"),
        )

    def _save(self, namespace: str) -> None:
        if not self.is_available:
            return
        index = self._indexes.get(namespace)
        if index is None:
            return
        idx_path, meta_path = self._ns_paths(namespace)
        try:
            self._faiss.write_index(index, idx_path)
            with open(meta_path, "wb") as f:
                pickle.dump({
                    "ids": self._id_maps.get(namespace, []),
                    "meta": self._meta_maps.get(namespace, {}),
                }, f)
        except Exception as e:
            logger.warning("Failed to persist FAISS index for %s: %s", namespace, e)

    def _load_all(self) -> None:
        """Load all persisted namespaces from disk."""
        if not self.is_available:
            return
        if not os.path.isdir(self._base_path):
            return
        for fname in os.listdir(self._base_path):
            if not fname.endswith(".index"):
                continue
            namespace = fname.replace(".index", "")
            idx_path, meta_path = self._ns_paths(namespace)
            try:
                index = self._faiss.read_index(idx_path)
                self._indexes[namespace] = index
                with open(meta_path, "rb") as f:
                    data = pickle.load(f)
                    self._id_maps[namespace] = data.get("ids", [])
                    self._meta_maps[namespace] = data.get("meta", {})
                logger.info("Loaded FAISS index for namespace %s", namespace)
            except Exception as e:
                logger.warning("Failed to load FAISS index for %s: %s", namespace, e)

# Singleton instance
_knowledge_base: Optional[PineconeKnowledgeBase] = None


def get_knowledge_base() -> PineconeKnowledgeBase:
    """Get the singleton knowledge base instance."""
    global _knowledge_base
    if _knowledge_base is None:
        use_local = bool(os.getenv("USE_LOCAL_VECTOR_DB"))
        _knowledge_base = PineconeKnowledgeBase(use_local_only=use_local)
    return _knowledge_base

