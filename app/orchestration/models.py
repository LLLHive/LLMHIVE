from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from uuid import uuid4
from enum import Enum

class JobStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class StepResult(BaseModel):
    """The output of a single step in the orchestration process."""
    step_name: str
    result: Any
    was_successful: bool = True
    error_message: Optional[str] = None

class SharedMemory(BaseModel):
    """A shared workspace for a Job, allowing agents to communicate."""
    original_prompt: str
    intermediate_steps: List[StepResult] = Field(default_factory=list)
    final_summary: Optional[str] = None
    
    def add_step_result(self, step_name: str, result: Any, was_successful: bool = True, error_message: Optional[str] = None):
        self.intermediate_steps.append(
            StepResult(step_name=step_name, result=result, was_successful=was_successful, error_message=error_message)
        )

class Job(BaseModel):
    """Represents a single, complete user request from start to finish."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    status: JobStatus = JobStatus.PENDING
    shared_memory: SharedMemory
    result: Optional[Any] = None

    @classmethod
    def from_prompt(cls, prompt: str) -> "Job":
        return cls(shared_memory=SharedMemory(original_prompt=prompt))
