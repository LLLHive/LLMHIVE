from typing import Set, Dict, List, Optional
from ..models.model_pool import model_pool, ModelProfile
from ..config import settings

class Router:
    def __init__(self, preferred_models: Optional[List[str]] = None):
        self.preferred_models = preferred_models

    def assign_models_to_roles(self, required_roles: Set[str]) -> Dict[str, str]:
        assignments: Dict[str, str] = {}
        
        available_models = model_pool.list_models()
        if self.preferred_models:
            preferred_pool = [m for m in available_models if m.model_id in self.preferred_models]
            if preferred_pool:
                available_models = preferred_pool

        if not available_models:
            raise ValueError("ModelPool is empty or filtered to empty.")

        for role in required_roles:
            best_model = self._find_best_model_for_role(role, available_models)
            assignments[role] = best_model.model_id
        
        if "critic" in required_roles and "critic" not in assignments:
             assignments["critic"] = settings.CRITIQUE_MODEL
        
        return assignments

    def _find_best_model_for_role(self, role: str, models: List[ModelProfile]) -> ModelProfile:
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
            return sorted(models, key=lambda m: m.cost_per_token)[0]

        return sorted(candidates, key=lambda m: m.cost_per_token)[0]