"""
KB Orchestrator Bridge - Wires KB pipelines into the orchestrator.

This module provides the integration layer between:
- KB query classifier
- KB pipeline selector  
- Pipeline implementations
- Trace logging

Usage:
    from llmhive.pipelines.kb_orchestrator_bridge import process_with_kb_pipeline
    
    result = await process_with_kb_pipeline(
        query="What is the capital of France?",
        tools_available=["web_search"],
    )
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import time
from typing import Any, Callable, Dict, List, Optional

from .types import PipelineContext, PipelineResult
from .guardrails import sanitize_input, enforce_no_cot
from .pipeline_registry import get_pipeline, get_fallback_pipeline

logger = logging.getLogger(__name__)

# Lazy imports to avoid circular dependencies
_kb_loaded = False
_query_classifier = None
_pipeline_selector = None


def _load_kb_modules():
    """Lazy load KB modules."""
    global _kb_loaded, _query_classifier, _pipeline_selector
    
    if _kb_loaded:
        return
    
    try:
        from llmhive.kb.query_classifier import get_query_classifier
        from llmhive.kb.pipeline_selector import select_pipeline as _select_pipeline
        
        _query_classifier = get_query_classifier()
        _pipeline_selector = _select_pipeline
        _kb_loaded = True
        logger.info("KB modules loaded successfully")
    except ImportError as e:
        logger.warning("KB modules not available: %s", e)
        _kb_loaded = True  # Mark as attempted


def _hash_query(query: str) -> str:
    """Create a hash of the query for tracing (no PII)."""
    return hashlib.sha256(query.encode()).hexdigest()[:16]


async def process_with_kb_pipeline(
    query: str,
    *,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    tools_available: Optional[List[str]] = None,
    models_available: Optional[List[str]] = None,
    cost_budget: str = "medium",
    latency_budget_ms: Optional[int] = None,
    system_prompt: Optional[str] = None,
    conversation_history: Optional[List[Dict[str, str]]] = None,
    force_pipeline: Optional[str] = None,
    enable_tracing: bool = True,
) -> PipelineResult:
    """
    Process a query using KB-aligned pipelines.
    
    This is the main entry point for KB-integrated orchestration.
    
    Flow:
    1. Sanitize input
    2. Classify query (reasoning_type, risk_level, domain)
    3. Select pipeline based on classification + KB rankings
    4. Execute pipeline
    5. Enforce no-CoT in output
    6. Emit trace
    
    Args:
        query: User query
        user_id: Optional user ID
        session_id: Optional session ID
        tools_available: Available tools
        models_available: Available models
        cost_budget: "low", "medium", "high"
        latency_budget_ms: Max latency in ms
        system_prompt: Optional system prompt
        conversation_history: Optional conversation history
        force_pipeline: Force specific pipeline (for testing)
        enable_tracing: Whether to emit traces
        
    Returns:
        PipelineResult with final answer and metadata
    """
    start_time = time.time()
    query_hash = _hash_query(query)
    
    # Load KB modules
    _load_kb_modules()
    
    # Step 1: Sanitize input
    sanitized_query = sanitize_input(query)
    
    # Step 2: Classify query
    classification = None
    reasoning_type = "general"
    risk_level = "low"
    domain = "general"
    citations_requested = False
    
    if _query_classifier is not None:
        try:
            classification = _query_classifier.classify(sanitized_query)
            reasoning_type = classification.reasoning_type.value
            risk_level = classification.risk_level.value
            domain = classification.domain.value
            citations_requested = classification.citations_requested
        except Exception as e:
            logger.warning("Classification failed: %s", e)
    
    # Step 3: Select pipeline
    pipeline_name = "PIPELINE_BASELINE_SINGLECALL"
    technique_ids: List[str] = []
    
    if force_pipeline:
        pipeline_name = force_pipeline
    elif _pipeline_selector is not None:
        try:
            selection = _pipeline_selector(
                query=sanitized_query,
                tools_available=tools_available or [],
                cost_budget=cost_budget,
            )
            pipeline_name = selection.pipeline_name.value
            technique_ids = selection.technique_ids
        except Exception as e:
            logger.warning("Pipeline selection failed: %s", e)
    
    # Step 4: Get and execute pipeline
    pipeline_fn = get_pipeline(pipeline_name)
    if pipeline_fn is None:
        logger.warning("Pipeline %s not found, using fallback", pipeline_name)
        pipeline_fn = get_fallback_pipeline()
        pipeline_name = "PIPELINE_BASELINE_SINGLECALL"
    
    # Build context
    context = PipelineContext(
        query=sanitized_query,
        user_id=user_id,
        session_id=session_id,
        reasoning_type=reasoning_type,
        risk_level=risk_level,
        domain=domain,
        citations_requested=citations_requested,
        tools_available=tools_available or [],
        models_available=models_available or [],
        cost_budget=cost_budget,
        latency_budget_ms=latency_budget_ms,
        system_prompt=system_prompt,
        conversation_history=conversation_history or [],
    )
    
    # Execute pipeline with fallback
    result = None
    error = None
    fallback_used = False
    
    try:
        if asyncio.iscoroutinefunction(pipeline_fn):
            result = await pipeline_fn(context)
        else:
            result = pipeline_fn(context)
    except Exception as e:
        logger.error("Pipeline %s failed: %s", pipeline_name, e)
        error = str(e)
        fallback_used = True
        
        # Fallback to baseline
        try:
            fallback_fn = get_fallback_pipeline()
            if asyncio.iscoroutinefunction(fallback_fn):
                result = await fallback_fn(context)
            else:
                result = fallback_fn(context)
            result.fallback_used = True
            result.error = error
        except Exception as fallback_error:
            # Complete failure
            result = PipelineResult(
                final_answer="I apologize, but I encountered an error processing your request.",
                pipeline_name="PIPELINE_ERROR_FALLBACK",
                technique_ids=[],
                confidence="low",
                error=str(fallback_error),
                fallback_used=True,
            )
    
    # Step 5: Enforce no-CoT in final answer
    if result:
        result.final_answer = enforce_no_cot(result.final_answer)
    
    # Calculate latency
    latency_ms = (time.time() - start_time) * 1000
    if result:
        result.metrics["total_latency_ms"] = latency_ms
    
    # Step 6: Emit trace
    if enable_tracing:
        try:
            from llmhive.app.orchestration.trace_writer import emit_pipeline_trace
            
            emit_pipeline_trace(
                event="pipeline_execution",
                query_hash=query_hash,
                reasoning_type=reasoning_type,
                risk_level=risk_level,
                domain=domain,
                selected_pipeline=pipeline_name,
                technique_ids=technique_ids or (result.technique_ids if result else []),
                tool_calls=result.tool_calls if result else None,
                verification={
                    k: v for k, v in (result.metrics.items() if result else [])
                    if k in ("self_consistency_n", "debate_rounds", "refine_iterations", "tot_used")
                } or None,
                outcome_confidence=result.confidence if result else "low",
                latency_ms=latency_ms,
                fallback_used=fallback_used,
                error=error,
            )
        except Exception as trace_error:
            # Never let tracing crash the main flow
            logger.debug("Tracing failed: %s", trace_error)
    
    return result


def create_kb_orchestrator_handler(
    model_caller: Optional[Callable] = None,
) -> Callable:
    """
    Create a handler function that can be used by the orchestrator.
    
    Args:
        model_caller: Function to call models
        
    Returns:
        Async handler function
    """
    # Set up model caller if provided
    if model_caller is not None:
        from .pipelines_impl import set_model_caller
        set_model_caller(model_caller)
    
    async def handler(
        query: str,
        **kwargs,
    ) -> str:
        """Handle a query and return the answer."""
        result = await process_with_kb_pipeline(query, **kwargs)
        return result.final_answer
    
    return handler

