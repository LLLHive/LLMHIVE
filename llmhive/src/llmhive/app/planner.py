"""Heuristic reasoning planner for LLMHive orchestrator."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Iterable, List, Sequence, Set


class PlanRole(str, Enum):
    """Enumerates the high-level roles supported by the orchestrator."""

    DRAFT = "draft"
    RESEARCH = "research"
    FACT_CHECK = "fact_check"
    CRITIQUE = "critique"
    SYNTHESIZE = "synthesize"
    RETRIEVAL = "retrieval"


@dataclass(slots=True)
class PlanStep:
    """Represents a single stage in the reasoning plan."""

    role: PlanRole
    description: str
    required_capabilities: Set[str] = field(default_factory=set)
    candidate_models: Sequence[str] = field(default_factory=list)
    parallelizable: bool = True


@dataclass(slots=True)
class ReasoningPlan:
    """Structured reasoning plan produced for a prompt."""

    strategy: str
    steps: List[PlanStep]
    confidence: float
    focus_areas: Sequence[str] = field(default_factory=list)
    context_summary: str | None = None

    def model_hints(self) -> List[str]:
        """Return flattened list of model hints gathered from steps."""

        hints: List[str] = []
        for step in self.steps:
            hints.extend(step.candidate_models)
        return hints


class ReasoningPlanner:
    """Derives a hierarchical, role-aware plan for a given prompt."""

    def create_plan(self, prompt: str, *, context: str | None = None) -> ReasoningPlan:
        lowered = prompt.lower()
        focus: List[str] = []
        steps: List[PlanStep] = []

        if any(keyword in lowered for keyword in ("debug", "code", "stack trace", "exception")):
            focus.append("coding")
            steps.extend(
                [
                    PlanStep(
                        role=PlanRole.DRAFT,
                        description="Generate an initial diagnostic or solution proposal for the coding issue.",
                        required_capabilities={"coding", "analysis"},
                        candidate_models=["gpt-4.1", "gpt-4o", "deepseek-reasoner"],
                    ),
                    PlanStep(
                        role=PlanRole.FACT_CHECK,
                        description="Validate code snippets or calculations and ensure reproducibility.",
                        required_capabilities={"code_execution", "validation"},
                        candidate_models=["gpt-4o-mini", "deepseek-chat"],
                    ),
                ]
            )
        elif any(keyword in lowered for keyword in ("research", "analysis", "compare", "impact")):
            focus.append("research")
            steps.extend(
                [
                    PlanStep(
                        role=PlanRole.RESEARCH,
                        description="Gather supporting evidence, statistics, or references relevant to the topic.",
                        required_capabilities={"retrieval", "analysis"},
                        candidate_models=["gemini-1.5-pro", "claude-3-sonnet-20240229"],
                    ),
                    PlanStep(
                        role=PlanRole.DRAFT,
                        description="Compose a comprehensive answer that integrates retrieved context.",
                        required_capabilities={"reasoning", "long_context"},
                        candidate_models=["claude-3-opus-20240229", "gpt-4.1"],
                    ),
                ]
            )
        elif any(keyword in lowered for keyword in ("summarize", "summary", "synthesize")):
            focus.append("summarization")
            steps.extend(
                [
                    PlanStep(
                        role=PlanRole.DRAFT,
                        description="Produce an initial structured summary covering the key points.",
                        required_capabilities={"summarization"},
                        candidate_models=["claude-3-haiku-20240307", "gpt-4o-mini"],
                    ),
                    PlanStep(
                        role=PlanRole.CRITIQUE,
                        description="Critique the summary for missing context or unclear structure.",
                        required_capabilities={"critical_thinking"},
                        candidate_models=["grok-1", "deepseek-chat"],
                    ),
                ]
            )
        else:
            focus.append("general_reasoning")
            steps.append(
                PlanStep(
                    role=PlanRole.DRAFT,
                    description="Generate a high-quality first draft response.",
                    required_capabilities={"reasoning"},
                    candidate_models=["gpt-4o", "claude-3-sonnet-20240229"],
                )
            )

        # Always include cross-critique and synthesis phases to align with hive workflow
        steps.append(
            PlanStep(
                role=PlanRole.CRITIQUE,
                description="Cross-review answers to surface disagreements or factual gaps.",
                required_capabilities={"critical_thinking", "fact_checking"},
                candidate_models=["grok-1", "deepseek-reasoner", "gpt-4o-mini"],
            )
        )
        steps.append(
            PlanStep(
                role=PlanRole.SYNTHESIZE,
                description="Merge improved answers into a unified, polished response with citations or caveats as needed.",
                required_capabilities={"synthesis", "editing"},
                candidate_models=["gpt-4.1", "claude-3-opus-20240229"],
                parallelizable=False,
            )
        )

        strategy = "hierarchical_plan_with_iterative_refinement"
        confidence = 0.75 if len(focus) > 1 else 0.65

        if context:
            focus.append("contextual_memory")

        return ReasoningPlan(
            strategy=strategy,
            steps=steps,
            confidence=confidence,
            focus_areas=focus,
            context_summary=context,
        )
