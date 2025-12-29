"""Chat API router for LLMHive.

Enhancement-6: Safe Mode validation and orchestrator metrics integration.
"""
from __future__ import annotations

import logging
from fastapi import APIRouter, Depends, HTTPException, status

from ..auth import verify_api_key
from ..models.orchestration import ChatRequest, ChatResponse
from ..services.orchestrator_adapter import run_orchestration

logger = logging.getLogger(__name__)

# Define router with /v1 prefix
router = APIRouter(prefix="/v1", tags=["chat"])

# Try to import guardrails for Safe Mode
try:
    from ..guardrails import (
        check_output_policy,
        enforce_output_policy,
        assess_query_risk,
    )
    GUARDRAILS_AVAILABLE = True
except ImportError:
    GUARDRAILS_AVAILABLE = False
    logger.info("Guardrails not available, Safe Mode disabled")


@router.post("/chat", response_model=ChatResponse, status_code=status.HTTP_200_OK)
async def chat_endpoint(
    payload: ChatRequest,
    user: str = Depends(verify_api_key),
) -> ChatResponse:
    """
    Chat orchestration endpoint.
    
    Accepts a ChatRequest with prompt, reasoning mode, domain pack, agent mode,
    tuning options, metadata, and conversation history.
    
    Enhancement-5: Stricter input validation via Pydantic models.
    Enhancement-6: Safe Mode filtering and error metrics tracking.
    
    Returns a ChatResponse with the final answer and orchestration artifacts.
    """
    try:
        logger.info(
            "Chat request received: prompt_length=%d, reasoning_mode=%s, domain=%s, agent_mode=%s, safe_mode=%s, dev_mode=%s",
            len(payload.prompt),
            payload.reasoning_mode.value,
            payload.domain_pack.value,
            payload.agent_mode.value,
            payload.orchestration.safe_mode_validator,
            payload.orchestration.dev_mode,
        )
        
        # Enhancement-5: Input risk assessment (if Safe Mode enabled)
        if GUARDRAILS_AVAILABLE and payload.orchestration.safe_mode_validator:
            risk = assess_query_risk(payload.prompt)
            if risk.blocked:
                logger.warning("Query blocked by risk assessment: %s", risk.block_reason)
                # Enhancement-2: Record error metric
                try:
                    from ..api.orchestrator_metrics import record_orchestrator_error
                    record_orchestrator_error("input_blocked")
                except Exception:
                    pass
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Query blocked: {risk.block_reason}",
                )
        
        # Run orchestration
        response = await run_orchestration(payload)
        
        # Enhancement-6: Apply Safe Mode output filtering
        if GUARDRAILS_AVAILABLE and payload.orchestration.safe_mode_validator:
            policy_check = check_output_policy(response.message)
            if not policy_check.is_allowed:
                logger.warning("Output violates safety policy, applying Safe Mode filter")
                sanitized, content_removed, issues = enforce_output_policy(response.message)
                if content_removed:
                    # Update response with sanitized content
                    response = ChatResponse(
                        message=sanitized,
                        models_used=response.models_used,
                        reasoning_mode=response.reasoning_mode,
                        reasoning_method=response.reasoning_method,
                        domain_pack=response.domain_pack,
                        agent_mode=response.agent_mode,
                        used_tuning=response.used_tuning,
                        metadata=response.metadata,
                        tokens_used=response.tokens_used,
                        latency_ms=response.latency_ms,
                        agent_traces=response.agent_traces,
                        extra={**response.extra, "safe_mode_filtered": True, "filter_issues": issues},
                    )
        
        logger.info(
            "Chat response generated: message_length=%d, latency=%dms",
            len(response.message),
            response.latency_ms or 0,
        )
        
        return response
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as exc:
        logger.exception("Chat endpoint error: %s", exc)
        # Enhancement-2: Log an orchestrator error metric
        try:
            from ..api.orchestrator_metrics import record_orchestrator_error
            record_orchestrator_error("internal")
        except Exception:
            pass
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Oops, something went wrong. Please try again.",
        ) from exc

