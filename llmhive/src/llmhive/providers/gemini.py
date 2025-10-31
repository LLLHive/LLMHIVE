"""Google Gemini provider implementation shared across runtimes."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - optional dependency for typing only
    try:
        from google.generativeai.types import GenerateContentResponse  # type: ignore
    except Exception:  # pragma: no cover - only for static analysis
        GenerateContentResponse = object  # type: ignore

from llmhive.app.config import settings
from llmhive.app.services.base import LLMProvider, LLMResult, ProviderNotConfiguredError


class GeminiProvider(LLMProvider):
    """Interact with Google Gemini models with graceful misconfiguration handling."""

    def __init__(self, api_key: str | None = None, timeout: float | None = None) -> None:
        try:
            import google.generativeai as genai  # type: ignore
        except Exception as exc:  # pragma: no cover - dependency not installed in tests
            raise ProviderNotConfiguredError(
                f"Google Generative AI library import failed: {exc}. "
                "Install 'google-generativeai' package or remove Gemini models from your configuration."
            ) from exc

        key = api_key or getattr(settings, "gemini_api_key", None)
        if not key:
            raise ProviderNotConfiguredError("Gemini API key is missing.")

        genai.configure(api_key=key)
        self.genai = genai
        self.timeout = timeout or getattr(settings, "gemini_timeout_seconds", 45.0)
        self._models = [
            "gemini-1.5-pro",
            "gemini-1.5-flash",
            "gemini-1.0-pro-vision",
        ]

    def list_models(self) -> list[str]:
        return list(self._models)

    async def _generate(
        self,
        prompt: str,
        *,
        model: str,
        system_instruction: str | None = None,
    ) -> LLMResult:
        try:
            generation_config = {
                "temperature": 0.6,
                "max_output_tokens": 4096,
            }

            model_instance = self.genai.GenerativeModel(
                model_name=model,
                generation_config=generation_config,
                system_instruction=system_instruction,
            )

            response = await model_instance.generate_content_async(prompt)
            content = response.text if hasattr(response, "text") else ""

            return LLMResult(
                content=content,
                model=model,
                tokens=None,
                cost=None,
            )
        except Exception as exc:
            raise ProviderNotConfiguredError(str(exc)) from exc

    async def complete(self, prompt: str, *, model: str) -> LLMResult:
        return await self._generate(
            prompt,
            model=model,
            system_instruction="You are an expert assistant working in a collaborative AI team.",
        )

    async def critique(
        self,
        subject: str,
        *,
        target_answer: str,
        author: str,
        model: str,
    ) -> LLMResult:
        critique_prompt = f"""Question: {subject}

Answer to critique: {target_answer}

Provide constructive critique of the above answer. Address accuracy, completeness, and clarity."""

        result = await self._generate(
            critique_prompt,
            model=model,
            system_instruction=(
                "You are reviewing another AI's answer. Be concise and point out factual errors, "
                "missing information, and opportunities to improve the response."
            ),
        )
        result.model = author
        return result

    async def improve(
        self,
        subject: str,
        *,
        previous_answer: str,
        critiques: list[str],
        model: str,
    ) -> LLMResult:
        critique_text = "\n".join(f"- {item}" for item in critiques) or "No critiques provided."
        improve_prompt = f"""Question: {subject}

Previous answer: {previous_answer}

Critiques received:
{critique_text}

Refine your answer using these critiques. Return the improved answer."""

        return await self._generate(
            improve_prompt,
            model=model,
            system_instruction=(
                "You are improving your previous answer after receiving critiques from peer models. "
                "Incorporate actionable feedback and provide a stronger final answer."
            ),
        )


__all__ = ["GeminiProvider"]
