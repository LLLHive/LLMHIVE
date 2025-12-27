"""
LLMHive Pipeline Selector

Selects the best execution pipeline based on:
- Query classification
- KB rankings
- Available tools
- Budget/latency constraints

Pipelines:
- PIPELINE_RAG_CITATION_COVE: For factual queries needing citations
- PIPELINE_MATH_REASONING: For mathematical/logical reasoning
- PIPELINE_CODING_AGENT: For coding tasks
- PIPELINE_TOOL_USE_REACT: For tasks requiring external tools
- PIPELINE_CRITIC_OR_DEBATE: For high-risk queries
- PIPELINE_COST_OPTIMIZED_ROUTING: For cost-constrained scenarios

Usage:
    from llmhive.kb.pipeline_selector import select_pipeline
    
    result = select_pipeline(
        query="Prove that sqrt(2) is irrational",
        tools_available=["calculator"],
        latency_budget=5000,
        cost_budget="low",
    )
    print(result.pipeline_name)  # "PIPELINE_MATH_REASONING"
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set

from .query_classifier import (
    ClassificationResult,
    QueryClassifier,
    ReasoningType,
    RiskLevel,
    Domain,
    get_query_classifier,
)
from .technique_kb import TechniqueKB, get_technique_kb

logger = logging.getLogger(__name__)


class PipelineName(str, Enum):
    """Available execution pipelines."""
    RAG_CITATION_COVE = "PIPELINE_RAG_CITATION_COVE"
    MATH_REASONING = "PIPELINE_MATH_REASONING"
    CODING_AGENT = "PIPELINE_CODING_AGENT"
    TOOL_USE_REACT = "PIPELINE_TOOL_USE_REACT"
    CRITIC_OR_DEBATE = "PIPELINE_CRITIC_OR_DEBATE"
    COST_OPTIMIZED_ROUTING = "PIPELINE_COST_OPTIMIZED_ROUTING"
    SIMPLE_DIRECT = "PIPELINE_SIMPLE_DIRECT"  # Fallback


@dataclass
class PipelineSelection:
    """Result of pipeline selection."""
    pipeline_name: PipelineName
    technique_ids: List[str]
    classification: ClassificationResult
    reasoning: str = ""
    fallback_pipeline: Optional[PipelineName] = None
    config: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "pipeline_name": self.pipeline_name.value,
            "technique_ids": self.technique_ids,
            "classification": self.classification.to_dict(),
            "reasoning": self.reasoning,
            "fallback_pipeline": self.fallback_pipeline.value if self.fallback_pipeline else None,
            "config": self.config,
        }


# Pipeline configurations
PIPELINE_CONFIGS = {
    PipelineName.RAG_CITATION_COVE: {
        "technique_ids": ["TECH_0013", "TECH_0014", "TECH_0010"],
        "description": "RAG with citations and Chain-of-Verification",
        "requires_tools": ["web_search"],
        "max_steps": 5,
        "cost_multiplier": 2.0,
    },
    PipelineName.MATH_REASONING: {
        "technique_ids": ["TECH_0027", "TECH_0012", "TECH_0028"],
        "description": "Mathematical reasoning with CoT and self-consistency",
        "requires_tools": [],
        "max_steps": 10,
        "cost_multiplier": 3.0,
    },
    PipelineName.CODING_AGENT: {
        "technique_ids": ["TECH_0001", "TECH_0004", "TECH_0011", "TECH_0003", "TECH_0026"],
        "description": "Coding with planning, testing, and reflection",
        "requires_tools": ["code_sandbox"],
        "max_steps": 15,
        "cost_multiplier": 2.5,
    },
    PipelineName.TOOL_USE_REACT: {
        "technique_ids": ["TECH_0002", "TECH_0021", "TECH_0035"],
        "description": "ReAct loop for tool use",
        "requires_tools": [],  # Any tools work
        "max_steps": 10,
        "cost_multiplier": 2.0,
    },
    PipelineName.CRITIC_OR_DEBATE: {
        "technique_ids": ["TECH_0007", "TECH_0008"],
        "description": "Judge/Critic or multi-model debate",
        "requires_tools": [],
        "max_steps": 5,
        "cost_multiplier": 4.0,
    },
    PipelineName.COST_OPTIMIZED_ROUTING: {
        "technique_ids": ["TECH_0005", "TECH_0006"],
        "description": "Specialist routing with cascade fallback",
        "requires_tools": [],
        "max_steps": 3,
        "cost_multiplier": 1.0,
    },
    PipelineName.SIMPLE_DIRECT: {
        "technique_ids": [],
        "description": "Direct single-model call (baseline)",
        "requires_tools": [],
        "max_steps": 1,
        "cost_multiplier": 1.0,
    },
}


def select_pipeline(
    query: str,
    tools_available: Optional[List[str]] = None,
    latency_budget: Optional[int] = None,  # ms
    cost_budget: Optional[str] = None,  # "low", "medium", "high"
    force_pipeline: Optional[PipelineName] = None,
    classifier: Optional[QueryClassifier] = None,
    kb: Optional[TechniqueKB] = None,
) -> PipelineSelection:
    """
    Select the best execution pipeline for a query.
    
    Args:
        query: The user's query
        tools_available: List of available tool names
        latency_budget: Maximum latency in ms
        cost_budget: Cost constraint ("low", "medium", "high")
        force_pipeline: Force a specific pipeline (for testing)
        classifier: Optional classifier instance
        kb: Optional KB instance
    
    Returns:
        PipelineSelection with chosen pipeline and config
    """
    tools_available = tools_available or []
    cost_budget = cost_budget or "medium"
    
    # Get instances
    if classifier is None:
        classifier = get_query_classifier()
    if kb is None:
        kb = get_technique_kb()
    
    # Classify the query
    classification = classifier.classify(query)
    
    # Force pipeline if specified
    if force_pipeline:
        config = PIPELINE_CONFIGS.get(force_pipeline, {})
        return PipelineSelection(
            pipeline_name=force_pipeline,
            technique_ids=config.get("technique_ids", []),
            classification=classification,
            reasoning=f"Forced pipeline: {force_pipeline.value}",
            config=config,
        )
    
    # Select pipeline based on classification
    reasoning_type = classification.reasoning_type
    risk_level = classification.risk_level
    domain = classification.domain
    
    # High-risk queries → Critic/Debate
    if risk_level == RiskLevel.HIGH:
        return PipelineSelection(
            pipeline_name=PipelineName.CRITIC_OR_DEBATE,
            technique_ids=PIPELINE_CONFIGS[PipelineName.CRITIC_OR_DEBATE]["technique_ids"],
            classification=classification,
            reasoning=f"High-risk query ({domain.value}) requires verification",
            fallback_pipeline=PipelineName.SIMPLE_DIRECT,
            config=PIPELINE_CONFIGS[PipelineName.CRITIC_OR_DEBATE],
        )
    
    # Cost-constrained → Cost optimized routing
    if cost_budget == "low":
        return PipelineSelection(
            pipeline_name=PipelineName.COST_OPTIMIZED_ROUTING,
            technique_ids=PIPELINE_CONFIGS[PipelineName.COST_OPTIMIZED_ROUTING]["technique_ids"],
            classification=classification,
            reasoning="Low cost budget requires optimized routing",
            fallback_pipeline=PipelineName.SIMPLE_DIRECT,
            config=PIPELINE_CONFIGS[PipelineName.COST_OPTIMIZED_ROUTING],
        )
    
    # Mathematical reasoning
    if reasoning_type == ReasoningType.MATHEMATICAL_REASONING:
        return PipelineSelection(
            pipeline_name=PipelineName.MATH_REASONING,
            technique_ids=PIPELINE_CONFIGS[PipelineName.MATH_REASONING]["technique_ids"],
            classification=classification,
            reasoning="Mathematical query requires structured reasoning",
            fallback_pipeline=PipelineName.SIMPLE_DIRECT,
            config=PIPELINE_CONFIGS[PipelineName.MATH_REASONING],
        )
    
    # Logical/deductive reasoning
    if reasoning_type == ReasoningType.LOGICAL_DEDUCTIVE:
        return PipelineSelection(
            pipeline_name=PipelineName.MATH_REASONING,
            technique_ids=PIPELINE_CONFIGS[PipelineName.MATH_REASONING]["technique_ids"],
            classification=classification,
            reasoning="Logical deduction requires structured reasoning",
            fallback_pipeline=PipelineName.SIMPLE_DIRECT,
            config=PIPELINE_CONFIGS[PipelineName.MATH_REASONING],
        )
    
    # Coding tasks
    if reasoning_type == ReasoningType.CODING or domain == Domain.CODING:
        # Check if sandbox available
        has_sandbox = "code_sandbox" in tools_available or "sandbox" in tools_available
        if has_sandbox:
            return PipelineSelection(
                pipeline_name=PipelineName.CODING_AGENT,
                technique_ids=PIPELINE_CONFIGS[PipelineName.CODING_AGENT]["technique_ids"],
                classification=classification,
                reasoning="Coding task with sandbox available",
                fallback_pipeline=PipelineName.SIMPLE_DIRECT,
                config=PIPELINE_CONFIGS[PipelineName.CODING_AGENT],
            )
        else:
            # Fallback to simpler coding without sandbox
            return PipelineSelection(
                pipeline_name=PipelineName.SIMPLE_DIRECT,
                technique_ids=["TECH_0027"],  # Just CoT
                classification=classification,
                reasoning="Coding task but no sandbox available",
                config={"max_steps": 1},
            )
    
    # Tool use
    if reasoning_type == ReasoningType.TOOL_USE:
        if tools_available:
            return PipelineSelection(
                pipeline_name=PipelineName.TOOL_USE_REACT,
                technique_ids=PIPELINE_CONFIGS[PipelineName.TOOL_USE_REACT]["technique_ids"],
                classification=classification,
                reasoning=f"Tool use with available tools: {tools_available}",
                fallback_pipeline=PipelineName.SIMPLE_DIRECT,
                config={
                    **PIPELINE_CONFIGS[PipelineName.TOOL_USE_REACT],
                    "available_tools": tools_available,
                },
            )
    
    # Retrieval/grounding/factual with citations
    if reasoning_type == ReasoningType.RETRIEVAL_GROUNDING or classification.citations_requested:
        has_search = "web_search" in tools_available or "search" in tools_available
        if has_search:
            return PipelineSelection(
                pipeline_name=PipelineName.RAG_CITATION_COVE,
                technique_ids=PIPELINE_CONFIGS[PipelineName.RAG_CITATION_COVE]["technique_ids"],
                classification=classification,
                reasoning="Factual query requires RAG with citations",
                fallback_pipeline=PipelineName.SIMPLE_DIRECT,
                config=PIPELINE_CONFIGS[PipelineName.RAG_CITATION_COVE],
            )
    
    # Default fallback
    return PipelineSelection(
        pipeline_name=PipelineName.SIMPLE_DIRECT,
        technique_ids=[],
        classification=classification,
        reasoning="No specialized pipeline needed",
        config=PIPELINE_CONFIGS[PipelineName.SIMPLE_DIRECT],
    )


def get_pipeline_for_reasoning_type(
    reasoning_type: str,
    tools_available: Optional[List[str]] = None,
) -> PipelineName:
    """
    Get the recommended pipeline for a reasoning type.
    
    Simplified helper for direct mapping.
    """
    mapping = {
        "mathematical_reasoning": PipelineName.MATH_REASONING,
        "logical_deductive": PipelineName.MATH_REASONING,
        "coding": PipelineName.CODING_AGENT,
        "planning_multistep": PipelineName.TOOL_USE_REACT,
        "tool_use": PipelineName.TOOL_USE_REACT,
        "retrieval_grounding": PipelineName.RAG_CITATION_COVE,
        "robustness_adversarial": PipelineName.CRITIC_OR_DEBATE,
    }
    return mapping.get(reasoning_type, PipelineName.SIMPLE_DIRECT)
