from .models import Job, JobStatus, StepResult
from .planner import Planner
from models.model_pool import model_pool
import logging
import re

logger = logging.getLogger("llmhive")

class OrchestrationEngine:
    def __init__(self):
        self.planner = Planner()
        self.model_pool = model_pool
        logger.info("OrchestrationEngine initialized for multi-step execution.")

    def _resolve_prompt_template(self, prompt_template: str, job: Job) -> str:
        """Resolves templates like {{steps.step_name.result}} from shared memory."""
        
        def replace_match(match):
            step_name = match.group(1)
            if step_name in job.shared_memory.intermediate_steps:
                return str(job.shared_memory.intermediate_steps[step_name].result)
            else:
                raise KeyError(f"Could not find result for step '{step_name}' in shared memory.")
        
        # Regex to find all occurrences of {{steps.some_name.result}}
        pattern = r"\{\{steps\.([a-zA-Z0-9_-]+)\.result\}\}"
        resolved_prompt = re.sub(pattern, replace_match, prompt_template)
        return resolved_prompt

    def execute_job(self, job: Job) -> Job:
        job.status = JobStatus.RUNNING
        logger.info(f"Executing Job ID: {job.id} with multi-step engine.")
        
        try:
            # 1. Generate the plan
            job.plan = self.planner.plan(job.shared_memory.original_prompt)
            logger.info(f"Job {job.id}: Plan created. Reasoning: {job.plan.reasoning}")

            # 2. Execute the plan step-by-step
            for step in job.plan.steps:
                logger.info(f"Job {job.id}: Executing step '{step.step_name}' with agent '{step.agent}'.")
                
                # Resolve any templates in the prompt
                resolved_prompt = self._resolve_prompt_template(step.prompt, job)
                
                agent = self.model_pool.get_agent(step.agent) or self.model_pool.get_tool(step.agent)
                if not agent:
                    raise ValueError(f"Agent or tool '{step.agent}' not found in model pool.")
                
                # Execute agent/tool
                if step.agent == "summarizer":
                    # The summarizer has a different signature
                    # We assume the main text comes from a previous step and the instruction is in the prompt
                    # A more robust solution would be needed for more complex agents
                    text_to_process = self._resolve_prompt_template("{{steps." + step.step_name + ".result}}", job) # A bit of a hack for now
                    result = agent.run(text_to_summarize=resolved_prompt, instruction=step.prompt)

                else: # Assumes a simple run(prompt) signature like Tavily
                     result = agent.run(resolved_prompt)

                step_result = StepResult(step_name=step.step_name, result=result)
                job.shared_memory.add_step_result(step_result)
                logger.info(f"Job {job.id}: Step '{step.step_name}' completed.")

            # Set the final result of the job to the result of the last step
            if job.plan.steps:
                last_step_name = job.plan.steps[-1].step_name
                job.result = job.shared_memory.intermediate_steps[last_step_name].result
            
            job.status = JobStatus.COMPLETED
            logger.info(f"Job {job.id}: Execution completed successfully.")

        except Exception as e:
            job.status = JobStatus.FAILED
            error_result = StepResult(step_name="Execution Error", result=str(e), was_successful=False, error_message=str(e))
            job.shared_memory.add_step_result(error_result)
            job.result = {"error": str(e)}
            logger.error(f"Job {job.id}: Execution failed. Error: {e}", exc_info=True)

        return job
