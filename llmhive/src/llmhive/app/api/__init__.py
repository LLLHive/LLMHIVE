"""Top-level API router for LLMHive backend.

This module exists primarily so that ``from .api import api_router`` in
``main.py`` works correctly in all environments (including Cloud Run).

It aggregates lower-level routers (system/status, billing, webhooks, etc.)
under the common ``/api/v1`` prefix.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter

from ..api import status  # type: ignore

logger = logging.getLogger(__name__)

# Root API router that main.py includes with:
#   app.include_router(api_router, prefix="/api/v1")
api_router = APIRouter()

# System/status endpoints (health, version info, etc.)
if hasattr(status, "router"):
    api_router.include_router(status.router, prefix="/system", tags=["system"])
else:
    logger.warning("Status router not found in api.status; /api/v1/system routes may be missing.")


