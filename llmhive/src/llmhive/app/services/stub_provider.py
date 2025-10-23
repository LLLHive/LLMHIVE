"""Deterministic stub provider for development and testing."""
from __future__ import annotations

import asyncio
import random
from typing import List

from .base import LLMProvider, LLMResult

# Maximum length of prompt to include in fallback stub response
MAX_PROMPT_PREVIEW_LENGTH = 100


class StubProvider(LLMProvider):
    """Simple provider that fabricates plausible responses."""

    def __init__(self, seed: int | None = None) -> None:
        self.random = random.Random(seed)

    async def _sleep(self) -> None:
        await asyncio.sleep(self.random.uniform(0.01, 0.05))

    def _generate_answer(self, prompt: str) -> str:
        """Generate a simple, plausible answer based on the prompt.
        
        This is a basic pattern-matching approach to provide helpful answers
        for common questions when real LLM providers aren't configured.
        """
        prompt_lower = prompt.lower()
        
        # Capital city questions
        if "capital" in prompt_lower:
            if "spain" in prompt_lower:
                return "The capital of Spain is Madrid."
            elif "france" in prompt_lower:
                return "The capital of France is Paris."
            elif "italy" in prompt_lower:
                return "The capital of Italy is Rome."
            elif "germany" in prompt_lower:
                return "The capital of Germany is Berlin."
            elif "japan" in prompt_lower:
                return "The capital of Japan is Tokyo."
            elif "china" in prompt_lower:
                return "The capital of China is Beijing."
            elif "usa" in prompt_lower or "united states" in prompt_lower or "america" in prompt_lower:
                return "The capital of the United States is Washington, D.C."
            elif "uk" in prompt_lower or "united kingdom" in prompt_lower or "britain" in prompt_lower:
                return "The capital of the United Kingdom is London."
            else:
                return "I would need to know which country you're asking about to answer what its capital is."
        
        # General questions - provide a generic but helpful response
        return f"This is a stub response. The question '{prompt[:MAX_PROMPT_PREVIEW_LENGTH]}' would normally be answered by a real LLM provider. Please configure API keys for OpenAI, Anthropic, or other providers to get actual AI responses."

    async def complete(self, prompt: str, *, model: str) -> LLMResult:
        await self._sleep()
        content = self._generate_answer(prompt)
        return LLMResult(content=content, model=model)

    async def critique(self, subject: str, *, target_answer: str, author: str, model: str) -> LLMResult:
        await self._sleep()
        feedback = f"{author} suggests clarifying details about '{subject[:48]}...'"
        return LLMResult(content=feedback, model=author)

    async def improve(
        self,
        subject: str,
        *,
        previous_answer: str,
        critiques: List[str],
        model: str,
    ) -> LLMResult:
        await self._sleep()
        critique_text = "; ".join(critiques) or "No critiques."
        content = f"Improved by {model}: {previous_answer} (considering: {critique_text})"
        return LLMResult(content=content[:1500], model=model)
