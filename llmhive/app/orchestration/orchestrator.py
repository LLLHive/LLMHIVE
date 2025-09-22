"""High level orchestration engine that coordinates all subsystems."""
from __future__ import annotations

from dataclasses import dataclass

from ..core.settings import settings
from ..utils.timing import StageTimer
from .challenge import ChallengeEngine, ChallengeFeedback
from .consensus import Citation, ConsensusBuilder, ConsensusResult
from .ensemble import EnsembleOutput, EnsembleRunner
from .equalizer import Equalizer, OrchestrationProfile
from .factcheck import FactCheckEngine, FactCheckResult
from .memory import MemoryStore
from .prompt_opt import PromptOptimizer, PromptPlan
from .routing import ModelRoute, Router
from .voting import VoteSummary, VotingEngine


@dataclass
class OrchestrationOptions:
    """User controllable sliders and generation flags."""

    accuracy: float
    speed: float
    creativity: float
    cost: float
    max_tokens: int
    json_mode: bool = False


@dataclass
class OrchestrationResult:
    """Final result returned to API layer."""

    final_answer: str
    confidence: float
    key_points: list[str]
    citations: list[Citation]
    costs: dict[str, float]
    timings: dict[str, float]


class Orchestrator:
    """Main facade orchestrating all reasoning subsystems."""

    def __init__(
        self,
        memory: MemoryStore | None = None,
        prompt_optimizer: PromptOptimizer | None = None,
        router: Router | None = None,
        ensemble: EnsembleRunner | None = None,
        voting: VotingEngine | None = None,
        challenge: ChallengeEngine | None = None,
        factcheck: FactCheckEngine | None = None,
        consensus: ConsensusBuilder | None = None,
        equalizer: Equalizer | None = None,
    ) -> None:
        self.memory = memory or MemoryStore()
        self.prompt_optimizer = prompt_optimizer or PromptOptimizer()
        self.router = router or Router(self.memory)
        self.ensemble = ensemble or EnsembleRunner()
        self.voting = voting or VotingEngine()
        self.challenge = challenge or ChallengeEngine()
        self.factcheck = factcheck or FactCheckEngine()
        self.consensus = consensus or ConsensusBuilder()
        self.equalizer = equalizer or Equalizer()

    async def run(self, query: str, options: OrchestrationOptions) -> OrchestrationResult:
        """Execute the orchestrated multi-model workflow."""

        timer = StageTimer()
        timings: dict[str, float] = {}
        costs: dict[str, float] = {"usd": 0.0, "tokens": 0.0}

        profile: OrchestrationProfile = self.equalizer.map_options(options)

        with timer.measure("prompt_optimization"):
            plan: PromptPlan = self.prompt_optimizer.optimize(query, profile)
        timings.update(timer.snapshot())

        with timer.measure("routing"):
            routes: list[ModelRoute] = self.router.select_models(plan, profile)
        timings.update(timer.snapshot())

        with timer.measure("ensemble"):
            outputs: list[EnsembleOutput] = await self.ensemble.run(plan, routes, profile)
        timings.update(timer.snapshot())

        for output in outputs:
            costs["usd"] += output.cost_usd
            costs["tokens"] += output.tokens

        with timer.measure("voting"):
            vote_summary: VoteSummary = self.voting.score(outputs, routes, profile)
        timings.update(timer.snapshot())

        challenge_feedback: list[ChallengeFeedback] = []
        if settings.enable_debate and profile.challenge_rounds > 0:
            with timer.measure("challenge"):
                challenge_feedback = await self.challenge.run(outputs, plan, profile)
            timings.update(timer.snapshot())

        factcheck_results: list[FactCheckResult] = []
        if settings.enable_factcheck and profile.factcheck_enabled:
            with timer.measure("factcheck"):
                factcheck_results = await self.factcheck.verify(outputs, plan, profile)
            timings.update(timer.snapshot())

        with timer.measure("consensus"):
            consensus: ConsensusResult = self.consensus.build(
                query=query,
                plan=plan,
                outputs=outputs,
                votes=vote_summary,
                challenges=challenge_feedback,
                fact_checks=factcheck_results,
                profile=profile,
            )
        timings.update(timer.snapshot())

        await self.memory.record_interaction(
            query=query,
            plan=plan,
            routes=routes,
            outputs=outputs,
            votes=vote_summary,
            challenges=challenge_feedback,
            fact_checks=factcheck_results,
            consensus=consensus,
            profile=profile,
        )

        timings["total"] = sum(timings.values())

        result = OrchestrationResult(
            final_answer=consensus.final_answer,
            confidence=consensus.confidence,
            key_points=consensus.key_points,
            citations=consensus.citations,
            costs=costs,
            timings=timings,
        )
        return result
