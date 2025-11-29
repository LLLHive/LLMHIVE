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
from ...app.orchestrator import Orchestrator
from .model_router import (
    get_models_for_reasoning_method,
    map_reasoning_mode_to_method,
    ReasoningMethod as RouterReasoningMethod,
    FALLBACK_GPT_4O,
    FALLBACK_GPT_4O_MINI,
    FALLBACK_CLAUDE_3_5,
    FALLBACK_CLAUDE_3_HAIKU,
    FALLBACK_GEMINI_2_5,
    FALLBACK_GROK_BETA,
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


async def run_orchestration(request: ChatRequest) -> ChatResponse:
    """
    Run orchestration with ChatRequest and return ChatResponse.
    
    This adapter builds an orchestration_config from the ChatRequest,
    selects appropriate models based on reasoning method, and calls the orchestrator.
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
        
        # Get available models from orchestrator
        available_models = list(_orchestrator.providers.keys())
        
        # Select models based on reasoning method
        selected_models = get_models_for_reasoning_method(
            reasoning_method,
            available_models=available_models,
        )
        
        # Map to actual model names that the orchestrator understands
        # For now, use fallback models since we don't have GPT-5.1, Claude 4.5, etc. yet
        actual_models = []
        for model_id in selected_models:
            # Map future models to current available models
            if "gpt-5" in model_id or "gpt-4" in model_id:
                actual_models.append(FALLBACK_GPT_4O_MINI if "mini" in model_id else FALLBACK_GPT_4O)
            elif "claude" in model_id:
                actual_models.append(FALLBACK_CLAUDE_3_HAIKU if "haiku" in model_id else FALLBACK_CLAUDE_3_5)
            elif "gemini" in model_id:
                actual_models.append(FALLBACK_GEMINI_2_5)
            elif "grok" in model_id:
                actual_models.append(FALLBACK_GROK_BETA)
            else:
                # Use first available model as fallback
                actual_models.append(available_models[0] if available_models else "stub")
        
        # Remove duplicates while preserving order
        seen = set()
        actual_models = [m for m in actual_models if not (m in seen or seen.add(m))]
        
        if not actual_models:
            actual_models = ["gpt-4o-mini", "claude-3-haiku"]
        
        logger.info(
            "Selected models for method %s: %s",
            reasoning_method.value,
            actual_models,
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
            "Running orchestration: method=%s, domain=%s, agent_mode=%s, models=%s",
            reasoning_method.value,
            orchestration_config["domain_pack"],
            orchestration_config["agent_mode"],
            actual_models,
        )
        
        # Call the orchestrator with enhanced prompt and selected models
        artifacts = await _orchestrator.orchestrate(enhanced_prompt, actual_models)
        
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
        }
        
        # Build response
        response = ChatResponse(
            message=final_text,
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

