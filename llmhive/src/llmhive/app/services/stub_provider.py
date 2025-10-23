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
        
        # Check if this is a synthesis prompt (from the orchestrator)
        if prompt.startswith("You are synthesizing answers from a collaborative team"):
            # Extract the original user prompt from the synthesis request
            lines = prompt.split('\n')
            original_prompt = ""
            capture_next = False
            for line in lines:
                if capture_next and line.strip():
                    original_prompt = line.strip()
                    break
                if line.strip() == "Original user prompt:":
                    capture_next = True
            
            # If we found the original prompt, try to answer it
            if original_prompt:
                return self._generate_answer(original_prompt)
            
            # Otherwise, try to extract answer from the improved answers section
            for i, line in enumerate(lines):
                if line.strip().startswith("Improved answers:") or line.strip().startswith("- "):
                    # Find first non-empty answer
                    for j in range(i+1, len(lines)):
                        if lines[j].strip().startswith("- ") and ":" in lines[j]:
                            # Extract the answer after the model name
                            answer = lines[j].split(":", 1)[1].strip()
                            if answer and not answer.startswith("Improved by"):
                                # Clean up improvement wrapper if present
                                if "Improved by" in answer:
                                    answer = answer.split("(considering:")[0].strip()
                                    answer = answer.replace("Improved by " + lines[j].split(":")[0].strip() + ":", "").strip()
                                return answer
            
            # Fallback for synthesis
            return "Based on the collaborative analysis, this question requires more specific information to provide an accurate answer. Please configure real LLM providers for detailed responses."
        
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
