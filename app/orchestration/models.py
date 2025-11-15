from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class Step(BaseModel):
    """Defines a single step in an orchestration plan."""

    step_name: str
    agent: str
    prompt: str


class Plan(BaseModel):
    """Structured orchestration plan supporting legacy steps and new protocols."""

    reasoning: str = ""
    protocol: str = "simple"
    params: Dict[str, Any] = Field(default_factory=dict)
    steps: List[Step] = Field(default_factory=list)


class StepResult(BaseModel):
    """The output of a single step in the orchestration process."""

    step_name: str
    result: Any
    was_successful: bool = True
    error_message: Optional[str] = None


class SharedMemory(BaseModel):
    """A shared workspace for a Job, allowing agents to communicate."""

    original_prompt: str
    intermediate_steps: Dict[str, StepResult] = Field(default_factory=dict)
    final_summary: Optional[str] = None

    def add_step_result(self, result: StepResult) -> None:
        self.intermediate_steps[result.step_name] = result


class Job(BaseModel):
    """Represents a single, complete user request from start to finish."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    status: JobStatus = JobStatus.PENDING
    plan: Optional[Plan] = None
    shared_memory: SharedMemory
    result: Optional[Any] = None

    @classmethod
    def from_prompt(cls, prompt: str) -> "Job":
        return cls(shared_memory=SharedMemory(original_prompt=prompt))
