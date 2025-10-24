"""
The Router component of the Orchestrator Engine.

Responsible for dynamic model selection. Based on the execution plan,
it assembles a "dream team" of LLMs, choosing the best model for each
sub-task by leveraging their known strengths and capabilities.
"""

from typing import List
from .planner import Plan
from ..models.model_pool import ModelPool, ModelProfile

class Router:
    """
    Selects the optimal set of LLMs for a given plan.
    """
    def __init__(self):
        self.model_pool = ModelPool()

    def select_models(self, plan: Plan) -> List[ModelProfile]:
        """
        Assembles the "dream team" of models for the given plan.

        This is a stub implementation. A real router would use a sophisticated
        strategy, possibly involving a classifier model or learned policy,
        to match task requirements with model profiles (cost, speed, expertise).
        """
        print("Selecting dream team...")
        dream_team = []
        required_roles = {step['role'] for step in plan.steps}

        # Simple logic: try to find a model for each required role
        for role in required_roles:
            # Find the best model for this role (e.g., based on hard-coded preferences)
            if role == "critic" or role == "analyst":
                model = self.model_pool.get_model_by_id("gpt-4")
            elif role == "researcher":
                model = self.model_pool.get_model_by_id("claude-3-opus") # Good with long context
            else: # lead, editor, etc.
                model = self.model_pool.get_model_by_id("gemini-pro")

            if model:
                model.role = role # Assign the role for this context
                if model not in dream_team:
                    dream_team.append(model)

        # Ensure at least one model is selected
        if not dream_team:
            dream_team.append(self.model_pool.get_model_by_id("gpt-4"))

        return dream_team
