"""Core orchestration workflow for coordinating multiple LLMs."""
from __future__ import annotations

import asyncio
import logging
import os
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, Iterable, List, Mapping, Sequence, Tuple

from .config import settings
from .services.base import LLMProvider, LLMResult, ProviderNotConfiguredError
from .services.openai_provider import OpenAIProvider
from .services.grok_provider import GrokProvider
from .services.anthropic_provider import AnthropicProvider
from .services.gemini_provider import GeminiProvider
from .services.deepseek_provider import DeepSeekProvider
from .services.manus_provider import ManusProvider
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

    def _get_key(self, *candidates: str) -> str | None:
        """Return the first available credential from settings or the raw environment."""

        for name in candidates:
            value = getattr(settings, name, None)
            if value:
                return value
            env_value = os.getenv(name)
            if env_value:
                return env_value
            env_value = os.getenv(name.upper())
            if env_value:
                return env_value
        return None

    def _default_providers(self) -> Dict[str, LLMProvider]:
        mapping: Dict[str, LLMProvider] = {}
        self.provider_errors.clear()

        # OpenAI / GPT family
        try:
            openai_key = self._get_key("openai_api_key", "OPENAI_API_KEY", "OPENAI_KEY")
            mapping["openai"] = OpenAIProvider(api_key=openai_key)
            logger.info("OpenAI provider configured.")
        except ProviderNotConfiguredError as exc:
            error_message = str(exc)
            self.provider_errors["openai"] = error_message
            logger.warning(
                "OpenAI provider not configured; continuing without OpenAI support: %s",
                error_message,
            )

        # Anthropic / Claude models
        try:
            anthropic_key = self._get_key("anthropic_api_key", "ANTHROPIC_API_KEY")
            mapping["anthropic"] = AnthropicProvider(
                api_key=anthropic_key,
                timeout=getattr(settings, "anthropic_timeout_seconds", None),
            )
            logger.info("Anthropic provider configured.")
        except ProviderNotConfiguredError as exc:
            error_message = str(exc)
            self.provider_errors["anthropic"] = error_message
            logger.warning(
                "Anthropic provider not configured; continuing without Anthropic support: %s",
                error_message,
            )

        # Grok (xAI)
        try:
            grok_key = self._get_key("grok_api_key", "GROK_API_KEY", "GROCK_API_KEY", "XAI_API_KEY")
            mapping["grok"] = GrokProvider(
                api_key=grok_key,
                timeout=getattr(settings, "grok_timeout_seconds", None),
            )
            logger.info("Grok provider configured.")
        except ProviderNotConfiguredError as exc:
            error_message = str(exc)
            self.provider_errors["grok"] = error_message
            logger.warning(
                "Grok provider not configured; continuing without Grok support: %s",
                error_message,
            )

        # Gemini
        try:
            gemini_key = self._get_key("gemini_api_key", "GEMINI_API_KEY")
            mapping["gemini"] = GeminiProvider(
                api_key=gemini_key,
                timeout=getattr(settings, "gemini_timeout_seconds", None),
            )
            logger.info("Gemini provider configured.")
        except ProviderNotConfiguredError as exc:
            error_message = str(exc)
            self.provider_errors["gemini"] = error_message
            logger.warning(
                "Gemini provider not configured; continuing without Gemini support: %s",
                error_message,
            )

        # DeepSeek
        try:
            deepseek_key = self._get_key("deepseek_api_key", "DEEPSEEK_API_KEY")
            mapping["deepseek"] = DeepSeekProvider(
                api_key=deepseek_key,
                timeout=getattr(settings, "deepseek_timeout_seconds", None),
            )
            logger.info("DeepSeek provider configured.")
        except ProviderNotConfiguredError as exc:
            error_message = str(exc)
            self.provider_errors["deepseek"] = error_message
            logger.warning(
                "DeepSeek provider not configured; continuing without DeepSeek support: %s",
                error_message,
            )

        # Manus
        try:
            manus_key = self._get_key("manus_api_key", "MANUS_API_KEY")
            mapping["manus"] = ManusProvider(
                api_key=manus_key,
                timeout=getattr(settings, "manus_timeout_seconds", None),
            )
            logger.info("Manus provider configured.")
        except ProviderNotConfiguredError as exc:
            error_message = str(exc)
            self.provider_errors["manus"] = error_message
            logger.warning(
                "Manus provider not configured; continuing without Manus support: %s",
                error_message,
            )

        if settings.enable_stub_provider:
            if "stub" not in mapping:
                mapping["stub"] = StubProvider()
                logger.debug("Stub provider configured for development and testing fallback.")
        else:
            logger.debug("Stub provider disabled. Set ENABLE_STUB_PROVIDER=1 to enable the fallback.")

        available = sorted(mapping.keys())
        logger.info("Provider mapping completed. Available providers: %s", available)
        expected_keys = {
            "openai": ("openai_api_key", "OPENAI_API_KEY"),
            "anthropic": ("anthropic_api_key", "ANTHROPIC_API_KEY"),
            "grok": ("grok_api_key", "GROK_API_KEY", "GROCK_API_KEY", "XAI_API_KEY"),
            "gemini": ("gemini_api_key", "GEMINI_API_KEY"),
            "deepseek": ("deepseek_api_key", "DEEPSEEK_API_KEY"),
            "manus": ("manus_api_key", "MANUS_API_KEY"),
        }
        missing_keys = [name for name, aliases in expected_keys.items() if not self._get_key(*aliases)]
        if missing_keys:
            logger.debug("Provider API keys missing for: %s", missing_keys)
        return mapping

    def _resolve_model(self, model: str) -> tuple[str, str]:
        requested = model.strip()
        canonical = self.model_aliases.get(requested.lower(), requested)
        return requested, canonical

    def _validate_stub_usage(self, provider_key: str | None, requested: str, canonical: str) -> None:
        """Disallow routing non-stub model names through the stub provider."""

        if provider_key != "stub":
            return

        requested_lower = requested.lower()
        canonical_lower = canonical.lower()
        if "stub" in requested_lower and "stub" in canonical_lower:
            return
        raise ProviderNotConfiguredError(
            "Stub provider can only be used for explicit stub models. Configure real credentials for"
            f" '{requested}'."
        )

    def _select_provider(self, canonical_model: str) -> tuple[str | None, LLMProvider]:
        key = canonical_model.lower()
        if key.startswith("gpt"):
            provider = self.providers.get("openai")
            if provider is not None:
                return "openai", provider
            raise ProviderNotConfiguredError(
                "OpenAI provider is not configured; set OPENAI_API_KEY to call GPT models."
            )
        if key.startswith("claude"):
            provider = self.providers.get("anthropic")
            if provider is not None:
                return "anthropic", provider
            raise ProviderNotConfiguredError(
                "Anthropic provider is not configured; set ANTHROPIC_API_KEY to call Claude models."
            )
        if key.startswith("grok"):
            provider = self.providers.get("grok")
            if provider is not None:
                return "grok", provider
            raise ProviderNotConfiguredError(
                "Grok provider is not configured; set GROK_API_KEY to call Grok models."
            )
        if key.startswith("gemini"):
            provider = self.providers.get("gemini")
            if provider is not None:
                return "gemini", provider
            raise ProviderNotConfiguredError(
                "Gemini provider is not configured; set GEMINI_API_KEY to call Gemini models."
            )
        if key.startswith("deepseek"):
            provider = self.providers.get("deepseek")
            if provider is not None:
                return "deepseek", provider
            raise ProviderNotConfiguredError(
                "DeepSeek provider is not configured; set DEEPSEEK_API_KEY to call DeepSeek models."
            )
        if key.startswith("manus"):
            provider = self.providers.get("manus")
            if provider is not None:
                return "manus", provider
            raise ProviderNotConfiguredError(
                "Manus provider is not configured; set MANUS_API_KEY to call Manus models."
            )
        if key.startswith("stub") and "stub" in self.providers:
            return "stub", self.providers["stub"]
        raise ProviderNotConfiguredError(
            f"No provider is available for model '{canonical_model}'. Configure an alias or install a provider."
        )

    def provider_status(self) -> Dict[str, Dict[str, str | bool | None]]:
        """Expose provider availability details for diagnostics."""

        status: Dict[str, Dict[str, str | bool | None]] = {}
        for name, provider in self.providers.items():
            entry: Dict[str, str | bool | None] = {
                "status": "available",
                "provider": provider.__class__.__name__,
                "configured": True,
            }
            if name == "stub":
                entry["stub"] = True
                entry["configured"] = bool(settings.enable_stub_provider)
            status[name] = entry

        for name, message in self.provider_errors.items():
            entry = status.setdefault(name, {"provider": None})
            entry.update(
                {
                    "status": "unavailable",
                    "configured": False,
                    "error": message,
                }
            )
        return status

    async def _gather_with_handling(
        self,
        coroutines: Sequence[asyncio.Future],
        task_metadata: Sequence[tuple[str | None, str]],
        stage: str,
    ) -> list[LLMResult]:
        results = await asyncio.gather(*[asyncio.create_task(coro) for coro in coroutines], return_exceptions=True)
        failures: list[str] = []
        successful: list[LLMResult] = []
        for (provider_key, label), result in zip(task_metadata, results):
            if isinstance(result, ProviderNotConfiguredError):
                message = str(result)
                if provider_key:
                    self.provider_errors[provider_key] = message
                failures.append(f"{label}: {message}")
            elif isinstance(result, Exception):  # pragma: no cover - defensive catch
                message = str(result)
                if provider_key:
                    self.provider_errors[provider_key] = message
                logger.exception("Provider call failed", exc_info=result)
                failures.append(f"{label}: {message}")
            else:
                successful.append(result)
        if failures:
            combined = "; ".join(failures)
            raise ProviderNotConfiguredError(f"Provider failures during {stage}: {combined}")
        return successful

    async def orchestrate(self, prompt: str, models: Iterable[str] | None = None) -> OrchestrationArtifacts:
        """Run the multi-stage orchestration for the provided prompt."""

        model_list = list(models or settings.default_models)
        if not model_list:
            raise ValueError("At least one model must be provided")

        logger.info("Starting orchestration for %s", model_list)

        # Independent responses
        resolved_models = [self._resolve_model(model) for model in model_list]

        completion_tasks = []
        completion_metadata: list[tuple[str | None, str]] = []
        completion_bindings: list[tuple[str | None, str, str]] = []
        for requested, canonical in resolved_models:
            provider_key, provider = self._select_provider(canonical)
            self._validate_stub_usage(provider_key, requested, canonical)
            completion_tasks.append(provider.complete(prompt, model=canonical))
            completion_metadata.append((provider_key, f"{requested} ({canonical})"))
            completion_bindings.append((provider_key, requested, canonical))
        initial_responses = await self._gather_with_handling(
            completion_tasks, completion_metadata, stage="initial response generation"
        )

        for result, (provider_key, requested, _) in zip(initial_responses, completion_bindings):
            result.model = requested
            result.provider = provider_key

        # Cross critiques
        critique_tasks: list[asyncio.Future] = []
        critique_metadata: list[tuple[str | None, str]] = []
        critique_bindings: list[tuple[str | None, str, str]] = []
        for author_result in initial_responses:
            for target_result in initial_responses:
                if author_result.model == target_result.model:
                    continue
                _, canonical_author = self._resolve_model(author_result.model)
                provider_key, provider = self._select_provider(canonical_author)
                self._validate_stub_usage(provider_key, author_result.model, canonical_author)
                critique_tasks.append(
                    provider.critique(
                        prompt,
                        target_answer=target_result.content,
                        author=author_result.model,
                        model=canonical_author,
                    )
                )
                critique_metadata.append(
                    (
                        provider_key,
                        f"critique {author_result.model}→{target_result.model} ({canonical_author})",
                    )
                )
                critique_bindings.append((provider_key, author_result.model, target_result.model))
        critique_results = await self._gather_with_handling(
            critique_tasks, critique_metadata, stage="peer critique"
        )
        critiques: list[Tuple[str, str, LLMResult]] = []
        for result, (provider_key, author_label, target_label) in zip(critique_results, critique_bindings):
            result.provider = provider_key
            critiques.append((author_label, target_label, result))

        critiques_by_model: Dict[str, list[str]] = defaultdict(list)
        for author, target, critique in critiques:
            critiques_by_model[target].append(critique.content)

        # Improvement stage
        improvement_tasks: list[asyncio.Future] = []
        improvement_metadata: list[tuple[str | None, str]] = []
        improvement_bindings: list[tuple[str | None, str, str]] = []
        for response in initial_responses:
            _, canonical_model = self._resolve_model(response.model)
            provider_key, provider = self._select_provider(canonical_model)
            self._validate_stub_usage(provider_key, response.model, canonical_model)
            improvement_tasks.append(
                provider.improve(
                    prompt,
                    previous_answer=response.content,
                    critiques=critiques_by_model.get(response.model, []),
                    model=canonical_model,
                )
            )
            improvement_metadata.append((provider_key, f"improve {response.model} ({canonical_model})"))
            improvement_bindings.append((provider_key, response.model, canonical_model))
        improvements = await self._gather_with_handling(
            improvement_tasks, improvement_metadata, stage="answer improvement"
        )

        for result, (provider_key, requested, _) in zip(improvements, improvement_bindings):
            result.model = requested
            result.provider = provider_key

        # Final synthesis
        synthesis_prompt = self._build_synthesis_prompt(prompt, improvements, initial_responses)
        first_requested, first_canonical = resolved_models[0]
        provider_key, synthesizer = self._select_provider(first_canonical)
        self._validate_stub_usage(provider_key, first_requested, first_canonical)
        try:
            final_response = await synthesizer.complete(synthesis_prompt, model=first_canonical)
        except ProviderNotConfiguredError as exc:
            if provider_key:
                self.provider_errors[provider_key] = str(exc)
            raise
        final_response.model = first_requested
        final_response.provider = provider_key

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
