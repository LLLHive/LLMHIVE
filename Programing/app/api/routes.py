"""Example API routes."""

from fastapi import APIRouter

router = APIRouter(tags=["examples"])


@router.get("/ping")
async def ping() -> dict[str, str]:
    """Simple ping endpoint."""
    return {"message": "pong"}
