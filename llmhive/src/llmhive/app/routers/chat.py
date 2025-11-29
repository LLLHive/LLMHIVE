"""Chat API router for LLMHive."""
from __future__ import annotations

import logging
from fastapi import APIRouter, Depends, HTTPException, status

from ..auth import verify_api_key
from ..models.orchestration import ChatRequest, ChatResponse
from ..services.orchestrator_adapter import run_orchestration

logger = logging.getLogger(__name__)

# Define router with /v1 prefix
router = APIRouter(prefix="/v1", tags=["chat"])


@router.post("/chat", response_model=ChatResponse, status_code=status.HTTP_200_OK)
async def chat_endpoint(
    payload: ChatRequest,
    user: str = Depends(verify_api_key),
) -> ChatResponse:
    """
    Chat orchestration endpoint.
    
    Accepts a ChatRequest with prompt, reasoning mode, domain pack, agent mode,
    tuning options, metadata, and conversation history.
    
    Returns a ChatResponse with the final answer and orchestration artifacts.
    """
    try:
        logger.info(
            "Chat request received: prompt_length=%d, reasoning_mode=%s, domain=%s, agent_mode=%s",
            len(payload.prompt),
            payload.reasoning_mode.value,
            payload.domain_pack.value,
            payload.agent_mode.value,
        )
        
        # Run orchestration
        response = await run_orchestration(payload)
        
        logger.info(
            "Chat response generated: message_length=%d, latency=%dms",
            len(response.message),
            response.latency_ms or 0,
        )
        
        return response
        
    except Exception as exc:
        logger.exception("Chat endpoint error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(exc)}",
        ) from exc

