from .models import Job, JobStatus, StepResult
from .planner import Planner
from .archivist import Archivist
from models.model_pool import model_pool
import logging
import re

logger = logging.getLogger("llmhive")

class OrchestrationEngine:
    def __init__(self):
        self.model_pool = model_pool
        self.archivist = Archivist()
        
        # Use the "gpt-4o" model from the pool to initialize the Planner.
        # This ensures the Planner has its dependency without managing API keys itself.
        planner_llm = self.model_pool.get_llm("gpt-4o")
        if not planner_llm:
            raise RuntimeError("Could not find 'gpt-4o' in model pool. Planner cannot be initialized.")
        self.planner = Planner(llm=planner_llm)
        
        logger.info("OrchestrationEngine initialized with multi-step and archival capabilities.")

    def _resolve_prompt_template(self, prompt_template: str, job: Job) -> str:
        """Resolves templates like {{steps.step_name.result}} from shared memory."""
        def replace_match(match):
            step_name = match.group(1)
            step_result = job.shared_memory.intermediate_steps.get(step_name)
            if step_result:
                return str(step_result.result)
            else:
                raise KeyError(f"Could not find result for step '{step_name}' in shared memory.")
        
        pattern = r"\{\{steps\.([a-zA-Z0-9_-]+)\.result\}\}"
        resolved_prompt = re.sub(pattern, replace_match, prompt_template)
        return resolved_prompt

    def execute_job(self, job: Job) -> Job:
        job.status = JobStatus.RUNNING
        logger.info(f"Executing Job ID: {job.id} with multi-step engine.")
        
        try:
            job.plan = self.planner.plan(job.shared_memory.original_prompt)
            logger.info(f"Job {job.id}: Plan created. Reasoning: {job.plan.reasoning}")

            for step in job.plan.steps:
                logger.info(f"Job {job.id}: Executing step '{step.step_name}' with agent '{step.agent}'.")
                resolved_prompt = self._resolve_prompt_template(step.prompt, job)
                agent = self.model_pool.get_agent(step.agent)
                if not agent:
                    raise ValueError(f"Agent '{step.agent}' not found in model pool.")
                
                result = agent.run(resolved_prompt)
                step_result = StepResult(step_name=step.step_name, result=result)
                job.shared_memory.add_step_result(step_result)
                logger.info(f"Job {job.id}: Step '{step.step_name}' completed.")

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
        
        finally:
            self.archivist.save_job(job)

        return job
