"""API endpoints for query status updates."""
from __future__ import annotations

import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, status
from datetime import datetime

logger = logging.getLogger(__name__)

# Included in api/__init__.py with prefix "/status"
router = APIRouter()

# In-memory status store (in production, use Redis or database)
_status_store: Dict[str, Dict[str, Any]] = {}


@router.get("/{query_id}", status_code=status.HTTP_200_OK)
def get_status(query_id: str) -> Dict[str, Any]:
    """
    Get the current status of a query.
    
    Returns status information including:
    - stage: Current processing stage (e.g., "planning", "model_query", "verification", "complete")
    - status: Status of current stage (e.g., "running", "completed", "error")
    - model: Current model being used (if applicable)
    - progress: Progress percentage (0-100)
    - message: Human-readable status message
    - timestamp: Last update timestamp
    """
    if query_id not in _status_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Query ID '{query_id}' not found"
        )
    
    return _status_store[query_id]


@router.post("/{query_id}", status_code=status.HTTP_200_OK)
def update_status(
    query_id: str,
    stage: str,
    status_value: str = "running",
    model: Optional[str] = None,
    progress: Optional[int] = None,
    message: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Update the status of a query.
    
    This endpoint is called internally by the orchestrator to update query status.
    """
    _status_store[query_id] = {
        "query_id": query_id,
        "stage": stage,
        "status": status_value,
        "model": model,
        "progress": progress,
        "message": message or f"Processing: {stage}",
        "timestamp": datetime.utcnow().isoformat(),
    }
    logger.debug("Status updated for query %s: %s - %s", query_id, stage, status_value)
    return _status_store[query_id]


@router.delete("/{query_id}", status_code=status.HTTP_200_OK)
def clear_status(query_id: str) -> Dict[str, str]:
    """Clear status for a query (cleanup after completion)."""
    if query_id in _status_store:
        del _status_store[query_id]
        logger.debug("Status cleared for query %s", query_id)
    return {"message": f"Status cleared for query {query_id}"}

