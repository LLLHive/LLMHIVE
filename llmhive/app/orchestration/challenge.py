"""Adversarial critique and referee logic."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import List

from .ensemble import EnsembleOutput
from .equalizer import OrchestrationProfile
from .prompt_opt import PromptPlan


@dataclass
class ChallengeFeedback:
    """Internal critique result for a single output."""

    model_name: str
    critique: str
    referee_score: float


class ChallengeEngine:
    """Generate internal critiques and referee assessments."""

    async def run(
        self,
        outputs: List[EnsembleOutput],
        plan: PromptPlan,
        profile: OrchestrationProfile,
    ) -> List[ChallengeFeedback]:
        feedback: List[ChallengeFeedback] = []
        for output in outputs:
            await asyncio.sleep(0)
            critique = self._build_critique(output, plan)
            referee_score = max(0.0, min(1.0, output.score_quality - 0.05 + output.score_factuality * 0.5))
            feedback.append(
                ChallengeFeedback(
                    model_name=output.model_name,
                    critique=critique,
                    referee_score=referee_score,
                )
            )
        return feedback

    def _build_critique(self, output: EnsembleOutput, plan: PromptPlan) -> str:
        hints = ["Ensure claims are supported."]
        if len(plan.segments) > 1:
            hints.append("Address each segment explicitly.")
        if len(output.text) < 120:
            hints.append("Response appears brief; elaborate if possible.")
        return " ".join(hints)
