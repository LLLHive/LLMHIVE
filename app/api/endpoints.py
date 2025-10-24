"""
API Endpoints for LLMHive.

This module defines the routes for interacting with the LLMHive platform.
The primary endpoint is for submitting prompts to the Orchestrator Engine.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from ..orchestration.orchestrator import Orchestrator

# Define the router for this module
router = APIRouter()

class PromptRequest(BaseModel):
    """
    Defines the request model for a user prompt.
    """
    user_id: str
    prompt: str

class PromptResponse(BaseModel):
    """
    Defines the response model for a processed prompt.
    """
    answer: str

@router.post("/prompt", response_model=PromptResponse, summary="Submit a prompt to LLMHive")
async def process_prompt(request: PromptRequest):
    """
    Receives a user prompt, processes it through the Orchestrator,
    and returns the synthesized answer.

    - **user_id**: A unique identifier for the user.
    - **prompt**: The user's query.
    """
    try:
        orchestrator = Orchestrator(user_id=request.user_id)
        final_answer = await orchestrator.run(request.prompt)
        return PromptResponse(answer=final_answer)
    except Exception as e:
        # In a real application, logging would be more detailed.
        print(f"An error occurred: {e}")
        raise HTTPException(status_code=500, detail="An internal error occurred while processing the prompt.")
