"""
Test the new N3 orchestration engine functionality.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from orchestration.models import Job, JobStatus, SharedMemory, StepResult
from orchestration.engine import OrchestrationEngine
from orchestration.planner import Planner, Plan

def test_job_creation():
    """Test creating a job from a prompt."""
    job = Job.from_prompt("What is the weather?")
    assert job.status == JobStatus.PENDING
    assert job.shared_memory.original_prompt == "What is the weather?"
    assert len(job.shared_memory.intermediate_steps) == 0
    print("✓ Job creation test passed")

def test_shared_memory():
    """Test shared memory functionality."""
    memory = SharedMemory(original_prompt="Test prompt")
    memory.add_step_result("Step1", {"result": "data"}, was_successful=True)
    assert len(memory.intermediate_steps) == 1
    assert memory.intermediate_steps[0].step_name == "Step1"
    assert memory.intermediate_steps[0].was_successful == True
    print("✓ SharedMemory test passed")

def test_planner_sync():
    """Test synchronous planner method."""
    planner = Planner()
    
    # Test search query
    plan = planner.plan("What is Python?")
    assert plan.tool == "tavily"
    assert plan.query == "What is Python?"
    print(f"✓ Planner search test passed: {plan.reasoning}")
    
    # Test non-search query
    plan2 = planner.plan("Write a poem")
    assert plan2.tool is None
    print(f"✓ Planner non-search test passed: {plan2.reasoning}")

def test_engine_initialization():
    """Test engine initialization."""
    engine = OrchestrationEngine()
    assert engine.planner is not None
    assert engine.model_pool is not None
    print("✓ Engine initialization test passed")

def test_job_execution_without_tavily():
    """Test job execution without Tavily (non-search query)."""
    engine = OrchestrationEngine()
    job = Job.from_prompt("Write a haiku")
    
    completed_job = engine.execute_job(job)
    
    assert completed_job.status == JobStatus.COMPLETED
    assert len(completed_job.shared_memory.intermediate_steps) >= 1
    assert completed_job.result is not None
    print(f"✓ Job execution test passed (status: {completed_job.status})")
    print(f"  Steps executed: {len(completed_job.shared_memory.intermediate_steps)}")

if __name__ == "__main__":
    print("Running N3 Orchestration Engine Tests...\n")
    
    test_job_creation()
    test_shared_memory()
    test_planner_sync()
    test_engine_initialization()
    test_job_execution_without_tavily()
    
    print("\n✅ All tests passed!")
