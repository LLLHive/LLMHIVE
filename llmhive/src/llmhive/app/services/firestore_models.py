"""Firestore Model Catalog Service.

Connects the orchestrator to the ModelDB's Firestore `model_catalog` collection,
which contains 353+ models with 262 enriched columns of research data.

This provides persistent, enriched model data for intelligent routing decisions.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Try to import Firestore
try:
    from google.cloud import firestore
    FIRESTORE_AVAILABLE = True
except ImportError:
    FIRESTORE_AVAILABLE = False
    firestore = None  # type: ignore
    logger.warning("Firestore not available for model catalog")


class FirestoreModelCatalogService:
    """Service to access the ModelDB's enriched model catalog from Firestore.
    
    The `model_catalog` collection contains:
    - 353+ models from OpenRouter
    - 262+ columns of enriched data including:
      - LMSYS Arena Elo scores
      - HuggingFace Open LLM Leaderboard benchmarks
      - OpenRouter rankings by category
      - Strengths, weaknesses, best use cases
      - Eval harness scores (programming, language, tool use)
      - Telemetry data (latency, TPS)
    """
    
    COLLECTION = "model_catalog"
    CACHE_TTL_SECONDS = 300  # 5 minutes
    
    def __init__(self):
        self.db = None
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._cache_timestamp: Optional[datetime] = None
        self._initialize()
    
    def _initialize(self) -> None:
        """Initialize Firestore client."""
        if not FIRESTORE_AVAILABLE:
            logger.warning("Firestore not available, model catalog will use fallback")
            return
        
        try:
            project_id = os.getenv(
                "GOOGLE_CLOUD_PROJECT", 
                os.getenv("GCP_PROJECT", "llmhive-orchestrator")
            )
            self.db = firestore.Client(project=project_id)
            logger.info("Firestore model catalog connected to project: %s", project_id)
        except Exception as e:
            logger.error("Failed to connect to Firestore model catalog: %s", e)
            self.db = None
    
    def is_available(self) -> bool:
        """Check if Firestore model catalog is available."""
        return self.db is not None
    
    def _is_cache_valid(self) -> bool:
        """Check if cache is still valid."""
        if not self._cache or not self._cache_timestamp:
            return False
        age = (datetime.now(timezone.utc) - self._cache_timestamp).total_seconds()
        return age < self.CACHE_TTL_SECONDS
    
    def get_all_models(self, use_cache: bool = True) -> List[Dict[str, Any]]:
        """Get all models from the catalog.
        
        Returns list of model dictionaries with enriched data.
        """
        if use_cache and self._is_cache_valid():
            return list(self._cache.values())
        
        if not self.db:
            logger.warning("Firestore not available, returning empty list")
            return []
        
        try:
            models = []
            docs = self.db.collection(self.COLLECTION).stream()
            
            for doc in docs:
                data = doc.to_dict()
                model_id = data.get("openrouter_slug") or doc.id
                self._cache[model_id] = data
                models.append(data)
            
            self._cache_timestamp = datetime.now(timezone.utc)
            logger.info("Loaded %d models from Firestore model_catalog", len(models))
            return models
            
        except Exception as e:
            logger.error("Failed to fetch models from Firestore: %s", e)
            return list(self._cache.values()) if self._cache else []
    
    def get_model(self, model_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific model by ID (openrouter_slug)."""
        # Check cache first
        if model_id in self._cache and self._is_cache_valid():
            return self._cache[model_id]
        
        if not self.db:
            return None
        
        try:
            # Query by openrouter_slug
            query = (
                self.db.collection(self.COLLECTION)
                .where("openrouter_slug", "==", model_id)
                .limit(1)
            )
            
            docs = list(query.stream())
            if docs:
                data = docs[0].to_dict()
                self._cache[model_id] = data
                return data
            
            return None
            
        except Exception as e:
            logger.error("Failed to fetch model %s: %s", model_id, e)
            return self._cache.get(model_id)
    
    def get_models_by_provider(self, provider: str) -> List[Dict[str, Any]]:
        """Get all models from a specific provider."""
        if not self.db:
            return []
        
        try:
            query = (
                self.db.collection(self.COLLECTION)
                .where("provider_name", "==", provider)
            )
            
            return [doc.to_dict() for doc in query.stream()]
            
        except Exception as e:
            logger.error("Failed to fetch models for provider %s: %s", provider, e)
            return []
    
    def get_top_models_by_category(
        self,
        category: str,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Get top-ranked models for a category.
        
        Categories include: programming, roleplay, marketing, science, etc.
        Uses the `openrouter_rank_*` or `derived_rank_*` fields.
        """
        if not self.db:
            return []
        
        # Map category to rank field
        rank_field_map = {
            "programming": "arena_rank",
            "context_length": "derived_rank_context",
            "cost": "derived_rank_price_input",
            "leaderboard": "hf_ollb_rank_overall",
        }
        
        rank_field = rank_field_map.get(category, f"openrouter_rank_{category}")
        
        try:
            query = (
                self.db.collection(self.COLLECTION)
                .where(rank_field, ">=", 1)
                .order_by(rank_field)
                .limit(limit)
            )
            
            return [doc.to_dict() for doc in query.stream()]
            
        except Exception as e:
            logger.error("Failed to fetch top models for %s: %s", category, e)
            return []
    
    def get_reasoning_models(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get models with strong reasoning capabilities."""
        all_models = self.get_all_models()
        
        # Filter for reasoning models based on enriched data
        reasoning_models = []
        for model in all_models:
            # Check for reasoning indicators
            name = (model.get("model_name") or "").lower()
            slug = (model.get("openrouter_slug") or "").lower()
            
            is_reasoning = any([
                "o1" in slug or "o3" in slug,
                "opus" in slug,
                "sonnet-4" in slug,
                "reasoning" in name,
                "think" in name,
            ])
            
            if is_reasoning:
                reasoning_models.append(model)
        
        return reasoning_models[:limit]
    
    def get_model_profiles_for_orchestrator(self) -> Dict[str, Dict[str, Any]]:
        """Get model profiles formatted for the orchestrator's adaptive router.
        
        Transforms Firestore data into the format expected by MODEL_PROFILES.
        """
        models = self.get_all_models()
        profiles = {}
        
        for model in models:
            slug = model.get("openrouter_slug")
            if not slug:
                continue
            
            # Extract capability scores from enriched data
            arena_score = model.get("arena_score") or 0
            hf_avg = model.get("hf_ollb_avg") or 0
            
            # Determine domains based on strengths and rankings
            domains = ["general"]
            if model.get("supports_function_calling"):
                domains.append("coding")
            if model.get("arena_rank") and model.get("arena_rank") <= 20:
                domains.append("research")
            
            # Calculate quality score from benchmarks
            base_quality = 0.5
            if arena_score > 1200:
                base_quality = 0.85 + (arena_score - 1200) / 1000
            elif hf_avg > 70:
                base_quality = 0.7 + (hf_avg - 70) / 100
            
            # Extract pricing
            price_input = model.get("price_input_usd_per_1m") or 0
            price_output = model.get("price_output_usd_per_1m") or 0
            
            # Cost rating (higher = cheaper)
            avg_cost = (price_input + price_output) / 2 if price_output else price_input
            if avg_cost == 0:
                cost_rating = 1.0
            elif avg_cost < 1:
                cost_rating = 0.95
            elif avg_cost < 5:
                cost_rating = 0.8
            elif avg_cost < 20:
                cost_rating = 0.6
            else:
                cost_rating = 0.4
            
            profiles[slug] = {
                "size": "large" if model.get("max_context_tokens", 0) > 100000 else "medium",
                "domains": domains,
                "base_quality": min(0.99, base_quality),
                "speed_rating": 0.7,  # Could be enhanced with telemetry data
                "cost_rating": cost_rating,
                "cost_per_1m_input": price_input,
                "cost_per_1m_output": price_output,
                "family": model.get("model_family", ""),
                "author": model.get("provider_name", ""),
                # Enriched data
                "arena_score": arena_score,
                "arena_rank": model.get("arena_rank"),
                "hf_avg": hf_avg,
                "strengths": model.get("strengths", ""),
                "weaknesses": model.get("weaknesses", ""),
                "context_length": model.get("max_context_tokens", 8192),
                "supports_tools": model.get("supports_function_calling", False),
                "supports_vision": model.get("supports_vision", False),
            }
        
        logger.info("Created %d model profiles from Firestore", len(profiles))
        return profiles
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the model catalog."""
        if not self.db:
            return {
                "available": False,
                "model_count": 0,
                "cache_size": len(self._cache),
            }
        
        try:
            # Count models
            count = sum(1 for _ in self.db.collection(self.COLLECTION).limit(1000).stream())
            
            return {
                "available": True,
                "model_count": count,
                "cache_size": len(self._cache),
                "cache_valid": self._is_cache_valid(),
            }
            
        except Exception as e:
            logger.error("Failed to get model catalog stats: %s", e)
            return {
                "available": False,
                "error": str(e),
                "cache_size": len(self._cache),
            }


# Singleton instance
_model_catalog_service: Optional[FirestoreModelCatalogService] = None


def get_firestore_model_catalog() -> FirestoreModelCatalogService:
    """Get the singleton Firestore model catalog service."""
    global _model_catalog_service
    if _model_catalog_service is None:
        _model_catalog_service = FirestoreModelCatalogService()
    return _model_catalog_service

