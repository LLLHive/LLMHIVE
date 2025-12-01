"""Stripe webhook handling for subscription events.

Uses Firestore for subscription storage (no SQL database needed).
No Vertex AI required - embeddings handled by Pinecone.
"""
from __future__ import annotations

import datetime as dt
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Request, status

from ..config import settings
from ..firestore_db import (
    FirestoreSubscriptionService,
    is_firestore_available,
)
from ..billing.payments import get_payment_processor, STRIPE_AVAILABLE

logger = logging.getLogger(__name__)

router = APIRouter()


def get_subscription_service() -> FirestoreSubscriptionService:
    """Get Firestore subscription service."""
    return FirestoreSubscriptionService()


@router.post("/stripe-webhook", status_code=status.HTTP_200_OK)
async def stripe_webhook(request: Request) -> dict:
    """Stripe webhook handling: Process Stripe webhook events.
    
    This endpoint receives webhook events from Stripe and updates Firestore.
    No SQL database required - uses Firestore for subscription storage.
    
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
            detail="Stripe SDK not available. Install with: pip install stripe",
        )
    
    if not is_firestore_available():
        logger.warning("Firestore not available - subscription will not be persisted")
    
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
        import stripe
        
        # Stripe webhook handling: Verify webhook signature and construct event
        webhook_secret = settings.stripe_webhook_secret
        if not webhook_secret:
            logger.error("STRIPE_WEBHOOK_SECRET not configured")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Webhook secret not configured",
            )
        
        event = stripe.Webhook.construct_event(
            payload,
            signature,
            webhook_secret,
        )
        
        event_type = event["type"]
        event_data = event["data"]["object"]
        
        service = get_subscription_service()
        
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
            
            # Stripe webhook handling: Get subscription from session
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
                tier_name = metadata.get("tier", "pro").lower()
                billing_cycle = metadata.get("billing_cycle", "monthly")
                
                # Stripe webhook handling: Check if subscription already exists
                existing = service.get_subscription_by_stripe_id(stripe_subscription_id)
                
                if existing:
                    # Update existing subscription
                    service.update_subscription(existing["id"], {
                        "status": "active",
                        "tier_name": tier_name,
                        "billing_cycle": billing_cycle,
                        "stripe_customer_id": stripe_customer_id,
                    })
                    logger.info(
                        "Stripe webhook handling: Updated subscription for user %s (tier: %s)",
                        user_id,
                        tier_name
                    )
                else:
                    # Create new subscription in Firestore
                    subscription = service.create_subscription(
                        user_id=user_id,
                        tier_name=tier_name,
                        billing_cycle=billing_cycle,
                        stripe_customer_id=stripe_customer_id,
                        stripe_subscription_id=stripe_subscription_id,
                    )
                    
                    if subscription:
                        logger.info(
                            "Stripe webhook handling: Created subscription %s for user %s (tier: %s)",
                            subscription.get("id"),
                            user_id,
                            tier_name
                        )
                    else:
                        logger.error("Failed to create subscription in Firestore")
                
            except Exception as exc:
                logger.exception(
                    "Stripe webhook handling: Failed to process checkout.session.completed: %s",
                    exc
                )
                return {"received": True, "processed": False, "error": str(exc)}
        
        # Stripe webhook handling: Handle customer.subscription.updated
        elif event_type == "customer.subscription.updated":
            stripe_subscription_id = event_data.get("id")
            subscription = service.get_subscription_by_stripe_id(stripe_subscription_id)
            
            if subscription:
                # Stripe webhook handling: Map Stripe status to our status
                status_map = {
                    "active": "active",
                    "canceled": "cancelled",
                    "past_due": "past_due",
                    "trialing": "trialing",
                    "unpaid": "expired",
                }
                stripe_status = event_data.get("status")
                our_status = status_map.get(stripe_status, "active")
                
                service.update_subscription(subscription["id"], {
                    "status": our_status,
                })
                
                logger.info(
                    "Stripe webhook handling: Updated subscription %s status to %s",
                    subscription["id"],
                    our_status
                )
        
        # Stripe webhook handling: Handle customer.subscription.deleted
        elif event_type == "customer.subscription.deleted":
            stripe_subscription_id = event_data.get("id")
            subscription = service.get_subscription_by_stripe_id(stripe_subscription_id)
            
            if subscription:
                service.cancel_subscription(subscription["id"])
                logger.info(
                    "Stripe webhook handling: Cancelled subscription %s (user: %s)",
                    subscription["id"],
                    subscription.get("user_id")
                )
        
        # Stripe webhook handling: Handle invoice.payment_failed
        elif event_type == "invoice.payment_failed":
            stripe_subscription_id = event_data.get("subscription")
            if stripe_subscription_id:
                subscription = service.get_subscription_by_stripe_id(stripe_subscription_id)
                if subscription:
                    service.update_subscription_status(subscription["id"], "past_due")
                    logger.warning(
                        "Stripe webhook handling: Payment failed for subscription %s",
                        subscription["id"]
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
async def stripe_webhook_alias(request: Request) -> dict:
    """Alias for Stripe webhook at /api/v1/stripe/webhook.
    
    This is an alias route that calls the main stripe_webhook handler.
    Configure this URL in your Stripe Dashboard:
    https://llmhive-orchestrator-792354158895.us-east1.run.app/api/v1/stripe/webhook
    """
    return await stripe_webhook(request)


@router.post("/stripe-webhook/test", status_code=status.HTTP_200_OK)
async def test_stripe_webhook(
    event_type: str,
    user_id: str,
    tier: str = "pro",
    billing_cycle: str = "monthly",
) -> dict:
    """Stripe webhook handling: Test endpoint to simulate webhook events.
    
    Uses Firestore for storage - no SQL database needed.
    
    Final path: /api/v1/webhooks/stripe-webhook/test?event_type={type}&user_id={id}
    
    Example:
        POST /api/v1/webhooks/stripe-webhook/test?event_type=checkout.session.completed&user_id=user123&tier=pro
    """
    if not is_firestore_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Firestore not available - ensure google-cloud-firestore is installed",
        )
    
    try:
        service = get_subscription_service()
        
        # Stripe webhook handling: Simulate checkout.session.completed
        if event_type == "checkout.session.completed":
            # Check if user already has a subscription
            existing = service.get_user_subscription(user_id)
            
            if existing:
                # Update existing
                service.update_subscription(existing["id"], {
                    "tier_name": tier,
                    "billing_cycle": billing_cycle,
                    "status": "active",
                })
                
                return {
                    "test": True,
                    "event_type": event_type,
                    "action": "updated",
                    "subscription_id": existing["id"],
                    "user_id": user_id,
                    "tier": tier,
                }
            else:
                # Create new subscription
                subscription = service.create_subscription(
                    user_id=user_id,
                    tier_name=tier,
                    billing_cycle=billing_cycle,
                )
                
                if subscription:
                    return {
                        "test": True,
                        "event_type": event_type,
                        "action": "created",
                        "subscription_id": subscription.get("id"),
                        "user_id": user_id,
                        "tier": tier,
                    }
                else:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Failed to create subscription in Firestore",
                    )
        
        # Stripe webhook handling: Simulate customer.subscription.deleted
        elif event_type == "customer.subscription.deleted":
            subscription = service.get_user_subscription(user_id)
            if subscription:
                service.cancel_subscription(subscription["id"])
                
                return {
                    "test": True,
                    "event_type": event_type,
                    "action": "cancelled",
                    "subscription_id": subscription["id"],
                    "user_id": user_id,
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
            
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Stripe webhook handling: Test webhook failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Test webhook failed: {exc}",
        ) from exc


@router.get("/subscription/{user_id}", status_code=status.HTTP_200_OK)
async def get_user_subscription(user_id: str) -> dict:
    """Get subscription for a user.
    
    Returns the user's current subscription status from Firestore.
    """
    if not is_firestore_available():
        return {
            "user_id": user_id,
            "subscription": None,
            "error": "Firestore not available",
        }
    
    service = get_subscription_service()
    subscription = service.get_user_subscription(user_id)
    
    if subscription:
        # Convert datetime objects to strings for JSON serialization
        for key in ["created_at", "updated_at", "cancelled_at", "current_period_start", "current_period_end"]:
            if key in subscription and subscription[key]:
                if hasattr(subscription[key], 'isoformat'):
                    subscription[key] = subscription[key].isoformat()
        
        return {
            "user_id": user_id,
            "subscription": subscription,
        }
    else:
        return {
            "user_id": user_id,
            "subscription": None,
            "tier": "free",  # Default tier for users without subscription
        }
