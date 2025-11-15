"""System endpoints such as health checks."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..diagnostics import DiagnosticsService
from ..schemas import DiagnosticsResponse
from .orchestration import _orchestrator

router = APIRouter()


@router.get("/healthz", summary="Health check")
async def health_check() -> dict[str, str]:
    """Return a simple health payload for readiness probes."""

    return {"status": "ok"}


@router.get(
    "/diagnostics",
    response_model=DiagnosticsResponse,
    summary="Runtime diagnostics for orchestration features",
)
def diagnostics(
    user_id: str | None = Query(
        default=None,
        description="Optional user identifier to scope knowledge base samples.",
    ),
    db: Session = Depends(get_db),
) -> DiagnosticsResponse:
    """Expose orchestration readiness signals useful for troubleshooting."""

    service = DiagnosticsService(db, _orchestrator)
    payload = service.collect(user_id=user_id)
    return DiagnosticsResponse(**payload.asdict())
