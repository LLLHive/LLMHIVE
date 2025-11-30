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

# Billing API routes
try:
    from . import billing  # type: ignore
    
    if hasattr(billing, "router"):
        api_router.include_router(billing.router, prefix="/billing", tags=["billing"])
        logger.info("Billing API routes registered at /api/v1/billing")
except Exception as exc:
    logger.warning("Failed to import billing router: %s", exc)

# Payment API routes (Stripe checkout)
try:
    from . import payment_routes  # type: ignore
    
    if hasattr(payment_routes, "router"):
        api_router.include_router(payment_routes.router, prefix="/payments", tags=["payments"])
        logger.info("Payment API routes registered at /api/v1/payments")
except Exception as exc:
    logger.warning("Failed to import payment routes: %s", exc)

# Webhook routes (Stripe webhooks)
try:
    from . import webhooks  # type: ignore
    
    if hasattr(webhooks, "router"):
        api_router.include_router(webhooks.router, prefix="/webhooks", tags=["webhooks"])
        logger.info("Webhook routes registered at /api/v1/webhooks")
except Exception as exc:
    logger.warning("Failed to import webhook routes: %s", exc)

# Admin API routes
try:
    from . import admin  # type: ignore
    
    if hasattr(admin, "router"):
        api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
        logger.info("Admin API routes registered at /api/v1/admin")
except Exception as exc:
    logger.warning("Failed to import admin router: %s", exc)

