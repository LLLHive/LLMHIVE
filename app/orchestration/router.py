from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from .engine import OrchestrationEngine
from .models import Job
import logging

logger = logging.getLogger("llmhive")
router = APIRouter()

# Initialize the engine once. It will be reused for all requests.
engine = OrchestrationEngine()

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
        completed_job = engine.execute_job(job)
        
        # 3. Return the completed job
        return completed_job

    except Exception as e:
        logger.critical(f"Unhandled exception in /prompt endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An internal server error occurred.")

@router.get("/health")
async def health_check():
    """Simple health check for the orchestration service."""
    return {"status": "ok"}
