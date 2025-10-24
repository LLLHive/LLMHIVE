"""
The LLM Pool (Model Hub).

This module manages the collection of all accessible LLM models. It maintains
a profile for each model, detailing its capabilities, strengths, cost, and
other attributes. The Orchestrator uses this information for dynamic model
selection.
"""

from pydantic import BaseModel
from typing import List, Optional

class ModelProfile(BaseModel):
    """
    Defines the profile for an LLM, including its capabilities.
    """
    model_id: str
    provider: str
    strengths: List[str]
    context_window: int
    cost_per_token: float
    role: Optional[str] = None # Role assigned for a specific task

class ModelPool:
    """
    Manages the catalog of available LLMs.
    """
    def __init__(self):
        # This catalog would ideally be loaded from a config file or database.
        # Currently only OpenAI and Anthropic providers are fully implemented.
        self._models = [
            ModelProfile(
                model_id="gpt-4", provider="openai",
                strengths=["reasoning", "coding", "general"],
                context_window=8192, cost_per_token=0.03
            ),
            ModelProfile(
                model_id="gpt-4-turbo", provider="openai",
                strengths=["reasoning", "coding", "general", "long-context"],
                context_window=128000, cost_per_token=0.01
            ),
            ModelProfile(
                model_id="claude-3-opus", provider="anthropic",
                strengths=["writing", "long-context", "analysis"],
                context_window=200000, cost_per_token=0.02
            ),
            ModelProfile(
                model_id="claude-3-sonnet", provider="anthropic",
                strengths=["writing", "analysis", "general"],
                context_window=200000, cost_per_token=0.01
            ),
        ]
        self._model_map = {model.model_id: model for model in self._models}

    def list_models(self) -> List[ModelProfile]:
        """Returns a list of all available models."""
        return self._models

    def get_model_by_id(self, model_id: str) -> Optional[ModelProfile]:
        """Retrieves a model profile by its ID."""
        return self._model_map.get(model_id)
