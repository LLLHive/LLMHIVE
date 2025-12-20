"""
Model Knowledge Sync - Populates the Model Knowledge Store from OpenRouter data.

This module bridges the OpenRouter sync (which fetches model data and rankings)
with the Model Knowledge Store (which the orchestrator uses for decisions).

It transforms raw model data into rich profiles with:
- Capability scores derived from model characteristics
- Reasoning model identification and analysis
- Strength/weakness inference from model features
- Category rankings from OpenRouter leaderboards
"""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Try to import required modules
try:
    from .model_knowledge_store import (
        ModelKnowledgeStore,
        ModelProfile,
        ModelKnowledgeType,
        get_model_knowledge_store,
    )
    KNOWLEDGE_STORE_AVAILABLE = True
except ImportError as e:
    KNOWLEDGE_STORE_AVAILABLE = False
    logger.warning(f"Model knowledge store not available: {e}")


# Known reasoning models and their characteristics
REASONING_MODEL_PATTERNS = {
    "o1": {
        "chain_of_thought": True,
        "self_verification": True,
        "multi_step_planning": True,
        "reasoning_score": 95,
        "strengths": ["Complex reasoning", "Mathematical proofs", "Code analysis", "Multi-step problems"],
        "weaknesses": ["Slower response time", "Higher cost", "Less suitable for simple queries"],
    },
    "o3": {
        "chain_of_thought": True,
        "self_verification": True,
        "multi_step_planning": True,
        "reasoning_score": 98,
        "strengths": ["Advanced reasoning", "Scientific analysis", "Complex code", "Research tasks"],
        "weaknesses": ["Very slow", "Very expensive", "Overkill for simple tasks"],
    },
    "claude-3.5-sonnet": {
        "chain_of_thought": True,
        "self_verification": False,
        "multi_step_planning": True,
        "reasoning_score": 88,
        "strengths": ["Balanced reasoning", "Code generation", "Long context", "Nuanced responses"],
        "weaknesses": ["Occasional verbosity", "Can be overly cautious"],
    },
    "claude-sonnet-4": {
        "chain_of_thought": True,
        "self_verification": True,
        "multi_step_planning": True,
        "reasoning_score": 92,
        "strengths": ["Strong reasoning", "Excellent coding", "Good judgment", "Balanced speed/quality"],
        "weaknesses": ["Can be verbose", "Moderate cost"],
    },
    "claude-opus-4": {
        "chain_of_thought": True,
        "self_verification": True,
        "multi_step_planning": True,
        "reasoning_score": 95,
        "strengths": ["Deep analysis", "Complex reasoning", "Research quality", "Nuanced understanding"],
        "weaknesses": ["Slower", "Higher cost", "Can overthink simple tasks"],
    },
    "gpt-4o": {
        "chain_of_thought": True,
        "self_verification": False,
        "multi_step_planning": True,
        "reasoning_score": 85,
        "strengths": ["Fast", "Multimodal", "Good balance of capabilities", "Reliable"],
        "weaknesses": ["Less deep reasoning than o1", "Can be generic"],
    },
    "gpt-4-turbo": {
        "chain_of_thought": True,
        "self_verification": False,
        "multi_step_planning": True,
        "reasoning_score": 82,
        "strengths": ["Large context", "Fast", "Good code", "Reliable"],
        "weaknesses": ["Not latest model", "Moderate reasoning"],
    },
    "gemini-2.0-pro": {
        "chain_of_thought": True,
        "self_verification": True,
        "multi_step_planning": True,
        "reasoning_score": 90,
        "strengths": ["Multimodal", "Large context", "Strong reasoning", "Fast"],
        "weaknesses": ["Occasional inconsistency", "Can be verbose"],
    },
    "deepseek-v3": {
        "chain_of_thought": True,
        "self_verification": True,
        "multi_step_planning": True,
        "reasoning_score": 88,
        "strengths": ["Cost effective", "Strong coding", "Good reasoning", "Open weights"],
        "weaknesses": ["Less established", "Occasional errors"],
    },
    "qwen": {
        "chain_of_thought": True,
        "self_verification": False,
        "multi_step_planning": True,
        "reasoning_score": 80,
        "strengths": ["Multilingual", "Cost effective", "Good general performance"],
        "weaknesses": ["Less known in West", "Variable quality"],
    },
}

# Category to capability mapping
CATEGORY_CAPABILITIES = {
    "programming": ["coding_score", "reasoning_score"],
    "reasoning": ["reasoning_score"],
    "science": ["reasoning_score", "accuracy_score"],
    "creative-writing": ["creative_score"],
    "roleplay": ["creative_score"],
    "marketing": ["creative_score"],
    "legal": ["accuracy_score", "reasoning_score"],
    "medical": ["accuracy_score", "reasoning_score"],
    "translation": ["accuracy_score"],
    "data-analysis": ["reasoning_score", "accuracy_score"],
    "tool-call": ["supports_tools"],
    "long-context": ["context_length"],
}


class ModelKnowledgeSync:
    """
    Syncs model data from OpenRouter to the Model Knowledge Store.
    
    This is called after OpenRouter sync completes to ensure the orchestrator
    has the latest intelligence about available models.
    """
    
    def __init__(self, knowledge_store: Optional[ModelKnowledgeStore] = None):
        """Initialize the sync."""
        if KNOWLEDGE_STORE_AVAILABLE:
            self.store = knowledge_store or get_model_knowledge_store()
        else:
            self.store = None
            logger.warning("Model knowledge store not available for sync")
    
    async def sync_models_to_knowledge(
        self,
        models: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Transform OpenRouter model data into Model Knowledge profiles.
        
        Args:
            models: List of model dictionaries from OpenRouter API
            
        Returns:
            Sync report with counts
        """
        if not self.store:
            return {"status": "skipped", "reason": "Knowledge store not available"}
        
        report = {
            "total_models": len(models),
            "profiles_created": 0,
            "reasoning_models_identified": 0,
            "errors": [],
        }
        
        for model in models:
            try:
                profile = self._create_model_profile(model)
                record_id = await self.store.store_model_profile(profile)
                
                if record_id:
                    report["profiles_created"] += 1
                    
                    if profile.is_reasoning_model:
                        report["reasoning_models_identified"] += 1
                        
                        # Store additional reasoning analysis
                        await self._store_reasoning_analysis(profile, model)
                        
            except Exception as e:
                report["errors"].append(f"Model {model.get('id', 'unknown')}: {str(e)}")
                logger.error(f"Failed to sync model {model.get('id')}: {e}")
        
        logger.info(
            f"Model knowledge sync complete: {report['profiles_created']} profiles, "
            f"{report['reasoning_models_identified']} reasoning models"
        )
        
        return report
    
    async def sync_rankings_to_knowledge(
        self,
        category: str,
        rankings: List[Dict[str, Any]],
        view: str = "week",
    ) -> Dict[str, Any]:
        """
        Store category rankings from OpenRouter in the knowledge store.
        
        Args:
            category: Category slug (e.g., "programming", "reasoning")
            rankings: List of ranking entries from OpenRouter
            view: Time period ("week", "month", etc.)
            
        Returns:
            Sync report
        """
        if not self.store:
            return {"status": "skipped", "reason": "Knowledge store not available"}
        
        try:
            record_ids = await self.store.store_category_ranking(
                category=category,
                rankings=rankings,
                view=view,
            )
            
            return {
                "category": category,
                "rankings_stored": len(record_ids),
                "status": "success",
            }
            
        except Exception as e:
            logger.error(f"Failed to sync rankings for {category}: {e}")
            return {
                "category": category,
                "status": "error",
                "error": str(e),
            }
    
    def _create_model_profile(self, model: Dict[str, Any]) -> ModelProfile:
        """
        Create a ModelProfile from OpenRouter model data.
        
        Infers capabilities, strengths, and weaknesses from model characteristics.
        """
        model_id = model.get("id", "")
        model_name = model.get("name", model_id.split("/")[-1])
        
        # Extract provider
        provider = model_id.split("/")[0] if "/" in model_id else "unknown"
        
        # Determine if this is a reasoning model
        is_reasoning = self._is_reasoning_model(model_id, model)
        reasoning_info = self._get_reasoning_info(model_id)
        
        # Calculate capability scores
        reasoning_score = reasoning_info.get("reasoning_score", 50)
        coding_score = self._estimate_coding_score(model)
        creative_score = self._estimate_creative_score(model)
        accuracy_score = self._estimate_accuracy_score(model)
        speed_score = self._estimate_speed_score(model)
        cost_efficiency = self._estimate_cost_efficiency(model)
        
        # Get context length
        context_length = model.get("context_length", 8192)
        
        # Get capabilities
        supports_tools = self._supports_tools(model)
        supports_vision = self._supports_vision(model)
        
        # Get strengths and weaknesses
        strengths = reasoning_info.get("strengths", [])
        weaknesses = reasoning_info.get("weaknesses", [])
        
        if not strengths:
            strengths = self._infer_strengths(model, is_reasoning, supports_tools, context_length)
        if not weaknesses:
            weaknesses = self._infer_weaknesses(model, is_reasoning)
        
        # Determine best use cases
        best_for = self._determine_best_for(
            is_reasoning, supports_tools, supports_vision, context_length, coding_score, creative_score
        )
        avoid_for = self._determine_avoid_for(is_reasoning, speed_score, cost_efficiency)
        
        return ModelProfile(
            model_id=model_id,
            model_name=model_name,
            provider=provider,
            reasoning_score=reasoning_score,
            coding_score=coding_score,
            creative_score=creative_score,
            accuracy_score=accuracy_score,
            speed_score=speed_score,
            cost_efficiency=cost_efficiency,
            context_length=context_length,
            supports_tools=supports_tools,
            supports_vision=supports_vision,
            supports_streaming=True,  # Most models support streaming
            is_reasoning_model=is_reasoning,
            chain_of_thought=reasoning_info.get("chain_of_thought", is_reasoning),
            self_verification=reasoning_info.get("self_verification", False),
            multi_step_planning=reasoning_info.get("multi_step_planning", is_reasoning),
            strengths=strengths,
            weaknesses=weaknesses,
            best_for=best_for,
            avoid_for=avoid_for,
            last_updated=0.0,  # Will be set by store
            source="openrouter",
        )
    
    def _is_reasoning_model(self, model_id: str, model: Dict[str, Any]) -> bool:
        """Determine if a model is a reasoning model."""
        model_id_lower = model_id.lower()
        
        # Check for known reasoning model patterns
        reasoning_indicators = [
            "o1", "o3", "reason", "think", "cot",
            "opus", "sonnet-4", "deepseek-v3", "qwen-2.5"
        ]
        
        for indicator in reasoning_indicators:
            if indicator in model_id_lower:
                return True
        
        # Check model description if available
        description = model.get("description", "").lower()
        if any(word in description for word in ["reasoning", "chain-of-thought", "step-by-step"]):
            return True
        
        return False
    
    def _get_reasoning_info(self, model_id: str) -> Dict[str, Any]:
        """Get known reasoning capabilities for a model."""
        model_id_lower = model_id.lower()
        
        for pattern, info in REASONING_MODEL_PATTERNS.items():
            if pattern.lower() in model_id_lower:
                return info
        
        return {}
    
    def _estimate_coding_score(self, model: Dict[str, Any]) -> int:
        """Estimate coding capability from model characteristics."""
        model_id = model.get("id", "").lower()
        
        # High coding scores for known coding models
        if any(x in model_id for x in ["codestral", "deepseek-coder", "code", "starcoder"]):
            return 90
        if any(x in model_id for x in ["gpt-4", "claude-3", "gemini"]):
            return 80
        if any(x in model_id for x in ["o1", "o3", "sonnet-4", "opus-4"]):
            return 85
        
        return 60
    
    def _estimate_creative_score(self, model: Dict[str, Any]) -> int:
        """Estimate creative capability."""
        model_id = model.get("id", "").lower()
        
        if any(x in model_id for x in ["claude", "gpt-4"]):
            return 80
        if any(x in model_id for x in ["llama", "mistral"]):
            return 70
        
        return 60
    
    def _estimate_accuracy_score(self, model: Dict[str, Any]) -> int:
        """Estimate accuracy/reliability."""
        model_id = model.get("id", "").lower()
        
        if any(x in model_id for x in ["o1", "o3", "opus"]):
            return 90
        if any(x in model_id for x in ["gpt-4", "claude-3", "gemini-pro"]):
            return 82
        
        return 70
    
    def _estimate_speed_score(self, model: Dict[str, Any]) -> int:
        """Estimate response speed (higher = faster)."""
        model_id = model.get("id", "").lower()
        
        # Reasoning models are slower
        if any(x in model_id for x in ["o1", "o3", "opus"]):
            return 40
        
        # Flash/turbo models are fast
        if any(x in model_id for x in ["flash", "turbo", "mini", "haiku"]):
            return 90
        
        return 65
    
    def _estimate_cost_efficiency(self, model: Dict[str, Any]) -> int:
        """Estimate cost efficiency (higher = cheaper per quality)."""
        pricing = model.get("pricing", {})
        
        if not pricing:
            return 50
        
        # Calculate cost per 1M tokens (input + output average)
        prompt_cost = float(pricing.get("prompt", "0").replace("$", ""))
        completion_cost = float(pricing.get("completion", "0").replace("$", ""))
        avg_cost = (prompt_cost + completion_cost) / 2
        
        if avg_cost == 0:
            return 90  # Free
        elif avg_cost < 1:
            return 80
        elif avg_cost < 5:
            return 60
        elif avg_cost < 20:
            return 40
        else:
            return 20
    
    def _supports_tools(self, model: Dict[str, Any]) -> bool:
        """Check if model supports function calling."""
        model_id = model.get("id", "").lower()
        
        # Known tool-supporting models
        tool_models = ["gpt-4", "gpt-3.5", "claude-3", "gemini", "mistral", "command"]
        return any(x in model_id for x in tool_models)
    
    def _supports_vision(self, model: Dict[str, Any]) -> bool:
        """Check if model supports vision/images."""
        model_id = model.get("id", "").lower()
        
        vision_indicators = ["vision", "gpt-4o", "gemini", "claude-3", "llava"]
        return any(x in model_id for x in vision_indicators)
    
    def _infer_strengths(
        self,
        model: Dict[str, Any],
        is_reasoning: bool,
        supports_tools: bool,
        context_length: int,
    ) -> List[str]:
        """Infer model strengths from characteristics."""
        strengths = []
        
        if is_reasoning:
            strengths.append("Complex reasoning")
        if supports_tools:
            strengths.append("Function calling")
        if context_length >= 100000:
            strengths.append("Very long context")
        elif context_length >= 32000:
            strengths.append("Long context")
        
        model_id = model.get("id", "").lower()
        if "code" in model_id:
            strengths.append("Code generation")
        if "flash" in model_id or "turbo" in model_id:
            strengths.append("Fast response")
        
        return strengths or ["General purpose"]
    
    def _infer_weaknesses(self, model: Dict[str, Any], is_reasoning: bool) -> List[str]:
        """Infer model weaknesses."""
        weaknesses = []
        
        if is_reasoning:
            weaknesses.append("Slower responses")
            weaknesses.append("Higher cost")
        
        model_id = model.get("id", "").lower()
        if "mini" in model_id or "flash" in model_id:
            weaknesses.append("Less thorough analysis")
        
        return weaknesses or ["None identified"]
    
    def _determine_best_for(
        self,
        is_reasoning: bool,
        supports_tools: bool,
        supports_vision: bool,
        context_length: int,
        coding_score: int,
        creative_score: int,
    ) -> List[str]:
        """Determine best use cases for a model."""
        best_for = []
        
        if is_reasoning:
            best_for.extend(["Complex analysis", "Multi-step problems", "Research"])
        if supports_tools:
            best_for.append("Agent tasks")
        if supports_vision:
            best_for.append("Image analysis")
        if context_length >= 100000:
            best_for.append("Document processing")
        if coding_score >= 80:
            best_for.append("Code generation")
        if creative_score >= 80:
            best_for.append("Creative writing")
        
        return best_for or ["General tasks"]
    
    def _determine_avoid_for(
        self,
        is_reasoning: bool,
        speed_score: int,
        cost_efficiency: int,
    ) -> List[str]:
        """Determine what to avoid using this model for."""
        avoid_for = []
        
        if is_reasoning:
            avoid_for.append("Simple factual queries")
            avoid_for.append("High-volume processing")
        if speed_score < 50:
            avoid_for.append("Real-time applications")
        if cost_efficiency < 40:
            avoid_for.append("Budget-constrained tasks")
        
        return avoid_for or ["None specified"]
    
    async def _store_reasoning_analysis(
        self,
        profile: ModelProfile,
        model: Dict[str, Any],
    ) -> None:
        """Store detailed reasoning analysis for a reasoning model."""
        if not self.store:
            return
        
        analysis = {
            "chain_of_thought_ability": "strong" if profile.chain_of_thought else "basic",
            "self_verification": "yes" if profile.self_verification else "no",
            "multi_step_planning": "yes" if profile.multi_step_planning else "limited",
            "recommended_for": profile.best_for,
            "not_recommended_for": profile.avoid_for,
            "notes": f"Reasoning score: {profile.reasoning_score}/100. "
                     f"Context: {profile.context_length:,} tokens.",
        }
        
        await self.store.store_reasoning_model_analysis(
            model_id=profile.model_id,
            model_name=profile.model_name,
            analysis=analysis,
        )


async def sync_openrouter_to_knowledge(
    models: List[Dict[str, Any]],
    categories_rankings: Optional[Dict[str, List[Dict[str, Any]]]] = None,
) -> Dict[str, Any]:
    """
    Main entry point: Sync all OpenRouter data to Model Knowledge Store.
    
    Call this after OpenRouter sync completes to update the orchestrator's
    model intelligence.
    
    Args:
        models: List of models from OpenRouter API
        categories_rankings: Dict of category -> rankings list
        
    Returns:
        Combined sync report
    """
    if not KNOWLEDGE_STORE_AVAILABLE:
        logger.warning("Model knowledge store not available, skipping sync")
        return {"status": "skipped", "reason": "Knowledge store not available"}
    
    sync = ModelKnowledgeSync()
    
    report = {
        "models": {},
        "rankings": {},
    }
    
    # Sync model profiles
    if models:
        report["models"] = await sync.sync_models_to_knowledge(models)
    
    # Sync category rankings
    if categories_rankings:
        for category, rankings in categories_rankings.items():
            report["rankings"][category] = await sync.sync_rankings_to_knowledge(
                category=category,
                rankings=rankings,
            )
    
    logger.info(f"OpenRouter to Knowledge sync complete: {report}")
    return report

