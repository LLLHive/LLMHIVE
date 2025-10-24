"""Orchestration API endpoints."""
from __future__ import annotations

import logging
from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..config import get_settings
from ..database import get_db
from ..models import Task
from ..orchestrator import Orchestrator
from ..schemas import Critique, Improvement, ModelAnswer, OrchestrationRequest, OrchestrationResponse
from ..services.base import ProviderNotConfiguredError

router = APIRouter()
logger = logging.getLogger(__name__)


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

    normalized_models: list[str] | None = None
    if payload.models is not None:
        normalized_models = []
        for item in payload.models:
            if isinstance(item, str):
                fragments = [part.strip() for part in item.split(",") if part.strip()]
                if fragments:
                    normalized_models.extend(fragments)
            elif item is not None:
                normalized_models.append(str(item).strip())
        normalized_models = [model for model in normalized_models if model]
        if not normalized_models:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"message": "At least one model must be provided in the 'models' array."},
            )

        unsupported: list[str] = []
        for requested in normalized_models:
            requested_label, canonical = orchestrator._resolve_model(requested)
            try:
                provider_key, _ = orchestrator._select_provider(canonical)
                orchestrator._validate_stub_usage(provider_key, requested_label, canonical)
            except ProviderNotConfiguredError as exc:
                logger.warning("Requested model '%s' is not available: %s", requested_label, exc)
                unsupported.append(requested_label)

        if unsupported:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": "One or more requested models are not configured for this deployment.",
                    "models": unsupported,
                    "providers": orchestrator.provider_status(),
                },
            )

    try:
        artifacts = await orchestrator.orchestrate(payload.prompt, normalized_models)
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

    current_settings = get_settings()

    stub_models = [
        answer.model for answer in artifacts.initial_responses if answer.provider == "stub"
    ]

    # Guardrail: real model names should never be served by the stub provider. If that
    # happens we fail loudly regardless of the fail-on-stub setting so operators know
    # credentials are missing or misconfigured.
    real_model_stub_responses = [
        model for model in stub_models if "stub" not in model.lower()
    ]
    if real_model_stub_responses:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "message": (
                    "Stub provider responses were generated for real model requests. "
                    "Verify provider API keys and deployment settings."
                ),
                "models": real_model_stub_responses,
                "providers": orchestrator.provider_status(),
            },
        )

    if current_settings.fail_on_stub_responses and stub_models:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "message": (
                    "Stub provider responses are disabled. Configure real provider credentials or set "
                    "FAIL_ON_STUB_RESPONSES=0 for development overrides."
                ),
                "models": stub_models,
                "providers": orchestrator.provider_status(),
            },
        )

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
