"""Adapter service to bridge ChatRequest to internal orchestrator."""
from __future__ import annotations

import logging
import time
from typing import Dict, Any

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

logger = logging.getLogger(__name__)

# Global orchestrator instance
_orchestrator = Orchestrator()


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
        
        # Call the orchestrator with enhanced prompt and selected models
        # Pass orchestration settings as kwargs
        artifacts = await _orchestrator.orchestrate(
            enhanced_prompt,
            actual_models,
            use_hrm=orchestration_config.get("use_hrm", False),
            use_adaptive_routing=orchestration_config.get("use_adaptive_routing", False),
            use_deep_consensus=orchestration_config.get("use_deep_consensus", False),
            use_prompt_diffusion=orchestration_config.get("use_prompt_diffusion", False),
            accuracy_level=orchestration_config.get("accuracy_level", 3),
        )
        
        # Extract final response
        final_text = artifacts.final_response.content
        
        # Build agent traces from artifacts (if available)
        traces: list[AgentTrace] = []
        
        # Extract token usage if available
        token_usage = None
        if hasattr(artifacts.final_response, 'tokens_used'):
            token_usage = artifacts.final_response.tokens_used
        
        # Calculate latency
        latency_ms = int((time.perf_counter() - start_time) * 1000)
        
        # Build extra data from artifacts
        extra: Dict[str, Any] = {
            "initial_responses_count": len(artifacts.initial_responses),
            "critiques_count": len(artifacts.critiques),
            "improvements_count": len(artifacts.improvements),
            "orchestration_settings": {
                "accuracy_level": orchestration_config.get("accuracy_level", 3),
                "hrm_enabled": orchestration_config.get("use_hrm", False),
                "adaptive_routing_enabled": orchestration_config.get("use_adaptive_routing", False),
                "deep_consensus_enabled": orchestration_config.get("use_deep_consensus", False),
                "prompt_diffusion_enabled": orchestration_config.get("use_prompt_diffusion", False),
            },
        }
        
        # Add consensus notes if available
        if hasattr(artifacts, 'consensus_notes') and artifacts.consensus_notes:
            extra["consensus_notes"] = artifacts.consensus_notes
        
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

