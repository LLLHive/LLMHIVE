"""Voting and aggregation logic for ensemble outputs."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from .ensemble import EnsembleOutput
from .equalizer import OrchestrationProfile
from .routing import ModelRoute


@dataclass
class VoteSummary:
    """Summarized voting outcome."""

    winner: EnsembleOutput
    scores: Dict[str, float]
    total_weight: float
    ranked_outputs: List[EnsembleOutput]


class VotingEngine:
    """Implements weighted majority voting for model outputs."""

    def score(
        self,
        outputs: List[EnsembleOutput],
        routes: List[ModelRoute],
        profile: OrchestrationProfile,
    ) -> VoteSummary:
        """Compute a weighted vote across ensemble outputs."""

        if not outputs:
            raise ValueError("No outputs provided for voting")

        route_lookup = {route.name: route for route in routes}
        scores: Dict[str, float] = {}
        for output in outputs:
            route = route_lookup.get(output.model_name)
            route_weight = route.weight if route else 0.3
            vote_weight = output.score_quality * 0.7 + output.score_factuality * 0.3
            vote_weight *= route_weight
            if profile.json_mode:
                vote_weight *= 0.95
            scores[output.model_name] = scores.get(output.model_name, 0.0) + vote_weight

        ranked = sorted(outputs, key=lambda o: scores.get(o.model_name, 0.0), reverse=True)
        winner = ranked[0]
        total = sum(scores.values()) or 1.0
        return VoteSummary(winner=winner, scores=scores, total_weight=total, ranked_outputs=ranked)
