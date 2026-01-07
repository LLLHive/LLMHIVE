"""Base runner interface for benchmark systems.

This module defines the abstract interface that all benchmark runners
must implement, ensuring consistent result collection across systems.
"""
from __future__ import annotations

import os
import time
import subprocess
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union


class RunnerStatus(Enum):
    """Status of a benchmark run."""
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    TIMEOUT = "timeout"
    ERROR = "error"


@dataclass
class SystemInfo:
    """Information about the system being benchmarked."""
    name: str
    version: str
    model_id: str
    description: str = ""
    capabilities: Dict[str, bool] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "model_id": self.model_id,
            "description": self.description,
            "capabilities": self.capabilities,
        }


@dataclass
class RunConfig:
    """Configuration for a benchmark run."""
    temperature: float = 0.0
    max_tokens: int = 2048
    timeout_seconds: float = 120.0
    top_p: float = 1.0
    enable_tools: bool = True
    enable_rag: bool = True
    enable_mcp2: bool = True
    deterministic: bool = True
    
    # LLMHive-specific settings
    reasoning_mode: str = "standard"
    accuracy_level: int = 3
    enable_hrm: bool = True
    enable_deep_consensus: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "timeout_seconds": self.timeout_seconds,
            "top_p": self.top_p,
            "enable_tools": self.enable_tools,
            "enable_rag": self.enable_rag,
            "enable_mcp2": self.enable_mcp2,
            "deterministic": self.deterministic,
            "reasoning_mode": self.reasoning_mode,
            "accuracy_level": self.accuracy_level,
            "enable_hrm": self.enable_hrm,
            "enable_deep_consensus": self.enable_deep_consensus,
        }


@dataclass
class BenchmarkCase:
    """A single benchmark case to run."""
    id: str
    category: str
    prompt: str
    expected: Dict[str, Any] = field(default_factory=dict)
    requirements: Dict[str, Any] = field(default_factory=dict)
    scoring: Dict[str, Any] = field(default_factory=dict)
    notes: str = ""
    
    @classmethod
    def from_yaml(cls, data: Dict[str, Any]) -> "BenchmarkCase":
        """Create a BenchmarkCase from YAML data."""
        return cls(
            id=data["id"],
            category=data["category"],
            prompt=data["prompt"],
            expected=data.get("expected", {}),
            requirements=data.get("requirements", {}),
            scoring=data.get("scoring", {}),
            notes=data.get("notes", ""),
        )
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "category": self.category,
            "prompt": self.prompt,
            "expected": self.expected,
            "requirements": self.requirements,
            "scoring": self.scoring,
            "notes": self.notes,
        }


@dataclass
class ToolTrace:
    """Trace of a tool execution."""
    tool_name: str
    triggered: bool
    success: bool
    execution_time_ms: float
    input_params: Dict[str, Any] = field(default_factory=dict)
    output: Optional[str] = None
    error: Optional[str] = None


@dataclass
class RetrievalTrace:
    """Trace of RAG retrieval."""
    documents_fetched: int
    top_score: float
    query_used: str
    rerank_model: Optional[str] = None
    sources: List[str] = field(default_factory=list)


@dataclass
class PlannerTrace:
    """Trace of planner execution (HRM/MCP2)."""
    steps_planned: int
    steps_executed: int
    strategy: str
    step_details: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class RunMetadata:
    """Detailed metadata from a run."""
    # Model/strategy info
    models_used: List[str] = field(default_factory=list)
    strategy_used: Optional[str] = None
    
    # Quality indicators
    verification_status: Optional[str] = None
    verification_score: Optional[float] = None
    confidence: Optional[float] = None
    
    # Resource usage
    sources_count: int = 0
    tools_used: List[str] = field(default_factory=list)
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: Optional[float] = None
    
    # Detailed traces
    tool_traces: List[ToolTrace] = field(default_factory=list)
    retrieval_trace: Optional[RetrievalTrace] = None
    planner_trace: Optional[PlannerTrace] = None
    
    # Debug info
    trace_id: Optional[str] = None
    raw_provider_payload: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            "models_used": self.models_used,
            "strategy_used": self.strategy_used,
            "verification_status": self.verification_status,
            "verification_score": self.verification_score,
            "confidence": self.confidence,
            "sources_count": self.sources_count,
            "tools_used": self.tools_used,
            "tokens_in": self.tokens_in,
            "tokens_out": self.tokens_out,
            "cost_usd": self.cost_usd,
            "trace_id": self.trace_id,
        }
        
        if self.tool_traces:
            result["tool_traces"] = [
                {
                    "tool_name": t.tool_name,
                    "triggered": t.triggered,
                    "success": t.success,
                    "execution_time_ms": t.execution_time_ms,
                }
                for t in self.tool_traces
            ]
        
        if self.retrieval_trace:
            result["retrieval_trace"] = {
                "documents_fetched": self.retrieval_trace.documents_fetched,
                "top_score": self.retrieval_trace.top_score,
                "rerank_model": self.retrieval_trace.rerank_model,
            }
        
        if self.planner_trace:
            result["planner_trace"] = {
                "steps_planned": self.planner_trace.steps_planned,
                "steps_executed": self.planner_trace.steps_executed,
                "strategy": self.planner_trace.strategy,
            }
        
        # Redact raw payload for security
        if self.raw_provider_payload:
            result["raw_provider_payload"] = "[REDACTED]"
        
        return result


@dataclass
class RunResult:
    """Result of running a benchmark case against a system."""
    # Identification
    system_name: str
    model_id: str
    prompt_id: str
    
    # Status
    status: RunnerStatus
    
    # Response
    answer_text: str
    structured_answer: Optional[Dict[str, Any]] = None
    
    # Timing
    latency_ms: float = 0.0
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    # Metadata
    metadata: RunMetadata = field(default_factory=RunMetadata)
    
    # Error info
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "system_name": self.system_name,
            "model_id": self.model_id,
            "prompt_id": self.prompt_id,
            "status": self.status.value,
            "answer_text": self.answer_text,
            "structured_answer": self.structured_answer,
            "latency_ms": self.latency_ms,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata.to_dict(),
            "error_message": self.error_message,
        }


def get_git_commit_hash() -> Optional[str]:
    """Get the current git commit hash."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()[:12]
    except Exception:
        pass
    return None


class RunnerBase(ABC):
    """Abstract base class for benchmark runners.
    
    All system runners (LLMHive, OpenAI, Anthropic, etc.) must implement
    this interface to ensure consistent benchmarking.
    """
    
    def __init__(self, config: Optional[RunConfig] = None):
        """Initialize the runner.
        
        Args:
            config: Run configuration. If None, uses defaults.
        """
        self.config = config or RunConfig()
        self._system_info: Optional[SystemInfo] = None
    
    @property
    @abstractmethod
    def system_name(self) -> str:
        """Return the name of this system."""
        pass
    
    @property
    @abstractmethod
    def model_id(self) -> str:
        """Return the model identifier."""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if this runner is available (has required keys/config).
        
        Returns:
            True if the runner can be used, False otherwise.
        """
        pass
    
    @abstractmethod
    async def run_case(
        self,
        case: BenchmarkCase,
        run_config: Optional[RunConfig] = None,
    ) -> RunResult:
        """Run a single benchmark case.
        
        Args:
            case: The benchmark case to run.
            run_config: Optional config override for this case.
        
        Returns:
            RunResult with the response and metadata.
        """
        pass
    
    def get_system_info(self) -> SystemInfo:
        """Get information about this system.
        
        Returns:
            SystemInfo describing this runner's system.
        """
        if self._system_info is None:
            self._system_info = SystemInfo(
                name=self.system_name,
                version=self._get_version(),
                model_id=self.model_id,
                description=self._get_description(),
                capabilities=self._get_capabilities(),
            )
        return self._system_info
    
    def _get_version(self) -> str:
        """Get the version of this system. Override in subclasses."""
        return "1.0.0"
    
    def _get_description(self) -> str:
        """Get a description of this system. Override in subclasses."""
        return f"{self.system_name} benchmark runner"
    
    def _get_capabilities(self) -> Dict[str, bool]:
        """Get capabilities of this system. Override in subclasses."""
        return {
            "tools": False,
            "rag": False,
            "mcp2": False,
            "streaming": False,
            "function_calling": False,
        }
    
    def skip_result(
        self,
        prompt_id: str,
        reason: str = "Runner not available",
    ) -> RunResult:
        """Create a skipped result.
        
        Args:
            prompt_id: The ID of the prompt that was skipped.
            reason: Why the run was skipped.
        
        Returns:
            RunResult with SKIPPED status.
        """
        return RunResult(
            system_name=self.system_name,
            model_id=self.model_id,
            prompt_id=prompt_id,
            status=RunnerStatus.SKIPPED,
            answer_text="",
            error_message=reason,
        )
    
    def error_result(
        self,
        prompt_id: str,
        error: str,
        latency_ms: float = 0.0,
    ) -> RunResult:
        """Create an error result.
        
        Args:
            prompt_id: The ID of the prompt that failed.
            error: The error message.
            latency_ms: Time elapsed before error.
        
        Returns:
            RunResult with ERROR status.
        """
        return RunResult(
            system_name=self.system_name,
            model_id=self.model_id,
            prompt_id=prompt_id,
            status=RunnerStatus.ERROR,
            answer_text="",
            latency_ms=latency_ms,
            error_message=error,
        )
    
    def timeout_result(
        self,
        prompt_id: str,
        timeout_seconds: float,
    ) -> RunResult:
        """Create a timeout result.
        
        Args:
            prompt_id: The ID of the prompt that timed out.
            timeout_seconds: The timeout duration.
        
        Returns:
            RunResult with TIMEOUT status.
        """
        return RunResult(
            system_name=self.system_name,
            model_id=self.model_id,
            prompt_id=prompt_id,
            status=RunnerStatus.TIMEOUT,
            answer_text="",
            latency_ms=timeout_seconds * 1000,
            error_message=f"Timed out after {timeout_seconds}s",
        )

