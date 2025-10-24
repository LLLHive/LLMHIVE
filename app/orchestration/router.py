"""
The Router component of the Orchestrator Engine.

Responsible for dynamic model selection ("Dream Team" assembly).
"""

from typing import List, Set
from ..models.model_pool import ModelPool, ModelProfile

class Router:
    """Selects the optimal set of LLMs for a given set of required roles."""
    def __init__(self):
        self.model_pool = ModelPool()

    def get_best_model_for_role(self, role: str) -> ModelProfile:
        """Finds the best model for a specific role based on strengths."""
        # More sophisticated logic could involve learned policies or cost-based optimization.
        role_preferences = {
            "planner": ["reasoning", "coding"],
            "researcher": ["long-context", "general"],
            "critic": ["reasoning", "analysis"],
            "editor": ["writing", "general"],
            "lead": ["reasoning", "general"],
            "analyst": ["analysis", "reasoning"],
        }
        
        candidates = self.model_pool.list_models()
        
        for strength in role_preferences.get(role, ["general"]):
            for model in candidates:
                if strength in model.strengths:
                    return model
        
        return candidates[0] # Fallback to the first model in the pool

    def select_models(self, required_roles: Set[str]) -> List[ModelProfile]:
        """Assembles the 'dream team' of models for the given plan."""
        dream_team = []
        assigned_models = set()

        for role in required_roles:
            model = self.get_best_model_for_role(role)
            # Avoid assigning the same model instance if we want diversity, but for now it's fine.
            model.role = role  # Assign the role for this context
            if model not in dream_team:
                 dream_team.append(model)
            assigned_models.add(model.model_id)

        # Ensure at least one model is selected
        if not dream_team:
            default_model = self.get_best_model_for_role("lead")
            default_model.role = "lead"
            dream_team.append(default_model)

        return dream_team
