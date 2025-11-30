"""Adaptive Model Router for intelligent model selection based on performance.

This module implements adaptive routing that selects models based on:
- Historical performance metrics
- Query domain matching
- Accuracy level requirements
- Available model capabilities
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from ..performance_tracker import performance_tracker, ModelPerformance

logger = logging.getLogger(__name__)


# Model profiles with capabilities and size classification
MODEL_PROFILES: Dict[str, Dict[str, Any]] = {
    # OpenAI models
    "gpt-4o": {
        "size": "large",
        "domains": ["general", "coding", "research", "legal", "medical"],
        "base_quality": 0.9,
        "speed_rating": 0.7,
        "cost_rating": 0.8,
    },
    "gpt-4o-mini": {
        "size": "small",
        "domains": ["general", "coding", "quick-tasks"],
        "base_quality": 0.75,
        "speed_rating": 0.95,
        "cost_rating": 0.95,
    },
    # Anthropic models
    "claude-3-opus-20240229": {
        "size": "large",
        "domains": ["research", "analysis", "writing", "legal"],
        "base_quality": 0.92,
        "speed_rating": 0.6,
        "cost_rating": 0.7,
    },
    "claude-3-sonnet-20240229": {
        "size": "medium",
        "domains": ["general", "coding", "analysis"],
        "base_quality": 0.85,
        "speed_rating": 0.8,
        "cost_rating": 0.85,
    },
    "claude-3-haiku-20240307": {
        "size": "small",
        "domains": ["general", "quick-tasks", "summarization"],
        "base_quality": 0.7,
        "speed_rating": 0.95,
        "cost_rating": 0.95,
    },
    # Google models
    "gemini-2.5-pro": {
        "size": "large",
        "domains": ["research", "coding", "multimodal", "analysis"],
        "base_quality": 0.88,
        "speed_rating": 0.75,
        "cost_rating": 0.75,
    },
    "gemini-2.5-flash": {
        "size": "medium",
        "domains": ["general", "quick-tasks", "coding"],
        "base_quality": 0.78,
        "speed_rating": 0.9,
        "cost_rating": 0.9,
    },
    # xAI models
    "grok-beta": {
        "size": "large",
        "domains": ["general", "reasoning", "real-time"],
        "base_quality": 0.82,
        "speed_rating": 0.8,
        "cost_rating": 0.8,
    },
    # DeepSeek models
    "deepseek-chat": {
        "size": "medium",
        "domains": ["coding", "math", "reasoning"],
        "base_quality": 0.8,
        "speed_rating": 0.85,
        "cost_rating": 0.95,
    },
    "deepseek-reasoner": {
        "size": "large",
        "domains": ["reasoning", "math", "analysis"],
        "base_quality": 0.87,
        "speed_rating": 0.7,
        "cost_rating": 0.9,
    },
    # Default stub
    "stub": {
        "size": "small",
        "domains": ["general"],
        "base_quality": 0.5,
        "speed_rating": 1.0,
        "cost_rating": 1.0,
    },
}

# Domain inference keywords
DOMAIN_KEYWORDS: Dict[str, List[str]] = {
    "medical": ["medical", "health", "disease", "symptom", "treatment", "diagnosis", "patient", "doctor"],
    "legal": ["legal", "law", "court", "attorney", "contract", "liability", "regulation", "statute"],
    "coding": ["code", "program", "function", "debug", "algorithm", "python", "javascript", "api"],
    "research": ["research", "study", "analyze", "investigate", "data", "findings", "methodology"],
    "math": ["calculate", "equation", "formula", "math", "solve", "theorem", "proof"],
    "finance": ["finance", "investment", "stock", "market", "portfolio", "trading", "revenue"],
    "writing": ["write", "essay", "article", "story", "content", "creative", "draft"],
    "general": [],  # Default fallback
}


@dataclass(slots=True)
class ModelScore:
    """Score breakdown for a model candidate."""
    model: str
    total_score: float
    domain_score: float
    performance_score: float
    accuracy_adjustment: float
    speed_adjustment: float
    reasoning: str


@dataclass(slots=True)
class AdaptiveRoutingResult:
    """Result of adaptive model routing."""
    primary_model: str
    secondary_models: List[str]
    role_assignments: Dict[str, str]  # role -> model
    model_scores: List[ModelScore]
    reasoning: str
    recommended_ensemble_size: int


class AdaptiveModelRouter:
    """Routes queries to optimal models based on adaptive scoring."""
    
    def __init__(
        self,
        available_providers: Optional[List[str]] = None,
        model_profiles: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> None:
        """
        Initialize adaptive router.
        
        Args:
            available_providers: List of available provider names
            model_profiles: Optional custom model profiles
        """
        self.available_providers = available_providers or []
        self.profiles = model_profiles or MODEL_PROFILES
    
    def infer_domain(self, query: str) -> str:
        """Infer the domain of a query based on keywords."""
        query_lower = query.lower()
        
        domain_scores: Dict[str, int] = {}
        for domain, keywords in DOMAIN_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in query_lower)
            if score > 0:
                domain_scores[domain] = score
        
        if not domain_scores:
            return "general"
        
        # Return domain with highest score
        return max(domain_scores.items(), key=lambda x: x[1])[0]
    
    def select_models_adaptive(
        self,
        query: str,
        roles: List[str],
        accuracy_level: int,
        *,
        available_models: Optional[List[str]] = None,
        max_models: Optional[int] = None,
    ) -> AdaptiveRoutingResult:
        """
        Adaptive model selection based on query, roles, and accuracy level.
        
        Args:
            query: The refined query to process
            roles: List of role names that need model assignment
            accuracy_level: Slider value 1-5 (1=fastest, 5=most accurate)
            available_models: Optional list of available model names
            max_models: Maximum number of models to select
            
        Returns:
            AdaptiveRoutingResult with model assignments and reasoning
        """
        # Infer domain
        domain = self.infer_domain(query)
        logger.info("Inferred domain: %s for query", domain)
        
        # Get performance snapshot
        perf_snapshot = performance_tracker.snapshot()
        
        # Get available models
        if available_models:
            candidates = [m for m in available_models if m in self.profiles]
        else:
            candidates = list(self.profiles.keys())
        
        if not candidates:
            candidates = ["stub"]
        
        # Score all models
        model_scores: List[ModelScore] = []
        for model in candidates:
            score = self._score_model(
                model,
                domain,
                accuracy_level,
                perf_snapshot.get(model),
            )
            model_scores.append(score)
        
        # Sort by total score (descending)
        model_scores.sort(key=lambda s: s.total_score, reverse=True)
        
        # Determine ensemble size based on accuracy level
        if accuracy_level <= 2:
            ensemble_size = 1
        elif accuracy_level <= 3:
            ensemble_size = 2
        elif accuracy_level <= 4:
            ensemble_size = 3
        else:
            ensemble_size = min(4, len(candidates))
        
        if max_models:
            ensemble_size = min(ensemble_size, max_models)
        
        # Select primary and secondary models
        primary_model = model_scores[0].model if model_scores else "stub"
        secondary_models = [s.model for s in model_scores[1:ensemble_size]]
        
        # Assign models to roles
        role_assignments = self._assign_models_to_roles(
            roles,
            model_scores,
            accuracy_level,
        )
        
        # Build reasoning
        reasoning_parts = [
            f"Domain: {domain}",
            f"Accuracy level: {accuracy_level}",
            f"Primary model: {primary_model} (score: {model_scores[0].total_score:.2f})" if model_scores else "No models available",
        ]
        if secondary_models:
            reasoning_parts.append(f"Secondary models: {', '.join(secondary_models)}")
        
        return AdaptiveRoutingResult(
            primary_model=primary_model,
            secondary_models=secondary_models,
            role_assignments=role_assignments,
            model_scores=model_scores,
            reasoning="; ".join(reasoning_parts),
            recommended_ensemble_size=ensemble_size,
        )
    
    def _score_model(
        self,
        model: str,
        domain: str,
        accuracy_level: int,
        perf: Optional[ModelPerformance],
    ) -> ModelScore:
        """Score a model for the given domain and accuracy level."""
        profile = self.profiles.get(model, self.profiles.get("stub", {}))
        
        # Base domain score
        model_domains = profile.get("domains", ["general"])
        if domain in model_domains:
            domain_score = 1.0
        elif "general" in model_domains:
            domain_score = 0.5
        else:
            domain_score = 0.2
        
        # Performance score from historical data
        if perf:
            # Combine success rate, quality, and domain-specific performance
            success_component = perf.success_rate * 0.4
            quality_component = perf.avg_quality * 0.3
            domain_success = perf.get_domain_success_rate(domain) * 0.3
            performance_score = success_component + quality_component + domain_success
        else:
            # New model: use base quality from profile
            performance_score = profile.get("base_quality", 0.5)
        
        # Accuracy adjustment based on slider
        # High accuracy = prefer larger models, lower speed requirement
        # Low accuracy = prefer smaller models, higher speed
        size = profile.get("size", "medium")
        speed_rating = profile.get("speed_rating", 0.7)
        
        if accuracy_level >= 4:
            # High accuracy mode: prefer large models
            if size == "large":
                accuracy_adjustment = 0.3
            elif size == "medium":
                accuracy_adjustment = 0.1
            else:
                accuracy_adjustment = -0.1  # Penalize small models
            speed_adjustment = 0.0  # Don't care about speed
        elif accuracy_level <= 2:
            # Speed mode: prefer small/fast models
            if size == "small":
                accuracy_adjustment = 0.2
            elif size == "medium":
                accuracy_adjustment = 0.1
            else:
                accuracy_adjustment = -0.2  # Penalize large models for speed mode
            speed_adjustment = speed_rating * 0.3
        else:
            # Balanced mode
            accuracy_adjustment = 0.0
            speed_adjustment = speed_rating * 0.15
        
        # Calculate total score
        total_score = (
            domain_score * 0.25
            + performance_score * 0.4
            + accuracy_adjustment
            + speed_adjustment
        )
        
        # Clamp to 0-1
        total_score = max(0.0, min(1.0, total_score))
        
        reasoning = (
            f"domain={domain_score:.2f}, perf={performance_score:.2f}, "
            f"acc_adj={accuracy_adjustment:.2f}, speed_adj={speed_adjustment:.2f}"
        )
        
        return ModelScore(
            model=model,
            total_score=total_score,
            domain_score=domain_score,
            performance_score=performance_score,
            accuracy_adjustment=accuracy_adjustment,
            speed_adjustment=speed_adjustment,
            reasoning=reasoning,
        )
    
    def _assign_models_to_roles(
        self,
        roles: List[str],
        model_scores: List[ModelScore],
        accuracy_level: int,
    ) -> Dict[str, str]:
        """Assign models to roles based on role requirements and model capabilities."""
        assignments: Dict[str, str] = {}
        
        if not model_scores:
            return {role: "stub" for role in roles}
        
        # Role-to-capability mapping
        role_preferences: Dict[str, List[str]] = {
            "coordinator": ["claude-3-opus-20240229", "gpt-4o", "gemini-2.5-pro"],
            "executive": ["gpt-4o", "claude-3-opus-20240229"],
            "quality_manager": ["claude-3-sonnet-20240229", "gpt-4o-mini"],
            "lead_researcher": ["gemini-2.5-pro", "claude-3-sonnet-20240229"],
            "fact_checker": ["gpt-4o-mini", "deepseek-chat"],
            "synthesizer": ["gpt-4o", "claude-3-opus-20240229"],
            "assistant": ["gpt-4o-mini", "claude-3-haiku-20240307"],
        }
        
        available_models = [s.model for s in model_scores]
        
        for role in roles:
            # Check role preferences
            prefs = role_preferences.get(role, [])
            assigned = None
            
            # Try preferred models first
            for pref in prefs:
                if pref in available_models:
                    assigned = pref
                    break
            
            # Fall back to role-level matching
            if not assigned:
                role_lower = role.lower()
                if "executive" in role_lower or "coordinator" in role_lower:
                    # Use top-scoring model for leadership roles
                    assigned = model_scores[0].model
                elif "assistant" in role_lower:
                    # Use smaller/faster model for assistant roles
                    small_models = [s.model for s in model_scores if self.profiles.get(s.model, {}).get("size") == "small"]
                    assigned = small_models[0] if small_models else model_scores[-1].model
                else:
                    # Use second-best model for specialist roles
                    assigned = model_scores[1].model if len(model_scores) > 1 else model_scores[0].model
            
            # Apply accuracy level adjustments
            if accuracy_level >= 5 and role in ["executive", "coordinator", "synthesizer"]:
                # For max accuracy, try to use the best model for key roles
                assigned = model_scores[0].model
            
            assignments[role] = assigned or "stub"
            
            # For high accuracy, assign secondary model for cross-checking
            if accuracy_level == 5:
                secondary_key = f"{role}_secondary"
                secondary_models = [s.model for s in model_scores if s.model != assigned]
                if secondary_models:
                    assignments[secondary_key] = secondary_models[0]
        
        return assignments
    
    def cascade_selection(
        self,
        query: str,
        initial_model: str,
        confidence_threshold: float = 0.7,
        available_models: Optional[List[str]] = None,
    ) -> Tuple[str, bool]:
        """
        Cascading model selection: start with lightweight, escalate if confidence is low.
        
        Args:
            query: The query to process
            initial_model: Initial lightweight model to try
            confidence_threshold: Minimum confidence to accept result
            available_models: Available model names
            
        Returns:
            Tuple of (selected_model, escalated)
        """
        # Get model size
        profile = self.profiles.get(initial_model, {})
        size = profile.get("size", "medium")
        
        # If already using large model, no escalation needed
        if size == "large":
            return (initial_model, False)
        
        # Check historical confidence for this model
        perf = performance_tracker.snapshot().get(initial_model)
        if perf:
            avg_quality = perf.avg_quality
            if avg_quality >= confidence_threshold:
                # Model historically performs well, use it
                return (initial_model, False)
        
        # Escalate to larger model
        escalation_chain = {
            "gpt-4o-mini": "gpt-4o",
            "claude-3-haiku-20240307": "claude-3-sonnet-20240229",
            "gemini-2.5-flash": "gemini-2.5-pro",
            "deepseek-chat": "deepseek-reasoner",
        }
        
        escalated_model = escalation_chain.get(initial_model)
        if escalated_model and (available_models is None or escalated_model in available_models):
            logger.info(
                "Cascading from %s to %s (confidence below %.2f)",
                initial_model,
                escalated_model,
                confidence_threshold,
            )
            return (escalated_model, True)
        
        # No escalation available
        return (initial_model, False)


# Global router instance
_adaptive_router: Optional[AdaptiveModelRouter] = None


def get_adaptive_router() -> AdaptiveModelRouter:
    """Get the global adaptive router instance."""
    global _adaptive_router
    if _adaptive_router is None:
        _adaptive_router = AdaptiveModelRouter()
    return _adaptive_router


def select_models_adaptive(
    refined_query: str,
    roles: List[str],
    accuracy_level: int,
    *,
    available_models: Optional[List[str]] = None,
) -> Dict[str, str]:
    """
    Convenience function for adaptive model selection.
    
    Args:
        refined_query: The refined query to process
        roles: List of role names that need model assignment
        accuracy_level: Slider value 1-5 (1=fastest, 5=most accurate)
        available_models: Optional list of available model names
        
    Returns:
        Dictionary mapping role names to model names
    """
    router = get_adaptive_router()
    result = router.select_models_adaptive(
        refined_query,
        roles,
        accuracy_level,
        available_models=available_models,
    )
    return result.role_assignments


def infer_domain(query: str) -> str:
    """Infer the domain of a query."""
    router = get_adaptive_router()
    return router.infer_domain(query)

