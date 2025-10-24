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
            # Extract the JSON part of the response
            plan_json_str = llm_response[llm_response.find('{'):llm_response.rfind('}')+1]
            plan_data = json.loads(plan_json_str)
            return Plan(**plan_data)
        except (json.JSONDecodeError, TypeError, KeyError) as e:
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
You are an expert AI orchestrator. Your job is to create a detailed, step-by-step execution plan to answer a user's prompt by coordinating a team of specialized AI agents.

Available Agent Roles:
- lead: A general-purpose, high-capability agent for drafting, analysis, or complex reasoning.
- researcher: An agent with web search capabilities to find up-to-date information.
- critic: An agent that reviews the work of other agents for accuracy, clarity, and completeness.
- editor: An agent that refines and polishes text into a final, well-formatted response.

Your plan must be in a valid JSON format. The plan can include 'sequential' and 'parallel' execution blocks.

- Use 'sequential' when steps must happen in order.
- Use 'parallel' when tasks can be performed simultaneously (e.g., getting two different perspectives).

Example for a complex research query:
{{
  "reasoning": "The user is asking a complex question that requires research, analysis, and a well-structured answer. I will first use a researcher to gather facts, then have a lead agent analyze them, a critic to review the analysis, and finally an editor to polish the response.",
  "steps": [
    {{
      "type": "sequential",
      "steps": [
        {{"role": "researcher", "task": "Gather up-to-date information and key facts about the user's query."}},
        {{"role": "lead", "task": "Analyze the gathered information and draft a comprehensive answer."}},
        {{"role": "critic", "task": "Review the drafted answer for factual accuracy and logical consistency. Provide specific feedback for improvement."}},
        {{"role": "editor", "task": "Incorporate the critic's feedback into the draft and produce a polished, final answer."}}
      ]
    }}
  ],
  "synthesis_strategy": "llm_merge"
}}

Example for a query asking for pros and cons:
{{
  "reasoning": "The user wants pros and cons. I can get two perspectives in parallel to generate diverse ideas and then merge them.",
  "steps": [
    {{
      "type": "parallel",
      "steps": [
        {{"role": "lead", "task": "Generate a strong argument for the 'pros' of the user's query.", "output_key": "pros_argument"}},
        {{"role": "lead", "task": "Generate a strong argument for the 'cons' of the user's query.", "output_key": "cons_argument"}}
      ]
    }}
  ],
  "synthesis_strategy": "llm_merge"
}}

User's Prompt: "{prompt}"

Now, create the JSON plan for this prompt.
"""
