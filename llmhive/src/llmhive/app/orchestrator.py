"""Core orchestration workflow for coordinating multiple LLMs."""
from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, Iterable, List, Mapping, Sequence, Tuple

from .config import settings
from .services.base import LLMProvider, LLMResult, ProviderNotConfiguredError
from .services.grok_provider import GrokProvider
from .services.openai_provider import OpenAIProvider
from .services.stub_provider import StubProvider

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class OrchestrationArtifacts:
    """Artifacts produced by the orchestrator stages."""

    initial_responses: list[LLMResult]
    critiques: list[Tuple[str, str, LLMResult]]  # (author, target, result)
    improvements: list[LLMResult]
    final_response: LLMResult


class Orchestrator:
    """Coordinates the multi-stage collaboration workflow across models."""

    def __init__(
        self,
        providers: Dict[str, LLMProvider] | None = None,
        *,
        model_aliases: Mapping[str, str] | None = None,
    ) -> None:
        self.provider_errors: Dict[str, str] = {}
        self.model_aliases: Dict[str, str] = {
            key.lower(): value for key, value in (model_aliases or settings.model_aliases).items()
        }
        if providers is None:
            providers = self._default_providers()
        self.providers = providers

    def _default_providers(self) -> Dict[str, LLMProvider]:
        mapping: Dict[str, LLMProvider] = {}
        self.provider_errors.clear()
        try:
            mapping["openai"] = OpenAIProvider()
        except ProviderNotConfiguredError as exc:
            error_message = str(exc)
            self.provider_errors["openai"] = error_message
            logger.info("OpenAI provider not configured; falling back to stub provider: %s", error_message)
        try:
            mapping["grok"] = GrokProvider()
        except ProviderNotConfiguredError as exc:
            error_message = str(exc)
            self.provider_errors["grok"] = error_message
            logger.info("Grok provider not configured; continuing without Grok: %s", error_message)
        if "openai" not in mapping:
            mapping["stub"] = StubProvider()
        else:
            mapping.setdefault("stub", StubProvider())
        return mapping

    def _resolve_model(self, model: str) -> tuple[str, str]:
        requested = model.strip()
        canonical = self.model_aliases.get(requested.lower(), requested)
        return requested, canonical

    def _select_provider(self, canonical_model: str) -> LLMProvider:
        key = canonical_model.lower()
        if key.startswith("gpt") and "openai" in self.providers:
            return self.providers["openai"]
        if "grok" in key and "grok" in self.providers:
            return self.providers["grok"]
        return self.providers.get("stub", StubProvider())

    def provider_status(self) -> Dict[str, Dict[str, str]]:
        """Expose provider availability details for diagnostics."""

        status: Dict[str, Dict[str, str]] = {}
        for name, provider in self.providers.items():
            status[name] = {
                "status": "available",
                "provider": provider.__class__.__name__,
            }
        for name, message in self.provider_errors.items():
            status.setdefault(name, {"provider": None})
            status[name].update({"status": "unavailable", "error": message})
        return status

    async def _gather_with_handling(self, coroutines: Sequence[asyncio.Future]) -> list[LLMResult]:
        results: list[LLMResult] = []
        for coro in asyncio.as_completed(coroutines):
            try:
                result = await coro
                results.append(result)
            except ProviderNotConfiguredError as exc:
                logger.warning("Provider misconfiguration: %s", exc)
            except Exception as exc:  # pragma: no cover - defensive catch
                logger.exception("Provider call failed", exc_info=exc)
        return results

    async def orchestrate(self, prompt: str, models: Iterable[str] | None = None) -> OrchestrationArtifacts:
        """Run the multi-stage orchestration for the provided prompt."""

        model_list = list(models or settings.default_models)
        if not model_list:
            raise ValueError("At least one model must be provided")

        logger.info("Starting orchestration for %s", model_list)

        # Independent responses
        resolved_models = [self._resolve_model(model) for model in model_list]

        completion_tasks = [
            self._select_provider(canonical).complete(prompt, model=canonical)
            for _, canonical in resolved_models
        ]
        initial_responses = await self._gather_with_handling(completion_tasks)

        for result, (requested, _) in zip(initial_responses, resolved_models):
            result.model = requested

        # Cross critiques
        critique_tasks: list[asyncio.Task[LLMResult]] = []
        for author_result in initial_responses:
            for target_result in initial_responses:
                if author_result.model == target_result.model:
                    continue
                _, canonical_author = self._resolve_model(author_result.model)
                provider = self._select_provider(canonical_author)
                critique_tasks.append(
                    asyncio.create_task(
                        provider.critique(
                            prompt,
                            target_answer=target_result.content,
                            author=author_result.model,
                            model=canonical_author,
                        )
                    )
                )
        critique_results = await self._gather_with_handling(critique_tasks)
        critiques: list[Tuple[str, str, LLMResult]] = []
        index = 0
        for author_result in initial_responses:
            for target_result in initial_responses:
                if author_result.model == target_result.model:
                    continue
                if index < len(critique_results):
                    critiques.append((author_result.model, target_result.model, critique_results[index]))
                index += 1

        critiques_by_model: Dict[str, list[str]] = defaultdict(list)
        for author, target, critique in critiques:
            critiques_by_model[target].append(critique.content)

        # Improvement stage
        improvement_tasks = []
        for response in initial_responses:
            _, canonical_model = self._resolve_model(response.model)
            provider = self._select_provider(canonical_model)
            improvement_tasks.append(
                asyncio.create_task(
                    provider.improve(
                        prompt,
                        previous_answer=response.content,
                        critiques=critiques_by_model.get(response.model, []),
                        model=canonical_model,
                    )
                )
            )
        improvements = await self._gather_with_handling(improvement_tasks)

        for result, (requested, _) in zip(improvements, resolved_models):
            result.model = requested

        # Final synthesis
        synthesis_prompt = self._build_synthesis_prompt(prompt, improvements, initial_responses)
        first_requested, first_canonical = resolved_models[0]
        synthesizer = self._select_provider(first_canonical)
        final_response = await synthesizer.complete(synthesis_prompt, model=first_canonical)
        final_response.model = first_requested

        return OrchestrationArtifacts(
            initial_responses=initial_responses,
            critiques=critiques,
            improvements=improvements,
            final_response=final_response,
        )

    def _build_synthesis_prompt(
        self,
        prompt: str,
        improvements: Sequence[LLMResult],
        initial_responses: Sequence[LLMResult],
    ) -> str:
        parts = [
            "You are synthesizing answers from a collaborative team of AI experts.",
            f"Original user prompt:\n{prompt}",
            "Improved answers:",
        ]
        for result in improvements:
            parts.append(f"- {result.model}: {result.content}")
        parts.append("Initial answers for reference:")
        for result in initial_responses:
            parts.append(f"- {result.model}: {result.content}")
        parts.append(
            "Craft a single final response that combines the best insights, resolves disagreements,"
            " and clearly communicates the answer to the user."
        )
        return "\n\n".join(parts)
