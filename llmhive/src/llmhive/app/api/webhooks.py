"""Stripe webhook handling for subscription events.

Stripe webhook handling: This module processes Stripe webhook events to keep
subscriptions in sync with Stripe's payment system.
"""
from __future__ import annotations

import datetime as dt
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..billing.payments import get_payment_processor, STRIPE_AVAILABLE
from ..billing.subscription import SubscriptionService
from ..billing.pricing import TierName, get_pricing_manager
from ..models import Subscription, SubscriptionStatus

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/stripe-webhook", status_code=status.HTTP_200_OK)
async def stripe_webhook(
    request: Request,
    db: Session = Depends(get_db),
) -> dict:
    """Stripe webhook handling: Process Stripe webhook events.
    
    This endpoint receives webhook events from Stripe and updates our database
    accordingly. It verifies the webhook signature before processing.
    
    Final path: /api/v1/webhooks/stripe-webhook
    
    Note: In production, configure this endpoint in Stripe Dashboard:
    - Go to Developers > Webhooks
    - Add endpoint URL
    - Select events: checkout.session.completed, customer.subscription.*, invoice.payment_*
    - Copy webhook signing secret to STRIPE_WEBHOOK_SECRET
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
    
    # Stripe webhook handling: Get webhook signature from headers
    signature = request.headers.get("stripe-signature")
    if not signature:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing stripe-signature header",
        )
    
    # Stripe webhook handling: Get raw payload
    payload = await request.body()
    
    try:
        # Stripe webhook handling: Verify webhook signature and construct event
        result = processor.handle_webhook(
            payload=payload,
            signature=signature,
            webhook_secret=settings.stripe_webhook_secret,
            db_session=db,
        )
        
        # Stripe webhook handling: Process additional events not handled by processor
        import stripe
        
        event = stripe.Webhook.construct_event(
            payload,
            signature,
            settings.stripe_webhook_secret or "",
        )
        
        event_type = event["type"]
        event_data = event["data"]["object"]
        
        service = SubscriptionService(db)
        pricing_manager = get_pricing_manager()
        
        # Stripe webhook handling: Handle checkout.session.completed
        if event_type == "checkout.session.completed":
            session = event_data
            
            # Stripe webhook handling: Get user ID from client_reference_id or metadata
            user_id = session.get("client_reference_id")
            if not user_id:
                metadata = session.get("metadata", {})
                user_id = metadata.get("user_id")
            
            if not user_id:
                logger.error(
                    "Stripe webhook handling: No user_id found in checkout session %s",
                    session.get("id")
                )
                return {"received": True, "processed": False, "error": "No user_id in session"}
            
            # Stripe webhook handling: Get subscription and tier from session
            stripe_subscription_id = session.get("subscription")
            if not stripe_subscription_id:
                logger.warning(
                    "Stripe webhook handling: No subscription in checkout session %s",
                    session.get("id")
                )
                return {"received": True, "processed": False, "error": "No subscription in session"}
            
            # Stripe webhook handling: Retrieve subscription from Stripe to get details
            try:
                stripe_subscription = stripe.Subscription.retrieve(stripe_subscription_id)
                stripe_customer_id = stripe_subscription.customer
                
                # Stripe webhook handling: Get tier from metadata or price
                metadata = session.get("metadata", {})
                tier_name = metadata.get("tier", "pro").lower()  # Default to pro
                
                # Stripe webhook handling: Get billing cycle from metadata
                billing_cycle = metadata.get("billing_cycle", "monthly")
                
                # Stripe webhook handling: Get period dates from subscription
                period_start = dt.datetime.fromtimestamp(
                    stripe_subscription.current_period_start,
                    tz=dt.timezone.utc
                ).replace(tzinfo=None)
                period_end = dt.datetime.fromtimestamp(
                    stripe_subscription.current_period_end,
                    tz=dt.timezone.utc
                ).replace(tzinfo=None)
                
                # Stripe webhook handling: Create or update subscription in our DB
                existing_subscription = (
                    db.query(Subscription)
                    .filter(Subscription.stripe_subscription_id == stripe_subscription_id)
                    .first()
                )
                
                if existing_subscription:
                    # Stripe webhook handling: Update existing subscription
                    existing_subscription.status = SubscriptionStatus.ACTIVE
                    existing_subscription.tier_name = tier_name
                    existing_subscription.billing_cycle = billing_cycle
                    existing_subscription.current_period_start = period_start
                    existing_subscription.current_period_end = period_end
                    existing_subscription.stripe_customer_id = stripe_customer_id
                    logger.info(
                        "Stripe webhook handling: Updated subscription for user %s (tier: %s)",
                        user_id,
                        tier_name
                    )
                else:
                    # Stripe webhook handling: Create new subscription
                    subscription = service.create_subscription(
                        user_id=user_id,
                        tier_name=tier_name,
                        billing_cycle=billing_cycle,
                        stripe_customer_id=stripe_customer_id,
                        stripe_subscription_id=stripe_subscription_id,
                    )
                    # Update period dates (create_subscription sets defaults)
                    subscription.current_period_start = period_start
                    subscription.current_period_end = period_end
                    logger.info(
                        "Stripe webhook handling: Created subscription for user %s (tier: %s, cycle: %s)",
                        user_id,
                        tier_name,
                        billing_cycle
                    )
                
                db.commit()
                
            except Exception as exc:
                logger.exception(
                    "Stripe webhook handling: Failed to process checkout.session.completed: %s",
                    exc
                )
                db.rollback()
                return {"received": True, "processed": False, "error": str(exc)}
        
        # Stripe webhook handling: Handle customer.subscription.updated
        elif event_type == "customer.subscription.updated":
            stripe_subscription_id = event_data.get("id")
            subscription = (
                db.query(Subscription)
                .filter(Subscription.stripe_subscription_id == stripe_subscription_id)
                .first()
            )
            
            if subscription:
                # Stripe webhook handling: Update period dates
                period_start = dt.datetime.fromtimestamp(
                    event_data.get("current_period_start", 0),
                    tz=dt.timezone.utc
                ).replace(tzinfo=None)
                period_end = dt.datetime.fromtimestamp(
                    event_data.get("current_period_end", 0),
                    tz=dt.timezone.utc
                ).replace(tzinfo=None)
                service.update_subscription_period(
                    subscription.id,
                    period_start,
                    period_end,
                )
                
                # Stripe webhook handling: Update status
                status_map = {
                    "active": SubscriptionStatus.ACTIVE,
                    "canceled": SubscriptionStatus.CANCELLED,
                    "past_due": SubscriptionStatus.PAST_DUE,
                    "trialing": SubscriptionStatus.TRIALING,
                    "unpaid": SubscriptionStatus.EXPIRED,
                }
                stripe_status = event_data.get("status")
                if stripe_status in status_map:
                    service.update_subscription_status(subscription.id, status_map[stripe_status])
                
                # Stripe webhook handling: Update tier if changed in metadata
                metadata = event_data.get("metadata", {})
                if "tier_name" in metadata:
                    new_tier = metadata["tier_name"]
                    if new_tier != subscription.tier_name:
                        tier = pricing_manager.get_tier(new_tier)
                        if tier:
                            subscription.tier_name = new_tier
                            logger.info(
                                "Stripe webhook handling: Updated tier for subscription %d: %s -> %s",
                                subscription.id,
                                subscription.tier_name,
                                new_tier
                            )
                
                db.commit()
        
        # Stripe webhook handling: Handle customer.subscription.deleted
        elif event_type == "customer.subscription.deleted":
            stripe_subscription_id = event_data.get("id")
            subscription = (
                db.query(Subscription)
                .filter(Subscription.stripe_subscription_id == stripe_subscription_id)
                .first()
            )
            
            if subscription:
                # Stripe webhook handling: Cancel subscription
                service.update_subscription_status(subscription.id, SubscriptionStatus.CANCELLED)
                subscription.cancelled_at = dt.datetime.utcnow()
                db.commit()
                logger.info(
                    "Stripe webhook handling: Cancelled subscription %d (user: %s)",
                    subscription.id,
                    subscription.user_id
                )
        
        # Stripe webhook handling: Handle invoice.payment_failed
        elif event_type == "invoice.payment_failed":
            stripe_subscription_id = event_data.get("subscription")
            if stripe_subscription_id:
                subscription = (
                    db.query(Subscription)
                    .filter(Subscription.stripe_subscription_id == stripe_subscription_id)
                    .first()
                )
                if subscription:
                    # Stripe webhook handling: Mark as past due
                    service.update_subscription_status(subscription.id, SubscriptionStatus.PAST_DUE)
                    db.commit()
                    logger.warning(
                        "Stripe webhook handling: Payment failed for subscription %d (user: %s)",
                        subscription.id,
                        subscription.user_id
                    )
        
        return {"received": True, "processed": True, "event_type": event_type}
        
    except ValueError as exc:
        logger.error("Stripe webhook handling: Invalid webhook payload: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid webhook payload",
        ) from exc
    except Exception as exc:
        if "SignatureVerificationError" in str(type(exc).__name__):
            logger.error("Stripe webhook handling: Invalid webhook signature: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid webhook signature",
            ) from exc
        logger.exception("Stripe webhook handling: Failed to process webhook: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process webhook",
        ) from exc


# Alias route for user's preferred URL: /api/v1/stripe/webhook
@router.post("/webhook", status_code=status.HTTP_200_OK)
async def stripe_webhook_alias(
    request: Request,
    db: Session = Depends(get_db),
) -> dict:
    """Alias for Stripe webhook at /api/v1/stripe/webhook.
    
    This is an alias route that calls the main stripe_webhook handler.
    Configure this URL in your Stripe Dashboard:
    https://llmhive-orchestrator-792354158895.us-east1.run.app/api/v1/stripe/webhook
    """
    return await stripe_webhook(request, db)


@router.post("/stripe-webhook/test", status_code=status.HTTP_200_OK)
async def test_stripe_webhook(
    event_type: str,
    user_id: str,
    tier: str = "pro",
    billing_cycle: str = "monthly",
    db: Session = Depends(get_db),
) -> dict:
    """Stripe webhook handling: Test endpoint to simulate webhook events.
    
    This endpoint allows testing webhook processing without actual Stripe events.
    Useful for development and testing.
    
    Final path: /api/v1/webhooks/stripe-webhook/test?event_type={type}&user_id={id}&tier={tier}&billing_cycle={cycle}
    
    Example:
        POST /api/v1/webhooks/stripe-webhook/test?event_type=checkout.session.completed&user_id=user123&tier=pro&billing_cycle=monthly
    """
    try:
        service = SubscriptionService(db)
        pricing_manager = get_pricing_manager()
        
        # Stripe webhook handling: Simulate checkout.session.completed
        if event_type == "checkout.session.completed":
            # Create subscription directly (simulating successful checkout)
            subscription = service.create_subscription(
                user_id=user_id,
                tier_name=tier,
                billing_cycle=billing_cycle,
            )
            db.commit()
            
            logger.info(
                "Stripe webhook handling: Test - Created subscription for user %s (tier: %s)",
                user_id,
                tier
            )
            
            return {
                "test": True,
                "event_type": event_type,
                "subscription_id": subscription.id,
                "user_id": user_id,
                "tier": tier,
            }
        
        # Stripe webhook handling: Simulate customer.subscription.deleted
        elif event_type == "customer.subscription.deleted":
            subscription = service.get_user_subscription(user_id)
            if subscription:
                service.cancel_subscription(subscription.id, cancel_immediately=True)
                db.commit()
                
                logger.info(
                    "Stripe webhook handling: Test - Cancelled subscription for user %s",
                    user_id
                )
                
                return {
                    "test": True,
                    "event_type": event_type,
                    "user_id": user_id,
                    "cancelled": True,
                }
            else:
                return {
                    "test": True,
                    "event_type": event_type,
                    "user_id": user_id,
                    "error": "No subscription found",
                }
        
        else:
            return {
                "test": True,
                "event_type": event_type,
                "error": f"Unsupported test event type: {event_type}",
            }
            
    except Exception as exc:
        logger.exception("Stripe webhook handling: Test webhook failed: %s", exc)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Test webhook failed: {exc}",
        ) from exc

