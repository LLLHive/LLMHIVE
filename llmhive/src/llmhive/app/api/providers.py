"""Diagnostics endpoints for provider visibility."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from ..orchestrator import Orchestrator
from .orchestration import get_orchestrator

router = APIRouter(prefix="/providers", tags=["diagnostics"])


@router.get("/", summary="List configured providers")
async def list_providers(orchestrator: Orchestrator = Depends(get_orchestrator)) -> dict[str, object]:
    """Return provider availability and the configured provider keys."""

    status = orchestrator.provider_status()
    available = [name for name, details in status.items() if details.get("status") == "available"]
    return {
        "available_providers": available,
        "providers": status,
    }
