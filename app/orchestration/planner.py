"""
The LLM-Powered Planner for LLMHive.

This component uses a high-capability LLM to perform hierarchical task
decomposition, creating a dynamic, structured execution plan in JSON format.
"""

import json
from typing import List, Dict
from pydantic import BaseModel, Field, ValidationError
from ..agents import LeadAgent
from ..config import settings
from .blackboard import Blackboard

class Plan(BaseModel):
    """Represents a structured execution plan."""
    reasoning: str
    steps: List[Dict]

class Planner:
    """
    Analyzes prompts using an LLM to create dynamic execution plans.
    """
    def __init__(self):
        # Use a powerful model for planning
        self.planner_agent = LeadAgent(model_id=settings.PLANNING_MODEL)

    async def create_plan(self, blackboard: Blackboard) -> Plan:
        """
        Creates a structured plan using an LLM to address the user's prompt.
        """
        prompt = blackboard.get("original_prompt")
        print(f"Creating LLM-driven plan for prompt: '{prompt}'")
        
        planning_prompt = self._build_planning_prompt(prompt)
        
        for attempt in range(2): # Allow for one self-correction attempt
            raw_response = await self.planner_agent.execute(planning_prompt)
            
            try:
                plan_json_str = raw_response[raw_response.find('{'):raw_response.rfind('}')+1]
                plan_data = json.loads(plan_json_str)
                validated_plan = Plan(**plan_data)
                blackboard.set("plan.raw", plan_data)
                blackboard.set("plan.reasoning", validated_plan.reasoning)
                return validated_plan
            except (json.JSONDecodeError, ValidationError) as e:
                error_msg = f"Plan validation failed on attempt {attempt + 1}: {e}. Raw response: {raw_response}"
                print(f"WARNING: {error_msg}")
                blackboard.append_to_list("logs.errors", error_msg)
                planning_prompt = f"The previous plan you generated was invalid. Error: {e}. Please regenerate a valid JSON plan based on the original request. User Prompt: '{prompt}'"
        
        print("ERROR: Failed to generate a valid plan after self-correction. Falling back to default.")
        return self.fallback_plan(prompt)

    def fallback_plan(self, prompt: str) -> Plan:
        """A simple rule-based fallback plan."""
        return Plan(reasoning="Fell back to default plan.", steps=[{"type": "simple", "role": "lead", "task": f"Provide a direct and comprehensive answer to: {prompt}"}])

    def _build_planning_prompt(self, prompt: str) -> str:
        return f"""
You are an expert AI orchestrator creating a JSON execution plan for a team of AI agents.

Available Agent Roles:
- lead: General-purpose agent for drafting and analysis.
- researcher: Agent with web search to find facts.
- critic: Agent that reviews another agent's work.
- editor: Agent that polishes final text.

Available Plan Types:
1. `simple`: A single agent performs a single task.
   `{{"type": "simple", "role": "lead", "task": "..."}}`
2. `critique_and_improve`: Generate parallel drafts, have them critique each other, then improve based on feedback. This is for maximum accuracy on complex, subjective, or creative tasks.
   `{{"type": "critique_and_improve", "drafting_task": "...", "drafting_roles": ["lead", "analyst"], "critic_role": "{settings.CRITIQUE_MODEL}", "improving_role": "lead"}}`

Based on the user's prompt, create the optimal plan. Prioritize `critique_and_improve` for complex, high-stakes queries. Your output MUST be a single, valid JSON object.

User's Prompt: "{prompt}"

JSON Plan:
"""
