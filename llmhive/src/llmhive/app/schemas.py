"""Pydantic schemas for API requests and responses."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Critique(BaseModel):
    """Critique of one model's answer by another model."""

    author: str = Field(..., description="Model providing the critique")
    target: str = Field(..., description="Model whose answer is being critiqued")
    feedback: str = Field(..., description="Feedback text")
    provider: str | None = Field(
        default=None, description="Provider that generated the critique"
    )


class ModelAnswer(BaseModel):
    """Representation of a model answer."""

    model: str
    content: str
    provider: str | None = Field(
        default=None, description="Provider that generated the answer"
    )


class Improvement(BaseModel):
    """Refined answer from a model after critiques."""

    model: str
    content: str
    provider: str | None = Field(
        default=None, description="Provider that generated the improvement"
    )


class OrchestrationRequest(BaseModel):
    """Payload accepted by the orchestrate endpoint."""

    prompt: str = Field(..., description="Prompt to orchestrate across models")
    models: Optional[List[str]] = Field(
        default=None,
        description="Optional explicit list of model identifiers",
        examples=[["grok", "gpt-4"]],
    )

    @field_validator("models", mode="before")
    @classmethod
    def _split_comma_separated(cls, value):  # type: ignore[override]
        if value is None:
            return value
        if isinstance(value, str):
            candidates = [value]
        else:
            candidates = list(value)

        expanded: list[str] = []
        for candidate in candidates:
            if not isinstance(candidate, str):
                continue
            parts = [part.strip() for part in candidate.split(",") if part.strip()]
            if parts:
                expanded.extend(parts)
        return expanded or None


class OrchestrationResponse(BaseModel):
    """Response returned after orchestrating the models."""

    prompt: str
    models: List[str]
    initial_responses: List[ModelAnswer]
    critiques: List[Critique]
    improvements: List[Improvement]
    final_response: str
    final_provider: str | None = Field(
        default=None, description="Provider that generated the final synthesized response"
    )


class TaskRecord(BaseModel):
    """Schema representing a persisted orchestration task."""

    id: int
    prompt: str
    models: List[str] = Field(alias="model_names")
    final_response: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
