"""Stripe payment routes for subscription checkout.

Stripe webhook handling: This module provides endpoints for creating Stripe checkout sessions
and handling payment flows.
"""
from __future__ import annotations

import logging
import os
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..billing.pricing import TierName, get_pricing_manager
from ..billing.payments import get_payment_processor, STRIPE_AVAILABLE
from ..billing.subscription_sync import upsert_subscription_from_checkout_session

logger = logging.getLogger(__name__)

router = APIRouter()


def _price_id_for_checkout(tier_lower: str, billing_cycle: str) -> Optional[str]:
    """Resolve current customer-facing Stripe price IDs.

    Standard/Premium must use current env vars, not legacy BASIC/PRO fallbacks,
    because those can point at retired $9.99/$29.99 products.
    """
    monthly = billing_cycle == "monthly"
    if tier_lower in ("lite", "standard"):
        return settings.stripe_price_id_standard_monthly if monthly else settings.stripe_price_id_standard_annual
    if tier_lower in ("pro", "premium"):
        return settings.stripe_price_id_premium_monthly if monthly else settings.stripe_price_id_premium_annual
    if tier_lower == "enterprise":
        return settings.stripe_price_id_enterprise_monthly if monthly else settings.stripe_price_id_enterprise_annual
    if tier_lower == "maximum":
        return settings.stripe_price_id_maximum_monthly if monthly else settings.stripe_price_id_maximum_annual
    return None


class CreateCheckoutRequest(BaseModel):
    """Request to create a Stripe checkout session."""
    
    tier: str = Field(..., description="Pricing tier name (lite, pro, enterprise, maximum)")
    billing_cycle: str = Field(default="monthly", description="Billing cycle: 'monthly' or 'annual'")
    user_email: Optional[str] = Field(default=None, description="User email for Stripe customer")
    user_id: str = Field(..., description="Internal user ID to link subscription")


class CheckoutSessionResponse(BaseModel):
    """Response with checkout session URL."""
    
    session_id: str
    url: str
    message: str = "Redirect user to the URL to complete payment"


@router.post("/create-checkout-session", response_model=CheckoutSessionResponse, status_code=status.HTTP_200_OK)
def create_checkout_session(
    request: CreateCheckoutRequest,
    db: Session = Depends(get_db),
) -> CheckoutSessionResponse:
    """Stripe webhook handling: Create a Stripe Checkout session for subscription payment.
    
    This endpoint creates a Stripe Checkout session that redirects the user to Stripe's
    hosted payment page. After successful payment, Stripe will send a webhook event.
    
    Final path: /api/v1/payments/create-checkout-session
    """
    if not STRIPE_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Stripe integration not available. Install stripe package.",
        )
    
    processor = get_payment_processor()
    if processor is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Stripe payment processor not configured. Set STRIPE_API_KEY environment variable.",
        )
    
    try:
        import stripe
        
        # Stripe webhook handling: Validate tier
        pricing_manager = get_pricing_manager()
        tier = pricing_manager.get_tier(request.tier)
        if tier is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid tier: {request.tier}",
            )
        
        # Stripe webhook handling: Validate billing cycle
        if request.billing_cycle not in ("monthly", "annual"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="billing_cycle must be 'monthly' or 'annual'",
            )
        
        # Stripe webhook handling: Get Stripe Price ID for the tier
        # SIMPLIFIED 4-TIER STRUCTURE (January 2026)
        tier_lower = request.tier.lower()
        price_id = _price_id_for_checkout(tier_lower, request.billing_cycle)

        if tier_lower == "free":
            # Free tier doesn't require payment
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Free tier does not require payment. Use subscription creation endpoint instead.",
            )
        
        if not price_id:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Stripe Price ID not configured for tier {request.tier} ({request.billing_cycle}). "
                       "Set STRIPE_PRICE_ID_{TIER}_{CYCLE} environment variable.",
            )
        
        # Stripe webhook handling: Create or retrieve Stripe customer
        customer_id = None
        if request.user_email:
            try:
                # Check if customer already exists
                customers = stripe.Customer.list(email=request.user_email, limit=1)
                if customers.data:
                    customer_id = customers.data[0].id
                    logger.debug("Found existing Stripe customer %s for email %s", customer_id, request.user_email)
                else:
                    # Create new customer
                    customer = processor.create_customer(
                        user_id=request.user_id,
                        email=request.user_email,
                    )
                    customer_id = customer.id
                    logger.info("Created Stripe customer %s for user %s", customer_id, request.user_id)
            except Exception as exc:
                logger.warning("Failed to create/retrieve Stripe customer: %s", exc)
                # Continue without customer - Stripe will create one during checkout
        
        # Stripe webhook handling: Create checkout session
        # Stripe rejects passing both ``customer`` and ``customer_email`` on the same session.
        session_kwargs: dict = {
            "payment_method_types": ["card"],
            "mode": "subscription",
            "line_items": [{"price": price_id, "quantity": 1}],
            "client_reference_id": request.user_id,
            "metadata": {
                "user_id": request.user_id,
                "tier": request.tier.lower(),
                "billing_cycle": request.billing_cycle,
            },
            "success_url": settings.stripe_success_url + f"?session_id={{CHECKOUT_SESSION_ID}}",
            "cancel_url": settings.stripe_cancel_url,
            "allow_promotion_codes": True,
        }
        if customer_id:
            session_kwargs["customer"] = customer_id
        elif request.user_email:
            session_kwargs["customer_email"] = request.user_email

        subscription_data: dict = {
            "metadata": {
                "user_id": request.user_id,
                "tier": tier_lower,
                "billing_cycle": request.billing_cycle,
            },
        }
        if tier_lower == "lite" and request.billing_cycle == "monthly":
            trial_days = int(os.getenv("STANDARD_TRIAL_DAYS", "3"))
            if trial_days > 0:
                subscription_data["trial_period_days"] = trial_days
                subscription_data["metadata"]["is_trial"] = "true"
        session_kwargs["subscription_data"] = subscription_data

        checkout_session = stripe.checkout.Session.create(**session_kwargs)
        
        logger.info(
            "Stripe webhook handling: Created checkout session %s for user %s (tier: %s, cycle: %s)",
            checkout_session.id,
            request.user_id,
            request.tier,
            request.billing_cycle,
        )
        
        return CheckoutSessionResponse(
            session_id=checkout_session.id,
            url=checkout_session.url,
            message="Redirect user to the URL to complete payment",
        )
        
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Stripe webhook handling: Failed to create checkout session: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create checkout session",
        ) from exc


@router.get("/checkout-session/{session_id}", status_code=status.HTTP_200_OK)
def get_checkout_session(
    session_id: str,
) -> dict:
    """Stripe webhook handling: Get checkout session details.
    
    Useful for checking session status after redirect.
    
    Final path: /api/v1/payments/checkout-session/{session_id}
    """
    if not STRIPE_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Stripe integration not available",
        )
    
    processor = get_payment_processor()
    if processor is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Stripe payment processor not configured",
        )
    
    try:
        import stripe
        
        session = stripe.checkout.Session.retrieve(session_id)
        
        return {
            "session_id": session.id,
            "status": session.payment_status,
            "customer": session.customer,
            "subscription": session.subscription,
            "client_reference_id": session.client_reference_id,
            "metadata": session.metadata,
        }
        
    except Exception as exc:
        logger.exception("Stripe webhook handling: Failed to retrieve checkout session: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve checkout session",
        ) from exc


@router.post(
    "/checkout-session/{session_id}/ensure-subscription",
    status_code=status.HTTP_200_OK,
)
def ensure_subscription_from_session(session_id: str) -> dict:
    """Synchronously upsert the Firestore subscription for a paid checkout session.

    Called by the frontend success page so the user's entitlement is active in
    Firestore before they click through to the app, eliminating the redirect
    loop that previously occurred while waiting for the Stripe webhook.

    Idempotent: if the webhook already created the row, this updates it with
    the latest fields. Returns ``{"created": bool, "updated": bool, ...}``.

    Final path: /api/v1/payments/checkout-session/{session_id}/ensure-subscription
    """
    if not STRIPE_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Stripe integration not available",
        )

    processor = get_payment_processor()
    if processor is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Stripe payment processor not configured",
        )

    try:
        import stripe

        session = stripe.checkout.Session.retrieve(session_id)
    except Exception as exc:
        logger.exception("ensure_subscription: failed to retrieve session %s: %s", session_id, exc)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Checkout session not found",
        ) from exc

    try:
        result = upsert_subscription_from_checkout_session(stripe, session)
    except ValueError as exc:
        # Surface session-not-paid / missing-fields as 409 so the client can
        # distinguish them from server errors and retry / abandon as needed.
        logger.info("ensure_subscription: session %s not eligible: %s", session_id, exc)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.exception("ensure_subscription: upsert failed for %s: %s", session_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to ensure subscription",
        ) from exc

    return {
        "session_id": session_id,
        "created": result.created,
        "updated": result.updated,
        "user_id": result.user_id,
        "tier_name": result.tier_name,
        "billing_cycle": result.get("billing_cycle"),
        "stripe_subscription_id": result.get("stripe_subscription_id"),
    }

