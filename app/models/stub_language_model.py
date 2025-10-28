"""Synchronous stub language model used when real API keys are unavailable."""

from __future__ import annotations

import json
from typing import Any, Dict, Optional


class StubLanguageModel:
    """Minimal drop-in replacement for :class:`LanguageModel`.

    The stub produces deterministic responses that keep the orchestration
    engine functional during local development or automated testing when
    external LLM APIs are not configured.
    """

    def __init__(self, model: str = "stub-gpt") -> None:
        self.model = model

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        response_format: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Return a deterministic response for the provided prompt."""

        if response_format and response_format.get("type") == "json_object":
            plan = {
                "reasoning": (
                    "Use an internal summarizer agent to craft a direct response "
                    "to the user's request."
                ),
                "steps": [
                    {
                        "step_name": "respond",
                        "agent": "summarizer",
                        "prompt": (
                            "Provide a concise and helpful answer to the following "
                            "request:\n\n" + prompt
                        ),
                    }
                ],
            }
            return json.dumps(plan)

        prompt_lower = prompt.lower()

        if "capital" in prompt_lower and "spain" in prompt_lower:
            return "The capital of Spain is Madrid."
        if "capital" in prompt_lower and "france" in prompt_lower:
            return "The capital of France is Paris."

        return (
            "This is a stub response generated locally because no external LLM "
            "provider is configured.\n\nRequest:\n" + prompt
        )
