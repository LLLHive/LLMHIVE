"""Core orchestration workflow for coordinating multiple LLMs."""
from __future__ import annotations

import asyncio
import logging
import os
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, Iterable, List, Sequence, Tuple

from .config import settings
from .services.base import LLMProvider, LLMResult, ProviderNotConfiguredError
from .services.openai_provider import OpenAIProvider
from .services.stub_provider import StubProvider

# Try to import optional providers
try:
    from .services.anthropic_provider import AnthropicProvider
except ImportError:
    AnthropicProvider = None

try:
    from .services.grok_provider import GrokProvider
except ImportError:
    GrokProvider = None

try:
    from .services.gemini_provider import GeminiProvider
except ImportError:
    GeminiProvider = None

try:
    from .services.deepseek_provider import DeepSeekProvider
except ImportError:
    DeepSeekProvider = None

try:
    from .services.manus_provider import ManusProvider
except ImportError:
    ManusProvider = None

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
            anthropic_key = self._get_key("anthropic_api_key", "ANTHROPIC_API_KEY")
            if anthropic_key and AnthropicProvider is not None:
                mapping["anthropic"] = AnthropicProvider(api_key=anthropic_key, timeout=getattr(settings, "anthropic_timeout_seconds", None))
                logger.info("Anthropic provider configured.")
            else:
                raise ProviderNotConfiguredError("Anthropic provider not available or API key not set")
        except ProviderNotConfiguredError:
            logger.info("Anthropic provider not configured; skipping.")

        # Grok (xAI)
        try:
            grok_key = self._get_key("grok_api_key", "GROK_API_KEY")
            if grok_key and GrokProvider is not None:
                mapping["grok"] = GrokProvider(api_key=grok_key, timeout=getattr(settings, "grok_timeout_seconds", None))
                logger.info("Grok provider configured.")
            else:
                raise ProviderNotConfiguredError("Grok provider not available or API key not set")
        except ProviderNotConfiguredError:
            logger.info("Grok provider not configured; skipping.")

        # Gemini (Google)
        try:
            gemini_key = self._get_key("gemini_api_key", "GEMINI_API_KEY")
            if gemini_key and GeminiProvider is not None:
                mapping["gemini"] = GeminiProvider(api_key=gemini_key, timeout=getattr(settings, "gemini_timeout_seconds", None))
                logger.info("Gemini provider configured.")
            else:
                raise ProviderNotConfiguredError("Gemini provider not available or API key not set")
        except ProviderNotConfiguredError:
            logger.info("Gemini provider not configured; skipping.")

        # DeepSeek
        try:
            deepseek_key = self._get_key("deepseek_api_key", "DEEPSEEK_API_KEY")
            if deepseek_key and DeepSeekProvider is not None:
                mapping["deepseek"] = DeepSeekProvider(api_key=deepseek_key, timeout=getattr(settings, "deepseek_timeout_seconds", None))
                logger.info("DeepSeek provider configured.")
            else:
                raise ProviderNotConfiguredError("DeepSeek provider not available or API key not set")
        except ProviderNotConfiguredError:
            logger.info("DeepSeek provider not configured; skipping.")

        # Manus (proxy)
        try:
            manus_key = self._get_key("manus_api_key", "MANUS_API_KEY")
            if manus_key and ManusProvider is not None:
                mapping["manus"] = ManusProvider(api_key=manus_key, timeout=getattr(settings, "manus_timeout_seconds", None))
                logger.info("Manus provider configured.")
            else:
                raise ProviderNotConfiguredError("Manus provider not available or API key not set")
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

    async def orchestrate(self, prompt: str, models: Iterable[str] | None = None) -> OrchestrationArtifacts:
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
        parts: list[str] = []
        parts.append("You are synthesizing answers from a collaborative team of AI experts.")
        parts.append("")
        parts.append("Original user prompt:")
        parts.append(prompt)
        parts.append("")
        parts.append("Improved answers:")
        for imp in improvements:
            parts.append(f"- {imp.model}: {imp.content}")
            parts.append("")
        parts.append("Initial answers for reference:")
        for ans in initial_responses:
            parts.append(f"- {ans.model}: {ans.content}")
            parts.append("")
        parts.append("Craft a single final response that combines the best insights, resolves disagreements, and clearly communicates the answer to the user.")
        return "\n".join(parts)
