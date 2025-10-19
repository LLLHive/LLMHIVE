"""Core orchestration workflow for coordinating multiple LLMs."""
from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, Iterable, List, Sequence, Tuple

from .config import settings
from .services.base import LLMProvider, LLMResult, ProviderNotConfiguredError
from .services.openai_provider import OpenAIProvider
from .services.stub_provider import StubProvider
from .services.anthropic_provider import AnthropicProvider
from .services.grok_provider import GrokProvider
from .services.gemini_provider import GeminiProvider
from .services.deepseek_provider import DeepSeekProvider
from .services.manus_provider import ManusProvider

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

    def __init__(self, providers: Dict[str, LLMProvider] | None = None) -> None:
        if providers is None:
            providers = self._default_providers()
        self.providers = providers

    def _default_providers(self) -> Dict[str, LLMProvider]:
        mapping: Dict[str, LLMProvider] = {}
        # Instantiate OpenAI provider if configured
        try:
            mapping["openai"] = OpenAIProvider(api_key=settings.openai_api_key, timeout=settings.openai_timeout_seconds)
        except ProviderNotConfiguredError:
            logger.info("OpenAI provider not configured; skipping.")
        # Instantiate Anthropic provider if configured
        if settings.anthropic_api_key:
            try:
                mapping["anthropic"] = AnthropicProvider(api_key=settings.anthropic_api_key, timeout=settings.anthropic_timeout_seconds)
            except ProviderNotConfiguredError:
                logger.info("Anthropic provider not configured; skipping.")
        # Instantiate Grok provider if configured
        if settings.grok_api_key:
            try:
                mapping["grok"] = GrokProvider(api_key=settings.grok_api_key, timeout=settings.grok_timeout_seconds)
            except ProviderNotConfiguredError:
                logger.info("Grok provider not configured; skipping.")
        # Instantiate Gemini provider if configured
        if settings.gemini_api_key:
            try:
                mapping["gemini"] = GeminiProvider(api_key=settings.gemini_api_key, timeout=settings.gemini_timeout_seconds)
            except ProviderNotConfiguredError:
                logger.info("Gemini provider not configured; skipping.")
        # Instantiate DeepSeek provider if configured
        if settings.deepseek_api_key:
            try:
                mapping["deepseek"] = DeepSeekProvider(api_key=settings.deepseek_api_key, timeout=settings.deepseek_timeout_seconds)
            except ProviderNotConfiguredError:
                logger.info("DeepSeek provider not configured; skipping.")
        # Instantiate Manus provider if configured
        if settings.manus_api_key:
            try:
                mapping["manus"] = ManusProvider(api_key=settings.manus_api_key, timeout=settings.manus_timeout_seconds)
            except ProviderNotConfiguredError:
                logger.info("Manus provider not configured; skipping.")
        # Always provide a stub provider as a fallback
        mapping.setdefault("stub", StubProvider())
        return mapping

    def _select_provider(self, model: str) -> LLMProvider:
        lower = model.lower()
        # Route based on model name prefixes
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
        # Fallback to stub
        return self.providers.get("stub", StubProvider())

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
        completion_tasks = [
            self._select_provider(model).complete(prompt, model=model)
            for model in model_list
        ]
        initial_responses = await self._gather_with_handling(completion_tasks)

        # Cross critiques
        critique_tasks: list[asyncio.Task[LLMResult]] = []
        for author_result in initial_responses:
            for target_result in initial_responses:
                if author_result.model == target_result.model:
                    continue
                provider = self._select_provider(author_result.model)
                critique_tasks.append(
                    asyncio.create_task(
                        provider.critique(
                            prompt,
                            target_answer=target_result.content,
                            author=author_result.model,
                            model=author_result.model,
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
            provider = self._select_provider(response.model)
            improvement_tasks.append(
                asyncio.create_task(
                    provider.improve(
                        prompt,
                        previous_answer=response.content,
                        critiques=critiques_by_model.get(response.model, []),
                        model=response.model,
                    )
                )
            )
        improvements = await self._gather_with_handling(improvement_tasks)

        # Final synthesis
        synthesis_prompt = self._build_synthesis_prompt(prompt, improvements, initial_responses)
        synthesizer = self._select_provider(model_list[0])
        final_response = await synthesizer.complete(synthesis_prompt, model=model_list[0])

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
            "Craft a single final response that combines the best insights, resolves disagreements,"\
            " and clearly communicates the answer to the user."
        )
        return "\n\n".join(parts)
