"""Core orchestration workflow for coordinating multiple LLMs."""
from __future__ import annotations

import asyncio
import logging
import os
import re
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, Iterable, List, Sequence, Tuple

from .config import settings
from .guardrails import GuardrailReport, SafetyValidator
from .model_registry import ModelRegistry
from .planner import PlanRole, PlanStep, ReasoningPlanner, ReasoningPlan
from .prompt_optimizer import optimize_prompt
from .services.base import LLMProvider, LLMResult, ProviderNotConfiguredError
from .services.openai_provider import OpenAIProvider
from .services.stub_provider import StubProvider
from .services.web_research import WebDocument, WebResearchClient

logger = logging.getLogger(__name__)

# Import optional providers with fallback
try:
    from .services.anthropic_provider import AnthropicProvider
except ImportError:
    logger.warning("AnthropicProvider not available")
    AnthropicProvider = None

try:
    from .services.grok_provider import GrokProvider
except ImportError:
    logger.warning("GrokProvider not available")
    GrokProvider = None

try:
    from ..providers.gemini import GeminiProvider
except ImportError:
    logger.warning("GeminiProvider not available")
    GeminiProvider = None

try:
    from .services.deepseek_provider import DeepSeekProvider
except ImportError:
    logger.warning("DeepSeekProvider not available")
    DeepSeekProvider = None

try:
    from .services.manus_provider import ManusProvider
except ImportError:
    logger.warning("ManusProvider not available")
    ManusProvider = None


@dataclass(slots=True)
class ResponseAssessment:
    """Lightweight quality assessment for a model response."""

    result: LLMResult
    score: float
    flags: list[str]
    highlights: list[str]


@dataclass(slots=True)
class ModelUsage:
    """Aggregated usage metrics for a single model."""

    tokens: int = 0
    cost: float = 0.0
    responses: int = 0


@dataclass(slots=True)
class UsageSummary:
    """Aggregated token/cost usage for an orchestration run."""

    total_tokens: int
    total_cost: float
    response_count: int
    per_model: Dict[str, ModelUsage]


@dataclass(slots=True)
class OrchestrationArtifacts:
    """Artifacts produced by the orchestrator stages."""

    plan: ReasoningPlan
    context_prompt: str | None
    optimized_prompt: str
    initial_responses: list[LLMResult]
    critiques: list[Tuple[str, str, LLMResult]]  # (author, target, result)
    improvements: list[LLMResult]
    consensus_notes: list[str]
    final_response: LLMResult
    guardrail_report: GuardrailReport | None
    step_outputs: Dict[str, list[LLMResult]]
    supporting_notes: list[str]
    quality_assessments: Dict[str, ResponseAssessment]
    evaluation: LLMResult | None
    knowledge_snippets: list[str]
    web_results: list[WebDocument]
    confirmation_notes: list[str]
    usage: UsageSummary
    used_stub_provider: bool


class _OutputFormatterV1:
    """Enforces a clean, consistent final Markdown structure."""
    def __init__(self, require_citations=True):
        self.require_citations = require_citations

    def format(self, question:str, final_answer:str, web_results=None, assumptions=None, notes=None):
        web_results = web_results or []
        assumptions = [a for a in (assumptions or []) if a and a.strip()]
        notes = [n for n in (notes or []) if n and n.strip()]

        # Build sources list from web_results if present
        src_lines = []
        for d in web_results[:6]:
            title = getattr(d, "title", None) or (d.get("title") if isinstance(d, dict) else None) or "source"
            url = getattr(d, "url", None) or (d.get("url") if isinstance(d, dict) else None) or ""
            snippet = getattr(d, "snippet", None) or (d.get("snippet") if isinstance(d, dict) else None) or ""
            item = f"- **{title}** — {snippet[:160]}".rstrip()
            if url: item += f"  \n  {url}"
            src_lines.append(item)

        # Assemble structured markdown
        out = []
        out.append("## Final Answer")
        out.append(final_answer.strip())

        # Make sure we always give quick scan
        out.append("\n---\n### TL;DR")
        tl = final_answer.strip().splitlines()[0]
        if len(tl) > 240: tl = tl[:237] + "…"
        out.append(f"- {tl}")

        # Optional assumptions
        if assumptions:
            out.append("\n### Assumptions used")
            for a in assumptions:
                out.append(f"- {a.strip()}")

        # Sources from web (if any)
        if src_lines and self.require_citations:
            out.append("\n### Sources")
            out.extend(src_lines)

        # No debug/notes after final unless explicitly requested
        return "\n".join(out).strip()

class Orchestrator:

    def _needs_clarification(self, prompt:str)->bool:
        """Very light heuristic: only true when critical fields are obviously missing."""
        low = prompt.lower()
        # Add lightweight checks; keep conservative to avoid loops
        triggers = ["tbd", "unknown", "???", "<required", "{required}"]
        return any(t in low for t in triggers)
    """Coordinates the multi-stage collaboration workflow across models."""

    def __init__(self, providers: Dict[str, LLMProvider] | None = None) -> None:
        if providers is None:
            providers = self._default_providers()
        self.providers = providers
        self.model_registry = ModelRegistry(self.providers)
        self.planner = ReasoningPlanner()
        self.guardrails = SafetyValidator()
        self.web_research = WebResearchClient(
            timeout=getattr(settings, "web_search_timeout", 8.0)
        )
        logger.info("Orchestrator initialized with providers: %s", list(self.providers.keys()))

    def _get_key(self, *candidates: str) -> str | None:
        """
        Return first non-empty value found either from settings.attr or from OS env.
        Example: _get_key("openai_api_key", "OPENAI_API_KEY", "OPENAI_KEY")
        """
        for name in candidates:
            val = getattr(settings, name, None)
            if val:
                return val
            val = os.getenv(name)
            if val:
                return val
            val = os.getenv(name.upper())
            if val:
                return val
        return None

    def _default_providers(self) -> Dict[str, LLMProvider]:
        mapping: Dict[str, LLMProvider] = {}

        # OpenAI / GPT family
        try:
            openai_key = self._get_key("openai_api_key", "OPENAI_API_KEY", "OPENAI_KEY")
            if openai_key:
                mapping["openai"] = OpenAIProvider(api_key=openai_key, timeout=getattr(settings, "openai_timeout_seconds", None))
                logger.info("OpenAI provider configured.")
            else:
                raise ProviderNotConfiguredError("OpenAI API key not set")
        except ProviderNotConfiguredError:
            logger.info("OpenAI provider not configured; skipping.")

        # Anthropic / Claude
        try:
            if AnthropicProvider is None:
                raise ProviderNotConfiguredError("AnthropicProvider module not available")
            anthropic_key = self._get_key("anthropic_api_key", "ANTHROPIC_API_KEY")
            if anthropic_key:
                mapping["anthropic"] = AnthropicProvider(api_key=anthropic_key, timeout=getattr(settings, "anthropic_timeout_seconds", None))
                logger.info("Anthropic provider configured.")
            else:
                raise ProviderNotConfiguredError("Anthropic API key not set")
        except ProviderNotConfiguredError:
            logger.info("Anthropic provider not configured; skipping.")

        # Grok (xAI)
        try:
            if GrokProvider is None:
                raise ProviderNotConfiguredError("GrokProvider module not available")
            grok_key = self._get_key("grok_api_key", "GROK_API_KEY")
            if grok_key:
                mapping["grok"] = GrokProvider(api_key=grok_key, timeout=getattr(settings, "grok_timeout_seconds", None))
                logger.info("Grok provider configured.")
            else:
                raise ProviderNotConfiguredError("Grok API key not set")
        except ProviderNotConfiguredError:
            logger.info("Grok provider not configured; skipping.")

        # Gemini (Google)
        try:
            if GeminiProvider is None:
                raise ProviderNotConfiguredError("GeminiProvider module not available")
            gemini_key = self._get_key("gemini_api_key", "GEMINI_API_KEY")
            if gemini_key:
                mapping["gemini"] = GeminiProvider(api_key=gemini_key, timeout=getattr(settings, "gemini_timeout_seconds", None))
                logger.info("Gemini provider configured.")
            else:
                raise ProviderNotConfiguredError("Gemini API key not set")
        except ProviderNotConfiguredError:
            logger.info("Gemini provider not configured; skipping.")

        # DeepSeek
        try:
            if DeepSeekProvider is None:
                raise ProviderNotConfiguredError("DeepSeekProvider module not available")
            deepseek_key = self._get_key("deepseek_api_key", "DEEPSEEK_API_KEY")
            if deepseek_key:
                mapping["deepseek"] = DeepSeekProvider(api_key=deepseek_key, timeout=getattr(settings, "deepseek_timeout_seconds", None))
                logger.info("DeepSeek provider configured.")
            else:
                raise ProviderNotConfiguredError("DeepSeek API key not set")
        except ProviderNotConfiguredError:
            logger.info("DeepSeek provider not configured; skipping.")

        # Manus (proxy)
        try:
            if ManusProvider is None:
                raise ProviderNotConfiguredError("ManusProvider module not available")
            manus_key = self._get_key("manus_api_key", "MANUS_API_KEY")
            if manus_key:
                mapping["manus"] = ManusProvider(api_key=manus_key, timeout=getattr(settings, "manus_timeout_seconds", None))
                logger.info("Manus provider configured.")
            else:
                raise ProviderNotConfiguredError("Manus API key not set")
        except ProviderNotConfiguredError:
            logger.info("Manus provider not configured; skipping.")

        # Always provide a stub provider as a fallback
        mapping.setdefault("stub", StubProvider())

        logger.info("Provider mapping completed. Available providers: %s", list(mapping.keys()))
        expected = {
            "openai": ("openai_api_key", "OPENAI_API_KEY"),
            "anthropic": ("anthropic_api_key", "ANTHROPIC_API_KEY"),
            "grok": ("grok_api_key", "GROK_API_KEY"),
            "gemini": ("gemini_api_key", "GEMINI_API_KEY"),
            "deepseek": ("deepseek_api_key", "DEEPSEEK_API_KEY"),
            "manus": ("manus_api_key", "MANUS_API_KEY"),
        }
        missing = [k for k, names in expected.items() if not self._get_key(*names)]
        if missing:
            logger.debug("Provider API keys missing for: %s", missing)

        return mapping

    def _select_provider(self, model: str) -> LLMProvider:
        lower = model.lower()
        if lower.startswith("gpt") and "openai" in self.providers:
            return self.providers["openai"]
        if lower.startswith("claude") and "anthropic" in self.providers:
            return self.providers["anthropic"]
        if lower.startswith("grok") and "grok" in self.providers:
            return self.providers["grok"]
        if lower.startswith("gemini") and "gemini" in self.providers:
            return self.providers["gemini"]
        if lower.startswith("deepseek") and "deepseek" in self.providers:
            return self.providers["deepseek"]
        if lower.startswith("manus") and "manus" in self.providers:
            return self.providers["manus"]
        return self.providers.get("stub", StubProvider())

    async def _gather_with_handling(self, coroutines: Sequence[asyncio.Future]) -> list[LLMResult]:
        results: list[LLMResult] = []
        for coro in asyncio.as_completed(coroutines):
            try:
                result = await coro
                results.append(result)
            except ProviderNotConfiguredError as exc:
                logger.warning("Provider misconfiguration during call: %s", exc)
            except Exception as exc:
                logger.exception("Provider call failed", exc_info=exc)
        return results

    async def orchestrate(
        self,
        prompt: str,
        models: Iterable[str] | None = None,
        *,
        context: str | None = None,
        knowledge_snippets: Sequence[str] | None = None,
    ) -> OrchestrationArtifacts:
        knowledge_snippets = list(knowledge_snippets or [])
        plan_prompt = optimize_prompt(prompt, knowledge_snippets)
        plan = self.planner.create_plan(plan_prompt, context=context)
        used_stub_provider = False
        if models:
            model_list = list(dict.fromkeys(models))
        else:
            required_roles = [step.role.value for step in plan.steps if step.role != PlanRole.SYNTHESIZE]
            required_capabilities = [list(step.required_capabilities or {"reasoning"}) for step in plan.steps if step.role != PlanRole.SYNTHESIZE]
            suggested = self.model_registry.suggest_team(required_roles, required_capabilities)
            if not suggested:
                suggested = list(settings.default_models)
            model_list = list(dict.fromkeys(suggested + plan.model_hints()))

        if not model_list:
            raise ValueError("At least one model must be provided")

        logger.info("Starting orchestration for models: %s", model_list)

        context_prompt = context
        augmented_prompt = plan_prompt
        if context:
            augmented_prompt = (
                "Context from memory:\n"
                f"{context}\n\n"
                f"Optimized request:\n{plan_prompt}"
            )

        step_outputs: Dict[str, list[LLMResult]] = {}
        supporting_notes: list[str] = list(knowledge_snippets)

        web_documents: list[WebDocument] = []
        if getattr(settings, "enable_live_research", True):
            try:
                web_documents = await self.web_research.search(prompt)
            except Exception as exc:  # pragma: no cover - defensive
                logger.warning("Web research client raised %s", exc)
                web_documents = []
        if web_documents:
            for doc in web_documents:
                snippet = doc.snippet or doc.title
                if snippet:
                    supporting_notes.append(f"Web: {doc.title or 'result'} — {self._truncate(snippet, 220)}")

            # Incorporate web search context into augmented_prompt for initial answers
            web_lines = ["Context from web search:"]
            for doc in web_documents[:3]:
                snippet = doc.snippet or doc.title
                if snippet:
                    web_lines.append(f"- {doc.title or 'result'}: {self._truncate(snippet, 220)}")
            web_block = "\n".join(web_lines)
            if context_prompt:
                augmented_prompt = (
                    f"Context from memory:\n{context_prompt}\n\n"
                    f"{web_block}\n\n"
                    f"Optimized request:\n{plan_prompt}"
                )
            else:
                augmented_prompt = f"{web_block}\n\nOptimized request:\n{plan_prompt}"
        # Execute the structured plan (excluding critique/synthesis which are handled separately)
        for step in plan.steps:
            if step.role in (PlanRole.CRITIQUE, PlanRole.SYNTHESIZE):
                continue
            step_models = self._models_for_step(step, model_list)
            if not step_models:
                continue
            step_prompt = self._build_step_prompt(
                step=step,
                base_prompt=prompt,
                augmented_prompt=augmented_prompt,
                context=context,
                step_outputs=step_outputs,
            )
            logger.debug("Executing plan step %s with models %s", step.role.value, step_models)
            completion_tasks = []
            for model in step_models:
                provider = self._select_provider(model)
                if isinstance(provider, StubProvider) and not model.lower().startswith("stub"):
                    used_stub_provider = True
                completion_tasks.append(provider.complete(step_prompt, model=model))
            results = await self._gather_with_handling(completion_tasks)
            if results:
                step_outputs[step.role.value] = results
                if step.role in {PlanRole.RESEARCH, PlanRole.RETRIEVAL, PlanRole.FACT_CHECK}:
                    supporting_notes.extend(self._collect_supporting_notes(results))

        initial_responses = list(step_outputs.get(PlanRole.DRAFT.value, []))
        if not initial_responses:
            # Fall back to whichever step produced results to maintain downstream flow
            fallback_results: list[LLMResult] = []
            for outputs in step_outputs.values():
                fallback_results.extend(outputs)
                if len(fallback_results) >= len(model_list):
                    break
            if not fallback_results:
                # As an ultimate fallback, generate direct completions
                completion_tasks = []
                for model in model_list:
                    provider = self._select_provider(model)
                    if isinstance(provider, StubProvider) and not model.lower().startswith("stub"):
                        used_stub_provider = True
                    completion_tasks.append(provider.complete(augmented_prompt, model=model))
                fallback_results = await self._gather_with_handling(completion_tasks)
                step_outputs.setdefault(PlanRole.DRAFT.value, fallback_results)
            initial_responses = fallback_results[: len(model_list)]

        quality_assessments: Dict[str, ResponseAssessment] = {}
        quality_highlights: list[str] = []
        if initial_responses:
            assessments = self._analyze_response_quality(initial_responses)
            selected, quality_assessments = self._select_top_responses(
                assessments,
                limit=len(model_list),
                min_score=getattr(settings, "minimum_quality_score", 0.3),
            )
            if selected:
                initial_responses = selected
            quality_highlights = self._quality_highlights(quality_assessments)

        critique_subject = self._build_critique_subject(
            prompt=prompt,
            context=context,
            supporting_notes=supporting_notes,
            step_outputs=step_outputs,
            quality_highlights=quality_highlights,
        )
        critiques, critiques_by_model = await self._run_cross_critiques(
            initial_responses,
            subject=critique_subject,
            supporting_notes=supporting_notes,
            step_outputs=step_outputs,
        )
        if critiques:
            step_outputs.setdefault(PlanRole.CRITIQUE.value, [crit for _, _, crit in critiques])

        improvement_subject = self._build_improvement_subject(
            prompt=prompt,
            context=context,
            supporting_notes=supporting_notes,
            critiques_by_model=critiques_by_model,
            step_outputs=step_outputs,
            quality_assessments=quality_assessments,
        )
        improvement_tasks = []
        for response in initial_responses:
            provider = self._select_provider(response.model)
            if isinstance(provider, StubProvider) and not response.model.lower().startswith("stub"):
                used_stub_provider = True
            improvement_tasks.append(
                asyncio.create_task(
                    provider.improve(
                        improvement_subject,
                        previous_answer=response.content,
                        critiques=critiques_by_model.get(response.model, []),
                        model=response.model,
                    )
                )
            )
        improvements = await self._gather_with_handling(improvement_tasks)
        if improvements:
            step_outputs["improvement"] = improvements

        consensus_notes = self._derive_consensus(
            improvements or initial_responses,
            supporting_notes=supporting_notes,
            quality_insights=quality_highlights,
        )
        synthesis_prompt = self._build_synthesis_prompt(
            prompt,
            improvements,
            initial_responses,
            plan,
            context,
            consensus_notes,
            step_outputs=step_outputs,
            supporting_notes=supporting_notes,
            quality_assessments=quality_assessments,
        )
        synthesizer_model = model_list[0]
        synthesizer = self._select_provider(synthesizer_model)
        if isinstance(synthesizer, StubProvider) and not synthesizer_model.lower().startswith("stub"):
            used_stub_provider = True
        try:
            final_response = await synthesizer.complete(
                synthesis_prompt, model=synthesizer_model
            )
        except ProviderNotConfiguredError as exc:
            logger.warning(
                "Primary synthesis provider '%s' unavailable (%s); falling back to stub.",
                synthesizer_model,
                exc,
            )
            fallback_provider = self.providers.get("stub") or StubProvider()
            self.providers.setdefault("stub", fallback_provider)
            used_stub_provider = True
            final_response = await fallback_provider.complete(
                synthesis_prompt, model=f"stub-fallback({synthesizer_model})"
            )
        except Exception as exc:  # pragma: no cover - defensive fallback
            logger.exception(
                "Unexpected synthesis failure with model '%s'; using stub fallback.",
                synthesizer_model,
                exc_info=exc,
            )
            fallback_provider = self.providers.get("stub") or StubProvider()
            self.providers.setdefault("stub", fallback_provider)
            used_stub_provider = True
            final_response = await fallback_provider.complete(
                synthesis_prompt, model=f"stub-fallback({synthesizer_model})"
            )

        guardrail_report = self.guardrails.inspect(final_response.content)
        if guardrail_report.sanitized_content != final_response.content:
            final_response = LLMResult(
                content=guardrail_report.sanitized_content,
                model=final_response.model,
                tokens=final_response.tokens,
                cost=final_response.cost,
            )

        evaluation: LLMResult | None = None
        try:
            evaluation_prompt = self._build_evaluation_prompt(
                prompt=prompt,
                final_answer=final_response.content,
                plan=plan,
                consensus_notes=consensus_notes,
                guardrail_report=guardrail_report,
                supporting_notes=supporting_notes,
                quality_assessments=quality_assessments,
            )
            evaluator_model = model_list[1] if len(model_list) > 1 else model_list[0]
            evaluator = self._select_provider(evaluator_model)
            if isinstance(evaluator, StubProvider) and not evaluator_model.lower().startswith("stub"):
                used_stub_provider = True
            evaluation = await evaluator.complete(evaluation_prompt, model=evaluator_model)
        except Exception as exc:  # pragma: no cover - evaluation is best effort
            logger.warning("Evaluation stage failed: %s", exc)

        confirmation_notes = []

        usage_summary = self._summarize_usage(
            initial_responses,
            improvements,
            [crit for _, _, crit in critiques],
            [final_response],
            [evaluation] if evaluation else [],
            [result for outputs in step_outputs.values() for result in outputs],
        )

        return OrchestrationArtifacts(
            plan=plan,
            context_prompt=context_prompt,
            optimized_prompt=plan_prompt,
            initial_responses=initial_responses,
            critiques=critiques,
            improvements=improvements,
            consensus_notes=consensus_notes,
            final_response=final_response,
            guardrail_report=guardrail_report,
            step_outputs=step_outputs,
            supporting_notes=supporting_notes,
            quality_assessments=quality_assessments,
            evaluation=evaluation,
            knowledge_snippets=knowledge_snippets,
            web_results=web_documents,
            confirmation_notes=confirmation_notes,
            usage=usage_summary,
            used_stub_provider=used_stub_provider,
        )

    def _summarize_usage(
        self,
        *collections: Sequence[LLMResult],
    ) -> UsageSummary:
        """Aggregate token and cost usage across result collections."""

        seen: set[int] = set()
        per_model: Dict[str, ModelUsage] = {}
        total_tokens = 0
        total_cost = 0.0
        response_count = 0

        for collection in collections:
            for result in collection:
                if result is None:
                    continue
                identity = id(result)
                if identity in seen:
                    continue
                seen.add(identity)
                response_count += 1

                tokens = int(result.tokens or 0)
                cost = float(result.cost or 0.0)
                total_tokens += tokens
                total_cost += cost

                usage = per_model.get(result.model)
                if usage is None:
                    usage = ModelUsage()
                    per_model[result.model] = usage
                usage.tokens += tokens
                usage.cost += cost
                usage.responses += 1

        total_cost = round(total_cost, 6)
        for usage in per_model.values():
            usage.cost = round(usage.cost, 6)

        return UsageSummary(
            total_tokens=total_tokens,
            total_cost=total_cost,
            response_count=response_count,
            per_model=per_model,
        )

    def _models_for_step(self, step: PlanStep, available_models: Sequence[str]) -> list[str]:
        """Return models that should be used for a given plan step."""

        if not available_models:
            return []

        if not step.candidate_models:
            return list(available_models)

        matched: list[str] = []
        lowered_available = {model.lower(): model for model in available_models}
        for candidate in step.candidate_models:
            candidate_lower = candidate.lower()
            if candidate_lower in lowered_available:
                matched.append(lowered_available[candidate_lower])
                continue
            for model in available_models:
                if model.lower().startswith(candidate_lower.split("-", 1)[0]):
                    matched.append(model)
        if not matched:
            return list(available_models)
        ordered: list[str] = []
        seen: set[str] = set()
        for model in matched:
            if model not in seen and model in available_models:
                ordered.append(model)
                seen.add(model)
        for model in available_models:
            if model not in seen:
                ordered.append(model)
        return ordered

    def _collect_supporting_notes(
        self, results: Sequence[LLMResult], *, limit: int = 6
    ) -> list[str]:
        notes: list[str] = []
        for result in results:
            snippet = self._truncate(result.content, 220)
            if snippet:
                notes.append(f"{result.model}: {snippet}")
            if len(notes) >= limit:
                break
        return notes

    def _build_step_prompt(
        self,
        *,
        step: PlanStep,
        base_prompt: str,
        augmented_prompt: str,
        context: str | None,
        step_outputs: Dict[str, Sequence[LLMResult]],
    ) -> str:
        parts: list[str] = []
        parts.append(
            f"You are the {step.role.value} specialist within the LLMHive multi-agent team."
        )
        parts.append(step.description)
        guidance = self._role_guidance(step.role)
        if guidance:
            parts.append(guidance)
        if context:
            parts.append("")
            parts.append("Long-term conversation context:")
            parts.append(context)
        if step_outputs:
            parts.append("")
            parts.append("Key insights from prior steps:")
            for role, outputs in step_outputs.items():
                if role == step.role.value or not outputs:
                    continue
                summary = self._summaries_from_outputs(outputs)
                if summary:
                    parts.append(f"- {role}: {summary}")
        parts.append("")
        parts.append("User request:")
        parts.append(base_prompt)
        parts.append("")
        parts.append(
            "Respond with structured, actionable content so downstream agents can build on it."
        )
        parts.append("---")
        parts.append("Context for reference:")
        parts.append(augmented_prompt)
        return "\n".join(parts)

    def _role_guidance(self, role: PlanRole) -> str:
        mapping = {
            PlanRole.DRAFT: (
                "Provide a complete first-pass solution with reasoning, assumptions, and explicit TODOs for gaps."
            ),
            PlanRole.RESEARCH: (
                "Surface relevant evidence, data points, and references in bullet form with inline citations."
            ),
            PlanRole.FACT_CHECK: (
                "Validate the latest proposals, flag inaccuracies, and suggest precise corrections or sources."
            ),
            PlanRole.CRITIQUE: (
                "Highlight weaknesses, contradictions, and missing coverage with actionable suggestions."
            ),
            PlanRole.RETRIEVAL: (
                "Retrieve authoritative snippets or references that ground the response in verifiable sources."
            ),
        }
        return mapping.get(role, "")

    def _summaries_from_outputs(
        self, outputs: Sequence[LLMResult], *, limit: int = 2
    ) -> str:
        snippets: list[str] = []
        for result in outputs[:limit]:
            snippet = self._truncate(result.content, 180)
            if snippet:
                snippets.append(f"{result.model}: {snippet}")
        return "; ".join(snippets)

    async def _run_cross_critiques(
        self,
        initial_responses: Sequence[LLMResult],
        *,
        subject: str,
        supporting_notes: Sequence[str],
        step_outputs: Dict[str, Sequence[LLMResult]],
    ) -> Tuple[list[Tuple[str, str, LLMResult]], Dict[str, list[str]]]:
        critique_tasks: list[Tuple[str, str, asyncio.Task[LLMResult]]] = []
        for author_result in initial_responses:
            for target_result in initial_responses:
                provider = self._select_provider(author_result.model)
                task = asyncio.create_task(
                    provider.critique(
                        subject,
                        target_answer=self._build_target_payload(
                            target_result, supporting_notes, step_outputs
                        ),
                        author=author_result.model,
                        model=author_result.model,
                    )
                )
                critique_tasks.append((author_result.model, target_result.model, task))

        critiques: list[Tuple[str, str, LLMResult]] = []
        critiques_by_model: Dict[str, list[str]] = defaultdict(list)
        for author, target, task in critique_tasks:
            try:
                result = await task
                critiques.append((author, target, result))
                critiques_by_model[target].append(result.content)
            except ProviderNotConfiguredError as exc:
                logger.warning("Provider misconfiguration during critique: %s", exc)
            except Exception as exc:  # pragma: no cover - defensive logging
                logger.exception("Critique call failed", exc_info=exc)
        return critiques, critiques_by_model

    def _build_critique_subject(
        self,
        *,
        prompt: str,
        context: str | None,
        supporting_notes: Sequence[str],
        step_outputs: Dict[str, Sequence[LLMResult]],
        quality_highlights: Sequence[str] | None = None,
    ) -> str:
        parts = [
            "You are reviewing peer answers within the LLMHive orchestration pipeline.",
            "Provide precise critiques focusing on factual accuracy, logical coherence, and completeness.",
        ]
        if context:
            parts.append("Conversation context summary:")
            parts.append(context)
        if supporting_notes:
            parts.append("Reference knowledge to consider:")
            for note in supporting_notes[:5]:
                parts.append(f"- {note}")
        if step_outputs.get(PlanRole.RESEARCH.value):
            parts.append("Research agents supplied the following leads:")
            parts.append(
                self._summaries_from_outputs(step_outputs[PlanRole.RESEARCH.value])
            )
        if quality_highlights:
            parts.append("Quality observations about peer drafts:")
            for highlight in list(quality_highlights)[:4]:
                parts.append(f"- {highlight}")
        parts.append("Original task:")
        parts.append(prompt)
        parts.append(
            "When critiquing, cite the specific claim you are addressing and suggest concrete fixes."
        )
        return "\n".join(parts)

    def _build_target_payload(
        self,
        target_result: LLMResult,
        supporting_notes: Sequence[str],
        step_outputs: Dict[str, Sequence[LLMResult]],
    ) -> str:
        supplemental: list[str] = []
        if supporting_notes:
            supplemental.append("Shared notes:")
            supplemental.extend(f"- {note}" for note in supporting_notes[:4])
        fact_checks = step_outputs.get(PlanRole.FACT_CHECK.value, [])
        if fact_checks:
            supplemental.append("Fact-check findings:")
            supplemental.append(self._summaries_from_outputs(fact_checks))
        if not supplemental:
            return target_result.content
        return f"{target_result.content}\n\nSupplemental context for critique:\n" + "\n".join(supplemental)

    def _build_improvement_subject(
        self,
        *,
        prompt: str,
        context: str | None,
        supporting_notes: Sequence[str],
        critiques_by_model: Dict[str, list[str]],
        step_outputs: Dict[str, Sequence[LLMResult]],
        quality_assessments: Dict[str, ResponseAssessment],
    ) -> str:
        parts = [
            "Improve the draft answers leveraging critiques and supporting evidence.",
            "Address each critique explicitly, incorporate validated facts, and ensure coherence.",
        ]
        if context:
            parts.append("Conversation context summary:")
            parts.append(context)
        if supporting_notes:
            parts.append("Evidence and research leads:")
            for note in supporting_notes[:6]:
                parts.append(f"- {note}")
        if quality_assessments:
            parts.append("Quality review of existing drafts:")
            for assessment in list(quality_assessments.values())[:4]:
                summary = "; ".join(assessment.highlights) or "Strong structure"
                parts.append(
                    f"- {assessment.result.model}: score={assessment.score:.2f}. {summary}"
                )
        if step_outputs.get(PlanRole.FACT_CHECK.value):
            parts.append("Fact-check insights to respect:")
            parts.append(
                self._summaries_from_outputs(step_outputs[PlanRole.FACT_CHECK.value])
            )
        if any(critiques_by_model.values()):
            parts.append("Critique themes detected across reviewers:")
            for model_name, feedbacks in critiques_by_model.items():
                if not feedbacks:
                    continue
                sample = self._truncate(" ".join(feedbacks), 200)
                parts.append(f"- {model_name}: {sample}")
        parts.append("Original task:")
        parts.append(prompt)
        parts.append(
            "Return a refined answer that references sources when available and notes any remaining uncertainties."
        )
        return "\n".join(parts)

    def _derive_consensus(
        self,
        responses: Sequence[LLMResult],
        *,
        supporting_notes: Sequence[str],
        quality_insights: Sequence[str] | None = None,
        limit: int = 8,
    ) -> list[str]:
        consensus: list[str] = []
        seen: set[str] = set()
        for response in responses:
            sentences = [
                segment.strip()
                for segment in response.content.replace("\n", " ").split(".")
                if segment.strip()
            ]
            for sentence in sentences[:3]:
                key = sentence.lower()
                if key in seen:
                    continue
                seen.add(key)
                consensus.append(f"{response.model}: {sentence}.")
                if len(consensus) >= limit:
                    return consensus
        for note in supporting_notes:
            if len(consensus) >= limit:
                break
            lowered = note.lower()
            if lowered in seen:
                continue
            seen.add(lowered)
            consensus.append(f"Evidence: {note}")
        if quality_insights:
            for highlight in quality_insights:
                if len(consensus) >= limit:
                    break
                lowered = highlight.lower()
                if lowered in seen:
                    continue
                seen.add(lowered)
                consensus.append(f"Quality-signal: {highlight}")
        return consensus

    def _build_synthesis_prompt(
        self,
        prompt: str,
        improvements: Sequence[LLMResult],
        initial_responses: Sequence[LLMResult],
        plan: ReasoningPlan,
        context: str | None,
        consensus_notes: Sequence[str],
        *,
        step_outputs: Dict[str, Sequence[LLMResult]],
        supporting_notes: Sequence[str],
        quality_assessments: Dict[str, ResponseAssessment],
    ) -> str:
        parts: list[str] = []
        parts.append("You are synthesizing answers from a collaborative team of AI experts.")
        parts.append(
            "Combine the best ideas, resolve disagreements, and present a cohesive final response."
        )
        parts.append("")
        parts.append("Original user prompt:")
        parts.append(prompt)
        parts.append("")
        if context:
            parts.append("Relevant context from long-term memory:")
            parts.append(context)
            parts.append("")
        if supporting_notes:
            parts.append("Research highlights and verified facts:")
            for note in supporting_notes[:6]:
                parts.append(f"- {note}")
            parts.append("")
        parts.append("Reasoning strategy: ")
        parts.append(plan.strategy)
        if plan.focus_areas:
            parts.append("Focus areas: " + ", ".join(plan.focus_areas))
        parts.append("")
        parts.append("Planned steps and outputs:")
        for step in plan.steps:
            parts.append(f"- {step.role.value}: {step.description}")
            outputs = step_outputs.get(step.role.value)
            if outputs:
                for result in outputs[:2]:
                    parts.append(
                        f"    • {result.model}: {self._truncate(result.content, 220)}"
                    )
        if improvements:
            parts.append("")
            parts.append("Improved answers ready for synthesis:")
            for imp in improvements:
                parts.append(f"- {imp.model}: {self._truncate(imp.content, 260)}")
        else:
            parts.append("")
            parts.append("Initial answers to reconcile:")
            for ans in initial_responses:
                parts.append(f"- {ans.model}: {self._truncate(ans.content, 220)}")
        if quality_assessments:
            parts.append("")
            parts.append("Quality scoring from DeepConf-style filtering:")
            for assessment in list(quality_assessments.values())[:5]:
                highlight = "; ".join(assessment.highlights) or "Comprehensive coverage"
                flag_text = f" Flags: {', '.join(assessment.flags)}" if assessment.flags else ""
                parts.append(
                    f"- {assessment.result.model}: {assessment.score:.2f} – {highlight}{flag_text}"
                )
        if consensus_notes:
            parts.append("")
            parts.append("Consensus signals from the hive team:")
            for note in consensus_notes:
                parts.append(f"- {note}")
        parts.append("")
        parts.append(
            "Produce a single, polished answer. Reference evidence when available and note any residual uncertainties."
        )
        return "\n".join(parts)

    def _confirmation_checks(
        self,
        *,
        prompt: str,
        final_answer: str,
        knowledge_snippets: Sequence[str],
        web_documents: Sequence[WebDocument],
    ) -> list[str]:
        notes: list[str] = []
        answer = final_answer.strip()
        if not answer:
            return ["Final response is empty; retry orchestration."]

        normalized = answer.lower()
        keywords = re.findall(r"[a-z]{5,}", prompt.lower())
        missing = [word for word in keywords[:5] if word not in normalized]
        if missing:
            notes.append(
                "Potentially missing prompt keywords: " + ", ".join(dict.fromkeys(missing))
            )

        if knowledge_snippets:
            tag_hits = sum(
                1
                for idx in range(1, len(knowledge_snippets) + 1)
                if f"[memory {idx}]" in normalized
            )
            if tag_hits == 0:
                notes.append(
                    "Final response does not explicitly reference retrieved memory snippets."
                )

        if web_documents:
            referenced = any(
                doc.url and doc.url.lower() in normalized for doc in web_documents if doc.url
            )
            if not referenced:
                notes.append("Consider citing at least one live research source for traceability.")

        if not notes:
            notes.append(
                "Confirmation checks passed: prompt coverage and grounding look healthy."
            )
        return notes

    def _build_evaluation_prompt(
        self,
        *,
        prompt: str,
        final_answer: str,
        plan: ReasoningPlan,
        consensus_notes: Sequence[str],
        guardrail_report: GuardrailReport | None,
        supporting_notes: Sequence[str],
        quality_assessments: Dict[str, ResponseAssessment],
    ) -> str:
        parts = [
            "Act as a quality assurance reviewer for the final orchestrated answer.",
            "Assess factual accuracy, completeness, tone, and alignment with the plan steps.",
        ]
        parts.append("Original task:")
        parts.append(prompt)
        if supporting_notes:
            parts.append("Key evidence considered:")
            for note in supporting_notes[:4]:
                parts.append(f"- {note}")
        if consensus_notes:
            parts.append("Consensus checkpoints:")
            for note in consensus_notes[:4]:
                parts.append(f"- {note}")
        if guardrail_report and guardrail_report.issues:
            parts.append("Guardrail issues detected:")
            for issue in guardrail_report.issues:
                parts.append(f"- {issue}")
        if quality_assessments:
            parts.append("Model quality assessments considered during synthesis:")
            for assessment in list(quality_assessments.values())[:4]:
                summary = "; ".join(assessment.highlights) or "Well structured"
                parts.append(
                    f"- {assessment.result.model}: score {assessment.score:.2f} ({summary})"
                )
        parts.append("Planned approach summary:")
        parts.append(plan.strategy)
        parts.append("Final answer to evaluate:")
        parts.append(final_answer)
        parts.append(
            "Respond with a concise evaluation summarizing strengths, risks, and any follow-up actions required."
        )
        return "\n".join(parts)

    def _analyze_response_quality(
        self, responses: Sequence[LLMResult]
    ) -> list[ResponseAssessment]:
        assessments: list[ResponseAssessment] = []
        for result in responses:
            text = result.content.strip()
            score = 0.0
            flags: list[str] = []
            highlights: list[str] = []

            length = len(text)
            if length > 1200:
                score += 0.45
                highlights.append("Extensive coverage")
            elif length > 600:
                score += 0.35
                highlights.append("Thorough response")
            elif length > 300:
                score += 0.25
            elif length < 120:
                score -= 0.2
                flags.append("Very short")

            if any(token in text.lower() for token in ("i am unsure", "cannot", "not sure")):
                score -= 0.25
                flags.append("Low confidence language")

            if "as an ai language model" in text.lower():
                score -= 0.3
                flags.append("Meta disclaimer")

            if "TODO" in text or "TBD" in text:
                score -= 0.15
                flags.append("Unresolved TODOs")

            if "http" in text or "[" in text and "]" in text:
                score += 0.1
                highlights.append("Includes references")

            if any(symbol in text for symbol in ("- ", "•", "1.", "2.")):
                score += 0.05
                highlights.append("Structured formatting")

            if "analysis" in text.lower() or "reason" in text.lower():
                score += 0.05

            if "hallucination" in text.lower():
                flags.append("Mentions hallucination handling")

            final_score = max(min(score, 1.2), -0.5)
            assessments.append(
                ResponseAssessment(
                    result=result,
                    score=final_score,
                    flags=flags,
                    highlights=highlights,
                )
            )

        assessments.sort(key=lambda assessment: assessment.score, reverse=True)
        return assessments

    def _select_top_responses(
        self,
        assessments: Sequence[ResponseAssessment],
        *,
        limit: int,
        min_score: float,
    ) -> Tuple[list[LLMResult], Dict[str, ResponseAssessment]]:
        selected: list[LLMResult] = []
        mapping: Dict[str, ResponseAssessment] = {}
        for assessment in assessments:
            if len(selected) >= limit:
                break
            if assessment.score < min_score and selected:
                continue
            if assessment.result.model in mapping:
                continue
            selected.append(assessment.result)
            mapping[assessment.result.model] = assessment

        if len(selected) < limit:
            for assessment in assessments:
                if assessment.result.model in mapping:
                    continue
                selected.append(assessment.result)
                mapping[assessment.result.model] = assessment
                if len(selected) >= limit:
                    break

        return selected, mapping

    def _quality_highlights(
        self, assessments: Dict[str, ResponseAssessment]
    ) -> list[str]:
        ordered = sorted(
            assessments.values(), key=lambda assessment: assessment.score, reverse=True
        )
        notes: list[str] = []
        for assessment in ordered:
            summary = "; ".join(assessment.highlights) or "Solid structure"
            flag_summary = f" (flags: {', '.join(assessment.flags)})" if assessment.flags else ""
            notes.append(f"{assessment.result.model} scored {assessment.score:.2f}: {summary}{flag_summary}")
        return notes

    def _truncate(self, text: str, limit: int = 200) -> str:
        cleaned = text.strip()
        if len(cleaned) <= limit:
            return cleaned
        return cleaned[: limit - 3].rstrip() + "..."