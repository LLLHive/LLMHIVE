"""
The LLM-Powered Planner for LLMHive.

Selects the optimal Thinking Protocol to handle the user's query.
"""

import json
from typing import Dict, Any, Optional
from pydantic import BaseModel, ValidationError
from ..agents import LeadAgent
from ..config import settings

class Plan(BaseModel):
    reasoning: str
    protocol: str  # The name of the protocol to use (e.g., 'simple', 'critique_and_improve')
    params: Dict[str, Any] = {} # Parameters for the chosen protocol

class Planner:
    """
    Analyzes prompts using an LLM to create dynamic execution plans.
    """
    def __init__(self, preferred_protocol: Optional[str] = None):
        # Use a powerful model for planning
        self.planner_agent = LeadAgent(model_id=settings.PLANNING_MODEL)
        self.preferred_protocol = preferred_protocol

    async def create_plan(self, prompt: str) -> Plan:
        """
        Creates a structured plan using an LLM to address the user's prompt.
        """
        if self.preferred_protocol:
            print(f"User specified preferred protocol: '{self.preferred_protocol}'. Bypassing planner LLM.")
            return Plan(
                reasoning=f"Using user-specified protocol '{self.preferred_protocol}'.",
                protocol=self.preferred_protocol,
                params={"task": prompt, "drafting_task": prompt, "drafting_roles": ["lead", "analyst"], "improving_role": "lead"}
            )

        print(f"Creating LLM-driven plan for prompt: '{prompt}'")
        
        planning_prompt = self._build_planning_prompt(prompt)
        
        for attempt in range(2): # Allow for one self-correction attempt
            raw_response = await self.planner_agent.execute(planning_prompt)
            
            try:
                plan_json_str = raw_response[raw_response.find('{'):raw_response.rfind('}')+1]
                plan_data = json.loads(plan_json_str)
                validated_plan = Plan(**plan_data)
                return validated_plan
            except (json.JSONDecodeError, ValidationError) as e:
                error_msg = f"Plan validation failed on attempt {attempt + 1}: {e}."
                print(f"WARNING: {error_msg}")
                planning_prompt = f"The previous plan was invalid. Error: {e}. Please regenerate a valid JSON plan. User Prompt: '{prompt}'"
        
        print("ERROR: Failed to generate a valid plan. Falling back to default.")
        return self.fallback_plan(prompt)

    def fallback_plan(self, prompt: str) -> Plan:
        """A simple rule-based fallback plan."""
        return Plan(reasoning="Fell back to default plan.", protocol="simple", params={"role": "lead", "task": f"Provide a direct answer to: {prompt}"})

    def _build_planning_prompt(self, prompt: str) -> str:
        return f"""
You are an expert AI orchestrator. Your job is to select the best "Thinking Protocol" to answer a user's prompt and provide the parameters for it in a JSON format.

Available Protocols:
1. `simple`: For straightforward questions. A single agent provides an answer.
   - params: `{{"role": "lead", "task": "..."}}`
2. `critique_and_improve`: For complex, subjective, or high-stakes queries requiring maximum accuracy. Multiple agents generate drafts, critique each other, and then improve their work.
   - params: `{{"drafting_task": "...", "drafting_roles": ["lead", "analyst"], "improving_role": "lead"}}`

Based on the user's prompt, choose the optimal protocol.

User's Prompt: "{prompt}"

Your output MUST be a single, valid JSON object containing "reasoning", "protocol", and "params".

JSON Plan:
"""
