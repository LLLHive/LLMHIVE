"""Top-level API router for LLMHive backend.

This module exists primarily so that ``from .api import api_router`` in
``main.py`` works correctly in all environments (including Cloud Run).

It aggregates lower-level routers (system/status, billing, webhooks, etc.)
under the common ``/api/v1`` prefix.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter

logger = logging.getLogger(__name__)

# Root API router that main.py includes with:
#   app.include_router(api_router, prefix="/api/v1")
api_router = APIRouter()

# Import and include sub-routers.
# NOTE: Import from .status (sibling module) to avoid circular import with this
# package, which is ``src.llmhive.app.api``.
try:
    from . import status  # type: ignore

    if hasattr(status, "router"):
        api_router.include_router(status.router, prefix="/system", tags=["system"])
    else:
        logger.warning(
            "Status router not found in api.status; /api/v1/system routes may be missing."
        )
except Exception as exc:  # pragma: no cover - defensive logging only
    logger.warning("Failed to import status router: %s", exc)


