from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.orchestration.orchestrator import Orchestrator


class PromptRequest(BaseModel):
    user_id: str
    prompt: str
    preferred_models: Optional[List[str]] = None
    preferred_protocol: Optional[str] = None


router = APIRouter()


@router.get("/health", status_code=200)
def health_check() -> dict[str, str]:
    """Simple health check endpoint for the public API."""

    return {"status": "ok"}


@router.post("/prompt", summary="Submit a prompt to LLMHive")
async def process_prompt_stream(request: PromptRequest) -> StreamingResponse:
    """Stream the orchestrated response token-by-token back to the caller."""

    try:
        orchestrator = Orchestrator(
            user_id=request.user_id,
            preferred_models=request.preferred_models,
            preferred_protocol=request.preferred_protocol,
        )
        response_stream = orchestrator.run(request.prompt)
        return StreamingResponse(response_stream, media_type="text/plain")
    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover - defensive safety net
        raise HTTPException(
            status_code=500,
            detail=f"An internal error occurred: {exc}",
        ) from exc
