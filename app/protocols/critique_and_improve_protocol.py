"""
Critique and Improve Protocol: A high-accuracy workflow involving drafts,
cross-critique, and iterative improvement.
"""
import asyncio
from .base_protocol import BaseProtocol
from ..orchestration.execution import execute_task
from ..config import settings

class CritiqueAndImproveProtocol(BaseProtocol):
    """
    Implements the high-accuracy workflow:
    1. Parallel Drafting
    2. Cross-Critique
    3. Improvement
    """
    async def execute(self) -> None:
        drafting_task = self.params['drafting_task']
        drafting_roles = self.params['drafting_roles']
        improving_role = self.params['improving_role']
        
        print("\n--- Executing Critique & Improve Protocol ---")
        self.blackboard.append_to_list("logs.execution", "Starting Critique & Improve Protocol.")

        # 1. Parallel Drafting
        draft_coros = {
            role: execute_task(role, self.assignments[role], drafting_task, self.blackboard)
            for role in drafting_roles if role in self.assignments
        }
        draft_results = await asyncio.gather(*draft_coros.values())
        drafts = dict(zip(draft_coros.keys(), draft_results))
        
        # 2. Cross-Critique
        critique_coros = {}
        for i, (role, draft) in enumerate(drafts.items()):
            critic_role = "critic"
            critic_model_id = self.assignments[critic_role]
            critique_task = f"Critique the following draft from the '{role}' agent:\n\n---\n{draft}\n---"
            critique_coros[f"critique_on_{role}"] = execute_task(critic_role, critic_model_id, critique_task, self.blackboard)
        
        critiques = dict(zip(critique_coros.keys(), await asyncio.gather(*critique_coros.values())))

        # 3. Improvement
        improvement_coros = {}
        for role, draft in drafts.items():
            feedback = critiques.get(f"critique_on_{role}", "No feedback received.")
            improvement_task = f"Based on the following critique, improve your original draft.\n\nCRITIQUE:\n{feedback}\n\nORIGINAL DRAFT:\n{draft}"
            improving_model_id = self.assignments[improving_role]
            improvement_coros[f"improved_{role}"] = execute_task(improving_role, improving_model_id, improvement_task, self.blackboard)
        
        improved_drafts = dict(zip(improvement_coros.keys(), await asyncio.gather(*improvement_coros.values())))
        
        # Store all intermediate steps on the blackboard for synthesis
        self.blackboard.set("results.critique_workflow", {
            "drafts": drafts,
            "critiques": critiques,
            "improved_drafts": improved_drafts
        })
        self.blackboard.append_to_list("logs.execution", "Critique & Improve Protocol Complete.")
        print("--- Critique & Improve Protocol Complete ---\n")
