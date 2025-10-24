"""
The LLM-Powered Planner for LLMHive.

This component uses a high-capability LLM to perform hierarchical task
decomposition, creating a dynamic, structured execution plan in JSON format.
"""

import json
from typing import List
from pydantic import BaseModel, Field
from ..agents import LeadAgent
from ..config import settings

class Plan(BaseModel):
    """Represents a structured execution plan."""
    reasoning: str = Field(description="The reasoning behind the chosen plan.")
    steps: List[dict] = Field(description="A list of steps, which can be sequential or parallel.")
    synthesis_strategy: str = Field(default="llm_merge", description="Strategy for the final synthesis.")

class Planner:
    """
    Analyzes prompts using an LLM to create dynamic execution plans.
    """
    def __init__(self):
        # Use a powerful model for planning
        self.planner_agent = LeadAgent(model_id=settings.DEFAULT_MODEL)

    async def create_plan(self, prompt: str, context: List[str]) -> Plan:
        """
        Creates a structured plan using an LLM to address the user's prompt.
        """
        print(f"Creating LLM-driven plan for prompt: '{prompt}'")
        
        planning_prompt = self._build_planning_prompt(prompt)
        
        llm_response = await self.planner_agent.execute(planning_prompt)
        
        try:
            # Extract the JSON part of the response using a more robust approach
            # Look for the first complete JSON object
            start_idx = llm_response.find('{')
            if start_idx == -1:
                raise json.JSONDecodeError("No JSON object found", llm_response, 0)
            
            # Find the matching closing brace by counting brackets
            brace_count = 0
            end_idx = start_idx
            for i in range(start_idx, len(llm_response)):
                if llm_response[i] == '{':
                    brace_count += 1
                elif llm_response[i] == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        end_idx = i + 1
                        break
            
            plan_json_str = llm_response[start_idx:end_idx]
            plan_data = json.loads(plan_json_str)
            return Plan(**plan_data)
        except (json.JSONDecodeError, TypeError, KeyError, ValueError) as e:
            print(f"Error parsing LLM plan, falling back to default. Error: {e}")
            return self.fallback_plan(prompt)

    def fallback_plan(self, prompt: str) -> Plan:
        """A simple rule-based fallback plan."""
        return Plan(
            reasoning="Fell back to a simple, single-step plan.",
            steps=[{"type": "sequential", "steps": [{"role": "lead", "task": "Provide a direct and comprehensive answer to the user's prompt."}]}],
            synthesis_strategy="direct"
        )

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
2. `sequential`: A series of agents perform tasks in order.
   `{{"type": "sequential", "steps": [...]}}`
3. `parallel`: Multiple agents perform tasks simultaneously.
   `{{"type": "parallel", "steps": [...]}}`
4. `critique_and_improve`: Generate parallel drafts, have them critique each other, then improve based on feedback. This is for maximum accuracy on complex, subjective, or creative tasks.
   `{{"type": "critique_and_improve", "drafting_task": "...", "drafting_agents": ["lead", "analyst"], "improving_agent": "lead"}}`

Based on the user's prompt, create the optimal plan. Prioritize `critique_and_improve` for complex, high-stakes queries.

User's Prompt: "{prompt}"

JSON Plan:
"""
