from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

def emit_trace(event: Dict[str, Any], *, path: Optional[str] = None) -> None:
    """
    Append a single JSON event to a JSONL trace file.

    Enable by setting:
      export LLMHIVE_TRACE_PATH="logs/orchestrator_trace.jsonl"

    Notes:
    - Uses string-based identifiers (no enums) to avoid import issues.
    - Never throws (trace should not crash orchestration).
    - Avoid putting full prompts/answers here (PII + size).
    """
    trace_path = (path or os.getenv("LLMHIVE_TRACE_PATH", "")).strip()
    if not trace_path:
        return

    try:
        p = Path(trace_path)
        p.parent.mkdir(parents=True, exist_ok=True)

        payload = dict(event)
        payload.setdefault("timestamp", _utc_iso())

        # normalize key name used by the dashboard script
        if "strategy" in payload and "reasoning_method" not in payload:
            payload["reasoning_method"] = payload["strategy"]

        # normalize common variants
        rm = payload.get("reasoning_method")
        if isinstance(rm, str):
            rm = rm.strip().lower()
            if rm == "reflection":
                rm = "reflexion"
            payload["reasoning_method"] = rm

        with p.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")
    except Exception:
        return


def emit_pipeline_trace(
    *,
    event: str = "pipeline_execution",
    query_hash: Optional[str] = None,
    # Classification outputs
    reasoning_type: Optional[str] = None,
    risk_level: Optional[str] = None,
    domain: Optional[str] = None,
    # Pipeline selection
    selected_pipeline: Optional[str] = None,
    technique_ids: Optional[List[str]] = None,
    # Tool calls summary (no secrets)
    tool_calls: Optional[List[Dict[str, Any]]] = None,
    # Verification outcomes
    verification: Optional[Dict[str, Any]] = None,
    # Final confidence
    outcome_confidence: Optional[str] = None,
    # Metrics
    latency_ms: Optional[float] = None,
    fallback_used: bool = False,
    error: Optional[str] = None,
    # Additional metadata
    **kwargs,
) -> None:
    """
    Emit a pipeline execution trace with KB-specific fields.
    
    This is the extended trace format for KB-integrated pipelines.
    
    Args:
        event: Event type (default: "pipeline_execution")
        query_hash: Hash of query for correlation (no PII)
        reasoning_type: Classified reasoning type
        risk_level: Classified risk level (low/medium/high)
        domain: Detected domain
        selected_pipeline: Name of pipeline used
        technique_ids: KB technique IDs used (e.g., ["TECH_0001", "TECH_0002"])
        tool_calls: Summary of tool calls [{tool_name, ok, latency_ms}]
        verification: Verification outcomes {self_refine_iters, debate_rounds, etc.}
        outcome_confidence: Final confidence label (low/med/high)
        latency_ms: Total latency
        fallback_used: Whether fallback was triggered
        error: Error message if any
        **kwargs: Additional fields
    """
    trace_event = {
        "event": event,
    }
    
    # Add classification
    if reasoning_type or risk_level or domain:
        trace_event["classification"] = {
            k: v for k, v in [
                ("reasoning_type", reasoning_type),
                ("risk_level", risk_level),
                ("domain", domain),
            ] if v is not None
        }
    
    # Add pipeline info
    if selected_pipeline:
        trace_event["selected_pipeline"] = selected_pipeline
        trace_event["reasoning_method"] = selected_pipeline.lower().replace("pipeline_", "")
    
    if technique_ids:
        trace_event["technique_ids"] = technique_ids
    
    # Add tool calls (sanitized)
    if tool_calls:
        # Remove any sensitive data, keep only summary
        sanitized_tools = []
        for tc in tool_calls:
            sanitized_tools.append({
                "tool_name": tc.get("tool_name", "unknown"),
                "ok": tc.get("ok", True),
                "latency_ms": tc.get("latency_ms"),
                "truncated_output_size": tc.get("truncated_output_size"),
            })
        trace_event["tool_calls"] = sanitized_tools
    
    # Add verification
    if verification:
        trace_event["verification"] = verification
    
    # Add outcome
    if outcome_confidence:
        trace_event["outcome_confidence"] = outcome_confidence
    
    # Add metrics
    if latency_ms is not None:
        trace_event["latency_ms"] = latency_ms
    
    if fallback_used:
        trace_event["fallback_used"] = True
    
    if error:
        trace_event["error"] = error[:200]  # Truncate error message
    
    if query_hash:
        trace_event["query_hash"] = query_hash
    
    # Add any extra kwargs
    trace_event.update(kwargs)
    
    emit_trace(trace_event)
