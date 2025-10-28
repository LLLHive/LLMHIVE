"""Pydantic schemas for API requests and responses."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class Critique(BaseModel):
    """Critique of one model's answer by another model."""

    author: str = Field(..., description="Model providing the critique")
    target: str = Field(..., description="Model whose answer is being critiqued")
    feedback: str = Field(..., description="Feedback text")


class ModelAnswer(BaseModel):
    """Representation of a model answer."""

    model: str
    content: str


class Improvement(BaseModel):
    """Refined answer from a model after critiques."""

    model: str
    content: str


class OrchestrationRequest(BaseModel):
    """Payload accepted by the orchestrate endpoint."""

    prompt: str = Field(..., description="Prompt to orchestrate across models")
    models: Optional[List[str]] = Field(
        default=None, description="Optional explicit list of model identifiers"
    )
    user_id: Optional[str] = Field(default=None, description="Identifier for the requesting user")
    conversation_id: Optional[int] = Field(default=None, description="Existing conversation identifier")
    topic: Optional[str] = Field(default=None, description="Optional topic hint for memory organization")
    enable_memory: bool = Field(default=True, description="Enable conversational memory retrieval and storage")


class OrchestrationResponse(BaseModel):
    """Response returned after orchestrating the models."""

    prompt: str
    models: List[str]
    initial_responses: List[ModelAnswer]
    critiques: List[Critique]
    improvements: List[Improvement]
    final_response: str
    conversation_id: Optional[int]
    consensus_notes: List[str]
    plan: Dict[str, Any]
    guardrails: Optional[Dict[str, Any]]
    context: Optional[str]


class TaskRecord(BaseModel):
    """Schema representing a persisted orchestration task."""

    id: int
    prompt: str
    models: List[str] = Field(alias="model_names")
    final_response: str
    conversation_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
