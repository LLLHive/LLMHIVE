import asyncio
from .base_protocol import BaseProtocol
from ..orchestration.execution import execute_task
from ..config import settings

class CritiqueAndImproveProtocol(BaseProtocol):
    async def execute(self) -> None:
        drafting_task = self.params['drafting_task']
        drafting_roles = self.params['drafting_roles']
        improving_role = self.params['improving_role']
        
        self.blackboard.append_to_list("logs.execution", "Starting Critique & Improve Protocol.")

        draft_coros = {
            role: execute_task(role, self.assignments[role], drafting_task, self.blackboard)
            for role in drafting_roles if role in self.assignments
        }
        draft_results = await asyncio.gather(*draft_coros.values())
        drafts = dict(zip(draft_coros.keys(), draft_results))
        
        critique_coros = {}
        for i, (role, draft) in enumerate(drafts.items()):
            critic_role = "critic"
            critic_model_id = self.assignments.get(critic_role, settings.CRITIQUE_MODEL)
            critique_task = f"Critique the following draft from the '{role}' agent:\n\n---\n{draft}\n---"
            critique_coros[f"critique_on_{role}"] = execute_task(critic_role, critic_model_id, critique_task, self.blackboard)
        
        critiques = dict(zip(critique_coros.keys(), await asyncio.gather(*critique_coros.values())))

        improvement_coros = {}
        for role, draft in drafts.items():
            feedback = critiques.get(f"critique_on_{role}", "No feedback received.")
            improvement_task = f"Based on the following critique, improve your original draft.\n\nCRITIQUE:\n{feedback}\n\nORIGINAL DRAFT:\n{draft}"
            improving_model_id = self.assignments.get(improving_role, settings.PLANNING_MODEL)
            improvement_coros[f"improved_{role}"] = execute_task(improving_role, improving_model_id, improvement_task, self.blackboard)
        
        improved_drafts = dict(zip(improvement_coros.keys(), await asyncio.gather(*improvement_coros.values())))
        
        self.blackboard.set("results.critique_workflow", {
            "drafts": drafts,
            "critiques": critiques,
            "improved_drafts": improved_drafts
        })
        self.blackboard.append_to_list("logs.execution", "Critique & Improve Protocol Complete.")