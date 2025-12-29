"""
Pipeline Registry - Maps pipeline names to implementations.
"""
from __future__ import annotations

import logging
from typing import Callable, Dict, List, Optional

from .types import PipelineContext, PipelineResult

logger = logging.getLogger(__name__)

# Type for pipeline functions
PipelineFunc = Callable[[PipelineContext], PipelineResult]

# Registry of pipelines
_PIPELINE_REGISTRY: Dict[str, PipelineFunc] = {}


def register_pipeline(name: str, fn: PipelineFunc) -> None:
    """
    Register a pipeline implementation.
    
    Args:
        name: Pipeline name (e.g., "PIPELINE_MATH_REASONING")
        fn: Pipeline function that takes PipelineContext and returns PipelineResult
    """
    _PIPELINE_REGISTRY[name] = fn
    logger.debug("Registered pipeline: %s", name)


def get_pipeline(name: str) -> Optional[PipelineFunc]:
    """
    Get a pipeline by name.
    
    Args:
        name: Pipeline name
        
    Returns:
        Pipeline function or None if not found
    """
    return _PIPELINE_REGISTRY.get(name)


def list_pipelines() -> List[str]:
    """
    List all registered pipeline names.
    
    Returns:
        List of pipeline names
    """
    return list(_PIPELINE_REGISTRY.keys())


def get_fallback_pipeline() -> PipelineFunc:
    """
    Get the baseline fallback pipeline.
    
    Returns:
        The PIPELINE_BASELINE_SINGLECALL pipeline
    """
    fallback = _PIPELINE_REGISTRY.get("PIPELINE_BASELINE_SINGLECALL")
    if fallback is None:
        # Return a minimal fallback if not registered
        def minimal_fallback(ctx: PipelineContext) -> PipelineResult:
            return PipelineResult(
                final_answer="I apologize, but I encountered an error processing your request.",
                pipeline_name="PIPELINE_FALLBACK_MINIMAL",
                technique_ids=[],
                confidence="low",
                error="No pipeline available",
                fallback_used=True,
            )
        return minimal_fallback
    return fallback

