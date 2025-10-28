from __future__ import annotations

import logging
import os

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..memory import MemoryManager
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

# Included in api/__init__.py with prefix "/orchestration"
router = APIRouter()
_orchestrator = Orchestrator()


@router.get("/providers", status_code=status.HTTP_200_OK)
def providers_status():
    """
    Diagnostic endpoint to show which providers the Orchestrator has configured.
    Final path: /api/v1/orchestration/providers
    """
    try:
        keys = list(_orchestrator.providers.keys())
        summary = {}
        for k, prov in _orchestrator.providers.items():
            try:
                models = prov.list_models() if hasattr(prov, "list_models") else []
            except Exception:
                models = []
            summary[k] = models
        registry_summary = _orchestrator.model_registry.summarize()
        return {
            "available_providers": keys,
            "provider_model_summary": summary,
            "registry_summary": registry_summary,
        }
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

    - Normalizes the 'models' array (splits comma-joined strings).
    - Validates that each requested model would route to a configured provider.
    - Runs orchestration and persists the result.
    - Optionally fails loudly if all responses look like stub responses (config diagnostic).
    """

    # Normalize models: accept either ["a","b"] or ["a, b"]
    raw_models = payload.models or list(settings.default_models)
    normalized_models: list[str] = []
    for item in raw_models:
        if isinstance(item, str) and "," in item:
            parts = [p.strip() for p in item.split(",") if p.strip()]
            normalized_models.extend(parts)
        else:
            normalized_models.append(item.strip() if isinstance(item, str) else item)

    if not normalized_models:
        logger.error(
            "No models supplied and DEFAULT_MODELS configuration is empty."
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "No models provided and no DEFAULT_MODELS configured. "
                "Add models to the request or configure DEFAULT_MODELS."
            ),
        )

    if payload.models is None:
        logger.info(
            "No models specified in request; using default models from settings.",
        )

    # Log warning if models will use stub provider as fallback
    # (allows execution to proceed even when real providers aren't configured)
    stub_fallback: list[str] = []
    for m in normalized_models:
        try:
            provider = _orchestrator._select_provider(m)
        except Exception:
            provider = _orchestrator.providers.get("stub", StubProvider())
        if isinstance(provider, StubProvider) and not str(m).lower().startswith("stub"):
            stub_fallback.append(m)

    if stub_fallback:
        logger.warning(
            "The following models will use stub provider (real provider not configured): %s. "
            "Call GET /api/v1/orchestration/providers to see what is configured.",
            stub_fallback
        )

    # Prepare memory context
    memory_context = None
    conversation = None
    memory_manager: MemoryManager | None = None
    context_string: str | None = None

    if payload.enable_memory:
        memory_manager = MemoryManager(db)
        conversation = memory_manager.get_or_create_conversation(
            payload.conversation_id,
            user_id=payload.user_id,
            topic=payload.topic,
        )
        memory_context = memory_manager.fetch_recent_context(conversation)
        context_string = memory_context.as_prompt_context()

    # Run orchestration
    try:
        artifacts = await _orchestrator.orchestrate(
            payload.prompt,
            normalized_models,
            context=context_string,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Orchestration failed: %s", exc)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Orchestration failed; check server logs")

    # Fail-fast if all responses are stubs when real providers are configured (LLMHIVE_FAIL_ON_STUB env var).
    # Only fails if non-stub providers exist (otherwise stub provider is the expected fallback).
    fail_on_stub = os.getenv("LLMHIVE_FAIL_ON_STUB", "true").lower() not in ("0", "false", "no")
    try:
        all_stub = all(
            isinstance(r.content, str)
            and r.content.startswith(f"[{r.model}] Response to:")
            for r in artifacts.initial_responses
        )
    except Exception:
        all_stub = False

    # Check if any real (non-stub) providers are configured
    has_real_providers = any(k != "stub" for k in _orchestrator.providers.keys())

    if fail_on_stub and all_stub and has_real_providers:
        available = list(_orchestrator.providers.keys())
        logger.error("All providers returned stub responses despite real providers being configured. Check provider configurations. Available providers: %s", available)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "No configured LLM providers produced real responses (received only stub placeholders). "
                "Check provider API keys, Secret Manager access, and environment variables. "
                f"Available providers at runtime: {available}. See GET /api/v1/orchestration/providers"
            ),
        )

    # Convert artifacts into response
    initial = [ModelAnswer(model=ans.model, content=ans.content) for ans in artifacts.initial_responses]
    critiques = [
        Critique(author=author, target=target, feedback=result.content)
        for author, target, result in artifacts.critiques
    ]
    improvements = [Improvement(model=item.model, content=item.content) for item in artifacts.improvements]

    # Persist Task (best-effort)
    try:
        task = Task(
            prompt=payload.prompt,
            model_names=[ans.model for ans in artifacts.initial_responses],
            initial_responses=[item.model_dump() for item in initial],
            critiques=[item.model_dump() for item in critiques],
            improvements=[item.model_dump() for item in improvements],
            final_response=artifacts.final_response.content,
            conversation_id=conversation.id if conversation else payload.conversation_id,
        )
        db.add(task)
        db.flush()
    except Exception as exc:
        logger.exception("Failed to persist orchestration task: %s", exc)

    plan_dict = {
        "strategy": artifacts.plan.strategy,
        "confidence": artifacts.plan.confidence,
        "focus_areas": list(artifacts.plan.focus_areas),
        "steps": [
            {
                "role": step.role.value,
                "description": step.description,
                "required_capabilities": list(step.required_capabilities),
                "candidate_models": list(step.candidate_models),
                "parallelizable": step.parallelizable,
            }
            for step in artifacts.plan.steps
        ],
    }

    guardrail_payload = None
    if artifacts.guardrail_report is not None:
        guardrail_payload = {
            "passed": artifacts.guardrail_report.passed,
            "issues": artifacts.guardrail_report.issues,
            "advisories": artifacts.guardrail_report.advisories,
        }

    # Persist conversation memory after successful orchestration
    if payload.enable_memory and memory_manager and conversation:
        try:
            memory_manager.append_entry(
                conversation,
                role="user",
                content=payload.prompt,
                metadata={"models": normalized_models},
            )
            memory_manager.append_entry(
                conversation,
                role="assistant",
                content=artifacts.final_response.content,
                metadata={"models": [ans.model for ans in artifacts.initial_responses]},
            )
            memory_manager.auto_summarize(conversation)
        except Exception as exc:
            logger.exception("Failed to update memory entries: %s", exc)

    step_outputs_payload = {
        role: [ModelAnswer(model=result.model, content=result.content) for result in results]
        for role, results in artifacts.step_outputs.items()
    }
    evaluation_text = artifacts.evaluation.content if artifacts.evaluation else None

    return OrchestrationResponse(
        prompt=payload.prompt,
        models=[ans.model for ans in artifacts.initial_responses],
        initial_responses=initial,
        critiques=critiques,
        improvements=improvements,
        final_response=artifacts.final_response.content,
        conversation_id=conversation.id if conversation else payload.conversation_id,
        consensus_notes=artifacts.consensus_notes,
        plan=plan_dict,
        guardrails=guardrail_payload,
        context=context_string,
        step_outputs=step_outputs_payload,
        supporting_notes=artifacts.supporting_notes,
        evaluation=evaluation_text,
    )
