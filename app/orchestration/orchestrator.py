"""
The Orchestrator Engine for LLMHive.

This is the "brain" of the platform, responsible for managing the entire
workflow from prompt analysis to final response synthesis. It coordinates
the various components like the Planner, Router, and Synthesizer.
"""
import asyncio
from typing import Dict, Any, AsyncGenerator

from .planner import Planner
from .router import Router
from .synthesizer import Synthesizer
from .blackboard import Blackboard
from ..memory.conversation_memory import ConversationMemory
from ..agents import Agent, ResearcherAgent, CriticAgent, EditorAgent, LeadAgent
from ..core.validators import Validator

class Orchestrator:
    """Orchestrates the multi-agent workflow."""
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.planner = Planner()
        self.router = Router()
        self.synthesizer = Synthesizer()
        self.memory = ConversationMemory(user_id)
        self.validator = Validator()

    def _get_agent_for_role(self, role: str, model_id: str) -> Agent:
        """Factory function to get an agent instance based on role."""
        role_map = {
            "researcher": ResearcherAgent, "critic": CriticAgent,
            "editor": EditorAgent, "lead": LeadAgent, "analyst": LeadAgent,
        }
        agent_class = role_map.get(role.lower())
        if not agent_class:
            raise ValueError(f"No agent class found for role: {role}")
        return agent_class(model_id=model_id)

    async def _execute_step(self, step: Dict[str, Any], blackboard: Blackboard, dream_team: list):
        """Executes a single agent task."""
        agent_role = step['role']
        task_prompt = step['task']
        output_key = step.get('output_key', f"results.{agent_role}")

        model_profile = next((m for m in dream_team if m.role == agent_role), dream_team[0])
        agent = self._get_agent_for_role(agent_role, model_profile.model_id)
        
        print(f"Executing: Role '{agent_role}' using model '{agent.model_id}'")
        
        context = blackboard.get_full_context()
        result = await agent.execute(task_prompt, context=context)
        
        if self.validator.check_content_policy(result):
            result = "[Content Redacted due to Policy Violation]"
            
        blackboard.set(output_key, result)

    async def run(self, prompt: str) -> AsyncGenerator[str, None]:
        """
        Executes the full orchestration pipeline and streams the final answer.
        """
        print(f"Orchestrator running for user '{self.user_id}' with prompt: '{prompt}'")
        
        blackboard = Blackboard(prompt)
        context_history = self.memory.retrieve_history()
        blackboard.set("history", context_history)

        plan = await self.planner.create_plan(prompt, context_history)
        print(f"Plan created with {len(plan.steps)} blocks. Reasoning: {plan.reasoning}")

        # Extract all required roles from the plan structure
        all_roles = set()
        for block in plan.steps:
            if 'steps' in block:
                for step in block['steps']:
                    if 'role' in step:
                        all_roles.add(step['role'])
        
        dream_team = self.router.select_models(all_roles)
        print(f"Dream team selected: {[(m.model_id, m.role) for m in dream_team]}")

        # Execute plan blocks
        for i, block in enumerate(plan.steps):
            print(f"Executing block {i+1}/{len(plan.steps)}: Type '{block['type']}'")
            if block['type'] == 'sequential':
                for step in block['steps']:
                    await self._execute_step(step, blackboard, dream_team)
            elif block['type'] == 'parallel':
                tasks = [self._execute_step(step, blackboard, dream_team) for step in block['steps']]
                await asyncio.gather(*tasks)

        # Iterative Refinement Example (Critic-Editor loop)
        critic_feedback = blackboard.get("results.critic")
        if critic_feedback:
            print("Critic feedback found. Starting refinement loop...")
            refinement_task = "Incorporate the following critic feedback into the draft answer and produce the final version."
            editor_agent = self._get_agent_for_role("editor", self.router.get_best_model_for_role("editor").model_id)
            final_draft = await editor_agent.execute(refinement_task, context=blackboard.get_full_context())
            blackboard.set("results.final_draft", final_draft)

        # Synthesize and stream the final answer
        final_answer_stream = self.synthesizer.synthesize_stream(blackboard, plan, prompt)
        
        final_answer_text = ""
        async for token in final_answer_stream:
            final_answer_text += token
            yield token
        
        print(f"Final Answer: {final_answer_text}")

        # Final validation and memory update
        if self.validator.check_for_pii(final_answer_text):
            yield "\n\n[Warning: This response may contain sensitive information.]"
        
        self.memory.store_interaction(prompt, final_answer_text)
