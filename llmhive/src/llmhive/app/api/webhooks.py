"""Stripe webhook handling for subscription events.

Enhanced version with:
- Idempotency via TTLCache (prevents duplicate processing)
- Background task processing (fast responses to Stripe)
- Optional Pub/Sub support (for distributed processing)
- Thread-safe cache access
- Comprehensive event handling

Uses Firestore for subscription storage (no SQL database needed).
No Vertex AI required - embeddings handled by Pinecone.
"""
from __future__ import annotations

import datetime as dt
import logging
import os
import json
import threading
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, status

from ..config import settings
from ..firestore_db import FirestoreSubscriptionService, is_firestore_available
from ..billing.payments import get_payment_processor, STRIPE_AVAILABLE

# Initialize logger and FastAPI router
logger = logging.getLogger(__name__)
router = APIRouter()

# In-memory cache for processed event IDs (to enforce idempotency)
try:
    from cachetools import TTLCache
    CACHE_AVAILABLE = True
except ImportError:
    CACHE_AVAILABLE = False
    TTLCache = None
    logger.warning("cachetools not installed - idempotency cache disabled. Add to requirements.txt")

# Initialize cache if available
if CACHE_AVAILABLE:
    processed_events = TTLCache(maxsize=10000, ttl=259200)  # Cache for 72 hours (259200 seconds)
    processed_events_lock = threading.Lock()
else:
    processed_events = {}  # Fallback to simple dict (less robust)
    processed_events_lock = threading.Lock()

# Optional Pub/Sub configuration (toggle via environment variable)
USE_PUBSUB: bool = os.getenv("USE_PUBSUB", "false").lower() == "true"
PUBSUB_TOPIC_NAME: str = os.getenv("STRIPE_PUBSUB_TOPIC", "stripe-events")


def get_subscription_service() -> FirestoreSubscriptionService:
    """Get Firestore subscription service instance."""
    return FirestoreSubscriptionService()


def publish_to_pubsub(event_payload: bytes, event_id: str, event_type: str) -> bool:
    """
    Publish the Stripe event payload to a Google Cloud Pub/Sub topic.
    Returns True if publish succeeded, False otherwise.
    """
    try:
        from google.cloud import pubsub_v1
    except ImportError:
        logger.error("Pub/Sub publish failed: google-cloud-pubsub not installed")
        return False

    # Determine GCP project for Pub/Sub (from settings or env)
    project_id = settings.google_cloud_project or os.getenv("GCP_PROJECT")
    if not project_id:
        logger.error("Pub/Sub publish failed: GOOGLE_CLOUD_PROJECT not configured")
        return False

    try:
        publisher = pubsub_v1.PublisherClient()
        topic_path = publisher.topic_path(project_id, PUBSUB_TOPIC_NAME)
        # Publish event payload as bytes with attributes for event_id and type
        future = publisher.publish(topic_path, event_payload, **{"event_id": event_id, "event_type": event_type})
        # Block briefly to catch errors (publish is async by default)
        future.result(timeout=2.0)
        logger.info("Published Stripe event %s to Pub/Sub topic %s", event_id, PUBSUB_TOPIC_NAME)
        return True
    except Exception as exc:
        logger.error("Pub/Sub publish failed for event %s: %s", event_id, exc)
        return False


def handle_stripe_event(event: dict) -> None:
    """
    Background task to process a Stripe event object.
    This performs the heavy logic (Stripe API calls, Firestore writes) outside the request cycle.
    """
    event_id = event.get("id")
    event_type = event.get("type")
    try:
        # Ensure Stripe API is initialized (set API key via payment processor if needed)
        processor = get_payment_processor()
        if processor is None:
            logger.error("Stripe PaymentProcessor not initialized; cannot process event %s", event_id)
            return

        import stripe  # Import here to use stripe SDK for API calls
        service = get_subscription_service()

        # Process event by type
        if event_type == "checkout.session.completed":
            # Extract checkout session details
            session = event["data"]["object"]
            user_id = session.get("client_reference_id") or session.get("metadata", {}).get("user_id")
            stripe_subscription_id = session.get("subscription")
            if not user_id or not stripe_subscription_id:
                # These should have been validated in the main handler
                logger.error("Missing user_id or subscription in checkout.session.completed event %s", event_id)
                return

            # Retrieve full Subscription from Stripe to get customer ID and latest info
            stripe_subscription = stripe.Subscription.retrieve(stripe_subscription_id)
            stripe_customer_id = stripe_subscription.customer
            tier_name = session.get("metadata", {}).get("tier", "pro").lower()
            billing_cycle = session.get("metadata", {}).get("billing_cycle", "monthly")

            # Create or update subscription record in Firestore
            existing = service.get_subscription_by_stripe_id(stripe_subscription_id)
            if existing:
                service.update_subscription(existing["id"], {
                    "status": "active",
                    "tier_name": tier_name,
                    "billing_cycle": billing_cycle,
                    "stripe_customer_id": stripe_customer_id,
                })
                logger.info("Stripe event %s: Updated existing subscription %s (user %s, tier %s)",
                            event_id, existing["id"], user_id, tier_name)
            else:
                subscription = service.create_subscription(
                    user_id=user_id,
                    tier_name=tier_name,
                    billing_cycle=billing_cycle,
                    stripe_customer_id=stripe_customer_id,
                    stripe_subscription_id=stripe_subscription_id,
                )
                if subscription:
                    logger.info("Stripe event %s: Created new subscription %s for user %s (tier %s)",
                                event_id, subscription.get("id"), user_id, tier_name)
                else:
                    logger.error("Stripe event %s: Failed to create subscription in Firestore for user %s", event_id, user_id)

        elif event_type == "customer.subscription.updated":
            sub_obj = event["data"]["object"]
            stripe_subscription_id = sub_obj.get("id")
            subscription = service.get_subscription_by_stripe_id(stripe_subscription_id)
            if subscription:
                # Map Stripe status to internal status names
                status_map = {
                    "active": "active",
                    "canceled": "cancelled",
                    "past_due": "past_due",
                    "trialing": "trialing",
                    "unpaid": "expired",
                }
                stripe_status = sub_obj.get("status")
                new_status = status_map.get(stripe_status, "active")
                # Prepare update fields (status and period dates if available)
                updates = {"status": new_status}
                if sub_obj.get("current_period_start"):
                    updates["current_period_start"] = dt.datetime.fromtimestamp(sub_obj["current_period_start"], tz=dt.timezone.utc)
                if sub_obj.get("current_period_end"):
                    updates["current_period_end"] = dt.datetime.fromtimestamp(sub_obj["current_period_end"], tz=dt.timezone.utc)
                service.update_subscription(subscription["id"], updates)
                logger.info("Stripe event %s: Updated subscription %s status to %s",
                            event_id, subscription["id"], new_status)

        elif event_type == "customer.subscription.deleted":
            sub_obj = event["data"]["object"]
            stripe_subscription_id = sub_obj.get("id")
            subscription = service.get_subscription_by_stripe_id(stripe_subscription_id)
            if subscription:
                service.cancel_subscription(subscription["id"])
                logger.info("Stripe event %s: Cancelled subscription %s for user %s",
                            event_id, subscription["id"], subscription.get("user_id"))

        elif event_type == "invoice.payment_succeeded":
            inv_obj = event["data"]["object"]
            stripe_subscription_id = inv_obj.get("subscription")
            if stripe_subscription_id:
                subscription = service.get_subscription_by_stripe_id(stripe_subscription_id)
                if subscription:
                    # Mark subscription active (payment succeeded) and update period if available
                    updates = {"status": "active"}
                    # If invoice contains period information, update current period dates
                    try:
                        lines = inv_obj.get("lines", {}).get("data", [])
                        if lines:
                            period = lines[0].get("period", {})
                            if period.get("start") and period.get("end"):
                                updates["current_period_start"] = dt.datetime.fromtimestamp(period["start"], tz=dt.timezone.utc)
                                updates["current_period_end"] = dt.datetime.fromtimestamp(period["end"], tz=dt.timezone.utc)
                    except Exception:
                        pass
                    service.update_subscription(subscription["id"], updates)
                    logger.info("Stripe event %s: Payment succeeded, updated subscription %s to active",
                                event_id, subscription["id"])

        elif event_type == "invoice.payment_failed":
            inv_obj = event["data"]["object"]
            stripe_subscription_id = inv_obj.get("subscription")
            if stripe_subscription_id:
                subscription = service.get_subscription_by_stripe_id(stripe_subscription_id)
                if subscription:
                    service.update_subscription_status(subscription["id"], "past_due")
                    logger.warning("Stripe event %s: Payment failed for subscription %s (marked past_due)",
                                   event_id, subscription["id"])

        # (Other event types can be handled here as needed)
    except Exception as exc:
        # On any processing error, log exception and remove event from cache (allowing potential retries/manual reprocess)
        logger.exception("Error processing Stripe event %s (%s): %s", event_id, event_type, exc)
        with processed_events_lock:
            processed_events.pop(event_id, None)
        # (No re-raise; background task errors do not affect HTTP response)
        return


@router.post("/stripe-webhook", status_code=status.HTTP_200_OK)
async def stripe_webhook(request: Request, background_tasks: BackgroundTasks) -> dict:
    """
    Stripe webhook endpoint. Verifies the Stripe signature and queues the event for processing.
    Responds quickly with 200 OK to avoid Stripe timeouts.
    
    Features:
    - Idempotency: Duplicate events are detected and skipped
    - Background processing: Heavy work happens after response
    - Optional Pub/Sub: Can publish to GCP Pub/Sub for distributed handling
    
    Final path: /api/v1/webhooks/stripe-webhook
    
    Note: In production, configure this endpoint in Stripe Dashboard:
    - Go to Developers > Webhooks
    - Add endpoint URL
    - Select events: checkout.session.completed, customer.subscription.*, invoice.payment_*
    - Copy webhook signing secret to STRIPE_WEBHOOK_SECRET
    """
    if not STRIPE_AVAILABLE:
        # Stripe library must be installed for webhook to function
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                            detail="Stripe SDK not available. Install the stripe package.")
    if not is_firestore_available():
        # Firestore may be optional (log a warning if not configured)
        logger.warning("Firestore not available - subscription data will not be persisted")

    signature = request.headers.get("stripe-signature")
    if not signature:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Missing stripe-signature header")

    payload = await request.body()
    try:
        import stripe
        webhook_secret = settings.stripe_webhook_secret
        if not webhook_secret:
            logger.error("STRIPE_WEBHOOK_SECRET is not set in environment")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                                detail="Webhook secret not configured")

        # Construct Stripe Event (will raise if signature verification fails)
        event = stripe.Webhook.construct_event(payload, signature, webhook_secret)
        event_id = event["id"]
        event_type = event["type"]

        # Idempotency check: skip already-processed events
        with processed_events_lock:
            if event_id in processed_events:
                logger.info("Received duplicate Stripe event %s (%s), skipping processing", event_id, event_type)
                return {"received": True, "processed": False, "idempotent": True, "event_type": event_type}
            # For checkout sessions, validate critical fields before accepting
            if event_type == "checkout.session.completed":
                sess = event["data"]["object"]
                user_check = sess.get("client_reference_id") or sess.get("metadata", {}).get("user_id")
                sub_check = sess.get("subscription")
                if not user_check:
                    logger.error("Stripe event %s: Missing user_id in checkout.session.completed", event_id)
                    return {"received": True, "processed": False, "error": "No user_id in session"}
                if not sub_check:
                    logger.warning("Stripe event %s: Missing subscription ID in checkout.session.completed", event_id)
                    return {"received": True, "processed": False, "error": "No subscription in session"}
            # Mark this event as processed to prevent duplicates
            processed_events[event_id] = True

        # Queue event for processing (via Pub/Sub or background task)
        if USE_PUBSUB:
            # Publish to Pub/Sub for out-of-process handling
            background_tasks.add_task(publish_to_pubsub, payload, event_id, event_type)
            logger.info("Stripe event %s (%s) published to Pub/Sub queue", event_id, event_type)
        else:
            # Direct in-process background handling
            background_tasks.add_task(handle_stripe_event, event)
            logger.info("Stripe event %s (%s) queued for background processing", event_id, event_type)

        # Respond immediately to Stripe
        return {"received": True, "processed": True, "event_type": event_type}

    except stripe.error.SignatureVerificationError as exc:
        logger.error("Stripe signature verification failed: %s", exc)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid webhook signature") from exc
    except ValueError as exc:
        logger.error("Stripe webhook payload error: %s", exc)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid webhook payload") from exc
    except HTTPException:
        # Re-raise known HTTP exceptions (e.g., missing secret)
        raise
    except Exception as exc:
        logger.exception("Unhandled exception in Stripe webhook: %s", exc)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Failed to process webhook") from exc


# Alias route for convenience (e.g. Stripe dashboard can use /api/v1/stripe/webhook)
@router.post("/webhook", status_code=status.HTTP_200_OK)
async def stripe_webhook_alias(request: Request, background_tasks: BackgroundTasks) -> dict:
    """
    Alias for Stripe webhook endpoint. This allows a cleaner URL:
    e.g. https://<service-url>/api/v1/stripe/webhook
    """
    return await stripe_webhook(request=request, background_tasks=background_tasks)


@router.post("/stripe-webhook/test", status_code=status.HTTP_200_OK)
async def test_stripe_webhook(event_type: str, user_id: str, tier: str = "pro", billing_cycle: str = "monthly") -> dict:
    """
    Test endpoint to simulate Stripe webhook events (for development use).
    Not protected by Stripe signature – **do not expose in production**.
    
    Final path: /api/v1/webhooks/stripe-webhook/test?event_type={type}&user_id={id}
    
    Example:
        POST /api/v1/webhooks/stripe-webhook/test?event_type=checkout.session.completed&user_id=user123&tier=pro
    """
    if not is_firestore_available():
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                            detail="Firestore not available - install google-cloud-firestore")
    service = get_subscription_service()
    try:
        if event_type == "checkout.session.completed":
            # Simulate creating or updating a subscription on checkout completion
            existing = service.get_user_subscription(user_id)
            if existing:
                service.update_subscription(existing["id"], {
                    "tier_name": tier.lower(),
                    "billing_cycle": billing_cycle,
                    "status": "active",
                })
                return {"test": True, "event_type": event_type, "action": "updated",
                        "subscription_id": existing["id"], "user_id": user_id, "tier": tier}
            else:
                subscription = service.create_subscription(user_id=user_id, tier_name=tier.lower(), billing_cycle=billing_cycle)
                if subscription:
                    return {"test": True, "event_type": event_type, "action": "created",
                            "subscription_id": subscription.get("id"), "user_id": user_id, "tier": tier}
                else:
                    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                                        detail="Failed to create subscription in Firestore")
        elif event_type == "customer.subscription.deleted":
            subscription = service.get_user_subscription(user_id)
            if subscription:
                service.cancel_subscription(subscription["id"])
                return {"test": True, "event_type": event_type, "action": "cancelled",
                        "subscription_id": subscription["id"], "user_id": user_id}
            else:
                return {"test": True, "event_type": event_type, "user_id": user_id,
                        "error": "No subscription found"}
        else:
            return {"test": True, "event_type": event_type,
                    "error": f"Unsupported test event type: {event_type}"}
    except Exception as exc:
        logger.exception("Test webhook failed: %s", exc)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Test webhook failed: {exc}")


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
