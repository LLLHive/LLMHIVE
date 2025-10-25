from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from starlette.responses import StreamingResponse
from typing import Optional, List
from orchestration.orchestrator import Orchestrator

class PromptRequest(BaseModel):
    user_id: str
    prompt: str
    preferred_models: Optional[List[str]] = None
    preferred_protocol: Optional[str] = None

router = APIRouter()

@router.get("/health", status_code=200)
def health_check():
    """
    Simple health check endpoint.
    """
    return {"status": "ok"}

@router.post("/prompt", summary="Submit a prompt to LLMHive")
async def process_prompt_stream(request: PromptRequest):
    try:
        orchestrator = Orchestrator(
            user_id=request.user_id,
            preferred_models=request.preferred_models,
            preferred_protocol=request.preferred_protocol
        )
        response_stream = orchestrator.run(request.prompt)
        return StreamingResponse(response_stream, media_type="text/plain")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An internal error occurred: {str(e)}")