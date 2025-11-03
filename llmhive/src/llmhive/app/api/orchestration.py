from __future__ import annotations

import logging
import os

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..knowledge import KnowledgeBase
from ..memory import MemoryManager
from ..models import Task
from ..orchestrator import Orchestrator
from ..schemas import (
    Critique,
    Improvement,
    KnowledgeHitSchema,
    ModelAnswer,
    ModelQualitySchema,
    ModelUsageMetrics,
    OrchestrationRequest,
    OrchestrationResponse,
    UsageMetrics,
    WebDocumentSchema,
)
from ..services.stub_provider import StubProvider

# Mapping of common model aliases (often used by UI labels or older configs)
# to the canonical identifiers expected by individual providers. This allows
# the API to accept friendly names like "gpt-4-turbo" while routing requests
# to the latest provider-specific model IDs (e.g. "gpt-4o").
MODEL_ALIAS_MAP: dict[str, str] = {
    "gpt-4-turbo": "gpt-4o",
    "gpt4-turbo": "gpt-4o",
    "gpt-4": "gpt-4.1",
    "gpt4": "gpt-4.1",
    "claude-3-opus": "claude-3-opus-20240229",
    "claude-3-opus-latest": "claude-3-opus-20240229",
    "claude-3-sonnet": "claude-3-sonnet-20240229",
    "claude-3-sonnet-latest": "claude-3-sonnet-20240229",
    "gemini-pro": "gemini-2.5-flash",
    "gemini-1.0-pro": "gemini-2.5-flash",
    "gemini-1.5-pro": "gemini-2.5-flash",
    "grok-1": "grok-3-mini",
    "grok-beta": "grok-3-mini",
}

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
    discarded_models: list[str] = []
    for item in raw_models:
        if not isinstance(item, str):
            discarded_models.append(repr(item))
            continue

        if "," in item:
            candidates = [p.strip() for p in item.split(",")]
        else:
            candidates = [item.strip()]

        valid = [candidate for candidate in candidates if candidate]
        if not valid:
            discarded_models.append(repr(item))
            continue

        normalized_models.extend(valid)

    # Deduplicate while preserving the caller's preferred ordering
    normalized_models = list(dict.fromkeys(normalized_models))

    # Remap friendly aliases (e.g. "gpt-4-turbo") to provider canonical IDs
    # so downstream provider clients receive model identifiers they recognize.
    alias_remap: dict[str, str] = {}
    canonical_models: list[str] = []
    for model in normalized_models:
        key = model.lower()
        canonical = MODEL_ALIAS_MAP.get(key)
        if canonical and canonical != model:
            alias_remap[model] = canonical
            canonical_models.append(canonical)
        else:
            canonical_models.append(canonical or model)

    if alias_remap:
        logger.info(
            "Remapped model aliases supplied by client to canonical identifiers: %s",
            alias_remap,
        )

    # Re-deduplicate after remapping to avoid duplicates caused by aliases
    normalized_models = list(dict.fromkeys(canonical_models))

    if discarded_models:
        logger.warning(
            "Ignoring invalid model identifiers supplied by client: %s",
            discarded_models,
        )

    if not normalized_models:
        if payload.models is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "No valid model names were provided. Supply at least one non-empty "
                    "string identifier or omit the models field to use defaults."
                ),
            )

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
    knowledge_base: KnowledgeBase | None = None
    knowledge_hits = []
    knowledge_snippets: list[str] = []

    db_dirty = False

    if payload.enable_memory:
        memory_manager = MemoryManager(db)
        conversation = memory_manager.get_or_create_conversation(
            payload.conversation_id,
            user_id=payload.user_id,
            topic=payload.topic,
        )
        memory_context = memory_manager.fetch_recent_context(conversation)
        context_string = memory_context.as_prompt_context()
        if conversation in db.new:
            db_dirty = True

    if payload.enable_knowledge and payload.user_id:
        knowledge_base = KnowledgeBase(db)
        knowledge_hits = knowledge_base.search(
            payload.user_id,
            payload.prompt,
            limit=settings.knowledge_max_hits,
        )
        knowledge_snippets = KnowledgeBase.snippets(knowledge_hits)
        knowledge_block = KnowledgeBase.to_prompt_block(knowledge_hits)
        if knowledge_block:
            context_parts = [context_string, knowledge_block]
            context_string = "\n\n".join([part for part in context_parts if part]) or None

    # Run orchestration
    requested_stub_only = all(str(m).lower().startswith("stub") for m in normalized_models)

    try:
        artifacts = await _orchestrator.orchestrate(
            payload.prompt,
            normalized_models,
            context=context_string,
            knowledge_snippets=knowledge_snippets,
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
        initial_responses = artifacts.initial_responses
        all_stub = bool(initial_responses) and all(
            StubProvider.is_stub_content(r.content)
            for r in initial_responses
        )
    except Exception:
        all_stub = False

    final_stub = False
    try:
        final_stub = StubProvider.is_stub_content(artifacts.final_response.content)
    except Exception:
        final_stub = False

    # Check if any real (non-stub) providers are configured
    has_real_providers = any(k != "stub" for k in _orchestrator.providers.keys())
    used_stub_provider = getattr(artifacts, "used_stub_provider", False)

    if (
        fail_on_stub
        and has_real_providers
        and (all_stub or final_stub)
        and not requested_stub_only
        and not used_stub_provider
    ):
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
        db_dirty = True
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
            db_dirty = True

            memory_manager.append_entry(
                conversation,
                role="assistant",
                content=artifacts.final_response.content,
                metadata={"models": [ans.model for ans in artifacts.initial_responses]},
            )
            db_dirty = True

            memory_manager.auto_summarize(conversation)
            db_dirty = True
            if payload.enable_knowledge and knowledge_base and payload.user_id:
                document = knowledge_base.record_interaction(
                    user_id=payload.user_id,
                    prompt=payload.prompt,
                    response=artifacts.final_response.content,
                    conversation_id=conversation.id,
                    supporting_notes=artifacts.supporting_notes,
                )
                if document is not None:
                    db_dirty = True
        except Exception as exc:
            logger.exception("Failed to update memory entries: %s", exc)
    elif payload.enable_knowledge and knowledge_base and payload.user_id:
        try:
            document = knowledge_base.record_interaction(
                user_id=payload.user_id,
                prompt=payload.prompt,
                response=artifacts.final_response.content,
                conversation_id=conversation.id if conversation else payload.conversation_id,
                supporting_notes=artifacts.supporting_notes,
            )
            if document is not None:
                db_dirty = True
        except Exception as exc:
            logger.exception("Failed to persist knowledge document: %s", exc)

    step_outputs_payload = {
        role: [ModelAnswer(model=result.model, content=result.content) for result in results]
        for role, results in artifacts.step_outputs.items()
    }
    evaluation_text = artifacts.evaluation.content if artifacts.evaluation else None

    knowledge_payload = [
        KnowledgeHitSchema(content=hit.content, score=hit.score, metadata=hit.metadata)
        for hit in knowledge_hits
    ]
    web_payload = [
        WebDocumentSchema(title=doc.title, url=doc.url, snippet=doc.snippet)
        for doc in artifacts.web_results
    ]

    quality_payload = [
        ModelQualitySchema(
            model=model,
            score=assessment.score,
            flags=assessment.flags,
            highlights=assessment.highlights,
        )
        for model, assessment in artifacts.quality_assessments.items()
    ]
    quality_payload.sort(key=lambda item: item.score, reverse=True)

    usage_payload = UsageMetrics(
        total_tokens=artifacts.usage.total_tokens,
        total_cost=artifacts.usage.total_cost,
        response_count=artifacts.usage.response_count,
        per_model={
            model: ModelUsageMetrics(
                tokens=metrics.tokens,
                cost=metrics.cost,
                responses=metrics.responses,
            )
            for model, metrics in artifacts.usage.per_model.items()
        },
    )

    response_payload = OrchestrationResponse(
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
        optimized_prompt=artifacts.optimized_prompt,
        knowledge_hits=knowledge_payload,
        web_results=web_payload,
        confirmation=artifacts.confirmation_notes,
        quality=quality_payload,
        usage=usage_payload,
    )

    if db_dirty:
        try:
            db.commit()
        except SQLAlchemyError as exc:
            db.rollback()
            logger.exception("Database commit failed: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to persist orchestration records",
            ) from exc

    return response_payload
