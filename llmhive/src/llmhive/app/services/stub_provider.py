"""Deterministic stub provider for development and testing."""
from __future__ import annotations

import asyncio
import random
import re
from typing import List, Sequence, Tuple

from .base import LLMProvider, LLMResult

# Maximum length of prompt to include in fallback stub response
MAX_PROMPT_PREVIEW_LENGTH = 100


class StubProvider(LLMProvider):
    """Simple provider that fabricates plausible responses."""

    def __init__(self, seed: int | None = None) -> None:
        self.random = random.Random(seed)
        self._models: List[str] = ["stub-v1", "stub-researcher", "stub-critic"]
        self._number_words = {
            "one": 1,
            "two": 2,
            "three": 3,
            "four": 4,
            "five": 5,
            "six": 6,
            "seven": 7,
            "eight": 8,
            "nine": 9,
            "ten": 10,
        }
        # Data is intentionally small and human curated so we don't pull in external dependencies
        # or APIs for the development stub provider.
        self._city_data: dict[str, List[Tuple[str, str | None]]] = {
            "europe": [
                ("Istanbul, Turkey", "15.8M"),
                ("Moscow, Russia", "12.5M"),
                ("London, United Kingdom", "9.5M"),
                ("Saint Petersburg, Russia", "5.4M"),
                ("Berlin, Germany", "3.6M"),
                ("Madrid, Spain", "3.3M"),
                ("Kiev, Ukraine", "2.9M"),
                ("Rome, Italy", "2.8M"),
                ("Bucharest, Romania", "1.8M"),
                ("Paris, France", "2.1M"),
            ],
            "world": [
                ("Tokyo, Japan", "37.4M"),
                ("Delhi, India", "32.9M"),
                ("Shanghai, China", "29.2M"),
                ("São Paulo, Brazil", "22.6M"),
                ("Mexico City, Mexico", "22.2M"),
                ("Cairo, Egypt", "22.1M"),
                ("Dhaka, Bangladesh", "22.0M"),
                ("Mumbai, India", "21.3M"),
                ("Beijing, China", "20.9M"),
                ("Osaka, Japan", "19.0M"),
            ],
            "spain": [
                ("Madrid", "3.2M"),
                ("Barcelona", "1.6M"),
                ("Valencia", "0.8M"),
                ("Seville (Sevilla)", "0.7M"),
                ("Zaragoza", "0.7M"),
                ("Málaga", "0.6M"),
                ("Murcia", "0.5M"),
                ("Palma de Mallorca", "0.4M"),
                ("Las Palmas de Gran Canaria", "0.4M"),
                ("Bilbao", "0.35M"),
            ],
            "usa": [
                ("New York City, New York", "8.8M"),
                ("Los Angeles, California", "3.9M"),
                ("Chicago, Illinois", "2.7M"),
                ("Houston, Texas", "2.3M"),
                ("Phoenix, Arizona", "1.6M"),
                ("Philadelphia, Pennsylvania", "1.6M"),
                ("San Antonio, Texas", "1.5M"),
                ("San Diego, California", "1.4M"),
                ("Dallas, Texas", "1.3M"),
                ("San Jose, California", "1.0M"),
            ],
            "florida": [
                ("Jacksonville", "954K"),
                ("Miami", "449K"),
                ("Tampa", "399K"),
                ("Orlando", "312K"),
                ("St. Petersburg", "259K"),
                ("Hialeah", "221K"),
                ("Port St. Lucie", "217K"),
                ("Cape Coral", "212K"),
                ("Tallahassee", "197K"),
                ("Fort Lauderdale", "183K"),
            ],
        }
        self._affordable_developer_data: dict[str, List[Tuple[str, str, str]]] = {
            "florida": [
                (
                    "Housing Trust Group (HTG)",
                    "Coconut Grove, FL",
                    "One of Florida's largest affordable and workforce housing developers with thousands of units delivered across the state.",
                ),
                (
                    "Atlantic Pacific Communities",
                    "Miami, FL",
                    "LIHTC-focused developer and property manager building affordable communities in Miami-Dade, Broward, Palm Beach, and beyond.",
                ),
                (
                    "Related Urban (The Related Group)",
                    "Miami, FL",
                    "Affordable and mixed-income arm of Related Group leading HOPE VI and public housing redevelopments statewide.",
                ),
                (
                    "Pinnacle Housing Group",
                    "Miami, FL",
                    "Regional developer specializing in affordable and workforce housing with more than 10,000 units completed in Florida.",
                ),
                (
                    "Carrfour Supportive Housing",
                    "Miami, FL",
                    "Nonprofit developer providing permanent supportive housing for formerly homeless and special-needs households across Florida.",
                ),
                (
                    "Smith & Henzy Advisory Group",
                    "Delray Beach, FL",
                    "Advises and co-develops large-scale affordable housing and public-private partnerships throughout South Florida.",
                ),
            ]
        }

    def list_models(self) -> List[str]:
        return list(self._models)

    async def _sleep(self) -> None:
        await asyncio.sleep(self.random.uniform(0.01, 0.05))

    def _extract_requested_count(self, prompt_lower: str) -> int | None:
        """Attempt to extract the desired number of items from the prompt."""
        # Look for explicit numbers first (e.g. "list the 3 largest")
        number_match = re.search(r"\b(\d{1,2})\b", prompt_lower)
        if number_match:
            try:
                return int(number_match.group(1))
            except ValueError:
                pass

        # Fall back to written number words up to ten
        for word, value in self._number_words.items():
            if re.search(rf"\b{word}\b", prompt_lower):
                return value

        return None

    def _format_city_list(
        self,
        cities: Sequence[Tuple[str, str | None]],
        count: int | None,
        include_population: bool,
        *,
        default: int,
        label: str,
    ) -> str:
        total = count or default
        total = max(1, min(total, len(cities)))
        lines = [
            f"{idx}. {name}{f' — population {population}' if include_population and population else ''}"
            for idx, (name, population) in enumerate(cities[:total], start=1)
        ]
        header = f"Here are the {total} largest cities in {label}:"
        if include_population:
            header += " (with approximate populations)"
        return header + "\n" + "\n".join(lines)

    def _format_developer_list(
        self,
        developers: Sequence[Tuple[str, str, str]],
        count: int | None,
        *,
        default: int,
        region_label: str,
    ) -> str:
        total = count or default
        total = max(1, min(total, len(developers)))
        lines = [
            f"{idx}. {name} — headquartered in {hq}. {summary}"
            for idx, (name, hq, summary) in enumerate(developers[:total], start=1)
        ]
        header = f"Here are leading {region_label} affordable housing developers:"
        return header + "\n" + "\n".join(lines)

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

        if (
            "florida" in prompt_lower
            and "affordable" in prompt_lower
            and "housing" in prompt_lower
            and ("developer" in prompt_lower or "development" in prompt_lower)
        ):
            count = self._extract_requested_count(prompt_lower)
            developers = self._affordable_developer_data.get("florida", [])
            if developers:
                return self._format_developer_list(
                    developers,
                    count,
                    default=5,
                    region_label="Florida",
                )

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
        
        # List questions about cities
        if "list" in prompt_lower or "largest" in prompt_lower or "biggest" in prompt_lower:
            if "city" in prompt_lower or "cities" in prompt_lower:
                requested_count = self._extract_requested_count(prompt_lower)
                include_population = "population" in prompt_lower or "populations" in prompt_lower

                if "florida" in prompt_lower:
                    return self._format_city_list(
                        self._city_data["florida"],
                        requested_count,
                        include_population,
                        default=5,
                        label="Florida",
                    )

                if "spain" in prompt_lower:
                    return self._format_city_list(
                        self._city_data["spain"],
                        requested_count,
                        include_population,
                        default=5,
                        label="Spain",
                    )

                if "europe" in prompt_lower or "european" in prompt_lower:
                    return self._format_city_list(
                        self._city_data["europe"],
                        requested_count,
                        include_population,
                        default=5,
                        label="Europe",
                    )

                if "world" in prompt_lower or "global" in prompt_lower:
                    return self._format_city_list(
                        self._city_data["world"],
                        requested_count,
                        include_population,
                        default=5,
                        label="the world",
                    )

                if (
                    "usa" in prompt_lower
                    or "united states" in prompt_lower
                    or "american" in prompt_lower
                    or " us " in prompt_lower
                    or prompt_lower.startswith("us ")
                    or prompt_lower.endswith(" us")
                ):
                    return self._format_city_list(
                        self._city_data["usa"],
                        requested_count,
                        include_population,
                        default=5,
                        label="the United States",
                    )

        if "best" in prompt_lower and "model" in prompt_lower and "coding" in prompt_lower:
            return (
                "Top AI coding assistants today include GPT-4.1 (OpenAI), Claude 3 Opus (Anthropic), and Gemini 1.5 Pro (Google). "
                "Each excels at complex reasoning, tool use, and code synthesis, so the best choice depends on your language, "
                "infrastructure, and budget requirements."
            )
        
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
