from .models import Job, JobStatus
from .planner import Planner
from models.model_pool import model_pool
import logging

logger = logging.getLogger("llmhive")

class OrchestrationEngine:
    def __init__(self):
        # In the future, the planner and model pool will be more integrated.
        # For now, we initialize them here.
        self.planner = Planner()
        self.model_pool = model_pool
        logger.info("OrchestrationEngine initialized.")

    def execute_job(self, job: Job) -> Job:
        """
        Executes the steps for a given job.
        Phase 1: This implements the existing simple Tavily search logic.
        """
        job.status = JobStatus.RUNNING
        logger.info(f"Executing Job ID: {job.id}")
        
        try:
            prompt = job.shared_memory.original_prompt
            
            # Step 1: Use the planner
            plan = self.planner.plan(prompt)
            job.shared_memory.add_step_result(step_name="Planner", result=plan.model_dump_json())
            logger.info(f"Job {job.id}: Plan created - {plan.reasoning}")

            # Step 2: Execute the plan
            if plan.tool == "tavily":
                tavily_tool = self.model_pool.get_tool("tavily")
                if tavily_tool:
                    result = tavily_tool.run(plan.query)
                    job.shared_memory.add_step_result(step_name="Tavily Search", result=result)
                    job.result = result # Set the final result for this simple workflow
                    logger.info(f"Job {job.id}: Tavily tool executed successfully.")
                else:
                    raise ValueError("Tavily tool not found in model pool.")
            else:
                # For now, if not a tavily search, we just return the reasoning.
                job.result = plan.reasoning
                logger.warning(f"Job {job.id}: No tool found for plan. Defaulting to reasoning.")

            job.status = JobStatus.COMPLETED
            logger.info(f"Job {job.id}: Execution completed successfully.")

        except Exception as e:
            job.status = JobStatus.FAILED
            job.shared_memory.add_step_result(step_name="Execution Error", result=str(e), was_successful=False, error_message=str(e))
            job.result = {"error": str(e)}
            logger.error(f"Job {job.id}: Execution failed. Error: {e}", exc_info=True)

        return job
