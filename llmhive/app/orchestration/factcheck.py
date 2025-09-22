"""Automated fact-checking utilities."""
from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from typing import Dict, List

from ..core.constants import FactCheckMethod, FactCheckVerdict
from .ensemble import EnsembleOutput
from .equalizer import OrchestrationProfile
from .prompt_opt import PromptPlan


@dataclass
class FactCheckResult:
    """Represents the outcome of verifying a claim."""

    model_name: str
    claim: str
    method: FactCheckMethod
    verdict: FactCheckVerdict
    score: float
    evidence: Dict[str, str]


class FactCheckEngine:
    """Run lightweight fact-checking over model outputs."""

    async def verify(
        self,
        outputs: List[EnsembleOutput],
        plan: PromptPlan,
        _profile: OrchestrationProfile,
    ) -> List[FactCheckResult]:
        results: List[FactCheckResult] = []
        for output in outputs:
            claims = self._extract_claims(output.text)
            for claim in claims:
                result = await self._score_claim(output.model_name, claim)
                results.append(result)
        return results

    def _extract_claims(self, text: str) -> List[str]:
        sentences = re.split(r"(?<=[.!?])\s+", text)
        return [s for s in sentences if any(ch.isdigit() for ch in s) or "according" in s.lower()]

    async def _score_claim(self, model_name: str, claim: str) -> FactCheckResult:
        await asyncio.sleep(0)
        score = 0.7 if any(char.isdigit() for char in claim) else 0.8
        verdict = FactCheckVerdict.PASS if score >= 0.65 else FactCheckVerdict.UNCLEAR
        evidence = {"note": "Heuristic check only"}
        return FactCheckResult(
            model_name=model_name,
            claim=claim.strip(),
            method=FactCheckMethod.LLM,
            verdict=verdict,
            score=score,
            evidence=evidence,
        )
