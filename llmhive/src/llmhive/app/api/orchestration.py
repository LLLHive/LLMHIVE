from __future__ import annotations

import logging
import os
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Task
from ..orchestrator import Orchestrator
from ..schemas import (
    Critique,
    Improvement,
    ModelAnswer,
    OrchestrationRequest,
    OrchestrationResponse,
)
from ..services.stub_provider import StubProvider

logger = logging.getLogger(__name__)

router = APIRouter()
_orchestrator = Orchestrator()


@router.get("/providers", status_code=status.HTTP_200_OK)
def providers_status():
    """
    Diagnostic endpoint (use in staging) to show which providers the Orchestrator has configured.
    Example: GET /api/v1/orchestration/providers
    """
    try:
        keys = list(_orchestrator.providers.keys())
        # For each provider, attempt to list models (if provider implements list_models)
        summary = {}
        for k, prov in _orchestrator.providers.items():
            try:
                models = prov.list_models() if hasattr(prov, "list_models") else []
            except Exception:
                models = []
            summary[k] = models
        return {"available_providers": keys, "provider_model_summary": summary}
    except Exception as exc:
        logger.exception("Failed to enumerate providers: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to enumerate providers")


@router.post("/", response_model=OrchestrationResponse, status_code=status.HTTP_200_OK)
async def orchestrate(
    payload: OrchestrationRequest,
    db: Session = Depends(get_db),
) -> OrchestrationResponse:
    """
    Orchestrate multiple LLMs for the given prompt.

    This endpoint:
    - Normalizes the 'models' array (splits comma-joined strings).
    - Validates that each requested model would route to a configured provider.
    - Runs orchestration and persists results.
    - Optionally fails loudly if all responses look like stub responses (config diagnostic).
    """

    # --- Normalize models: accept either ["a","b"] or ["a, b"] from callers
    raw_models = payload.models or []
    normalized_models: list[str] = []
    for item in raw_models:
        if isinstance(item, str) and "," in item:
            parts = [p.strip() for p in item.split(",") if p.strip()]
            normalized_models.extend(parts)
        else:
            normalized_models.append(item.strip() if isinstance(item, str) else item)

    if not normalized_models:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one model must be provided in the 'models' array.",
        )

    # --- Validate each requested model maps to a configured non-stub provider.
    unsupported: list[str] = []
    for m in normalized_models:
        try:
            provider = _orchestrator._select_provider(m)
        except Exception:
            provider = _orchestrator.providers.get("stub", StubProvider())
        # If provider is a stub provider and the requested model is not an explicit 'stub' request, mark unsupported
        if isinstance(provider, StubProvider) and not str(m).lower().startswith("stub"):
            unsupported.append(m)

    if unsupported:
        logger.warning("Requested models do not have configured providers: %s", unsupported)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"The following models are not configured or supported in this deployment: {unsupported}. "
                "Ensure provider API keys/settings are present and correct. Call GET /api/v1/orchestration/providers to see what is configured."
            ),
        )

    # --- Run orchestration
    try:
        artifacts = await _orchestrator.orchestrate(payload.prompt, normalized_models)
    except ValueError as exc:
        # Likely an invalid argument (e.g., empty model list)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Orchestration failed: %s", exc)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Orchestration failed; check server logs")

    # --- Optional staging fail-fast: if all initial responses look like stubs, fail loudly so ops fix config
    # Controlled by env var LLMHIVE_FAIL_ON_STUB (default "true" to surface issues in staging)
    fail_on_stub = os.getenv("LLMHIVE_FAIL_ON_STUB", "true").lower() not in ("0", "false", "no")
    try:
        all_stub = all(
            isinstance(r.content, str)
            and r.content.startswith(f"[{r.model}] Response to:")
            for r in artifacts.initial_responses
        )
    except Exception:
        all_stub = False

    if fail_on_stub and all_stub:
        available = list(_orchestrator.providers.keys())
        logger.error("All providers returned stub responses. Available providers: %s", available)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "No configured LLM providers produced real responses (received only stub placeholders). "
                "Check provider API keys, Secret Manager access, and environment variables. "
                f"Available providers at runtime: {available}. See GET /api/v1/orchestration/providers"
            ),
        )

    # --- Convert artifacts into response shapes
    initial = [ModelAnswer(model=ans.model, content=ans.content) for ans in artifacts.initial_responses]

    critiques = [
        Critique(author=author, target=target, feedback=result.content)
        for author, target, result in artifacts.critiques
    ]

    improvements = [Improvement(model=item.model, content=item.content) for item in artifacts.improvements]

    # --- Persist a Task record (best-effort; errors here should not break successful responses)
    try:
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
    except Exception as exc:
        logger.exception("Failed to persist orchestration task: %s", exc)
        # Continue — we still return the orchestration result even if DB persists fails

    response = OrchestrationResponse(
        prompt=payload.prompt,
        models=[ans.model for ans in artifacts.initial_responses],
        initial_responses=initial,
        critiques=critiques,
        improvements=improvements,
        final_response=artifacts.final_response.content,
    )

    return response
