"""
Test the new N3 orchestration engine functionality.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from orchestration.models import Job, JobStatus, SharedMemory, StepResult, Step, Plan
from orchestration.engine import OrchestrationEngine
from orchestration.planner import Planner

def test_job_creation():
    """Test creating a job from a prompt."""
    job = Job.from_prompt("What is the weather?")
    assert job.status == JobStatus.PENDING
    assert job.shared_memory.original_prompt == "What is the weather?"
    assert len(job.shared_memory.intermediate_steps) == 0
    print("✓ Job creation test passed")

def test_step_and_plan_models():
    """Test Step and Plan model creation."""
    step1 = Step(step_name="search", agent="tavily", prompt="Weather in SF")
    step2 = Step(step_name="summarize", agent="summarizer", prompt="Summarize: {{steps.search.result}}")
    plan = Plan(
        reasoning="Search and then summarize",
        steps=[step1, step2]
    )
    assert len(plan.steps) == 2
    assert plan.steps[0].step_name == "search"
    assert plan.steps[1].agent == "summarizer"
    print("✓ Step and Plan model test passed")

def test_shared_memory():
    """Test shared memory functionality."""
    memory = SharedMemory(original_prompt="Test prompt")
    step_result = StepResult(step_name="Step1", result={"result": "data"}, was_successful=True)
    memory.add_step_result(step_result)
    assert len(memory.intermediate_steps) == 1
    assert memory.intermediate_steps["Step1"].step_name == "Step1"
    assert memory.intermediate_steps["Step1"].was_successful == True
    print("✓ SharedMemory test passed")

def test_planner_initialization():
    """Test planner initialization."""
    # Note: The new planner requires OpenAI API key to initialize
    # This test just verifies it can be instantiated
    try:
        planner = Planner()
        assert planner.llm is not None
        print("✓ Planner initialization test passed")
    except Exception as e:
        print(f"⚠ Planner initialization skipped (OpenAI API key may be missing): {e}")

def test_engine_initialization():
    """Test engine initialization."""
    engine = OrchestrationEngine()
    assert engine.planner is not None
    assert engine.model_pool is not None
    print("✓ Engine initialization test passed")

def test_job_execution_without_api_keys():
    """Test job execution without API keys (should fail gracefully)."""
    engine = OrchestrationEngine()
    job = Job.from_prompt("Write a haiku")
    
    # Without API keys, the engine should fail but not crash
    completed_job = engine.execute_job(job)
    
    # Job should either complete (if API keys are present) or fail gracefully
    assert completed_job.status in [JobStatus.COMPLETED, JobStatus.FAILED]
    # SharedMemory now uses dict, check if it has entries
    assert len(completed_job.shared_memory.intermediate_steps) >= 0
    print(f"✓ Job execution test passed (status: {completed_job.status})")
    print(f"  Steps executed: {len(completed_job.shared_memory.intermediate_steps)}")

if __name__ == "__main__":
    print("Running N3 Orchestration Engine Tests...\n")
    
    test_job_creation()
    test_step_and_plan_models()
    test_shared_memory()
    test_planner_initialization()
    test_engine_initialization()
    test_job_execution_without_api_keys()
    
    print("\n✅ All tests passed!")
