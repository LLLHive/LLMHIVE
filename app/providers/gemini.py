"""Google Gemini provider integration for the simplified app runtime."""
from __future__ import annotations

import logging
from typing import Any, AsyncGenerator, ClassVar, Dict, List, Tuple

logger = logging.getLogger("llmhive.providers.gemini")

_ALLOWED_CONFIG_KEYS: set[str] = {"temperature", "top_p", "top_k", "max_output_tokens", "candidate_count"}


class GeminiProvider:
    """Lightweight asynchronous wrapper around the Google Generative AI SDK."""

    _SUPPORTED_MODELS: ClassVar[List[str]] = [
        "gemini-1.5-pro",
        "gemini-pro",
        "gemini-pro-vision",
    ]
    _DEFAULT_GENERATION_CONFIG: ClassVar[Dict[str, Any]] = {
        "temperature": 0.4,
        "max_output_tokens": 2048,
    }

    def __init__(
        self,
        api_key: str,
        *,
        generation_config: Dict[str, Any] | None = None,
    ) -> None:
        if not api_key:
            raise ValueError("Gemini API key must be provided.")

        try:
            import google.generativeai as genai  # type: ignore
        except Exception as exc:  # pragma: no cover - optional dependency
            raise ImportError(
                "The 'google-generativeai' package is required for the Gemini provider. "
                "Install it with 'pip install google-generativeai'."
            ) from exc

        genai.configure(api_key=api_key)
        self._client = genai
        base_config = dict(self._DEFAULT_GENERATION_CONFIG)
        if generation_config:
            base_config.update(generation_config)
        self._generation_config = base_config

    @classmethod
    def list_supported_models(cls) -> List[str]:
        """Return the model identifiers that this provider understands."""

        return list(cls._SUPPORTED_MODELS)

    def _prepare_prompt(self, messages: List[Dict[str, str]]) -> Tuple[str | None, str]:
        system_instruction: str | None = None
        prompt_lines: List[str] = []

        for message in messages:
            role = message.get("role", "user")
            content = str(message.get("content", ""))
            if not content:
                continue

            if role == "system" and system_instruction is None:
                system_instruction = content
                continue

            label = "ASSISTANT" if role == "assistant" else "USER"
            prompt_lines.append(f"{label}: {content}")

        prompt_body = "\n\n".join(prompt_lines).strip()
        return system_instruction, prompt_body or ""

    def _merge_generation_config(self, overrides: Dict[str, Any]) -> Dict[str, Any]:
        config = dict(self._generation_config)
        for key, value in overrides.items():
            if key in _ALLOWED_CONFIG_KEYS and value is not None:
                config[key] = value
        return config

    def _extract_text(self, response: Any) -> str:
        text = getattr(response, "text", None)
        if isinstance(text, str) and text.strip():
            return text

        candidates = getattr(response, "candidates", None)
        if isinstance(candidates, list):
            for candidate in candidates:
                content = getattr(candidate, "content", None)
                parts = getattr(content, "parts", None)
                if isinstance(parts, list):
                    pieces = [getattr(part, "text", "") for part in parts if getattr(part, "text", "")]
                    joined = "".join(pieces).strip()
                    if joined:
                        return joined
        return ""

    async def generate(self, messages: List[Dict[str, str]], model: str, **kwargs: Any) -> str:
        """Return a completion for the provided chat transcript."""

        system_instruction, prompt = self._prepare_prompt(messages)
        config = self._merge_generation_config(kwargs)

        try:
            model_instance = self._client.GenerativeModel(
                model_name=model,
                system_instruction=system_instruction,
            )
            response = await model_instance.generate_content_async(
                prompt,
                generation_config=config,
            )
        except Exception as exc:  # pragma: no cover - network failure surface
            logger.warning("Gemini generate request failed for model %s: %s", model, exc)
            return f"Error: Could not get response from {model}."

        return self._extract_text(response)

    async def generate_stream(
        self,
        messages: List[Dict[str, str]],
        model: str,
        **kwargs: Any,
    ) -> AsyncGenerator[str, None]:
        """Yield the completion for callers expecting a streaming interface."""

        content = await self.generate(messages, model, **kwargs)
        if content:
            yield content

