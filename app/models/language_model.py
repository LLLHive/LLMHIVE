"""Synchronous wrapper around the OpenAI Chat Completions API."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from openai import OpenAI

from .stub_language_model import StubLanguageModel

logger = logging.getLogger(__name__)


class LanguageModel:
    """Encapsulate OpenAI interactions with graceful fallback behaviour."""

    def __init__(self, api_key: str, model: str = "gpt-4o"):
        """Initialise the OpenAI client and prepare a stub fallback."""

        self.client = OpenAI(api_key=api_key)
        self.model = model
        # Use a stub model as a safety net when quota or network issues occur.
        self._fallback = StubLanguageModel(model=f"stub-{model}")

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        response_format: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Generate a response, falling back to the stub model when OpenAI fails."""

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        kwargs = {"model": self.model, "messages": messages}
        if response_format:
            kwargs["response_format"] = response_format

        try:
            response = self.client.chat.completions.create(**kwargs)
            return response.choices[0].message.content or ""
        except Exception as exc:
            if self._should_use_fallback(exc):
                logger.warning(
                    "OpenAI chat completion failed due to quota or rate limits; using stub fallback. Error: %s",
                    exc,
                )
                return self._fallback.generate(
                    prompt,
                    system_prompt=system_prompt,
                    response_format=response_format,
                )

            logger.exception("OpenAI chat completion failed", exc_info=exc)
            raise

    def _should_use_fallback(self, exc: Exception) -> bool:
        """Return True when the exception indicates an OpenAI quota or 429 error."""

        message = str(exc).lower()
        if (
            "insufficient_quota" in message
            or "you exceeded your current quota" in message
            or "rate limit" in message
        ):
            return True

        status_code = getattr(exc, "status_code", None)
        if status_code == 429:
            return True

        response = getattr(exc, "response", None)
        response_status = getattr(response, "status_code", None)
        return response_status == 429
