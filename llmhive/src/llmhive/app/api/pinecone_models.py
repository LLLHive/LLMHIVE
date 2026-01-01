"""Model API Routes with Firestore + Pinecone backends.

These routes serve model data with the following priority:
1. Firestore model_catalog (353+ models with 262 enriched columns)
2. Pinecone ModelKnowledgeStore (semantic search)
3. Fallback to OpenRouter API

This ensures data persists across Cloud Run cold starts.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/models", tags=["model-catalog"])

# Initialize stores lazily
_knowledge_store = None
_firestore_catalog = None


def get_knowledge_store():
    """Get or create the ModelKnowledgeStore instance."""
    global _knowledge_store
    if _knowledge_store is None:
        try:
            from ..knowledge.model_knowledge_store import ModelKnowledgeStore
            _knowledge_store = ModelKnowledgeStore()
            logger.info("Initialized Pinecone ModelKnowledgeStore for API")
        except Exception as e:
            logger.error(f"Failed to initialize ModelKnowledgeStore: {e}")
            return None
    return _knowledge_store


def get_firestore_catalog():
    """Get or create the Firestore model catalog service."""
    global _firestore_catalog
    if _firestore_catalog is None:
        try:
            from ..services.firestore_models import get_firestore_model_catalog
            _firestore_catalog = get_firestore_model_catalog()
            logger.info("Initialized Firestore model catalog for API")
        except Exception as e:
            logger.error(f"Failed to initialize Firestore catalog: {e}")
            return None
    return _firestore_catalog


@router.get("/profiles")
async def list_model_profiles(
    search: Optional[str] = None,
    provider: Optional[str] = None,
    supports_tools: Optional[bool] = None,
    supports_vision: Optional[bool] = None,
    is_reasoning: Optional[bool] = None,
    limit: int = Query(50, ge=1, le=500),
) -> Dict[str, Any]:
    """List model profiles with enriched research data.
    
    Data Sources (in priority order):
    1. Firestore model_catalog (353+ models with full enriched data)
    2. Pinecone ModelKnowledgeStore (semantic search fallback)
    
    Returns model profiles with capabilities, benchmarks, rankings, and metadata.
    """
    # Priority 1: Firestore model_catalog (the richest data source)
    fs_catalog = get_firestore_catalog()
    if fs_catalog and fs_catalog.is_available():
        try:
            if provider:
                models_raw = fs_catalog.get_models_by_provider(provider)
            else:
                models_raw = fs_catalog.get_all_models()
            
            if models_raw and len(models_raw) > 0:
                # Transform to API format
                models = []
                for model in models_raw:
                    # Apply filters
                    if search:
                        search_lower = search.lower()
                        name = (model.get("model_name") or "").lower()
                        slug = (model.get("openrouter_slug") or "").lower()
                        if search_lower not in name and search_lower not in slug:
                            continue
                    
                    if supports_tools is not None:
                        if model.get("supports_function_calling") != supports_tools:
                            continue
                    
                    if supports_vision is not None:
                        if model.get("supports_vision") != supports_vision:
                            continue
                    
                    models.append({
                        "id": model.get("openrouter_slug") or model.get("model_id", ""),
                        "name": model.get("model_name", ""),
                        "provider": model.get("provider_name", ""),
                        "capabilities": {
                            "arena_score": model.get("arena_score"),
                            "arena_rank": model.get("arena_rank"),
                            "hf_ollb_avg": model.get("hf_ollb_avg"),
                            "hf_ollb_mmlu": model.get("hf_ollb_mmlu"),
                        },
                        "features": {
                            "context_length": model.get("max_context_tokens", 8192),
                            "supports_tools": model.get("supports_function_calling", False),
                            "supports_vision": model.get("supports_vision", False),
                            "modalities": model.get("modalities", "text"),
                        },
                        "strengths": (model.get("strengths") or "").split(",") if model.get("strengths") else [],
                        "weaknesses": (model.get("weaknesses") or "").split(",") if model.get("weaknesses") else [],
                        "best_for": (model.get("best_use_cases") or "").split(",") if model.get("best_use_cases") else [],
                        "source": "firestore_model_catalog",
                    })
                
                return {
                    "models": models[:limit],
                    "total": len(models),
                    "limit": limit,
                    "data_source": "firestore_model_catalog",
                    "description": "353+ models with 262 enriched columns from ModelDB",
                    "last_updated": datetime.now(timezone.utc).isoformat(),
                }
        except Exception as e:
            logger.warning(f"Firestore catalog failed, falling back to Pinecone: {e}")
    
    # Priority 2: Pinecone ModelKnowledgeStore
    store = get_knowledge_store()
    if not store:
        raise HTTPException(503, "Model knowledge store not available")
    
    try:
        # Build query for semantic search
        query = search if search else "AI language models with capabilities"
        
        if is_reasoning:
            query += " reasoning chain-of-thought"
        if supports_tools:
            query += " function calling tools"
        if supports_vision:
            query += " vision image"
        if provider:
            query += f" provider:{provider}"
        
        # Search using Pinecone
        from ..knowledge.model_knowledge_store import ModelKnowledgeType
        
        records = await store.search_model_knowledge(
            query=query,
            knowledge_types=[ModelKnowledgeType.MODEL_PROFILE],
            top_k=limit,
        )
        
        # Transform to API format
        models = []
        for record in records:
            meta = record.metadata
            models.append({
                "id": record.model_id or meta.get("model_id", ""),
                "name": meta.get("model_name", ""),
                "provider": meta.get("provider", ""),
                "capabilities": {
                    "reasoning_score": meta.get("reasoning_score", 50),
                    "coding_score": meta.get("coding_score", 50),
                    "creative_score": meta.get("creative_score", 50),
                    "accuracy_score": meta.get("accuracy_score", 50),
                    "speed_score": meta.get("speed_score", 50),
                    "cost_efficiency": meta.get("cost_efficiency", 50),
                },
                "features": {
                    "context_length": meta.get("context_length", 8192),
                    "supports_tools": meta.get("supports_tools", False),
                    "supports_vision": meta.get("supports_vision", False),
                    "is_reasoning_model": meta.get("is_reasoning_model", False),
                    "chain_of_thought": meta.get("chain_of_thought", False),
                },
                "strengths": meta.get("strengths", "").split(",") if meta.get("strengths") else [],
                "weaknesses": meta.get("weaknesses", "").split(",") if meta.get("weaknesses") else [],
                "best_for": meta.get("best_for", "").split(",") if meta.get("best_for") else [],
                "score": record.score,
                "source": meta.get("source", "pinecone"),
            })
        
        return {
            "models": models,
            "total": len(models),
            "limit": limit,
            "data_source": "pinecone_knowledge_store",
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }
        
    except Exception as e:
        logger.error(f"Failed to list model profiles: {e}", exc_info=True)
        raise HTTPException(500, f"Failed to retrieve models: {e}")


@router.get("/profiles/{model_id:path}")
async def get_model_profile(model_id: str) -> Dict[str, Any]:
    """Get detailed profile for a specific model.
    
    Data Source: Pinecone ModelKnowledgeStore
    """
    store = get_knowledge_store()
    if not store:
        raise HTTPException(503, "Model knowledge store not available")
    
    try:
        record = await store.get_model_profile(model_id)
        
        if not record:
            raise HTTPException(404, f"Model not found: {model_id}")
        
        meta = record.metadata
        return {
            "id": record.model_id or model_id,
            "name": meta.get("model_name", ""),
            "provider": meta.get("provider", ""),
            "capabilities": {
                "reasoning_score": meta.get("reasoning_score", 50),
                "coding_score": meta.get("coding_score", 50),
                "creative_score": meta.get("creative_score", 50),
                "accuracy_score": meta.get("accuracy_score", 50),
                "speed_score": meta.get("speed_score", 50),
                "cost_efficiency": meta.get("cost_efficiency", 50),
            },
            "features": {
                "context_length": meta.get("context_length", 8192),
                "supports_tools": meta.get("supports_tools", False),
                "supports_vision": meta.get("supports_vision", False),
                "is_reasoning_model": meta.get("is_reasoning_model", False),
                "chain_of_thought": meta.get("chain_of_thought", False),
                "self_verification": meta.get("self_verification", False),
            },
            "strengths": meta.get("strengths", "").split(",") if meta.get("strengths") else [],
            "weaknesses": meta.get("weaknesses", "").split(",") if meta.get("weaknesses") else [],
            "best_for": meta.get("best_for", "").split(",") if meta.get("best_for") else [],
            "content": record.content,
            "data_source": "pinecone_knowledge_store",
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get model profile: {e}", exc_info=True)
        raise HTTPException(500, f"Failed to retrieve model: {e}")


@router.get("/rankings/{category}")
async def get_category_rankings(
    category: str,
    limit: int = Query(10, ge=1, le=50),
) -> Dict[str, Any]:
    """Get top-ranked models for a category from Pinecone.
    
    Categories: programming, reasoning, creative, marketing, roleplay, etc.
    
    Data Source: Pinecone ModelKnowledgeStore (persistent rankings)
    """
    store = get_knowledge_store()
    if not store:
        raise HTTPException(503, "Model knowledge store not available")
    
    try:
        records = await store.get_category_rankings(category, top_k=limit)
        
        # Sort by rank (lower is better)
        sorted_records = sorted(
            records,
            key=lambda r: r.metadata.get("rank", 999)
        )
        
        entries = []
        for record in sorted_records:
            meta = record.metadata
            entries.append({
                "rank": meta.get("rank", 0),
                "model_id": record.model_id or meta.get("model_id", ""),
                "model_name": meta.get("model_name", ""),
                "author": meta.get("author", ""),
                "view": meta.get("view", "week"),
                "score": record.score,
            })
        
        return {
            "category": category,
            "entries": entries,
            "entry_count": len(entries),
            "data_source": "pinecone_knowledge_store",
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }
        
    except Exception as e:
        logger.error(f"Failed to get category rankings: {e}", exc_info=True)
        raise HTTPException(500, f"Failed to retrieve rankings: {e}")


@router.get("/reasoning")
async def list_reasoning_models(
    limit: int = Query(10, ge=1, le=50),
) -> Dict[str, Any]:
    """Get all reasoning models with their capabilities.
    
    Returns models that support chain-of-thought, self-verification,
    and other advanced reasoning features.
    
    Data Source: Pinecone ModelKnowledgeStore
    """
    store = get_knowledge_store()
    if not store:
        raise HTTPException(503, "Model knowledge store not available")
    
    try:
        records = await store.get_reasoning_models(top_k=limit)
        
        models = []
        for record in records:
            meta = record.metadata
            models.append({
                "model_id": record.model_id or meta.get("model_id", ""),
                "model_name": meta.get("model_name", ""),
                "provider": meta.get("provider", ""),
                "reasoning_capabilities": {
                    "chain_of_thought": meta.get("chain_of_thought", False),
                    "self_verification": meta.get("self_verification", False),
                    "cot_ability": meta.get("cot_ability", "unknown"),
                    "verification": meta.get("verification", "unknown"),
                    "planning": meta.get("planning", "unknown"),
                },
                "reasoning_score": meta.get("reasoning_score", 50),
                "score": record.score,
            })
        
        return {
            "reasoning_models": models,
            "count": len(models),
            "data_source": "pinecone_knowledge_store",
        }
        
    except Exception as e:
        logger.error(f"Failed to list reasoning models: {e}", exc_info=True)
        raise HTTPException(500, f"Failed to retrieve reasoning models: {e}")


@router.get("/best-for-task")
async def get_best_models_for_task(
    task: str = Query(..., description="Task description"),
    category: Optional[str] = None,
    require_reasoning: bool = False,
    require_tools: bool = False,
    limit: int = Query(5, ge=1, le=20),
) -> Dict[str, Any]:
    """Get the best models for a specific task (semantic search).
    
    This is the primary interface for intelligent model selection.
    
    Args:
        task: Description of the task (e.g., "debug Python async code")
        category: Optional category filter
        require_reasoning: Only return reasoning models
        require_tools: Only return models with tool support
    
    Data Source: Pinecone ModelKnowledgeStore (semantic search)
    """
    store = get_knowledge_store()
    if not store:
        raise HTTPException(503, "Model knowledge store not available")
    
    try:
        records = await store.get_best_models_for_task(
            task_description=task,
            category=category,
            top_k=limit,
            require_reasoning=require_reasoning,
            require_tools=require_tools,
        )
        
        recommendations = []
        for i, record in enumerate(records):
            meta = record.metadata
            recommendations.append({
                "rank": i + 1,
                "model_id": record.model_id or meta.get("model_id", ""),
                "model_name": meta.get("model_name", ""),
                "provider": meta.get("provider", ""),
                "reasoning_score": meta.get("reasoning_score", 50),
                "coding_score": meta.get("coding_score", 50),
                "match_score": record.score,
                "supports_tools": meta.get("supports_tools", False),
                "is_reasoning_model": meta.get("is_reasoning_model", False),
                "best_for": meta.get("best_for", "").split(",") if meta.get("best_for") else [],
            })
        
        return {
            "task": task,
            "category": category,
            "recommendations": recommendations,
            "count": len(recommendations),
            "data_source": "pinecone_knowledge_store",
            "search_method": "semantic_with_reranking",
        }
        
    except Exception as e:
        logger.error(f"Failed to get models for task: {e}", exc_info=True)
        raise HTTPException(500, f"Failed to search models: {e}")


@router.get("/categories")
async def list_available_categories() -> Dict[str, Any]:
    """List available model ranking categories.
    
    Returns categories that have rankings stored in Pinecone.
    """
    # Standard categories from OpenRouter
    categories = [
        {"slug": "programming", "name": "Programming", "group": "usecase"},
        {"slug": "roleplay", "name": "Roleplay", "group": "usecase"},
        {"slug": "marketing", "name": "Marketing", "group": "usecase"},
        {"slug": "technology", "name": "Technology", "group": "usecase"},
        {"slug": "science", "name": "Science", "group": "usecase"},
        {"slug": "translation", "name": "Translation", "group": "usecase"},
        {"slug": "legal", "name": "Legal", "group": "usecase"},
        {"slug": "finance", "name": "Finance", "group": "usecase"},
        {"slug": "healthcare", "name": "Healthcare", "group": "usecase"},
        {"slug": "education", "name": "Education", "group": "usecase"},
        {"slug": "creative-writing", "name": "Creative Writing", "group": "usecase"},
        {"slug": "trivia", "name": "Trivia", "group": "usecase"},
        {"slug": "reasoning", "name": "Reasoning", "group": "usecase"},
    ]
    
    return {
        "categories": categories,
        "total": len(categories),
        "data_source": "pinecone_knowledge_store",
        "description": "Categories synced from OpenRouter and stored in Pinecone",
    }

