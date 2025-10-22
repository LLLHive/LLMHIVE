"""Diagnostics endpoints for provider visibility."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from ..orchestrator import Orchestrator
from .orchestration import get_orchestrator

router = APIRouter(prefix="/providers", tags=["diagnostics"])


@router.get("/", summary="List configured providers")
async def list_providers(orchestrator: Orchestrator = Depends(get_orchestrator)) -> dict[str, object]:
    """Return provider availability and helpful diagnostics."""

    status = orchestrator.provider_status()
    available = [name for name, details in status.items() if details.get("status") == "available"]
    real_providers = [name for name in available if not status[name].get("stub")]
    unavailable = [name for name, details in status.items() if details.get("status") != "available"]

    return {
        "available_providers": available,
        "real_providers": real_providers,
        "stub_only": bool(available) and not real_providers,
        "unavailable_providers": unavailable,
        "providers": status,
    }
