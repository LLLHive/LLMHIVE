"""
The LLM Pool (Model Hub).

This module manages the collection of all accessible LLM models. It maintains
a profile for each model, detailing its capabilities, strengths, cost, and
other attributes. The Orchestrator uses this information for dynamic model
selection.
"""

import yaml
from pydantic import BaseModel
from typing import List, Optional, Dict
from ..config import settings

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
    """Manages the catalog of available LLMs, loaded from a config file."""
    def __init__(self, config_path: str = settings.MODEL_CONFIG_PATH):
        self._models: Dict[str, ModelProfile] = self._load_models_from_config(config_path)
        print(f"ModelPool loaded with {len(self._models)} models: {list(self._models.keys())}")

    def _load_models_from_config(self, path: str) -> Dict[str, ModelProfile]:
        try:
            with open(path, 'r') as f:
                config = yaml.safe_load(f)
            models = [ModelProfile(**m) for m in config.get('models', [])]
            return {model.model_id: model for model in models}
        except FileNotFoundError:
            print(f"Warning: Model config file not found at '{path}'. No models loaded.")
            return {}
        except Exception as e:
            print(f"Error loading model config: {e}")
            return {}

    def get_model_profile(self, model_id: str) -> Optional[ModelProfile]:
        """Retrieves a model profile by its ID."""
        return self._models.get(model_id)

    def list_models(self) -> List[ModelProfile]:
        """Returns a list of all available model profiles."""
        return list(self._models.values())

    def get_model_by_id(self, model_id: str) -> Optional[ModelProfile]:
        """Retrieves a model profile by its ID. (Compatibility alias)"""
        return self.get_model_profile(model_id)

# Singleton instance
model_pool = ModelPool()
