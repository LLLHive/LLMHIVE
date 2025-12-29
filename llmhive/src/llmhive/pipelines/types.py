"""
Pipeline Types - Core data structures for KB-aligned pipelines.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class PipelineContext:
    """Context passed to pipeline execution.
    
    Contains all information needed to execute a technique-aligned pipeline.
    """
    query: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    
    # Classification results (from query_classifier)
    reasoning_type: str = "general"
    risk_level: str = "low"
    domain: str = "general"
    citations_requested: bool = False
    
    # Available resources
    tools_available: List[str] = field(default_factory=list)
    models_available: List[str] = field(default_factory=list)
    
    # Budget constraints
    latency_budget_ms: Optional[int] = None  # Max latency in ms
    cost_budget: str = "medium"  # "low", "medium", "high"
    max_tokens: int = 4096
    
    # Pipeline config overrides
    max_steps: int = 10
    max_tool_calls: int = 6
    max_retries: int = 2
    
    # Additional context
    system_prompt: Optional[str] = None
    conversation_history: List[Dict[str, str]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging."""
        return {
            "query_length": len(self.query),
            "reasoning_type": self.reasoning_type,
            "risk_level": self.risk_level,
            "domain": self.domain,
            "citations_requested": self.citations_requested,
            "tools_available": self.tools_available,
            "cost_budget": self.cost_budget,
            "max_steps": self.max_steps,
        }


@dataclass
class PipelineResult:
    """Result from pipeline execution.
    
    Contains the final answer plus metadata for tracing and evaluation.
    """
    final_answer: str
    pipeline_name: str
    technique_ids: List[str] = field(default_factory=list)
    
    # Quality indicators
    confidence: str = "medium"  # "low", "medium", "high"
    verified: bool = False
    
    # Citations if applicable
    citations: List[Dict[str, str]] = field(default_factory=list)
    
    # Metrics for observability
    metrics: Dict[str, Any] = field(default_factory=dict)
    
    # Debug/trace information (internal only, not returned to user)
    debug_meta: Dict[str, Any] = field(default_factory=dict)
    
    # Tool call summary
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    
    # Error information if any
    error: Optional[str] = None
    fallback_used: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging."""
        return {
            "pipeline_name": self.pipeline_name,
            "technique_ids": self.technique_ids,
            "confidence": self.confidence,
            "verified": self.verified,
            "citations_count": len(self.citations),
            "tool_calls_count": len(self.tool_calls),
            "metrics": self.metrics,
            "fallback_used": self.fallback_used,
            "error": self.error,
        }

