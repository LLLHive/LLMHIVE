"""
The Orchestrator Engine for LLMHive.

This is the "brain" of the platform, responsible for managing the entire
workflow from prompt analysis to final response synthesis. It coordinates
the various components like the Planner, Router, and Synthesizer.
"""
import asyncio
from typing import Dict, Any, AsyncGenerator, List, Set

from .planner import Planner
from .router import Router
from .synthesizer import Synthesizer
from .blackboard import Blackboard
from ..memory.conversation_memory import ConversationMemory
from ..agents import Agent, ResearcherAgent, CriticAgent, EditorAgent, LeadAgent
from ..core.validators import Validator
from ..config import settings

class Orchestrator:
    """Orchestrates the multi-agent workflow."""
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.planner = Planner()
        self.router = Router()
        self.synthesizer = Synthesizer()
        self.memory = ConversationMemory(user_id)
        self.validator = Validator()

    def _get_agent(self, role: str, model_id: str) -> Agent:
        """Factory function to get an agent instance based on role."""
        role_map = {
            "researcher": ResearcherAgent, "critic": CriticAgent,
            "editor": EditorAgent, "lead": LeadAgent, "analyst": LeadAgent,
        }
        agent_class = role_map.get(role.lower())
        if not agent_class:
            raise ValueError(f"Agent role '{role}' not supported.")
        return agent_class(model_id=model_id)

    async def _execute_task(self, role: str, model_id: str, task: str, blackboard: Blackboard) -> str:
        """Executes a single, robust agent task."""
        context = blackboard.get_full_context()
        try:
            agent = self._get_agent(role, model_id)
            result = await agent.execute(task, context=context)
            if self.validator.check_content_policy(result):
                result = "[Content Redacted due to Policy Violation]"
            blackboard.append_to_list("logs.execution", f"SUCCESS: Role '{role}' on model '{model_id}' completed task.")
            return result
        except Exception as e:
            error_msg = f"FAILURE: Role '{role}' on model '{model_id}' failed. Error: {e}"
            print(f"ERROR: {error_msg}")
            blackboard.append_to_list("logs.errors", error_msg)
            return f"Agent {role} failed to execute."

    async def _execute_critique_and_improve(self, block: Dict[str, Any], blackboard: Blackboard, dream_team: Dict[str, str]):
        """Executes the high-accuracy critique and improve workflow."""
        drafting_task = block['drafting_task']
        drafting_roles = block['drafting_roles']
        critic_model = block['critic_role']
        improving_role = block['improving_role']
        
        print("\n--- Starting Critique & Improve Workflow ---")
        # 1. Parallel Drafting
        draft_coros = {role: self._execute_task(role, dream_team[role], drafting_task, blackboard) for role in drafting_roles}
        drafts = dict(zip(drafting_roles, await asyncio.gather(*draft_coros.values())))
        
        # 2. Cross-Critique
        critique_coros = {}
        for i, (role, draft) in enumerate(drafts.items()):
            critic_task = f"Critique the following draft from the '{role}' agent:\n\n---\n{draft}\n---"
            critique_coros[f"critique_on_{role}"] = self._execute_task("critic", critic_model, critic_task, blackboard)
        critiques = dict(zip(critique_coros.keys(), await asyncio.gather(*critique_coros.values())))

        # 3. Improvement
        improvement_coros = {}
        for role, draft in drafts.items():
            feedback = critiques.get(f"critique_on_{role}", "No feedback.")
            improvement_task = f"Based on the following critique, improve your original draft.\n\nCRITIQUE:\n{feedback}\n\nORIGINAL DRAFT:\n{draft}"
            improvement_coros[f"improved_{role}"] = self._execute_task(improving_role, dream_team[improving_role], improvement_task, blackboard)
        
        improved_drafts = dict(zip(improvement_coros.keys(), await asyncio.gather(*improvement_coros.values())))
        blackboard.set("results.critique_workflow", {"drafts": drafts, "critiques": critiques, "improved_drafts": improved_drafts})
        print("--- Critique & Improve Workflow Complete ---\n")

    async def run(self, prompt: str) -> AsyncGenerator[str, None]:
        """
        Executes the full orchestration pipeline and streams the final answer.
        """
        print(f"Orchestrator running for user '{self.user_id}' with prompt: '{prompt}'")
        
        blackboard = Blackboard(prompt)
        blackboard.set("history", "\n".join(self.memory.retrieve_history()))

        plan = await self.planner.create_plan(blackboard)
        
        all_roles = self._extract_roles_from_plan(plan.steps)
        dream_team_assignments = self.router.assign_models_to_roles(all_roles)
        blackboard.set("plan.assignments", dream_team_assignments)
        
        for block in plan.steps:
            if block["type"] == "simple":
                result = await self._execute_task(block['role'], dream_team_assignments[block['role']], block['task'], blackboard)
                blackboard.set(f"results.{block['role']}", result)
            elif block["type"] == "critique_and_improve":
                await self._execute_critique_and_improve(block, blackboard, dream_team_assignments)

        final_answer_text = ""
        async for token in self.synthesizer.synthesize_stream(blackboard):
            final_answer_text += token
            yield token
        
        self.memory.store_interaction(prompt, final_answer_text)

    def _extract_roles_from_plan(self, steps: List[Dict]) -> Set[str]:
        """Extract all unique roles from the plan steps."""
        roles = set()
        for block in steps:
            if block['type'] == 'simple': 
                roles.add(block['role'])
            elif block['type'] == 'critique_and_improve':
                roles.update(block['drafting_roles'])
                roles.add(block['improving_role'])
                roles.add("critic")
        return roles
