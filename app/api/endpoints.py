"""
API Endpoints for LLMHive.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from starlette.responses import StreamingResponse
from ..orchestration.orchestrator import Orchestrator

router = APIRouter()

class PromptRequest(BaseModel):
    user_id: str
    prompt: str

@router.post("/prompt", summary="Submit a prompt to LLMHive for a streaming response")
async def process_prompt_stream(request: PromptRequest):
    """
    Receives a user prompt, processes it through the Orchestrator,
    and streams the synthesized answer back token by token.
    """
    try:
        orchestrator = Orchestrator(user_id=request.user_id)
        response_stream = orchestrator.run(request.prompt)
        return StreamingResponse(response_stream, media_type="text/plain")
    except Exception as e:
        print(f"An error occurred: {e}")
        raise HTTPException(status_code=500, detail=f"An internal error occurred: {str(e)}")
