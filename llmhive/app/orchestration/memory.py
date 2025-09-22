"""Persistent shared memory abstraction."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Dict, List

from typing import TYPE_CHECKING

from .equalizer import OrchestrationProfile

if TYPE_CHECKING:
    from .challenge import ChallengeFeedback
    from .consensus import ConsensusResult
    from .ensemble import EnsembleOutput
    from .factcheck import FactCheckResult
    from .prompt_opt import PromptPlan
    from .routing import ModelRoute
    from .voting import VoteSummary


@dataclass
class ModelScorecard:
    """Aggregated metrics for a particular model."""

    model_name: str
    tasks: int
    avg_quality: float
    avg_factuality: float
    avg_latency_ms: float
    avg_cost_usd: float


@dataclass
class InteractionRecord:
    query: str
    plan: PromptPlan
    routes: List[ModelRoute]
    outputs: List[EnsembleOutput]
    votes: VoteSummary
    challenges: List[ChallengeFeedback]
    fact_checks: List[FactCheckResult]
    consensus: ConsensusResult
    profile: OrchestrationProfile


class MemoryStore:
    """In-memory implementation used for local development and tests."""

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._interactions: List[InteractionRecord] = []
        self._scorecards: Dict[str, Dict[str, float]] = {}

    async def record_interaction(
        self,
        query: str,
        plan: PromptPlan,
        routes: List[ModelRoute],
        outputs: List[EnsembleOutput],
        votes: VoteSummary,
        challenges: List[ChallengeFeedback],
        fact_checks: List[FactCheckResult],
        consensus: ConsensusResult,
        profile: OrchestrationProfile,
    ) -> None:
        async with self._lock:
            self._interactions.append(
                InteractionRecord(
                    query=query,
                    plan=plan,
                    routes=routes,
                    outputs=outputs,
                    votes=votes,
                    challenges=challenges,
                    fact_checks=fact_checks,
                    consensus=consensus,
                    profile=profile,
                )
            )
            for output in outputs:
                metrics = self._scorecards.setdefault(
                    output.model_name,
                    {
                        "tasks": 0,
                        "quality": 0.0,
                        "factuality": 0.0,
                        "latency": 0.0,
                        "cost": 0.0,
                    },
                )
                metrics["tasks"] += 1
                metrics["quality"] += output.score_quality
                metrics["factuality"] += output.score_factuality
                metrics["latency"] += output.latency_ms
                metrics["cost"] += output.cost_usd

    def get_scorecards(self) -> List[ModelScorecard]:
        cards: List[ModelScorecard] = []
        for name, metrics in self._scorecards.items():
            tasks = max(1, int(metrics["tasks"]))
            cards.append(
                ModelScorecard(
                    model_name=name,
                    tasks=tasks,
                    avg_quality=metrics["quality"] / tasks,
                    avg_factuality=metrics["factuality"] / tasks,
                    avg_latency_ms=metrics["latency"] / tasks,
                    avg_cost_usd=metrics["cost"] / tasks,
                )
            )
        cards.sort(key=lambda c: c.avg_quality, reverse=True)
        return cards
