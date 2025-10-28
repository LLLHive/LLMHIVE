from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from .engine import OrchestrationEngine
from .models import Job
import logging
from typing import Optional

logger = logging.getLogger("llmhive")
router = APIRouter()
versioned_router = APIRouter(prefix="/orchestration")

# Lazily instantiate the engine to avoid requiring cloud credentials during import.
_engine: Optional[OrchestrationEngine] = None


def get_engine() -> OrchestrationEngine:
    global _engine
    if _engine is None:
        _engine = OrchestrationEngine()
    return _engine

class PromptRequest(BaseModel):
    prompt: str

@router.post("/prompt", response_model=Job)
async def submit_prompt(request: PromptRequest):
    """
    Accepts a user prompt, creates a Job, executes it via the
    OrchestrationEngine, and returns the final state of the Job.
    """
    logger.info(f"Received new prompt request (length: {len(request.prompt)} chars)")
    try:
        # 1. Create a Job from the prompt
        job = Job.from_prompt(request.prompt)
        
        # 2. Execute the Job using the engine
        completed_job = get_engine().execute_job(job)
        
        # 3. Return the completed job
        return completed_job

    except Exception as e:
        logger.critical(f"Unhandled exception in /prompt endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An internal server error occurred.")

@router.get("/health")
async def health_check():
    """Simple health check for the orchestration service."""
    return {"status": "ok"}


@versioned_router.post("/", response_model=Job, tags=["Orchestration"])
async def orchestrate_prompt(request: PromptRequest) -> Job:
    """Versioned orchestration endpoint compatible with documented /api/v1 routes."""
    return await submit_prompt(request)


@versioned_router.get("/health", tags=["Orchestration"])
async def orchestrator_health() -> dict[str, str]:
    """Expose orchestration health check under the versioned API prefix."""
    return await health_check()
