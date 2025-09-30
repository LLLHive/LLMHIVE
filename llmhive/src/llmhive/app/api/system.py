"""System endpoints such as health checks."""
from __future__ import annotations

from fastapi import APIRouter

router = APIRouter()


@router.get("/healthz", summary="Health check")
async def health_check() -> dict[str, str]:
    """Return a simple health payload for readiness probes."""

    return {"status": "ok"}
