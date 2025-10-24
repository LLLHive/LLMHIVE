"""Manages LLM profiling and dynamic model selection."""

from typing import List, Dict


class ModelProfile:
    """Represents the capabilities and attributes of an LLM."""

    def __init__(self, name: str, strengths: List[str], cost: float, latency: float):
        self.name = name
        self.strengths = strengths
        self.cost = cost
        self.latency = latency


class ModelSelector:
    """Handles dynamic selection of models for tasks."""

    def __init__(self):
        self.models = []

    def add_model(self, profile: ModelProfile):
        """Add a new model profile."""
        self.models.append(profile)

    def select_models(self, task_requirements: List[str]) -> List[ModelProfile]:
        """Select the best models based on task requirements."""
        selected_models = []
        for model in self.models:
            if any(req in model.strengths for req in task_requirements):
                selected_models.append(model)
        return selected_models
