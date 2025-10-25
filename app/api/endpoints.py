"""
API Endpoints for LLMHive.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from starlette.responses import StreamingResponse
from typing import Optional, List
from ..orchestration.orchestrator import Orchestrator

router = APIRouter()

class PromptRequest(BaseModel):
    user_id: str
    prompt: str
    preferred_models: Optional[List[str]] = None
    preferred_protocol: Optional[str] = None

@router.post("/prompt", summary="Submit a prompt to LLMHive for a streaming response")
async def process_prompt_stream(request: PromptRequest):
    """
    Receives a user prompt, processes it through the Orchestrator,
    and streams the synthesized answer back token by token.
    """
    try:
        orchestrator = Orchestrator(
            user_id=request.user_id,
            preferred_models=request.preferred_models,
            preferred_protocol=request.preferred_protocol
        )
        response_stream = orchestrator.run(request.prompt)
        return StreamingResponse(response_stream, media_type="text/plain")
    except Exception as e:
        import logging
        logging.error(f"Error in process_prompt_stream: {e}", exc_info=True)
        # In a real app, you'd have more structured logging and error responses.
        raise HTTPException(status_code=500, detail="An internal error occurred while processing the prompt.")
