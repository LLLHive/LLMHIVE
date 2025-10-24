"""
The Orchestrator Engine for LLMHive.

This is the "brain" of the platform, responsible for managing the entire
workflow from prompt analysis to final response synthesis. It coordinates
the various components like the Planner, Router, and Synthesizer.
"""
import asyncio
from typing import Dict

from .planner import Planner, Plan
from .router import Router
from .synthesizer import Synthesizer
from ..memory.conversation_memory import ConversationMemory
from ..agents import (
    Agent, ResearcherAgent, CriticAgent, EditorAgent, LeadAgent
)
from ..core.validators import Validator


class Orchestrator:
    """
    Orchestrates the multi-agent workflow.
    """
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.planner = Planner()
        self.router = Router()
        self.synthesizer = Synthesizer()
        self.memory = ConversationMemory(user_id)
        self.validator = Validator()

    def _get_agent_for_role(self, role: str, model_id: str) -> Agent:
        """Factory function to get an agent instance based on role.
        
        Note: LeadAgent is used for 'analyst' role as it's suitable for 
        general-purpose analysis tasks that require comprehensive reasoning.
        """
        role_map = {
            "researcher": ResearcherAgent,
            "critic": CriticAgent,
            "editor": EditorAgent,
            "lead": LeadAgent,
            "analyst": LeadAgent,  # LeadAgent handles general-purpose analysis
        }
        agent_class = role_map.get(role.lower())
        if not agent_class:
            raise ValueError(f"No agent class found for role: {role}")
        return agent_class(model_id=model_id)

    async def run(self, prompt: str) -> str:
        """
        Executes the full orchestration pipeline for a given prompt.
        """
        print(f"Orchestrator running for user '{self.user_id}' with prompt: '{prompt}'")

        # 1. Get context from memory
        context_history = self.memory.retrieve_history()

        # 2. Analyze prompt and create a plan
        plan = self.planner.create_plan(prompt, context_history)
        print(f"Plan created with {len(plan.steps)} steps.")

        # 3. Select models based on the plan
        dream_team = self.router.select_models(plan)
        print(f"Dream team selected: {[model.model_id for model in dream_team]}")

        # 4. Execute the plan
        partial_results: Dict[str, str] = {}
        shared_context = f"Original Prompt: {prompt}\n\nConversation History:\n{''.join(context_history)}"

        # Sequentially execute steps to allow building on previous results
        for i, step in enumerate(plan.steps):
            agent_role = step['role']
            task_prompt = step['task']

            # Find the model assigned to this role, or use the first in the team as fallback
            model_profile = next((m for m in dream_team if m.role == agent_role), dream_team[0])
            agent = self._get_agent_for_role(agent_role, model_profile.model_id)
            
            print(f"Executing step {i+1}/{len(plan.steps)}: Role '{agent_role}' using model '{agent.model_id}'")

            # The agent receives the specific task and the shared context (including previous results)
            result = await agent.execute(task_prompt, context=shared_context)

            # Validate the intermediate result
            if self.validator.check_content_policy(result):
                result = "[Content Redacted due to Policy Violation]"

            partial_results[agent_role] = result
            # Update shared context for the next agent
            shared_context += f"\n\n--- Result from {agent_role} ---\n{result}"

        # 5. Synthesize the final answer using an LLM
        final_answer = await self.synthesizer.synthesize(partial_results, plan, prompt)
        print(f"Synthesized answer: {final_answer}")

        # 6. Final validation
        if self.validator.check_for_pii(final_answer):
            final_answer += "\n\n[Warning: This response may contain sensitive information.]"

        # 7. Store interaction in memory
        self.memory.store_interaction(prompt, final_answer)

        return final_answer
