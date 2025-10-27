from models.language_model import LanguageModel
from .models import Plan, Job
from .archivist import Archivist
import json

class Planner:
    """
    The Maestro. It consults the Archivist for past experiences to create
    an informed, multi-step plan.
    """
    def __init__(self, llm: LanguageModel, archivist: Archivist):
        self.llm = llm
        self.archivist = archivist

    def _format_past_jobs_for_prompt(self, jobs: list[Job]) -> str:
        if not jobs:
            return "No similar past jobs found."

        context = "Here are some similar tasks we have successfully executed in the past. Learn from their structure and reasoning to create the best possible plan for the new prompt.\n\n"
        for i, job in enumerate(jobs):
            context += f"--- Past Job Example {i+1} ---\n"
            context += f"Original Prompt: {job.shared_memory.original_prompt}\n"
            context += f"Reasoning: {job.plan.reasoning}\n"
            # Pretty-print the JSON plan for clarity in the prompt
            plan_json = json.dumps([step.model_dump() for step in job.plan.steps], indent=2)
            context += f"Plan:\n{plan_json}\n"
            context += f"--- End of Example {i+1} ---\n\n"
        return context

    def plan(self, prompt: str) -> Plan:
        # 1. Find similar jobs from the past
        similar_jobs = self.archivist.find_similar_jobs(prompt)
        
        # 2. Format the past jobs into a context string for the LLM
        past_job_context = self._format_past_jobs_for_prompt(similar_jobs)

        system_prompt = f"""You are the Maestro, an expert planner for a powerful AI orchestration engine. Your job is to analyze a user's prompt and create a JSON object representing a step-by-step plan to fulfill it.

# Context from Past Jobs:
{past_job_context}

# Available Agents:
- "tavily": Web search tool. Use for questions about recent events, facts, or public information.
- "summarizer": An LLM agent that can summarize, analyze, or transform text.

# Instructions:
1.  Analyze the new user prompt below.
2.  Use the context from past jobs to inform your strategy. If a past plan was effective, learn from it.
3.  Create a "reasoning" string explaining your new plan.
4.  Create a "steps" list for the new prompt. Each step must have "step_name", "agent", and "prompt".
5.  To use the output of a previous step, use the exact template format: `{{{{steps.previous_step_name.result}}}}`.

Now, create the plan for the following new user prompt.
"""
        plan_str = self.llm.generate(prompt, system_prompt=system_prompt, response_format={"type": "json_object"})
        return Plan.model_validate_json(plan_str)

