"""System endpoints such as health checks."""
from __future__ import annotations

from fastapi import APIRouter

router = APIRouter()


@router.get("/healthz", summary="Health check")
async def health_check() -> dict[str, str]:
    """Return a simple health payload for readiness probes."""

    return {"status": "ok"}

@router.get("/api/v1/healthz", summary="Health check (api v1)")
async def health_check_v1() -> dict[str, str]:
    return {"status": "ok"}
