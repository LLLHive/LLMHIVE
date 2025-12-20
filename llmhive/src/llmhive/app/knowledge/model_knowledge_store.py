"""
Model Knowledge Store - Persistent storage for AI model intelligence.

This module provides Pinecone-backed storage for critical model knowledge that
the orchestrator needs to make intelligent routing and team composition decisions:

1. Model Rankings by Category (programming, reasoning, creative, etc.)
2. Model Characteristics (strengths, weaknesses, capabilities, context limits)
3. Reasoning Model Profiles (chain-of-thought ability, verification capability)
4. Tool Efficiency Data (which models are best at function calling)
5. AI Development Updates (new techniques, model releases, improvements)

This knowledge is CRUCIAL for effective orchestration - the system cannot make
optimal decisions without understanding model capabilities and relative rankings.
"""

import hashlib
import logging
import os
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Check for Pinecone availability
try:
    from pinecone import Pinecone
    PINECONE_AVAILABLE = True
except ImportError:
    PINECONE_AVAILABLE = False
    logger.warning("Pinecone not installed. Model knowledge will use in-memory fallback.")


class ModelKnowledgeType(str, Enum):
    """Types of model knowledge stored."""
    MODEL_PROFILE = "model_profile"  # Full model characteristics
    CATEGORY_RANKING = "category_ranking"  # Ranking within a category
    REASONING_CAPABILITY = "reasoning_capability"  # Reasoning model analysis
    TOOL_EFFICIENCY = "tool_efficiency"  # Function calling ability
    STRENGTH_WEAKNESS = "strength_weakness"  # Specific strengths/weaknesses
    AI_DEVELOPMENT = "ai_development"  # New techniques/releases
    BENCHMARK_RESULT = "benchmark_result"  # Performance benchmarks


@dataclass
class ModelProfile:
    """Complete profile of an AI model for orchestration decisions."""
    model_id: str  # e.g., "openai/gpt-4o", "anthropic/claude-sonnet-4"
    model_name: str  # Human-readable name
    provider: str  # OpenAI, Anthropic, Google, etc.
    
    # Capabilities (0-100 scores)
    reasoning_score: int = 50
    coding_score: int = 50
    creative_score: int = 50
    accuracy_score: int = 50
    speed_score: int = 50  # Response speed
    cost_efficiency: int = 50  # Cost per quality
    
    # Characteristics
    context_length: int = 8192
    supports_tools: bool = True
    supports_vision: bool = False
    supports_streaming: bool = True
    
    # Reasoning-specific
    is_reasoning_model: bool = False
    chain_of_thought: bool = False
    self_verification: bool = False
    multi_step_planning: bool = False
    
    # Strengths and weaknesses
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)
    best_for: List[str] = field(default_factory=list)  # Use cases
    avoid_for: List[str] = field(default_factory=list)  # Anti-patterns
    
    # Rankings
    category_rankings: Dict[str, int] = field(default_factory=dict)  # category -> rank
    
    # Metadata
    last_updated: float = 0.0
    source: str = "openrouter"  # Where this data came from
    

@dataclass
class ModelKnowledgeRecord:
    """A record in the model knowledge store."""
    id: str
    knowledge_type: ModelKnowledgeType
    content: str  # Text content for embedding/search
    model_id: Optional[str] = None  # Which model this is about
    category: Optional[str] = None  # Which category (programming, reasoning, etc.)
    metadata: Dict[str, Any] = field(default_factory=dict)
    score: float = 0.0
    timestamp: float = field(default_factory=time.time)


class ModelKnowledgeStore:
    """
    Pinecone-backed store for model intelligence.
    
    This is the orchestrator's "brain" for understanding AI models -
    their capabilities, rankings, and when to use each one.
    """
    
    INDEX_NAME = "llmhive-model-knowledge"
    EMBEDDING_MODEL = "llama-text-embed-v2"
    RERANKER_MODEL = "bge-reranker-v2-m3"
    NAMESPACE_MODELS = "model_profiles"
    NAMESPACE_RANKINGS = "category_rankings"
    NAMESPACE_AI_DEVELOPMENTS = "ai_developments"
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize the model knowledge store."""
        self.api_key = api_key or os.getenv("PINECONE_API_KEY")
        self.pc: Optional[Pinecone] = None
        self.index = None
        self._initialized = False
        self._local_cache: Dict[str, Dict[str, ModelKnowledgeRecord]] = {}
        
        if PINECONE_AVAILABLE and self.api_key:
            self._initialize_pinecone()
        else:
            logger.info("Using in-memory cache for model knowledge")
    
    def _initialize_pinecone(self) -> None:
        """Initialize Pinecone client and ensure index exists."""
        try:
            self.pc = Pinecone(api_key=self.api_key)
            
            # Check if index exists, create if not
            if not self.pc.has_index(self.INDEX_NAME):
                logger.info(f"Creating Pinecone index for model knowledge: {self.INDEX_NAME}")
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
            logger.info("Model knowledge store initialized with Pinecone")
            
        except Exception as e:
            logger.error(f"Failed to initialize Pinecone for model knowledge: {e}")
            self._initialized = False
    
    def _generate_id(self, *parts: str) -> str:
        """Generate a unique ID from parts."""
        hash_input = ":".join(str(p) for p in parts)
        return hashlib.sha256(hash_input.encode()).hexdigest()[:16]
    
    # =========================================================================
    # Model Profile Storage
    # =========================================================================
    
    async def store_model_profile(self, profile: ModelProfile) -> Optional[str]:
        """
        Store a complete model profile for orchestration decisions.
        
        This is the core data that helps the orchestrator understand
        what each model is good at and when to use it.
        """
        record_id = self._generate_id("profile", profile.model_id)
        
        # Create searchable content from profile
        content = f"""
Model: {profile.model_name} ({profile.model_id})
Provider: {profile.provider}
Type: {"Reasoning Model" if profile.is_reasoning_model else "General Model"}

Capabilities:
- Reasoning: {profile.reasoning_score}/100
- Coding: {profile.coding_score}/100
- Creative: {profile.creative_score}/100
- Accuracy: {profile.accuracy_score}/100
- Speed: {profile.speed_score}/100
- Cost Efficiency: {profile.cost_efficiency}/100

Features:
- Context Length: {profile.context_length:,} tokens
- Tool Support: {"Yes" if profile.supports_tools else "No"}
- Vision: {"Yes" if profile.supports_vision else "No"}
- Chain-of-Thought: {"Yes" if profile.chain_of_thought else "No"}
- Self-Verification: {"Yes" if profile.self_verification else "No"}

Strengths: {', '.join(profile.strengths) if profile.strengths else 'Not specified'}
Weaknesses: {', '.join(profile.weaknesses) if profile.weaknesses else 'Not specified'}
Best For: {', '.join(profile.best_for) if profile.best_for else 'General use'}
Avoid For: {', '.join(profile.avoid_for) if profile.avoid_for else 'None specified'}
"""
        
        record = {
            "_id": record_id,
            "content": content.strip(),
            "knowledge_type": ModelKnowledgeType.MODEL_PROFILE.value,
            "model_id": profile.model_id,
            "model_name": profile.model_name,
            "provider": profile.provider,
            "reasoning_score": profile.reasoning_score,
            "coding_score": profile.coding_score,
            "creative_score": profile.creative_score,
            "accuracy_score": profile.accuracy_score,
            "speed_score": profile.speed_score,
            "cost_efficiency": profile.cost_efficiency,
            "context_length": profile.context_length,
            "supports_tools": profile.supports_tools,
            "supports_vision": profile.supports_vision,
            "is_reasoning_model": profile.is_reasoning_model,
            "chain_of_thought": profile.chain_of_thought,
            "self_verification": profile.self_verification,
            "strengths": ",".join(profile.strengths) if profile.strengths else "",
            "weaknesses": ",".join(profile.weaknesses) if profile.weaknesses else "",
            "best_for": ",".join(profile.best_for) if profile.best_for else "",
            "timestamp": time.time(),
            "source": profile.source,
        }
        
        return await self._store_record(record, self.NAMESPACE_MODELS)
    
    async def store_category_ranking(
        self,
        category: str,
        rankings: List[Dict[str, Any]],  # List of {model_id, rank, score, ...}
        view: str = "week",
    ) -> List[str]:
        """
        Store model rankings for a category (e.g., programming, reasoning).
        
        This data comes from OpenRouter sync and tells us which models
        are currently best for each use case.
        """
        record_ids = []
        
        for rank_data in rankings:
            model_id = rank_data.get("model_id", "")
            model_name = rank_data.get("model_name", "")
            rank = rank_data.get("rank", 0)
            
            record_id = self._generate_id("ranking", category, model_id, view)
            
            content = f"""
Category: {category}
Rank: #{rank}
Model: {model_name} ({model_id})
Time Period: {view}

This model is ranked #{rank} in the {category} category based on user preference
and performance metrics. Use this model when tasks require {category} expertise.
"""
            
            record = {
                "_id": record_id,
                "content": content.strip(),
                "knowledge_type": ModelKnowledgeType.CATEGORY_RANKING.value,
                "model_id": model_id,
                "model_name": model_name,
                "category": category,
                "rank": rank,
                "view": view,
                "author": rank_data.get("author", ""),
                "timestamp": time.time(),
            }
            
            stored_id = await self._store_record(record, self.NAMESPACE_RANKINGS)
            if stored_id:
                record_ids.append(stored_id)
        
        logger.info(f"Stored {len(record_ids)} rankings for category '{category}'")
        return record_ids
    
    async def store_reasoning_model_analysis(
        self,
        model_id: str,
        model_name: str,
        analysis: Dict[str, Any],
    ) -> Optional[str]:
        """
        Store detailed analysis of a reasoning model's capabilities.
        
        This helps the orchestrator understand HOW a model reasons,
        not just IF it can reason.
        """
        record_id = self._generate_id("reasoning", model_id)
        
        cot_ability = analysis.get("chain_of_thought_ability", "unknown")
        verification = analysis.get("self_verification", "unknown")
        planning = analysis.get("multi_step_planning", "unknown")
        
        content = f"""
Reasoning Model Analysis: {model_name} ({model_id})

Chain-of-Thought Ability: {cot_ability}
- Can break down complex problems into steps
- Shows intermediate reasoning in output

Self-Verification: {verification}
- Checks its own answers for errors
- Can identify and correct mistakes

Multi-Step Planning: {planning}
- Plans ahead for complex tasks
- Manages dependencies between steps

Recommended For:
{chr(10).join('- ' + r for r in analysis.get('recommended_for', ['Complex reasoning tasks']))}

Not Recommended For:
{chr(10).join('- ' + r for r in analysis.get('not_recommended_for', ['Simple factual queries']))}

Notes: {analysis.get('notes', 'No additional notes')}
"""
        
        record = {
            "_id": record_id,
            "content": content.strip(),
            "knowledge_type": ModelKnowledgeType.REASONING_CAPABILITY.value,
            "model_id": model_id,
            "model_name": model_name,
            "cot_ability": str(cot_ability),
            "verification": str(verification),
            "planning": str(planning),
            "timestamp": time.time(),
        }
        
        return await self._store_record(record, self.NAMESPACE_MODELS)
    
    async def store_ai_development(
        self,
        title: str,
        summary: str,
        source: str,
        impact: str = "medium",
        relevance_to_orchestration: str = "",
        integration_proposal: Optional[str] = None,
    ) -> Optional[str]:
        """
        Store AI development news/research for continuous improvement.
        
        The research agent discovers new techniques and models,
        and this stores that knowledge for the planning agent.
        """
        record_id = self._generate_id("ai_dev", title, str(time.time()))
        
        content = f"""
AI Development: {title}

Summary: {summary}

Source: {source}
Impact Level: {impact}
Relevance to LLMHive: {relevance_to_orchestration}

{f'Integration Proposal: {integration_proposal}' if integration_proposal else ''}

This development may affect how we orchestrate AI models and should be
considered for future improvements to the system.
"""
        
        record = {
            "_id": record_id,
            "content": content.strip(),
            "knowledge_type": ModelKnowledgeType.AI_DEVELOPMENT.value,
            "title": title[:200],
            "source": source[:100],
            "impact": impact,
            "has_proposal": bool(integration_proposal),
            "timestamp": time.time(),
        }
        
        return await self._store_record(record, self.NAMESPACE_AI_DEVELOPMENTS)
    
    # =========================================================================
    # Knowledge Retrieval for Orchestration
    # =========================================================================
    
    async def get_best_models_for_task(
        self,
        task_description: str,
        category: Optional[str] = None,
        top_k: int = 5,
        require_reasoning: bool = False,
        require_tools: bool = False,
    ) -> List[ModelKnowledgeRecord]:
        """
        Get the best models for a specific task.
        
        This is the primary interface for the orchestrator to understand
        which models to use for a given task.
        """
        # Build search query
        query = f"Best AI models for: {task_description}"
        if category:
            query += f" Category: {category}"
        if require_reasoning:
            query += " Requires strong reasoning and chain-of-thought capability"
        if require_tools:
            query += " Must support function calling and tool use"
        
        # Build filter
        filter_criteria: Dict[str, Any] = {
            "knowledge_type": {"$in": [
                ModelKnowledgeType.MODEL_PROFILE.value,
                ModelKnowledgeType.CATEGORY_RANKING.value,
            ]}
        }
        
        if require_reasoning:
            filter_criteria["is_reasoning_model"] = {"$eq": True}
        
        if require_tools:
            filter_criteria["supports_tools"] = {"$eq": True}
        
        return await self._search(
            query=query,
            namespace=self.NAMESPACE_MODELS,
            top_k=top_k,
            filter_criteria=filter_criteria,
        )
    
    async def get_model_profile(self, model_id: str) -> Optional[ModelKnowledgeRecord]:
        """Get the full profile for a specific model."""
        records = await self._search(
            query=f"Model profile for {model_id}",
            namespace=self.NAMESPACE_MODELS,
            top_k=1,
            filter_criteria={
                "model_id": {"$eq": model_id},
                "knowledge_type": {"$eq": ModelKnowledgeType.MODEL_PROFILE.value},
            },
        )
        return records[0] if records else None
    
    async def get_category_rankings(
        self,
        category: str,
        top_k: int = 10,
    ) -> List[ModelKnowledgeRecord]:
        """Get top models for a category from stored rankings."""
        return await self._search(
            query=f"Top ranked models for {category}",
            namespace=self.NAMESPACE_RANKINGS,
            top_k=top_k,
            filter_criteria={
                "category": {"$eq": category},
                "knowledge_type": {"$eq": ModelKnowledgeType.CATEGORY_RANKING.value},
            },
        )
    
    async def get_reasoning_models(self, top_k: int = 10) -> List[ModelKnowledgeRecord]:
        """Get all reasoning models with their capabilities."""
        return await self._search(
            query="Reasoning models with chain-of-thought and verification capabilities",
            namespace=self.NAMESPACE_MODELS,
            top_k=top_k,
            filter_criteria={
                "is_reasoning_model": {"$eq": True},
            },
        )
    
    async def get_recent_ai_developments(
        self,
        days: int = 7,
        impact: Optional[str] = None,
        top_k: int = 10,
    ) -> List[ModelKnowledgeRecord]:
        """Get recent AI developments for the planning agent."""
        cutoff_time = time.time() - (days * 24 * 60 * 60)
        
        filter_criteria: Dict[str, Any] = {
            "timestamp": {"$gte": cutoff_time},
            "knowledge_type": {"$eq": ModelKnowledgeType.AI_DEVELOPMENT.value},
        }
        
        if impact:
            filter_criteria["impact"] = {"$eq": impact}
        
        return await self._search(
            query="Recent AI developments and new model releases",
            namespace=self.NAMESPACE_AI_DEVELOPMENTS,
            top_k=top_k,
            filter_criteria=filter_criteria,
        )
    
    async def search_model_knowledge(
        self,
        query: str,
        knowledge_types: Optional[List[ModelKnowledgeType]] = None,
        top_k: int = 10,
    ) -> List[ModelKnowledgeRecord]:
        """
        General semantic search across all model knowledge.
        
        Use this when you need to find specific information about
        models that doesn't fit the structured queries above.
        """
        filter_criteria: Dict[str, Any] = {}
        
        if knowledge_types:
            filter_criteria["knowledge_type"] = {
                "$in": [kt.value for kt in knowledge_types]
            }
        
        # Search across all namespaces by searching each and combining
        all_results: List[ModelKnowledgeRecord] = []
        
        for namespace in [self.NAMESPACE_MODELS, self.NAMESPACE_RANKINGS, self.NAMESPACE_AI_DEVELOPMENTS]:
            results = await self._search(
                query=query,
                namespace=namespace,
                top_k=top_k,
                filter_criteria=filter_criteria if filter_criteria else None,
            )
            all_results.extend(results)
        
        # Sort by score and return top_k
        all_results.sort(key=lambda r: r.score, reverse=True)
        return all_results[:top_k]
    
    # =========================================================================
    # Internal Storage Methods
    # =========================================================================
    
    async def _store_record(
        self,
        record: Dict[str, Any],
        namespace: str,
    ) -> Optional[str]:
        """Store a record in Pinecone or local cache."""
        record_id = record.get("_id", "")
        
        if self._initialized and self.index:
            try:
                self.index.upsert_records(namespace, [record])
                logger.debug(f"Stored model knowledge in Pinecone: {record_id}")
                return record_id
            except Exception as e:
                logger.error(f"Failed to store in Pinecone: {e}")
        
        # Fallback to local cache
        if namespace not in self._local_cache:
            self._local_cache[namespace] = {}
        
        self._local_cache[namespace][record_id] = ModelKnowledgeRecord(
            id=record_id,
            knowledge_type=ModelKnowledgeType(record.get("knowledge_type", "model_profile")),
            content=record.get("content", ""),
            model_id=record.get("model_id"),
            category=record.get("category"),
            metadata={k: v for k, v in record.items() if k not in ["_id", "content"]},
            timestamp=record.get("timestamp", time.time()),
        )
        
        return record_id
    
    async def _search(
        self,
        query: str,
        namespace: str,
        top_k: int = 5,
        filter_criteria: Optional[Dict[str, Any]] = None,
    ) -> List[ModelKnowledgeRecord]:
        """Search for records in Pinecone or local cache."""
        if self._initialized and self.index:
            try:
                search_query: Dict[str, Any] = {
                    "top_k": top_k * 2,
                    "inputs": {"text": query},
                }
                
                if filter_criteria:
                    search_query["filter"] = filter_criteria
                
                results = self.index.search(
                    namespace=namespace,
                    query=search_query,
                    rerank={
                        "model": self.RERANKER_MODEL,
                        "top_n": top_k,
                        "rank_fields": ["content"],
                    }
                )
                
                records = []
                for hit in results.get("result", {}).get("hits", []):
                    fields = hit.get("fields", {})
                    records.append(ModelKnowledgeRecord(
                        id=hit.get("_id", ""),
                        knowledge_type=ModelKnowledgeType(
                            fields.get("knowledge_type", "model_profile")
                        ),
                        content=fields.get("content", ""),
                        model_id=fields.get("model_id"),
                        category=fields.get("category"),
                        metadata={k: v for k, v in fields.items()
                                  if k not in ["content", "_id", "knowledge_type"]},
                        score=hit.get("_score", 0.0),
                    ))
                
                return records
                
            except Exception as e:
                logger.error(f"Pinecone search failed: {e}")
        
        # Fallback to local cache search
        return self._local_search(query, namespace, top_k, filter_criteria)
    
    def _local_search(
        self,
        query: str,
        namespace: str,
        top_k: int,
        filter_criteria: Optional[Dict[str, Any]] = None,
    ) -> List[ModelKnowledgeRecord]:
        """Simple keyword search in local cache."""
        if namespace not in self._local_cache:
            return []
        
        query_words = set(query.lower().split())
        scored: List[Tuple[ModelKnowledgeRecord, float]] = []
        
        for record in self._local_cache[namespace].values():
            # Apply filters
            if filter_criteria:
                match = True
                for key, condition in filter_criteria.items():
                    value = record.metadata.get(key)
                    if isinstance(condition, dict):
                        if "$eq" in condition and value != condition["$eq"]:
                            match = False
                        elif "$in" in condition and value not in condition["$in"]:
                            match = False
                        elif "$gte" in condition and (value is None or value < condition["$gte"]):
                            match = False
                    elif value != condition:
                        match = False
                if not match:
                    continue
            
            # Score by keyword overlap
            content_words = set(record.content.lower().split())
            overlap = len(query_words & content_words)
            if overlap > 0:
                score = overlap / len(query_words)
                scored.append((record, score))
        
        scored.sort(key=lambda x: x[1], reverse=True)
        return [r for r, _ in scored[:top_k]]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the model knowledge store."""
        if self._initialized and self.index:
            try:
                stats = self.index.describe_index_stats()
                return {
                    "initialized": True,
                    "backend": "pinecone",
                    "index_name": self.INDEX_NAME,
                    "total_records": stats.get("total_vector_count", 0),
                    "namespaces": stats.get("namespaces", {}),
                }
            except Exception as e:
                logger.error(f"Failed to get Pinecone stats: {e}")
        
        return {
            "initialized": False,
            "backend": "local_cache",
            "namespaces": {
                ns: len(records) for ns, records in self._local_cache.items()
            },
        }


# Singleton instance
_model_knowledge_store: Optional[ModelKnowledgeStore] = None


def get_model_knowledge_store() -> ModelKnowledgeStore:
    """Get the singleton model knowledge store instance."""
    global _model_knowledge_store
    if _model_knowledge_store is None:
        _model_knowledge_store = ModelKnowledgeStore()
    return _model_knowledge_store

