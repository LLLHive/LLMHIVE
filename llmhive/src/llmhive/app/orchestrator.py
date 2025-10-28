"""Core orchestration workflow for coordinating multiple LLMs."""
from __future__ import annotations

import asyncio
import logging
import os
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, Iterable, List, Sequence, Tuple

from .config import settings
from .guardrails import GuardrailReport, SafetyValidator
from .model_registry import ModelRegistry
from .planner import PlanRole, PlanStep, ReasoningPlanner, ReasoningPlan
from .services.base import LLMProvider, LLMResult, ProviderNotConfiguredError
from .services.openai_provider import OpenAIProvider
from .services.stub_provider import StubProvider

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
    from .services.gemini_provider import GeminiProvider
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
class OrchestrationArtifacts:
    """Artifacts produced by the orchestrator stages."""

    plan: ReasoningPlan
    context_prompt: str | None
    initial_responses: list[LLMResult]
    critiques: list[Tuple[str, str, LLMResult]]  # (author, target, result)
    improvements: list[LLMResult]
    consensus_notes: list[str]
    final_response: LLMResult
    guardrail_report: GuardrailReport | None
    step_outputs: Dict[str, list[LLMResult]]
    supporting_notes: list[str]
    evaluation: LLMResult | None


class Orchestrator:
    """Coordinates the multi-stage collaboration workflow across models."""

    def __init__(self, providers: Dict[str, LLMProvider] | None = None) -> None:
        if providers is None:
            providers = self._default_providers()
        self.providers = providers
        self.model_registry = ModelRegistry(self.providers)
        self.planner = ReasoningPlanner()
        self.guardrails = SafetyValidator()
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
    ) -> OrchestrationArtifacts:
        plan = self.planner.create_plan(prompt, context=context)
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
        augmented_prompt = prompt
        if context:
            augmented_prompt = f"Context from memory:\n{context}\n\nUser request:\n{prompt}"

        step_outputs: Dict[str, list[LLMResult]] = {}
        supporting_notes: list[str] = []

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
            completion_tasks = [
                self._select_provider(model).complete(step_prompt, model=model)
                for model in step_models
            ]
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
                completion_tasks = [
                    self._select_provider(model).complete(augmented_prompt, model=model)
                    for model in model_list
                ]
                fallback_results = await self._gather_with_handling(completion_tasks)
                step_outputs.setdefault(PlanRole.DRAFT.value, fallback_results)
            initial_responses = fallback_results[: len(model_list)]

        critique_subject = self._build_critique_subject(
            prompt=prompt,
            context=context,
            supporting_notes=supporting_notes,
            step_outputs=step_outputs,
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
        )
        improvement_tasks = []
        for response in initial_responses:
            provider = self._select_provider(response.model)
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
        )
        synthesizer = self._select_provider(model_list[0])
        final_response = await synthesizer.complete(synthesis_prompt, model=model_list[0])

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
            )
            evaluator_model = model_list[1] if len(model_list) > 1 else model_list[0]
            evaluator = self._select_provider(evaluator_model)
            evaluation = await evaluator.complete(evaluation_prompt, model=evaluator_model)
        except Exception as exc:  # pragma: no cover - evaluation is best effort
            logger.warning("Evaluation stage failed: %s", exc)

        return OrchestrationArtifacts(
            plan=plan,
            context_prompt=context_prompt,
            initial_responses=initial_responses,
            critiques=critiques,
            improvements=improvements,
            consensus_notes=consensus_notes,
            final_response=final_response,
            guardrail_report=guardrail_report,
            step_outputs=step_outputs,
            supporting_notes=supporting_notes,
            evaluation=evaluation,
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
                if author_result.model == target_result.model:
                    continue
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

    def _build_evaluation_prompt(
        self,
        *,
        prompt: str,
        final_answer: str,
        plan: ReasoningPlan,
        consensus_notes: Sequence[str],
        guardrail_report: GuardrailReport | None,
        supporting_notes: Sequence[str],
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
        parts.append("Planned approach summary:")
        parts.append(plan.strategy)
        parts.append("Final answer to evaluate:")
        parts.append(final_answer)
        parts.append(
            "Respond with a concise evaluation summarizing strengths, risks, and any follow-up actions required."
        )
        return "\n".join(parts)

    def _truncate(self, text: str, limit: int = 200) -> str:
        cleaned = text.strip()
        if len(cleaned) <= limit:
            return cleaned
        return cleaned[: limit - 3].rstrip() + "..."
