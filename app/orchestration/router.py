"""
The Router component of the Orchestrator Engine.

Responsible for dynamic model selection ("Dream Team" assembly).
"""

from typing import Set, Dict, List
from ..models.model_pool import model_pool, ModelProfile

class Router:
    """Selects the optimal set of LLMs for a given set of required roles."""
    def __init__(self):
        pass

    def assign_models_to_roles(self, required_roles: Set[str]) -> Dict[str, str]:
        """Assigns the best available model for each required role."""
        assignments: Dict[str, str] = {}
        all_models = model_pool.list_models()
        if not all_models:
            raise ValueError("ModelPool is empty. Cannot make assignments.")

        for role in required_roles:
            # Find the best model for this role based on strengths
            # This logic can be enhanced with cost-analysis, latency, etc.
            best_model = self._find_best_model_for_role(role, all_models)
            assignments[role] = best_model.model_id
        
        print(f"Router assignments: {assignments}")
        return assignments

    def _find_best_model_for_role(self, role: str, models: List[ModelProfile]) -> ModelProfile:
        """Finds the best model for a role, sorted by cost as a tie-breaker."""
        role_preferences = {
            "planner": ["reasoning"], "researcher": ["long-context"],
            "critic": ["reasoning", "analysis"], "editor": ["writing"],
            "lead": ["general", "reasoning"], "analyst": ["analysis"],
        }.get(role, ["general"])

        candidates = []
        for strength in role_preferences:
            for model in models:
                if strength in model.strengths:
                    candidates.append(model)
        
        if not candidates:
            # Fallback: sort all models by cost and pick the cheapest general one
            return sorted(models, key=lambda m: m.cost_per_token)[0]

        # Sort candidates by cost and return the cheapest one that fits
        return sorted(candidates, key=lambda m: m.cost_per_token)[0]

    def get_best_model_for_role(self, role: str) -> ModelProfile:
        """Finds the best model for a specific role based on strengths. (Compatibility method)"""
        all_models = model_pool.list_models()
        if not all_models:
            raise ValueError("ModelPool is empty. Cannot find model for role.")
        return self._find_best_model_for_role(role, all_models)

    def select_models(self, required_roles: Set[str]) -> List[ModelProfile]:
        """Assembles the 'dream team' of models for the given plan. (Compatibility method)"""
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
