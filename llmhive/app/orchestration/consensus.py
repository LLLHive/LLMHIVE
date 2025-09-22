"""Consensus synthesis logic."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List

from ..utils.redact import apply_incognito_style
from .challenge import ChallengeFeedback
from .ensemble import EnsembleOutput
from .equalizer import OrchestrationProfile
from .factcheck import FactCheckResult
from .prompt_opt import PromptPlan
from .voting import VoteSummary


@dataclass
class Citation:
    """Citation reference exposed to API consumers."""

    source: str
    span: str

    def dict(self) -> dict[str, str]:
        return {"source": self.source, "span": self.span}


@dataclass
class ConsensusResult:
    """Final synthesis output."""

    final_answer: str
    confidence: float
    key_points: List[str]
    citations: List[Citation]
    style_incognito: bool


class ConsensusBuilder:
    """Combine model responses, votes, and fact-checks into a final answer."""

    def build(
        self,
        query: str,
        plan: PromptPlan,
        outputs: List[EnsembleOutput],
        votes: VoteSummary,
        challenges: List[ChallengeFeedback],
        fact_checks: List[FactCheckResult],
        profile: OrchestrationProfile,
    ) -> ConsensusResult:
        base_text = votes.winner.text
        enriched = self._merge_with_alternatives(base_text, votes)
        normalized = apply_incognito_style(enriched)
        key_points = self._extract_key_points(normalized)
        citations = self._build_citations(fact_checks)
        confidence = self._compute_confidence(votes, fact_checks)
        return ConsensusResult(
            final_answer=normalized,
            confidence=confidence,
            key_points=key_points,
            citations=citations,
            style_incognito=True,
        )

    def _merge_with_alternatives(self, base: str, votes: VoteSummary) -> str:
        additions: List[str] = []
        for alt in votes.ranked_outputs[1:3]:
            additions.append(alt.text.split("\n")[0])
        if additions:
            base = base + "\n\n" + "\n".join({line.strip() for line in additions if line.strip()})
        return base

    def _extract_key_points(self, text: str) -> List[str]:
        sentences = [sentence.strip() for sentence in text.split(".") if sentence.strip()]
        return sentences[:3]

    def _build_citations(self, fact_checks: List[FactCheckResult]) -> List[Citation]:
        citations: List[Citation] = []
        for check in fact_checks:
            citations.append(Citation(source=f"internal://{check.model_name}", span=check.claim))
        return citations

    def _compute_confidence(self, votes: VoteSummary, fact_checks: List[FactCheckResult]) -> float:
        vote_component = votes.scores.get(votes.winner.model_name, 0.0) / max(votes.total_weight, 1e-6)
        if fact_checks:
            fact_component = sum(check.score for check in fact_checks) / (len(fact_checks) * 1.1)
        else:
            fact_component = 0.6
        confidence = 0.6 * vote_component + 0.4 * fact_component
        return max(0.0, min(1.0, confidence))
