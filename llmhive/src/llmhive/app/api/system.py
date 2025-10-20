"""System endpoints such as health checks."""
from __future__ import annotations

from fastapi import APIRouter

from ..config import settings
from ..orchestrator import Orchestrator

router = APIRouter()


def _health_payload() -> dict[str, object]:
    orchestrator = Orchestrator()
    return {
        "status": "ok",
        "providers": orchestrator.provider_status(),
        "default_models": settings.default_models,
    }


@router.get("/healthz", summary="Health check")
async def health_check() -> dict[str, object]:
    """Return a simple health payload for readiness probes."""

    return _health_payload()


@router.get("/api/v1/healthz", summary="Health check (api v1)")
async def health_check_v1() -> dict[str, object]:
    return _health_payload()
