"""Utilities for profiling and selecting language models."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Sequence


@dataclass(frozen=True)
class ModelProfile:
    """Represents a deployable language model option."""

    name: str
    strengths: Sequence[str]
    cost: float
    latency: float


class ModelSelector:
    """Keeps track of available models and performs simple matching."""

    def __init__(self) -> None:
        self.models: List[ModelProfile] = []

    def add_model(self, profile: ModelProfile) -> None:
        """Register a new model profile."""

        if not isinstance(profile, ModelProfile):  # pragma: no cover - defensive branch
            raise TypeError("profile must be a ModelProfile instance")
        self.models.append(profile)

    def select_models(self, task_requirements: Iterable[str]) -> List[ModelProfile]:
        """Return models that advertise support for at least one requirement."""

        requirements = {req.lower() for req in task_requirements if req}
        if not requirements:
            return []

        scored_matches: List[tuple[int, ModelProfile]] = []
        for model in self.models:
            strengths = {strength.lower() for strength in model.strengths}
            overlap = strengths & requirements
            if overlap:
                scored_matches.append((len(overlap), model))

        scored_matches.sort(
            key=lambda item: (-item[0], item[1].cost, item[1].latency, item[1].name)
        )
        return [model for _, model in scored_matches]
