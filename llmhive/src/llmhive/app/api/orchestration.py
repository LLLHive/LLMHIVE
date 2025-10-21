"""Orchestration API endpoints."""
from __future__ import annotations

from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Task
from ..orchestrator import Orchestrator
from ..schemas import Critique, Improvement, ModelAnswer, OrchestrationRequest, OrchestrationResponse
from ..services.base import ProviderNotConfiguredError

router = APIRouter()


@lru_cache()
def get_orchestrator() -> Orchestrator:
    """Return a cached orchestrator instance.

    Using a cached factory keeps provider initialization lazy while ensuring
    each process picks up environment configuration changes after restarts.
    """

    return Orchestrator()


@router.post("/", response_model=OrchestrationResponse, status_code=status.HTTP_200_OK)
async def orchestrate(
    payload: OrchestrationRequest,
    db: Session = Depends(get_db),
    orchestrator: Orchestrator = Depends(get_orchestrator),
) -> OrchestrationResponse:
    """Run the multi-LLM orchestration workflow and persist the result."""

    try:
        artifacts = await orchestrator.orchestrate(payload.prompt, payload.models)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except ProviderNotConfiguredError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "message": str(exc),
                "providers": orchestrator.provider_status(),
            },
        ) from exc

    initial = [
        ModelAnswer(model=ans.model, content=ans.content, provider=ans.provider)
        for ans in artifacts.initial_responses
    ]
    critiques = [
        Critique(
            author=author,
            target=target,
            feedback=result.content,
            provider=result.provider,
        )
        for author, target, result in artifacts.critiques
    ]
    improvements = [
        Improvement(model=item.model, content=item.content, provider=item.provider)
        for item in artifacts.improvements
    ]

    task = Task(
        prompt=payload.prompt,
        model_names=[ans.model for ans in artifacts.initial_responses],
        initial_responses=[item.model_dump() for item in initial],
        critiques=[item.model_dump() for item in critiques],
        improvements=[item.model_dump() for item in improvements],
        final_response=artifacts.final_response.content,
    )
    db.add(task)
    db.flush()

    response = OrchestrationResponse(
        prompt=payload.prompt,
        models=task.model_names,
        initial_responses=initial,
        critiques=critiques,
        improvements=improvements,
        final_response=artifacts.final_response.content,
        final_provider=artifacts.final_response.provider,
    )
    return response
