"""Adapter service to bridge ChatRequest to internal orchestrator.

Enhanced with Elite Orchestration for maximum performance:
- Intelligent model-task matching
- Quality-weighted fusion
- Parallel execution
- Challenge and refine strategies
"""
from __future__ import annotations

import logging
import time
from typing import Dict, Any, Optional

from ..models.orchestration import (
    ChatRequest,
    ChatResponse,
    AgentTrace,
    ReasoningMode,
    ReasoningMethod,
    DomainPack,
    AgentMode,
)
from ..orchestrator import Orchestrator
from .model_router import (
    get_models_for_reasoning_method,
    map_reasoning_mode_to_method,
    ReasoningMethod as RouterReasoningMethod,
    FALLBACK_GPT_4O,
    FALLBACK_GPT_4O_MINI,
    FALLBACK_CLAUDE_SONNET_4,
    FALLBACK_CLAUDE_3_5,
    FALLBACK_CLAUDE_3_HAIKU,
    FALLBACK_GEMINI_2_5,
    FALLBACK_GEMINI_2_5_FLASH,
    FALLBACK_GROK_2,
    FALLBACK_GROK_BETA,
    FALLBACK_DEEPSEEK,
)
from .reasoning_prompts import get_reasoning_prompt_template

# Import Elite Orchestrator and Quality Booster
try:
    from ..orchestration.elite_orchestrator import (
        EliteOrchestrator,
        EliteResult,
        get_best_model_for_task,
    )
    ELITE_AVAILABLE = True
except ImportError:
    ELITE_AVAILABLE = False
    EliteOrchestrator = None

try:
    from ..orchestration.quality_booster import (
        QualityBooster,
        boost_response,
    )
    QUALITY_BOOSTER_AVAILABLE = True
except ImportError:
    QUALITY_BOOSTER_AVAILABLE = False
    QualityBooster = None

logger = logging.getLogger(__name__)

# Global orchestrator instance
_orchestrator = Orchestrator()

# Elite orchestrator instance (initialized on first use)
_elite_orchestrator: Optional[EliteOrchestrator] = None
_quality_booster: Optional[QualityBooster] = None


def _get_elite_orchestrator() -> Optional[EliteOrchestrator]:
    """Get or create elite orchestrator instance."""
    global _elite_orchestrator
    if _elite_orchestrator is None and ELITE_AVAILABLE:
        _elite_orchestrator = EliteOrchestrator(
            providers=_orchestrator.providers,
            performance_tracker=getattr(_orchestrator, 'performance_tracker', None),
            enable_learning=True,
        )
        logger.info("Elite orchestrator initialized")
    return _elite_orchestrator


def _get_quality_booster() -> Optional[QualityBooster]:
    """Get or create quality booster instance."""
    global _quality_booster
    if _quality_booster is None and QUALITY_BOOSTER_AVAILABLE:
        _quality_booster = QualityBooster(
            providers=_orchestrator.providers,
            default_model="gpt-4o",
        )
        logger.info("Quality booster initialized")
    return _quality_booster


def _detect_task_type(prompt: str) -> str:
    """Detect task type from prompt for optimal routing."""
    prompt_lower = prompt.lower()
    
    if any(kw in prompt_lower for kw in ["code", "function", "implement", "debug", "program"]):
        return "code_generation"
    elif any(kw in prompt_lower for kw in ["calculate", "solve", "math", "equation"]):
        return "math_problem"
    elif any(kw in prompt_lower for kw in ["research", "analyze", "comprehensive", "in-depth"]):
        return "research_analysis"
    elif any(kw in prompt_lower for kw in ["explain", "what is", "how does", "why"]):
        return "explanation"
    elif any(kw in prompt_lower for kw in ["compare", "versus", "difference"]):
        return "comparison"
    elif any(kw in prompt_lower for kw in ["summarize", "summary", "tldr"]):
        return "summarization"
    elif any(kw in prompt_lower for kw in ["quick", "fast", "brief"]):
        return "fast_response"
    elif any(kw in prompt_lower for kw in ["detailed", "thorough", "complete"]):
        return "high_quality"
    else:
        return "general"


def _select_elite_strategy(accuracy_level: int, task_type: str, num_models: int) -> str:
    """Select the best elite orchestration strategy."""
    # High accuracy = use more sophisticated strategies
    if accuracy_level >= 4:
        if task_type in ["code_generation", "debugging"]:
            return "challenge_and_refine"
        elif task_type in ["research_analysis", "comparison"]:
            return "expert_panel" if num_models >= 3 else "quality_weighted_fusion"
        else:
            return "best_of_n"
    elif accuracy_level >= 3:
        return "quality_weighted_fusion"
    elif accuracy_level >= 2:
        return "parallel_race"
    else:
        return "single_best"


def _map_reasoning_mode(mode: ReasoningMode) -> int:
    """Map ReasoningMode enum to reasoning depth integer."""
    mapping = {
        ReasoningMode.fast: 1,
        ReasoningMode.standard: 2,
        ReasoningMode.deep: 3,
    }
    return mapping.get(mode, 2)


def _map_model_to_provider(model_id: str, available_providers: list) -> str:
    """Map a user-selected model ID to an actual provider/model name.
    
    Latest models (December 2025):
    - OpenAI: GPT-4o, GPT-4o-mini, o1, o1-mini
    - Anthropic: Claude Sonnet 4, Claude 3.5 Sonnet, Claude 3.5 Haiku
    - Google: Gemini 2.5 Pro, Gemini 2.5 Flash
    - xAI: Grok-2, Grok-2-mini
    """
    model_lower = model_id.lower()
    
    # OpenAI models
    if "gpt-5" in model_lower or "gpt-4" in model_lower or "o1" in model_lower:
        if "mini" in model_lower:
            return FALLBACK_GPT_4O_MINI
        return FALLBACK_GPT_4O
    
    # Anthropic Claude models
    elif "claude" in model_lower:
        if "haiku" in model_lower:
            return FALLBACK_CLAUDE_3_HAIKU  # claude-3-5-haiku-20241022
        elif "sonnet-4" in model_lower or "4.5" in model_lower or "opus" in model_lower:
            return FALLBACK_CLAUDE_SONNET_4  # claude-sonnet-4-20250514
        return FALLBACK_CLAUDE_3_5  # claude-3-5-sonnet-20241022
    
    # Google Gemini models
    elif "gemini" in model_lower:
        if "flash" in model_lower:
            return FALLBACK_GEMINI_2_5_FLASH  # gemini-2.5-flash
        return FALLBACK_GEMINI_2_5  # gemini-2.5-pro
    
    # xAI Grok models - Use Grok-2 (latest)
    elif "grok" in model_lower:
        return FALLBACK_GROK_2  # grok-2
    
    # DeepSeek models
    elif "deepseek" in model_lower:
        return FALLBACK_DEEPSEEK  # deepseek-chat
    
    # Llama (local)
    elif "llama" in model_lower:
        if "local" in available_providers:
            return "local"
        return "stub"
    
    # Direct model name match
    elif model_id in available_providers:
        return model_id
    
    else:
        # Default to first available
        return available_providers[0] if available_providers else "stub"


async def run_orchestration(request: ChatRequest) -> ChatResponse:
    """
    Run orchestration with ChatRequest and return ChatResponse.
    
    This adapter builds an orchestration_config from the ChatRequest,
    uses user-selected models if provided, and calls the orchestrator.
    """
    start_time = time.perf_counter()
    
    try:
        # Determine reasoning method
        if request.reasoning_method:
            reasoning_method = RouterReasoningMethod(request.reasoning_method.value)
        else:
            # Infer from reasoning_mode for backward compatibility
            reasoning_method = map_reasoning_mode_to_method(request.reasoning_mode.value)
        
        logger.info(
            "Using reasoning method: %s (from mode: %s)",
            reasoning_method.value,
            request.reasoning_mode.value,
        )
        
        # Get available providers from orchestrator
        available_providers = list(_orchestrator.providers.keys())
        
        # Use user-selected models if provided, otherwise auto-select
        if request.models and len(request.models) > 0:
            logger.info("User selected models: %s", request.models)
            
            # Map user-selected model names to actual provider models
            actual_models = []
            user_model_names = []  # Track what the user selected for response
            
            for model_id in request.models:
                mapped_model = _map_model_to_provider(model_id, available_providers)
                if mapped_model not in actual_models:  # Avoid duplicates
                    actual_models.append(mapped_model)
                    user_model_names.append(model_id)
            
            logger.info(
                "Mapped user models to providers: %s -> %s",
                request.models,
                actual_models,
            )
        else:
            # Auto-select models based on reasoning method
            selected_models = get_models_for_reasoning_method(
                reasoning_method,
                available_models=available_providers,
            )
            
            # Map to actual model names
            actual_models = []
            user_model_names = []
            for model_id in selected_models:
                mapped = _map_model_to_provider(model_id, available_providers)
                if mapped not in actual_models:
                    actual_models.append(mapped)
                    user_model_names.append(model_id)
        
        if not actual_models:
            actual_models = ["gpt-4o-mini"]
            user_model_names = ["GPT-4o Mini"]
        
        logger.info(
            "Final models for orchestration: %s (display: %s)",
            actual_models,
            user_model_names,
        )
        
        # Extract criteria settings from metadata if provided
        criteria_settings = None
        if request.metadata and hasattr(request.metadata, 'extra'):
            extra = getattr(request.metadata, 'extra', {})
            if isinstance(extra, dict) and 'criteria' in extra:
                criteria_settings = extra['criteria']
        # Also check metadata dict directly
        metadata_dict = request.metadata.dict(exclude_none=True) if hasattr(request.metadata, 'dict') else {}
        if 'criteria' in metadata_dict:
            criteria_settings = metadata_dict['criteria']
        
        # Build orchestration_config dict
        orchestration_config: Dict[str, Any] = {
            "reasoning_depth": _map_reasoning_mode(request.reasoning_mode),
            "reasoning_method": reasoning_method.value,
            "domain_pack": request.domain_pack.value,
            "agent_mode": request.agent_mode.value,
            "use_prompt_optimization": request.tuning.prompt_optimization,
            "use_output_validation": request.tuning.output_validation,
            "use_answer_structure": request.tuning.answer_structure,
            "learn_from_chat": request.tuning.learn_from_chat,
            "metadata": metadata_dict,
            "history": request.history or [],
            # Orchestration Studio settings
            "accuracy_level": request.orchestration.accuracy_level,
            "use_hrm": request.orchestration.enable_hrm,
            "use_prompt_diffusion": request.orchestration.enable_prompt_diffusion,
            "use_deep_consensus": request.orchestration.enable_deep_consensus,
            "use_adaptive_routing": request.orchestration.enable_adaptive_ensemble,
        }
        
        # Add criteria settings if provided (for dynamic criteria equaliser)
        if criteria_settings:
            orchestration_config["criteria"] = criteria_settings
            logger.info(
                "Using criteria settings: accuracy=%d%%, speed=%d%%, creativity=%d%%",
                criteria_settings.get("accuracy", 70),
                criteria_settings.get("speed", 70),
                criteria_settings.get("creativity", 50),
            )
        
        # Enhance prompt with reasoning method template
        base_prompt = request.prompt
        enhanced_prompt = get_reasoning_prompt_template(
            reasoning_method,
            base_prompt,
            domain_pack=request.domain_pack.value,
        )
        
        logger.info(
            "Running orchestration: method=%s, domain=%s, agent_mode=%s, models=%s, "
            "hrm=%s, adaptive=%s, accuracy=%d",
            reasoning_method.value,
            orchestration_config["domain_pack"],
            orchestration_config["agent_mode"],
            actual_models,
            orchestration_config.get("use_hrm", False),
            orchestration_config.get("use_adaptive_routing", False),
            orchestration_config.get("accuracy_level", 3),
        )
        
        # Detect task type for optimal routing
        task_type = _detect_task_type(base_prompt)
        accuracy_level = orchestration_config.get("accuracy_level", 3)
        
        # Determine if we should use elite orchestration
        use_elite = (
            ELITE_AVAILABLE and 
            accuracy_level >= 3 and 
            len(actual_models) >= 2
        )
        
        elite_result = None
        
        if use_elite:
            logger.info(
                "Using ELITE orchestration: task=%s, accuracy=%d, strategy=auto",
                task_type, accuracy_level
            )
            
            elite = _get_elite_orchestrator()
            if elite:
                try:
                    # Select strategy based on accuracy and task
                    strategy = _select_elite_strategy(accuracy_level, task_type, len(actual_models))
                    
                    elite_result = await elite.orchestrate(
                        enhanced_prompt,
                        task_type=task_type,
                        available_models=actual_models,
                        strategy=strategy,
                        quality_threshold=0.7,
                        max_parallel=min(3, len(actual_models)),
                    )
                    
                    final_text = elite_result.final_answer
                    
                    logger.info(
                        "Elite orchestration complete: strategy=%s, quality=%.2f, models=%s",
                        elite_result.strategy_used,
                        elite_result.quality_score,
                        elite_result.models_used,
                    )
                except Exception as e:
                    logger.warning("Elite orchestration failed, falling back: %s", e)
                    use_elite = False
        
        if not use_elite or elite_result is None:
            # Standard orchestration path
            artifacts = await _orchestrator.orchestrate(
                enhanced_prompt,
                actual_models,
                use_hrm=orchestration_config.get("use_hrm", False),
                use_adaptive_routing=orchestration_config.get("use_adaptive_routing", False),
                use_deep_consensus=orchestration_config.get("use_deep_consensus", False),
                use_prompt_diffusion=orchestration_config.get("use_prompt_diffusion", False),
                accuracy_level=accuracy_level,
            )
            final_text = artifacts.final_response.content
        
        # Apply quality boosting for high accuracy requests
        if QUALITY_BOOSTER_AVAILABLE and accuracy_level >= 4:
            booster = _get_quality_booster()
            if booster:
                try:
                    logger.info("Applying quality boost for high-accuracy request")
                    boost_result = await booster.boost(
                        base_prompt,
                        final_text,
                        techniques=["reflection", "verification"],
                        max_iterations=1,
                    )
                    if boost_result.quality_improvement > 0:
                        final_text = boost_result.boosted_response
                        logger.info(
                            "Quality boost applied: improvement=%.2f, techniques=%s",
                            boost_result.quality_improvement,
                            boost_result.techniques_applied,
                        )
                except Exception as e:
                    logger.warning("Quality boost failed: %s", e)
        
        # Build agent traces from artifacts (if available)
        traces: list[AgentTrace] = []
        
        # Extract token usage and other metrics
        token_usage = None
        quality_score = None
        
        if elite_result:
            # Use elite orchestrator metrics
            token_usage = elite_result.total_tokens
            quality_score = elite_result.quality_score
            actual_models_used = elite_result.models_used
        elif 'artifacts' in dir() and artifacts:
            if hasattr(artifacts.final_response, 'tokens_used'):
                token_usage = artifacts.final_response.tokens_used
            actual_models_used = actual_models
        else:
            actual_models_used = actual_models
        
        # Calculate latency
        latency_ms = int((time.perf_counter() - start_time) * 1000)
        
        # Build extra data
        extra: Dict[str, Any] = {
            "orchestration_settings": {
                "accuracy_level": orchestration_config.get("accuracy_level", 3),
                "hrm_enabled": orchestration_config.get("use_hrm", False),
                "adaptive_routing_enabled": orchestration_config.get("use_adaptive_routing", False),
                "deep_consensus_enabled": orchestration_config.get("use_deep_consensus", False),
                "prompt_diffusion_enabled": orchestration_config.get("use_prompt_diffusion", False),
            },
        }
        
        # Add elite orchestrator info if used
        if elite_result:
            extra["elite_orchestration"] = {
                "enabled": True,
                "strategy": elite_result.strategy_used,
                "synthesis_method": elite_result.synthesis_method,
                "quality_score": elite_result.quality_score,
                "confidence": elite_result.confidence,
                "responses_generated": elite_result.responses_generated,
                "primary_model": elite_result.primary_model,
            }
            extra["performance_notes"] = elite_result.performance_notes
        else:
            if 'artifacts' in dir() and artifacts:
                extra["initial_responses_count"] = len(artifacts.initial_responses)
                extra["critiques_count"] = len(artifacts.critiques)
                extra["improvements_count"] = len(artifacts.improvements)
                # Add consensus notes if available
                if hasattr(artifacts, 'consensus_notes') and artifacts.consensus_notes:
                    extra["consensus_notes"] = artifacts.consensus_notes
        
        # Add task type detected
        extra["task_type"] = task_type
        
        # Add models used info to extra
        extra["models_requested"] = request.models or []
        extra["models_mapped"] = actual_models
        
        # Build response with models_used
        response = ChatResponse(
            message=final_text,
            models_used=user_model_names,
            reasoning_mode=request.reasoning_mode,
            reasoning_method=request.reasoning_method,
            domain_pack=request.domain_pack,
            agent_mode=request.agent_mode,
            used_tuning=request.tuning,
            metadata=request.metadata,
            tokens_used=token_usage,
            latency_ms=latency_ms,
            agent_traces=traces,
            extra=extra,
        )
        
        logger.info(
            "Orchestration completed: latency=%dms, tokens=%s",
            latency_ms,
            token_usage or "unknown",
        )
        
        return response
        
    except Exception as exc:
        latency_ms = int((time.perf_counter() - start_time) * 1000)
        logger.exception("Orchestration failed: %s", exc)
        
        # Return error response
        return ChatResponse(
            message=f"I apologize, but I encountered an error processing your request: {str(exc)}",
            models_used=request.models or [],
            reasoning_mode=request.reasoning_mode,
            reasoning_method=request.reasoning_method,
            domain_pack=request.domain_pack,
            agent_mode=request.agent_mode,
            used_tuning=request.tuning,
            metadata=request.metadata,
            latency_ms=latency_ms,
            agent_traces=[],
            extra={"error": str(exc)},
        )

