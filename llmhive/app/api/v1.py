"""Versioned API routes for LLMHIVE."""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from ..core.security import sanitize_output
from ..core.settings import settings
from ..orchestration.orchestrator import OrchestrationOptions, Orchestrator

logger = logging.getLogger(__name__)

router = APIRouter(tags=["orchestration"])
orchestrator = Orchestrator()


class SliderOptions(BaseModel):
    """User controllable sliders that influence orchestration depth."""

    accuracy: float = Field(default=settings.default_accuracy, ge=0.0, le=1.0)
    speed: float = Field(default=settings.default_speed, ge=0.0, le=1.0)
    creativity: float = Field(default=settings.default_creativity, ge=0.0, le=1.0)
    cost: float = Field(default=settings.default_cost, ge=0.0, le=1.0)
    max_tokens: int = Field(default=600, ge=64, le=4096)
    json_mode: bool = Field(default=False)


class OrchestrateRequest(BaseModel):
    """Request payload for the orchestration endpoint."""

    query: str = Field(..., min_length=1)
    options: SliderOptions = Field(default_factory=SliderOptions)


class Citation(BaseModel):
    source: str
    span: str


class OrchestrateResponse(BaseModel):
    """Structured response returned to API clients."""

    final_answer: str
    confidence: float = Field(ge=0.0, le=1.0)
    key_points: list[str]
    citations: list[Citation]
    costs: dict[str, float]
    timings: dict[str, float]


async def get_orchestrator() -> Orchestrator:
    """Dependency injection hook for orchestrator, facilitates testing."""
    return orchestrator


@router.post("/orchestrate", response_model=OrchestrateResponse)
async def orchestrate(
    payload: OrchestrateRequest,
    orchestrator: Orchestrator = Depends(get_orchestrator),
) -> OrchestrateResponse:
    """Trigger the multi-LLM orchestration workflow."""

    logger.info("Received orchestration request", extra={"query_len": len(payload.query)})

    options = OrchestrationOptions(
        accuracy=payload.options.accuracy,
        speed=payload.options.speed,
        creativity=payload.options.creativity,
        cost=payload.options.cost,
        max_tokens=payload.options.max_tokens,
        json_mode=payload.options.json_mode,
    )

    result = await orchestrator.run(query=payload.query, options=options)

    sanitized = sanitize_output(result.final_answer)

    response = OrchestrateResponse(
        final_answer=sanitized,
        confidence=result.confidence,
        key_points=result.key_points,
        citations=[Citation(**c.dict()) for c in result.citations],
        costs=result.costs,
        timings=result.timings,
    )

    return response
