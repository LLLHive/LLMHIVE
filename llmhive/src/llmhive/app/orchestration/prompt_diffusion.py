"""Prompt Diffusion and Refinement system for LLMHive orchestrator.

Prompt Diffusion implements an iterative refinement process where multiple agents
collaboratively refine prompts through multiple rounds, with each agent building
upon previous versions. This creates a "diffusion" effect where the prompt
gradually improves through collaborative iteration.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from ..services.base import LLMProvider, LLMResult

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class PromptVersion:
    """Represents a version of a prompt during the diffusion process."""

    version: int
    prompt: str
    author: str  # Model/agent that created this version
    parent_version: Optional[int] = None  # Version this was derived from
    score: float = 0.0  # Quality score for this version
    improvements: List[str] = field(default_factory=list)  # List of improvements made
    metadata: Dict[str, any] = field(default_factory=dict)  # type: ignore[type-arg]


@dataclass(slots=True)
class DiffusionResult:
    """Result of the prompt diffusion process."""

    final_prompt: str
    versions: List[PromptVersion]
    convergence_score: float  # How well the diffusion converged
    rounds_completed: int
    best_version: PromptVersion


class PromptDiffusion:
    """Manages the prompt diffusion and refinement process."""

    def __init__(
        self,
        providers: Dict[str, LLMProvider],
        max_rounds: int = 3,
        convergence_threshold: float = 0.85,
    ) -> None:
        self.providers = providers
        self.max_rounds = max_rounds
        self.convergence_threshold = convergence_threshold

    async def diffuse(
        self,
        initial_prompt: str,
        models: List[str],
        *,
        context: Optional[str] = None,
        subject: Optional[str] = None,
    ) -> DiffusionResult:
        """Run the prompt diffusion process.

        Args:
            initial_prompt: The starting prompt
            models: List of models to use for diffusion
            context: Optional context to include
            subject: Optional subject description for refinement

        Returns:
            DiffusionResult with final prompt and version history
        """
        if not models:
            raise ValueError("At least one model is required for prompt diffusion")

        versions: List[PromptVersion] = []
        current_prompt = initial_prompt
        convergence_scores: List[float] = []

        # Create initial version
        initial_version = PromptVersion(
            version=0,
            prompt=initial_prompt,
            author="user",
            score=0.5,  # Baseline score
        )
        versions.append(initial_version)

        for round_num in range(1, self.max_rounds + 1):
            logger.info("Prompt diffusion round %d/%d", round_num, self.max_rounds)

            # Get refinements from all models in parallel
            refinement_tasks = []
            for model in models:
                task = self._refine_prompt(
                    current_prompt,
                    model,
                    round_num=round_num,
                    previous_versions=versions,
                    context=context,
                    subject=subject,
                )
                refinement_tasks.append((model, task))

            # Collect all refinements
            refined_prompts: List[Tuple[str, str, float]] = []  # (model, prompt, score)
            for model, task in refinement_tasks:
                try:
                    result = await task
                    refined_prompts.append((model, result[0], result[1]))
                except Exception as exc:
                    logger.warning("Model %s failed to refine prompt: %s", model, exc)
                    continue

            if not refined_prompts:
                logger.warning("No successful refinements in round %d", round_num)
                break

            # Score and select best refinement
            best_model, best_prompt, best_score = max(
                refined_prompts, key=lambda x: x[2]
            )

            # Create version for best refinement
            new_version = PromptVersion(
                version=round_num,
                prompt=best_prompt,
                author=best_model,
                parent_version=round_num - 1,
                score=best_score,
                improvements=self._extract_improvements(
                    versions[-1].prompt, best_prompt
                ),
            )
            versions.append(new_version)

            # Calculate convergence (how similar is this to previous versions?)
            convergence = self._calculate_convergence(versions)
            convergence_scores.append(convergence)

            logger.info(
                "Round %d: Best score %.2f, Convergence %.2f",
                round_num,
                best_score,
                convergence,
            )

            # Check for convergence
            if convergence >= self.convergence_threshold:
                logger.info(
                    "Prompt diffusion converged at round %d (score: %.2f)",
                    round_num,
                    convergence,
                )
                break

            # Update current prompt for next round
            current_prompt = best_prompt

        # Select best version overall
        best_version = max(versions, key=lambda v: v.score)

        final_convergence = (
            convergence_scores[-1] if convergence_scores else 0.0
        )

        return DiffusionResult(
            final_prompt=best_version.prompt,
            versions=versions,
            convergence_score=final_convergence,
            rounds_completed=len(versions) - 1,
            best_version=best_version,
        )

    async def _refine_prompt(
        self,
        current_prompt: str,
        model: str,
        *,
        round_num: int,
        previous_versions: List[PromptVersion],
        context: Optional[str] = None,
        subject: Optional[str] = None,
    ) -> Tuple[str, float]:
        """Refine a prompt using a specific model.

        Returns:
            Tuple of (refined_prompt, quality_score)
        """
        provider = self._select_provider(model)

        # Build refinement prompt
        refinement_prompt = self._build_refinement_prompt(
            current_prompt,
            round_num=round_num,
            previous_versions=previous_versions,
            context=context,
            subject=subject,
        )

        # Get refinement from model
        result = await provider.complete(refinement_prompt, model=model)

        refined_prompt = result.content.strip()

        # Score the refinement
        score = await self._score_refinement(
            original=current_prompt,
            refined=refined_prompt,
            model=model,
        )

        return (refined_prompt, score)

    def _build_refinement_prompt(
        self,
        current_prompt: str,
        *,
        round_num: int,
        previous_versions: List[PromptVersion],
        context: Optional[str] = None,
        subject: Optional[str] = None,
    ) -> str:
        """Build the prompt for refining another prompt."""
        lines = [
            "You are an expert at refining and optimizing prompts for AI models.",
            "",
            f"Current prompt (Round {round_num}):",
            f'"{current_prompt}"',
            "",
        ]

        if subject:
            lines.append(f"Subject/Context: {subject}")
            lines.append("")

        if len(previous_versions) > 1:
            lines.append("Previous versions for reference:")
            for v in previous_versions[-3:]:  # Show last 3 versions
                lines.append(f"  Round {v.version}: {v.prompt[:100]}...")
            lines.append("")

        if context:
            lines.append(f"Additional context: {context}")
            lines.append("")

        lines.extend(
            [
                "Your task:",
                "1. Analyze the current prompt for clarity, specificity, and effectiveness",
                "2. Identify areas for improvement (clarity, detail, structure, etc.)",
                "3. Create an improved version that:",
                "   - Is more specific and actionable",
                "   - Provides better context and constraints",
                "   - Is clearer and easier to understand",
                "   - Maintains the original intent",
                "",
                "Output ONLY the refined prompt, without any explanation or commentary.",
                "The refined prompt should be ready to use directly.",
            ]
        )

        return "\n".join(lines)

    async def _score_refinement(
        self,
        original: str,
        refined: str,
        model: str,
    ) -> float:
        """Score a refined prompt against the original.

        Returns a score between 0.0 and 1.0.
        """
        provider = self._select_provider(model)

        scoring_prompt = f"""Evaluate this prompt refinement on a scale of 0.0 to 1.0.

Original prompt:
"{original}"

Refined prompt:
"{refined}"

Consider:
- Clarity improvement (0.0-0.3)
- Specificity improvement (0.0-0.3)
- Structure improvement (0.0-0.2)
- Maintains original intent (0.0-0.2)

Respond with ONLY a number between 0.0 and 1.0, nothing else."""

        try:
            result = await provider.complete(scoring_prompt, model=model)
            score_text = result.content.strip()
            # Extract number from response
            import re

            match = re.search(r"(\d+\.?\d*)", score_text)
            if match:
                score = float(match.group(1))
                return min(1.0, max(0.0, score / 1.0))  # Normalize to 0-1
        except Exception as exc:
            logger.warning("Failed to score refinement: %s", exc)

        # Default score based on length and similarity
        length_improvement = min(1.0, len(refined) / max(len(original), 1))
        return 0.5 + (length_improvement - 0.5) * 0.3  # Bias toward improvements

    def _calculate_convergence(self, versions: List[PromptVersion]) -> float:
        """Calculate how well the diffusion has converged.

        Returns a score between 0.0 and 1.0, where 1.0 means perfect convergence.
        """
        if len(versions) < 2:
            return 0.0

        # Compare last two versions
        last = versions[-1]
        prev = versions[-2]

        # Simple similarity based on length and content overlap
        length_similarity = 1.0 - abs(len(last.prompt) - len(prev.prompt)) / max(
            len(last.prompt), len(prev.prompt), 1
        )

        # Word overlap
        last_words = set(last.prompt.lower().split())
        prev_words = set(prev.prompt.lower().split())
        if last_words or prev_words:
            overlap = len(last_words & prev_words) / max(
                len(last_words | prev_words), 1
            )
        else:
            overlap = 0.0

        # Score improvement (higher scores indicate convergence)
        score_improvement = max(0.0, last.score - prev.score)

        # Convergence is high when prompts are similar and scores are improving
        convergence = (length_similarity * 0.3 + overlap * 0.5 + score_improvement * 0.2)

        return min(1.0, convergence)

    def _extract_improvements(
        self, original: str, refined: str
    ) -> List[str]:
        """Extract a list of improvements made in the refinement."""
        improvements = []

        if len(refined) > len(original) * 1.1:
            improvements.append("Added more detail")
        elif len(refined) < len(original) * 0.9:
            improvements.append("Made more concise")

        # Simple keyword-based improvements
        refined_lower = refined.lower()
        if "specific" in refined_lower or "detailed" in refined_lower:
            improvements.append("Increased specificity")
        if "clear" in refined_lower or "explicit" in refined_lower:
            improvements.append("Improved clarity")

        return improvements

    def _select_provider(self, model: str) -> LLMProvider:
        """Select provider for a model."""
        model_lower = model.lower()
        if model_lower.startswith("gpt") and "openai" in self.providers:
            return self.providers["openai"]
        if model_lower.startswith("claude") and "anthropic" in self.providers:
            return self.providers["anthropic"]
        if model_lower.startswith("grok") and "grok" in self.providers:
            return self.providers["grok"]
        if model_lower.startswith("gemini") and "gemini" in self.providers:
            return self.providers["gemini"]
        if model_lower.startswith("deepseek") and "deepseek" in self.providers:
            return self.providers["deepseek"]
        return self.providers.get("stub", self.providers.get(list(self.providers.keys())[0]))

