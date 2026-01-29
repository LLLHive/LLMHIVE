"""Adaptive model router for intelligent model selection and fallback."""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

from ..model_registry import ModelRegistry, ModelProfile
from ..performance_tracker import performance_tracker, ModelPerformance
from ..services.base import LLMProvider, LLMResult

# Import orchestration engines
from .hrm import HRMRegistry, HRMRole
from .prompt_diffusion import PromptDiffusion
from .deepconf import DeepConf
from .adaptive_ensemble import AdaptiveEnsemble

logger = logging.getLogger(__name__)


@dataclass
class RoutingDecision:
    """Represents a routing decision made by the router."""
    
    selected_models: List[str]
    primary_model: str
    fallback_models: List[str]
    reasoning: str
    domain: str
    confidence: float
    use_ensemble: bool = False
    ensemble_size: int = 1


@dataclass
class ModelResponse:
    """Response from a model with quality assessment."""
    
    result: LLMResult
    model: str
    quality_score: float  # 0.0-1.0
    confidence: float  # 0.0-1.0
    passed_quality_check: bool
    failure_reason: Optional[str] = None


class ModelRouter:
    """
    Adaptive model router for intelligent model selection, fallback, and ensemble.
    
    Features:
    - Dynamic model selection based on query analysis and performance
    - Automatic fallback on failure or low quality
    - Parallel ensemble for important queries
    - Quality-based voting/scoring
    """
    
    def __init__(
        self,
        model_registry: ModelRegistry,
        providers: Dict[str, LLMProvider],
        *,
        min_quality_threshold: float = 0.5,
        enable_fallback: bool = True,
        enable_ensemble: bool = True,
        max_fallback_attempts: int = 2,
    ):
        """
        Initialize model router.
        
        Args:
            model_registry: Model registry for model selection
            providers: Dictionary of LLM providers
            min_quality_threshold: Minimum quality score to accept (0.0-1.0)
            enable_fallback: Enable automatic fallback on failure
            enable_ensemble: Enable parallel ensemble for important queries
            max_fallback_attempts: Maximum number of fallback attempts
        """
        self.model_registry = model_registry
        self.providers = providers
        self.min_quality_threshold = min_quality_threshold
        self.enable_fallback = enable_fallback
        self.enable_ensemble = enable_ensemble
        self.max_fallback_attempts = max_fallback_attempts
        self.routing_history: List[RoutingDecision] = []
        
        # Initialize orchestration engines
        self.hrm_registry = HRMRegistry()
        self.prompt_diffusion = PromptDiffusion(providers)
        self.deepconf = DeepConf(providers, performance_tracker=performance_tracker)
        self.adaptive_ensemble = AdaptiveEnsemble(providers)
    
    def route(
        self,
        query: str,
        *,
        mode: str = "accuracy",
        required_capabilities: Optional[Sequence[str]] = None,
        use_ensemble: Optional[bool] = None,
        max_models: Optional[int] = None,
    ) -> RoutingDecision:
        """
        Route a query to appropriate model(s).
        
        Args:
            query: User query
            mode: "speed" or "accuracy"
            required_capabilities: Optional required capabilities
            use_ensemble: Force ensemble mode (None = auto-detect)
            max_models: Maximum number of models to use
            
        Returns:
            RoutingDecision with selected models and reasoning
        """
        # Detect domain
        domain = self.model_registry._detect_domain(query)
        best_domain_model = self._best_model_for_domain(domain)
        
        # Analyze query difficulty/importance
        is_important = self._is_important_query(query)
        is_complex = self._is_complex_query(query)
        
        # Determine if ensemble should be used
        should_use_ensemble = False
        if use_ensemble is not None:
            should_use_ensemble = use_ensemble
        elif self.enable_ensemble:
            # Use ensemble for important/complex queries in accuracy mode
            should_use_ensemble = (mode == "accuracy" and (is_important or is_complex))
        
        # Select models
        if should_use_ensemble:
            # Ensemble mode: select multiple models
            ensemble_size = 2 if mode == "speed" else (3 if is_important else 2)
            if max_models:
                ensemble_size = min(ensemble_size, max_models)
            
            selected_models = self.model_registry.select_models_for_query(
                query,
                mode=mode,
                max_models=ensemble_size,
                required_capabilities=required_capabilities,
            )
            
            primary_model = selected_models[0] if selected_models else None
            fallback_models = selected_models[1:] if len(selected_models) > 1 else []
            
            reasoning = (
                f"Ensemble mode: Selected {len(selected_models)} models for "
                f"{'important' if is_important else 'complex'} query in {mode} mode"
            )
        else:
            # Single model mode
            selected_models = self.model_registry.select_models_for_query(
                query,
                mode=mode,
                max_models=1,
                required_capabilities=required_capabilities,
            )
            # If we have a data-driven domain preference, make sure it's first
            if best_domain_model:
                if best_domain_model in selected_models:
                    selected_models.remove(best_domain_model)
                selected_models.insert(0, best_domain_model)
            
            primary_model = selected_models[0] if selected_models else None
            fallback_models = self._select_fallback_models(
                query, domain, primary_model, mode
            )
            
            reasoning = (
                f"Single model mode: Selected {primary_model} for {domain} domain "
                f"with {len(fallback_models)} fallback(s)"
            )
        
        if not primary_model:
            # Fallback to default
            primary_model = "gpt-4o-mini"
            selected_models = [primary_model]
            reasoning = "Fallback to default model (no suitable models found)"
        
        # Calculate confidence based on model performance
        confidence = self._calculate_routing_confidence(primary_model, domain)
        
        decision = RoutingDecision(
            selected_models=selected_models,
            primary_model=primary_model,
            fallback_models=fallback_models,
            reasoning=reasoning,
            domain=domain,
            confidence=confidence,
            use_ensemble=should_use_ensemble,
            ensemble_size=len(selected_models),
        )
        
        # Log routing decision
        self.routing_history.append(decision)
        logger.info(
            "Model Router: %s (domain=%s, confidence=%.2f, ensemble=%s)",
            reasoning,
            domain,
            confidence,
            should_use_ensemble,
        )
        if best_domain_model:
            logger.info(
                "Routing boosted by historical domain success: %s for %s",
                best_domain_model,
                domain,
            )
        
        return decision
    
    async def execute_with_fallback(
        self,
        query: str,
        prompt: str,
        *,
        routing_decision: Optional[RoutingDecision] = None,
        mode: str = "accuracy",
        context: Optional[str] = None,
    ) -> ModelResponse:
        """
        Execute query with automatic fallback on failure or low quality.
        
        Args:
            query: Original user query
            prompt: Augmented prompt to send to model
            routing_decision: Optional pre-computed routing decision
            mode: Query mode
            context: Optional context
            
        Returns:
            ModelResponse with result and quality assessment
        """
        if not routing_decision:
            routing_decision = self.route(query, mode=mode)
        
        # Try primary model first
        primary_model = routing_decision.primary_model
        logger.info("Model Router: Attempting primary model: %s", primary_model)
        
        response = await self._try_model(primary_model, prompt, context)
        
        # Check quality
        if response.passed_quality_check:
            logger.info(
                "Model Router: Primary model %s passed quality check (score=%.2f)",
                primary_model,
                response.quality_score,
            )
            return response
        
        # Primary model failed, try fallback
        if self.enable_fallback and routing_decision.fallback_models:
            logger.warning(
                "Model Router: Primary model %s failed quality check (score=%.2f), "
                "trying fallback models",
                primary_model,
                response.quality_score,
            )
            
            for fallback_model in routing_decision.fallback_models[:self.max_fallback_attempts]:
                logger.info("Model Router: Attempting fallback model: %s", fallback_model)
                fallback_response = await self._try_model(fallback_model, prompt, context)
                
                if fallback_response.passed_quality_check:
                    logger.info(
                        "Model Router: Fallback model %s passed quality check (score=%.2f)",
                        fallback_model,
                        fallback_response.quality_score,
                    )
                    return fallback_response
                
                logger.warning(
                    "Model Router: Fallback model %s also failed (score=%.2f)",
                    fallback_model,
                    fallback_response.quality_score,
                )
        
        # All models failed, return primary response with failure flag
        logger.error(
            "Model Router: All models failed quality check. Returning primary response."
        )
        return response
    
    async def execute_ensemble(
        self,
        query: str,
        prompt: str,
        *,
        routing_decision: Optional[RoutingDecision] = None,
        mode: str = "accuracy",
        context: Optional[str] = None,
    ) -> List[ModelResponse]:
        """
        Execute query with parallel ensemble (multiple models in parallel).
        
        Args:
            query: Original user query
            prompt: Augmented prompt to send to models
            routing_decision: Optional pre-computed routing decision
            mode: Query mode
            context: Optional context
            
        Returns:
            List of ModelResponse objects from all models
        """
        if not routing_decision:
            routing_decision = self.route(query, mode=mode, use_ensemble=True)
        
        if not routing_decision.use_ensemble:
            # Fallback to single model
            response = await self.execute_with_fallback(
                query, prompt, routing_decision=routing_decision, mode=mode, context=context
            )
            return [response]
        
        models = routing_decision.selected_models
        logger.info(
            "Model Router: Executing ensemble with %d models: %s",
            len(models),
            models,
        )
        
        # Execute all models in parallel
        tasks = [
            self._try_model(model, prompt, context) for model in models
        ]
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions
        valid_responses: List[ModelResponse] = []
        for i, response in enumerate(responses):
            if isinstance(response, Exception):
                logger.error(
                    "Model Router: Exception in ensemble execution for %s: %s",
                    models[i],
                    response,
                )
                continue
            valid_responses.append(response)
        
        # Log ensemble results
        passed = sum(1 for r in valid_responses if r.passed_quality_check)
        logger.info(
            "Model Router: Ensemble completed: %d/%d models passed quality check",
            passed,
            len(valid_responses),
        )
        
        return valid_responses
    
    def vote_on_responses(
        self,
        responses: List[ModelResponse],
        *,
        domain: Optional[str] = None,
    ) -> ModelResponse:
        """
        Vote/score multiple responses and select the best one.
        
        Args:
            responses: List of model responses
            domain: Optional domain for domain-specific weighting
            
        Returns:
            Best ModelResponse based on voting
        """
        if not responses:
            raise ValueError("No responses to vote on")
        
        if len(responses) == 1:
            return responses[0]
        
        # Score each response
        scored_responses: List[Tuple[ModelResponse, float]] = []
        
        for response in responses:
            score = 0.0
            
            # Quality score (40% weight)
            score += response.quality_score * 0.4
            
            # Model reliability (30% weight)
            profile = next(
                (p for p in self.model_registry.available_profiles() if p.name == response.model),
                None,
            )
            if profile:
                reliability = profile.get_reliability_score()
                score += reliability * 0.3
                
                # Domain expertise boost (20% weight)
                if domain:
                    domain_score = profile.score_for_domain(domain)
                    score += domain_score * 0.2
            
            # Confidence boost (10% weight)
            score += response.confidence * 0.1
            
            scored_responses.append((response, score))
        
        # Sort by score (highest first)
        scored_responses.sort(key=lambda x: x[1], reverse=True)
        
        best_response, best_score = scored_responses[0]
        
        logger.info(
            "Model Router: Voting selected %s (score=%.2f) from %d responses",
            best_response.model,
            best_score,
            len(responses),
        )
        
        return best_response
    
    async def _try_model(
        self,
        model: str,
        prompt: str,
        context: Optional[str] = None,
    ) -> ModelResponse:
        """Try to execute a model and assess quality."""
        provider = self._select_provider(model)
        
        # Build augmented prompt
        augmented_prompt = prompt
        if context:
            augmented_prompt = f"{context}\n\n{prompt}"
        
        try:
            # Execute model
            result = await provider.complete(augmented_prompt, model=model)
            
            # Assess quality
            quality_score = self._assess_quality(result, model)
            confidence = self._assess_confidence(result, model)
            passed = quality_score >= self.min_quality_threshold
            
            return ModelResponse(
                result=result,
                model=model,
                quality_score=quality_score,
                confidence=confidence,
                passed_quality_check=passed,
                failure_reason=None if passed else f"Quality score {quality_score:.2f} below threshold {self.min_quality_threshold:.2f}",
            )
        except Exception as exc:
            logger.error("Model Router: Model %s failed with exception: %s", model, exc)
            # Return error response
            from ..services.base import LLMResult
            error_result = LLMResult(
                model=model,
                content=f"Error: {str(exc)}",
                tokens=0,
            )
            return ModelResponse(
                result=error_result,
                model=model,
                quality_score=0.0,
                confidence=0.0,
                passed_quality_check=False,
                failure_reason=str(exc),
            )
    
    def _select_provider(self, model: str) -> LLMProvider:
        """Select provider for a model."""
        # Try to find provider that supports this model
        for provider_name, provider in self.providers.items():
            if hasattr(provider, "supports_model") and provider.supports_model(model):
                return provider
            # Fallback: check if model name contains provider name
            if provider_name.lower() in model.lower():
                return provider
        
        # Default to openrouter or first non-stub provider (NEVER stub)
        return self.providers.get("openrouter") or next((p for n, p in self.providers.items() if n != "stub"), next(iter(self.providers.values())))
    
    def _select_fallback_models(
        self,
        query: str,
        domain: str,
        primary_model: Optional[str],
        mode: str,
    ) -> List[str]:
        """Select fallback models for a query."""
        # Get alternative models for the domain
        available = self.model_registry.available_profiles()
        
        # Filter out primary model
        candidates = [
            p for p in available
            if p.name != primary_model
        ]
        
        # Score candidates
        scored: List[Tuple[ModelProfile, float]] = []
        perf_snapshot = performance_tracker.snapshot()
        
        for profile in candidates:
            score = 0.0
            
            # Domain expertise
            domain_score = profile.score_for_domain(domain)
            score += domain_score * 0.35
            
            # Performance
            perf: ModelPerformance | None = perf_snapshot.get(profile.name)  # type: ignore[assignment]
            if perf:
                recent_success = perf.success_rate
                quality = perf.avg_quality
                domain_success = perf.get_domain_success_rate(domain)
                # Boost quality and domain-specific wins, penalize recent failures
                score += recent_success * 0.25
                score += quality * 0.25
                score += domain_success * 0.15
                failure_rate = 1 - recent_success
                score -= failure_rate * 0.1
            
            # Cost/latency (prefer cheaper/faster for fallback)
            if mode == "speed":
                score -= (profile.cost_rating + profile.latency_rating) * 0.1
            
            scored.append((profile, score))
            logger.debug(
                "Fallback scoring %s -> score=%.3f (domain=%.2f, success=%.2f, quality=%.2f, domain_success=%.2f)",
                profile.name,
                score,
                domain_score,
                perf.success_rate if perf else -1.0,
                perf.avg_quality if perf else -1.0,
                perf.get_domain_success_rate(domain) if perf else -1.0,
            )
        
        # Sort and select top 2
        scored.sort(key=lambda x: x[1], reverse=True)
        return [p.name for p, _ in scored[:2]]
    
    def _best_model_for_domain(self, domain: str) -> Optional[str]:
        """
        Pick the model with the strongest domain-specific success history.
        
        Uses performance_tracker domain stats to surface a preferred model that has
        consistently passed verification for this domain. Returns None if no clear
        winner exists.
        """
        perf_snapshot = performance_tracker.snapshot()
        best_model = None
        best_score = 0.0
        for model_name, perf in perf_snapshot.items():
            domain_success = perf.get_domain_success_rate(domain)
            successes = perf.domain_performance.get(domain, {}).get("success", 0)
            total = successes + perf.domain_performance.get(domain, {}).get("failure", 0)
            # Require at least a small sample to avoid noise
            if total < 2:
                continue
            if domain_success > best_score:
                best_score = domain_success
                best_model = model_name
        if best_model and best_score >= 0.6:
            logger.info(
                "Data-driven domain preference: %s selected for domain %s (success=%.2f)",
                best_model,
                domain,
                best_score,
            )
            return best_model
        return None
    
    def _is_important_query(self, query: str) -> bool:
        """Determine if query is important (requires high quality)."""
        important_keywords = [
            "critical", "important", "urgent", "decision", "recommendation",
            "medical", "legal", "financial", "security", "safety",
        ]
        query_lower = query.lower()
        return any(keyword in query_lower for keyword in important_keywords)
    
    def _is_complex_query(self, query: str) -> bool:
        """Determine if query is complex (requires multiple models)."""
        # Long queries are likely complex
        if len(query.split()) > 50:
            return True
        
        complex_keywords = [
            "analyze", "compare", "evaluate", "synthesize", "comprehensive",
            "multiple", "various", "different", "pros and cons",
        ]
        query_lower = query.lower()
        return any(keyword in query_lower for keyword in complex_keywords)
    
    def _calculate_routing_confidence(
        self,
        model: str,
        domain: str,
    ) -> float:
        """Calculate confidence in routing decision."""
        profile = next(
            (p for p in self.model_registry.available_profiles() if p.name == model),
            None,
        )
        if not profile:
            return 0.5  # Default confidence
        
        # Base confidence on domain expertise and reliability
        domain_score = profile.score_for_domain(domain)
        reliability = profile.get_reliability_score()
        
        # Combine scores
        confidence = (domain_score * 0.6) + (reliability * 0.4)
        return min(1.0, max(0.0, confidence))
    
    def _assess_quality(
        self,
        result: LLMResult,
        model: str,
    ) -> float:
        """Assess quality of a model response."""
        if not result.content or not result.content.strip():
            return 0.0
        
        score = 0.5  # Base score
        
        # Length heuristic (too short or too long is suspicious)
        content_length = len(result.content)
        if 50 <= content_length <= 5000:
            score += 0.2
        elif content_length < 50:
            score -= 0.3  # Too short
        elif content_length > 10000:
            score -= 0.1  # Possibly verbose
        
        # Error indicators
        error_indicators = ["error", "failed", "unable", "cannot", "sorry"]
        content_lower = result.content.lower()
        if any(indicator in content_lower for indicator in error_indicators):
            score -= 0.2
        
        # Model performance boost
        perf_snapshot = performance_tracker.snapshot()
        perf: ModelPerformance | None = perf_snapshot.get(model)  # type: ignore[assignment]
        if perf:
            score += perf.avg_quality * 0.3
        
        return min(1.0, max(0.0, score))
    
    def _assess_confidence(
        self,
        result: LLMResult,
        model: str,
    ) -> float:
        """Assess confidence in a model response."""
        # Base confidence on model reliability
        profile = next(
            (p for p in self.model_registry.available_profiles() if p.name == model),
            None,
        )
        if profile:
            return profile.get_reliability_score()
        
        return 0.5  # Default confidence

