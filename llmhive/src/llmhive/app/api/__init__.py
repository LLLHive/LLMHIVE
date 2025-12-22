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
        
        # Also register at /stripe/webhook for user's preferred URL
        api_router.include_router(webhooks.router, prefix="/stripe", tags=["stripe"])
        logger.info("Stripe webhook routes also registered at /api/v1/stripe")
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

# RLHF Feedback routes (Pinecone-powered)
try:
    from ..rlhf.pinecone_feedback import create_feedback_router
    
    feedback_router = create_feedback_router()
    api_router.include_router(feedback_router, prefix="/rlhf", tags=["rlhf"])
    logger.info("RLHF Feedback routes registered at /api/v1/rlhf")
except Exception as exc:
    logger.warning("Failed to import RLHF feedback router: %s", exc)

# Spell Check routes
try:
    from ..tools.spell_check import create_spell_check_router
    
    spell_check_router = create_spell_check_router()
    api_router.include_router(spell_check_router, prefix="/spellcheck", tags=["spellcheck"])
    logger.info("Spell Check routes registered at /api/v1/spellcheck")
except Exception as exc:
    logger.warning("Failed to import spell check router: %s", exc)

# Metrics and observability routes
try:
    from . import metrics  # type: ignore
    
    if hasattr(metrics, "router"):
        api_router.include_router(metrics.router, prefix="/metrics", tags=["metrics"])
        logger.info("Metrics routes registered at /api/v1/metrics")
except Exception as exc:
    logger.warning("Failed to import metrics router: %s", exc)

# OpenRouter integration routes (models, rankings, inference)
try:
    from . import openrouter  # type: ignore
    
    if hasattr(openrouter, "router"):
        api_router.include_router(openrouter.router, tags=["openrouter"])
        logger.info("OpenRouter routes registered at /api/v1/openrouter")
except Exception as exc:
    logger.warning("Failed to import OpenRouter router: %s", exc)

# Pinecone-backed model API (persistent storage, primary source)
try:
    from . import pinecone_models  # type: ignore
    
    if hasattr(pinecone_models, "router"):
        api_router.include_router(pinecone_models.router, tags=["models"])
        logger.info("Pinecone Models routes registered at /api/v1/models")
except Exception as exc:
    logger.warning("Failed to import Pinecone models router: %s", exc)

