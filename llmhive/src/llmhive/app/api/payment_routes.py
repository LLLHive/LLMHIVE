"""Stripe payment routes for subscription checkout.

Stripe webhook handling: This module provides endpoints for creating Stripe checkout sessions
and handling payment flows.
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..billing.pricing import TierName, get_pricing_manager
from ..billing.payments import get_payment_processor, STRIPE_AVAILABLE

logger = logging.getLogger(__name__)

router = APIRouter()


class CreateCheckoutRequest(BaseModel):
    """Request to create a Stripe checkout session."""
    
    tier: str = Field(..., description="Pricing tier name (free, basic, pro, enterprise)")
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
        price_id = None
        if request.tier.lower() == "free":
            # Free tier doesn't require payment
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Free tier does not require payment. Use subscription creation endpoint instead.",
            )
        elif request.tier.lower() == "basic":
            if request.billing_cycle == "monthly":
                price_id = settings.stripe_price_id_basic_monthly
            else:
                price_id = settings.stripe_price_id_basic_annual
        elif request.tier.lower() == "pro":
            if request.billing_cycle == "monthly":
                price_id = settings.stripe_price_id_pro_monthly
            else:
                price_id = settings.stripe_price_id_pro_annual
        elif request.tier.lower() == "enterprise":
            if request.billing_cycle == "monthly":
                price_id = settings.stripe_price_id_enterprise_monthly
            else:
                price_id = settings.stripe_price_id_enterprise_annual
        
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
        # Use client_reference_id to link session to our user
        checkout_session = stripe.checkout.Session.create(
            customer=customer_id,  # Optional - Stripe will create if not provided
            customer_email=request.user_email,  # Pre-fill email if customer not created
            payment_method_types=["card"],
            mode="subscription",
            line_items=[
                {
                    "price": price_id,
                    "quantity": 1,
                }
            ],
            # Stripe webhook handling: Link session to user via client_reference_id
            client_reference_id=request.user_id,
            # Stripe webhook handling: Pass metadata for webhook processing
            metadata={
                "user_id": request.user_id,
                "tier": request.tier.lower(),
                "billing_cycle": request.billing_cycle,
            },
            # Stripe webhook handling: Redirect URLs
            success_url=settings.stripe_success_url + f"?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=settings.stripe_cancel_url,
            # Stripe webhook handling: Allow promotion codes
            allow_promotion_codes=True,
        )
        
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

