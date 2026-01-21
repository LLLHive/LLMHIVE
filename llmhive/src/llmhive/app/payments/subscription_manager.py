"""Subscription Management for LLMHive Stage 4.

This module implements Section 9 of Stage 4 upgrades:
- Stripe integration for payments
- Prorated billing & failed payment recovery
- Logging and user guidance

Production Hardening:
- Webhook signature verification with timing-safe comparison
- Idempotent webhook handling (dedupe by event_id)
- Explicit subscription state machine
- No sensitive card data stored
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import os
import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set

from llmhive.app.orchestration.stage4_hardening import get_config, hash_user_id

logger = logging.getLogger(__name__)


# ==============================================================================
# IDEMPOTENCY TRACKING
# ==============================================================================

class WebhookIdempotencyStore:
    """Tracks processed webhook event IDs to prevent duplicate processing.
    
    Features:
    - Atomic consume_if_new operation (prevents race conditions)
    - Optional Redis backend for distributed deployments
    - TTL-based expiration for old events
    - In-memory fallback when Redis is unavailable
    """
    
    def __init__(
        self,
        max_events: int = 10000,
        ttl_hours: int = 24,
        use_redis: bool = False,
    ):
        self._processed: Dict[str, datetime] = {}
        self._max_events = max_events
        self._ttl = timedelta(hours=ttl_hours)
        self._ttl_seconds = ttl_hours * 3600
        self._lock = threading.Lock()
        self._use_redis = use_redis or os.getenv("USE_REDIS_IDEMPOTENCY", "0") == "1"
        self._redis_client = None
        
        if self._use_redis:
            self._init_redis()
    
    def _init_redis(self):
        """Initialize Redis connection if available."""
        try:
            import redis
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
            self._redis_client = redis.from_url(redis_url)
            self._redis_client.ping()
            logger.info("Idempotency store using Redis backend")
        except Exception as e:
            logger.warning("Redis not available for idempotency store: %s", e)
            self._use_redis = False
            self._redis_client = None
    
    def _redis_key(self, event_id: str) -> str:
        """Generate Redis key for an event ID."""
        prefix = os.getenv("RATE_LIMIT_REDIS_PREFIX", "llmhive:")
        return f"{prefix}webhook:processed:{event_id}"
    
    def is_processed(self, event_id: str) -> bool:
        """Check if event was already processed."""
        if self._use_redis and self._redis_client:
            try:
                return self._redis_client.exists(self._redis_key(event_id)) > 0
            except Exception as e:
                logger.warning("Redis is_processed check failed: %s", e)
        
        with self._lock:
            self._cleanup_expired()
            return event_id in self._processed
    
    def mark_processed(self, event_id: str) -> None:
        """Mark an event as processed."""
        if self._use_redis and self._redis_client:
            try:
                self._redis_client.setex(
                    self._redis_key(event_id),
                    self._ttl_seconds,
                    "1"
                )
                return
            except Exception as e:
                logger.warning("Redis mark_processed failed: %s", e)
        
        with self._lock:
            self._processed[event_id] = datetime.now(timezone.utc)
            
            # Evict oldest if over limit
            if len(self._processed) > self._max_events:
                oldest = min(self._processed.keys(), key=lambda k: self._processed[k])
                del self._processed[oldest]
    
    def consume_if_new(self, event_id: str) -> bool:
        """
        Atomically check if event is new and mark it as processed.
        
        This is the preferred method for idempotency checking as it
        prevents race conditions where two threads could both see
        an event as unprocessed.
        
        Returns:
            True if the event was new and is now marked as processed.
            False if the event was already processed.
        """
        if self._use_redis and self._redis_client:
            try:
                # SETNX (set if not exists) is atomic
                key = self._redis_key(event_id)
                result = self._redis_client.set(key, "1", nx=True, ex=self._ttl_seconds)
                return result is True
            except Exception as e:
                logger.warning("Redis consume_if_new failed: %s", e)
        
        # Fall back to in-memory with lock
        with self._lock:
            self._cleanup_expired()
            if event_id in self._processed:
                return False
            
            self._processed[event_id] = datetime.now(timezone.utc)
            
            # Evict oldest if over limit
            if len(self._processed) > self._max_events:
                oldest = min(self._processed.keys(), key=lambda k: self._processed[k])
                del self._processed[oldest]
            
            return True
    
    def _cleanup_expired(self) -> None:
        """Remove expired entries."""
        now = datetime.now(timezone.utc)
        expired = [
            k for k, v in self._processed.items()
            if now - v > self._ttl
        ]
        for k in expired:
            del self._processed[k]
    
    def clear(self) -> None:
        """Clear all entries (for testing)."""
        with self._lock:
            self._processed = {}


# Singleton instance
_idempotency_store: Optional[WebhookIdempotencyStore] = None
_idempotency_lock = threading.Lock()


def get_idempotency_store() -> WebhookIdempotencyStore:
    """Get the singleton idempotency store."""
    global _idempotency_store
    if _idempotency_store is None:
        with _idempotency_lock:
            if _idempotency_store is None:
                _idempotency_store = WebhookIdempotencyStore()
    return _idempotency_store


def reset_idempotency_store() -> None:
    """Reset the idempotency store singleton (for testing).
    
    Call this in test teardown to ensure fresh state for each test.
    """
    global _idempotency_store
    with _idempotency_lock:
        _idempotency_store = None


def set_idempotency_store(store: WebhookIdempotencyStore) -> None:
    """Inject a specific idempotency store (for testing).
    
    Args:
        store: The store instance to use
    """
    global _idempotency_store
    with _idempotency_lock:
        _idempotency_store = store


# ==============================================================================
# SUBSCRIPTION STATUS
# ==============================================================================

class SubscriptionStatus(Enum):
    """Status of a subscription.
    
    State machine transitions:
    - FREE -> TRIALING (start trial) -> ACTIVE (payment confirmed)
    - FREE -> ACTIVE (direct purchase)
    - ACTIVE -> PAST_DUE (payment failed) -> UNPAID (grace period expired)
    - ACTIVE -> CANCELED (user cancels)
    - PAST_DUE -> ACTIVE (payment retry success)
    - UNPAID -> FREE (downgrade)
    - * -> PAUSED (optional: user pauses)
    """
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELED = "canceled"
    TRIALING = "trialing"
    UNPAID = "unpaid"
    INCOMPLETE = "incomplete"
    PAUSED = "paused"
    FREE = "free"
    
    @classmethod
    def valid_transitions(cls) -> Dict["SubscriptionStatus", Set["SubscriptionStatus"]]:
        """Return valid state transitions."""
        return {
            cls.FREE: {cls.TRIALING, cls.ACTIVE, cls.INCOMPLETE},
            cls.TRIALING: {cls.ACTIVE, cls.PAST_DUE, cls.CANCELED},
            cls.ACTIVE: {cls.PAST_DUE, cls.CANCELED, cls.PAUSED},
            cls.PAST_DUE: {cls.ACTIVE, cls.UNPAID, cls.CANCELED},
            cls.UNPAID: {cls.FREE, cls.ACTIVE},
            cls.INCOMPLETE: {cls.ACTIVE, cls.FREE},
            cls.PAUSED: {cls.ACTIVE, cls.CANCELED},
            cls.CANCELED: {cls.FREE},  # Can resubscribe
        }
    
    def can_transition_to(self, new_status: "SubscriptionStatus") -> bool:
        """Check if transition to new status is valid."""
        valid = self.valid_transitions().get(self, set())
        return new_status in valid


class PaymentEvent(Enum):
    """Types of payment events."""
    PAYMENT_SUCCEEDED = "payment_succeeded"
    PAYMENT_FAILED = "payment_failed"
    SUBSCRIPTION_CREATED = "subscription_created"
    SUBSCRIPTION_UPDATED = "subscription_updated"
    SUBSCRIPTION_CANCELED = "subscription_canceled"
    INVOICE_PAID = "invoice_paid"
    INVOICE_PAYMENT_FAILED = "invoice_payment_failed"


# ==============================================================================
# DATA MODELS
# ==============================================================================

@dataclass
class UserSubscription:
    """User subscription information."""
    user_id: str
    stripe_customer_id: Optional[str] = None
    stripe_subscription_id: Optional[str] = None
    tier: str = "lite"  # Default to Lite tier (January 2026 simplified structure)
    status: SubscriptionStatus = SubscriptionStatus.FREE
    current_period_end: Optional[datetime] = None
    grace_period_end: Optional[datetime] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    @property
    def is_active(self) -> bool:
        """Check if subscription is active."""
        if self.status == SubscriptionStatus.FREE:
            return True
        return self.status in (
            SubscriptionStatus.ACTIVE,
            SubscriptionStatus.TRIALING,
        )
    
    @property
    def is_past_due(self) -> bool:
        """Check if subscription is past due."""
        return self.status == SubscriptionStatus.PAST_DUE
    
    @property
    def in_grace_period(self) -> bool:
        """Check if in grace period."""
        if not self.grace_period_end:
            return False
        return datetime.now(timezone.utc) < self.grace_period_end


@dataclass
class PaymentLog:
    """Log entry for a payment event."""
    event_id: str
    user_id: str
    event_type: PaymentEvent
    amount: Optional[float] = None
    currency: str = "usd"
    success: bool = True
    error_message: Optional[str] = None
    stripe_event_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


# ==============================================================================
# STRIPE CLIENT
# ==============================================================================

class StripeClient:
    """Client for Stripe API operations."""
    
    def __init__(self, api_key: Optional[str] = None):
        self._api_key = api_key or os.getenv("STRIPE_SECRET_KEY")
        self._stripe = None
        self._init_stripe()
    
    def _init_stripe(self):
        """Initialize Stripe SDK."""
        if not self._api_key:
            logger.warning("Stripe API key not configured")
            return
        
        try:
            import stripe
            stripe.api_key = self._api_key
            self._stripe = stripe
            logger.info("Stripe client initialized")
        except ImportError:
            logger.warning("stripe package not installed")
    
    @property
    def is_configured(self) -> bool:
        """Check if Stripe is configured."""
        return self._stripe is not None
    
    async def create_customer(
        self,
        email: str,
        name: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> Optional[str]:
        """Create a Stripe customer."""
        if not self._stripe:
            return None
        
        try:
            customer = self._stripe.Customer.create(
                email=email,
                name=name,
                metadata=metadata or {},
            )
            logger.info("Created Stripe customer: %s", customer.id)
            return customer.id
        except Exception as e:
            logger.error("Failed to create Stripe customer: %s", e)
            return None
    
    async def create_subscription(
        self,
        customer_id: str,
        price_id: str,
        trial_days: int = 0,
    ) -> Optional[Dict[str, Any]]:
        """Create a subscription for a customer."""
        if not self._stripe:
            return None
        
        try:
            params = {
                "customer": customer_id,
                "items": [{"price": price_id}],
                "proration_behavior": "create_prorations",
            }
            
            if trial_days > 0:
                params["trial_period_days"] = trial_days
            
            subscription = self._stripe.Subscription.create(**params)
            
            logger.info(
                "Created subscription %s for customer %s",
                subscription.id, customer_id
            )
            
            return {
                "subscription_id": subscription.id,
                "status": subscription.status,
                "current_period_end": subscription.current_period_end,
            }
            
        except Exception as e:
            logger.error("Failed to create subscription: %s", e)
            return None
    
    async def update_subscription(
        self,
        subscription_id: str,
        new_price_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Update a subscription (upgrade/downgrade)."""
        if not self._stripe:
            return None
        
        try:
            subscription = self._stripe.Subscription.retrieve(subscription_id)
            
            # Update with proration
            updated = self._stripe.Subscription.modify(
                subscription_id,
                items=[{
                    "id": subscription["items"]["data"][0].id,
                    "price": new_price_id,
                }],
                proration_behavior="create_prorations",
            )
            
            logger.info("Updated subscription %s to price %s", subscription_id, new_price_id)
            
            return {
                "subscription_id": updated.id,
                "status": updated.status,
                "current_period_end": updated.current_period_end,
            }
            
        except Exception as e:
            logger.error("Failed to update subscription: %s", e)
            return None
    
    async def cancel_subscription(
        self,
        subscription_id: str,
        at_period_end: bool = True,
    ) -> bool:
        """Cancel a subscription."""
        if not self._stripe:
            return False
        
        try:
            if at_period_end:
                self._stripe.Subscription.modify(
                    subscription_id,
                    cancel_at_period_end=True,
                )
                logger.info("Subscription %s will cancel at period end", subscription_id)
            else:
                self._stripe.Subscription.delete(subscription_id)
                logger.info("Subscription %s canceled immediately", subscription_id)
            
            return True
            
        except Exception as e:
            logger.error("Failed to cancel subscription: %s", e)
            return False
    
    async def get_subscription(
        self,
        subscription_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Get subscription details."""
        if not self._stripe:
            return None
        
        try:
            subscription = self._stripe.Subscription.retrieve(subscription_id)
            
            return {
                "subscription_id": subscription.id,
                "status": subscription.status,
                "current_period_end": subscription.current_period_end,
                "cancel_at_period_end": subscription.cancel_at_period_end,
            }
            
        except Exception as e:
            logger.error("Failed to get subscription: %s", e)
            return None
    
    async def list_subscriptions(
        self,
        status_filter: Optional[List[str]] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """List subscriptions with optional status filter.
        
        Args:
            status_filter: List of statuses to include (e.g., ["active", "trialing"])
            limit: Maximum subscriptions to return
        
        Returns:
            List of subscription data dictionaries
        """
        if not self._stripe:
            return []
        
        try:
            all_subscriptions = []
            
            if status_filter:
                for status in status_filter:
                    subs = self._stripe.Subscription.list(status=status, limit=limit)
                    all_subscriptions.extend(subs.data)
            else:
                subs = self._stripe.Subscription.list(limit=limit)
                all_subscriptions.extend(subs.data)
            
            return [
                {
                    "id": sub.id,
                    "customer": sub.customer,
                    "status": sub.status,
                    "current_period_end": sub.current_period_end,
                    "items": {"data": [{"price": {"id": item.price.id}} for item in sub.items.data]},
                }
                for sub in all_subscriptions
            ]
            
        except Exception as e:
            logger.error("Failed to list subscriptions: %s", e)
            return []
    
    async def get_customer(
        self,
        customer_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Get customer details including metadata.
        
        Args:
            customer_id: Stripe customer ID
            
        Returns:
            Customer data dictionary with metadata
        """
        if not self._stripe:
            return None
        
        try:
            customer = self._stripe.Customer.retrieve(customer_id)
            
            return {
                "id": customer.id,
                "email": customer.email,
                "name": customer.name,
                "metadata": dict(customer.metadata) if customer.metadata else {},
            }
            
        except Exception as e:
            logger.error("Failed to get customer: %s", e)
            return None
    
    async def load_active_subscriptions_from_stripe(self) -> int:
        """Reload active subscriptions from Stripe on startup.
        
        Fetches all non-canceled subscriptions from Stripe and reconstructs
        the in-memory subscription state. Uses customer metadata (user_id)
        to map subscriptions back to users.
        
        Returns:
            Number of subscriptions loaded
        
        Note:
            This should be called during service initialization to restore
            subscription state after restarts, ensuring paying users retain
            access without waiting for webhook events.
        """
        if not self._stripe:
            logger.warning("Stripe not initialized, cannot load subscriptions")
            return 0
        
        loaded_count = 0
        
        try:
            # Fetch active, trialing, and past_due subscriptions
            statuses_to_load = ["active", "trialing", "past_due"]
            subscriptions = await self.list_subscriptions(
                status_filter=statuses_to_load,
                limit=100,
            )
            
            logger.info(
                "Loading %d subscriptions from Stripe (statuses: %s)",
                len(subscriptions),
                statuses_to_load,
            )
            
            for sub_data in subscriptions:
                try:
                    customer_id = sub_data.get("customer")
                    if not customer_id:
                        continue
                    
                    # Get customer to retrieve user_id from metadata
                    customer = await self.get_customer(customer_id)
                    if not customer:
                        logger.warning(
                            "Could not retrieve customer %s for subscription %s",
                            customer_id,
                            sub_data.get("id"),
                        )
                        continue
                    
                    user_id = customer.get("metadata", {}).get("user_id")
                    if not user_id:
                        logger.warning(
                            "Customer %s has no user_id in metadata, skipping",
                            customer_id,
                        )
                        continue
                    
                    # Map Stripe status to our status enum
                    stripe_status = sub_data.get("status", "").lower()
                    status_map = {
                        "active": SubscriptionStatus.ACTIVE,
                        "trialing": SubscriptionStatus.TRIALING,
                        "past_due": SubscriptionStatus.PAST_DUE,
                        "canceled": SubscriptionStatus.CANCELED,
                        "unpaid": SubscriptionStatus.CANCELED,
                    }
                    status = status_map.get(stripe_status, SubscriptionStatus.FREE)
                    
                    # Determine tier from price ID
                    tier = SubscriptionTier.FREE
                    items = sub_data.get("items", {}).get("data", [])
                    if items:
                        price_id = items[0].get("price", {}).get("id", "")
                        tier = self._get_tier_from_price_id(price_id)
                    
                    # Create or update user subscription
                    user_sub = UserSubscription(
                        user_id=user_id,
                        tier=tier,
                        status=status,
                        stripe_customer_id=customer_id,
                        stripe_subscription_id=sub_data.get("id"),
                        current_period_end=datetime.fromtimestamp(
                            sub_data.get("current_period_end", 0),
                            tz=timezone.utc,
                        ),
                    )
                    
                    self._subscriptions[user_id] = user_sub
                    loaded_count += 1
                    
                    logger.debug(
                        "Loaded subscription for user %s: tier=%s, status=%s",
                        user_id,
                        tier.value,
                        status.value,
                    )
                    
                except Exception as e:
                    logger.error(
                        "Error loading subscription %s: %s",
                        sub_data.get("id"),
                        e,
                    )
                    continue
            
            logger.info(
                "Successfully loaded %d subscriptions from Stripe",
                loaded_count,
            )
            return loaded_count
            
        except Exception as e:
            logger.error("Failed to load subscriptions from Stripe: %s", e)
            return loaded_count
    
    def _get_tier_from_price_id(self, price_id: str) -> SubscriptionTier:
        """Map a Stripe price ID to a subscription tier.
        
        Args:
            price_id: Stripe price ID
            
        Returns:
            Corresponding subscription tier
        """
        # Check against known price IDs from config
        config = get_config()
        price_to_tier = config.get("price_to_tier", {})
        
        if price_id in price_to_tier:
            tier_name = price_to_tier[price_id]
            try:
                return SubscriptionTier(tier_name)
            except ValueError:
                pass
        
        # Fallback: infer from price ID naming convention
        price_lower = price_id.lower()
        if "enterprise" in price_lower:
            return SubscriptionTier.ENTERPRISE
        elif "pro" in price_lower:
            return SubscriptionTier.PRO
        elif "basic" in price_lower or "starter" in price_lower:
            return SubscriptionTier.BASIC
        
        logger.warning("Unknown price ID %s, defaulting to BASIC tier", price_id)
        return SubscriptionTier.BASIC
    
    def verify_webhook(
        self,
        payload: bytes,
        signature: str,
        webhook_secret: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Verify and parse a Stripe webhook with security hardening.
        
        Security:
        - Uses Stripe's signature verification (timing-safe)
        - Logs attempts without leaking secrets
        - Returns None on any verification failure
        """
        if not self._stripe:
            logger.warning("Stripe not configured, rejecting webhook")
            return None
        
        if not webhook_secret:
            logger.error("Webhook secret not configured")
            return None
        
        if not signature:
            logger.warning("Missing webhook signature header")
            return None
        
        try:
            # Stripe's construct_event uses timing-safe comparison internally
            event = self._stripe.Webhook.construct_event(
                payload, signature, webhook_secret
            )
            
            logger.info(
                "Webhook verified: type=%s, id=%s",
                event.type, event.id
            )
            
            return {
                "type": event.type,
                "data": event.data.object,
                "id": event.id,
                "created": event.created,
            }
            
        except self._stripe.error.SignatureVerificationError as e:
            # Log without revealing secret details
            logger.warning("Webhook signature verification failed")
            return None
        except Exception as e:
            # Generic error - don't leak details
            logger.error("Webhook processing error: %s", type(e).__name__)
            return None


# ==============================================================================
# SUBSCRIPTION MANAGER
# ==============================================================================

class SubscriptionManager:
    """Manages user subscriptions with Stripe integration.
    
    Implements Stage 4 Section 9: Payments & Subscription System.
    """
    
    # Tier to Stripe price ID mapping - SIMPLIFIED 4-TIER (January 2026)
    TIER_PRICES = {
        "lite": os.getenv("STRIPE_PRICE_ID_BASIC_MONTHLY"),  # Lite uses BASIC env for backwards compat
        "pro": os.getenv("STRIPE_PRICE_ID_PRO_MONTHLY"),
        "enterprise": os.getenv("STRIPE_PRICE_ID_ENTERPRISE_MONTHLY"),
        "maximum": os.getenv("STRIPE_PRICE_ID_MAXIMUM_MONTHLY"),
        # Legacy mapping
        "basic": os.getenv("STRIPE_PRICE_ID_BASIC_MONTHLY"),
    }
    
    GRACE_PERIOD_DAYS = 7
    
    def __init__(
        self,
        stripe_client: Optional[StripeClient] = None,
        user_store: Optional[Any] = None,
        auto_reload_from_stripe: bool = False,
    ):
        self._stripe = stripe_client or StripeClient()
        self._user_store = user_store
        self._subscriptions: Dict[str, UserSubscription] = {}
        self._payment_logs: List[PaymentLog] = []
        
        # Optionally reload subscriptions from Stripe on init
        if auto_reload_from_stripe:
            import asyncio
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(self.load_subscriptions_from_stripe())
            except RuntimeError:
                # No running loop, skip async reload
                logger.info("Skipping async Stripe reload - no event loop")
    
    async def load_subscriptions_from_stripe(self) -> int:
        """
        Reload active subscriptions from Stripe.
        
        Call this on server startup to restore subscription state.
        Uses Stripe Customer metadata (user_id) to map back to users.
        
        Returns:
            Number of subscriptions loaded
        """
        if not self._stripe.is_configured:
            logger.warning("Cannot reload from Stripe - not configured")
            return 0
        
        loaded = 0
        try:
            # Get all active/trialing/past_due subscriptions
            subscriptions = await self._stripe.list_subscriptions(
                status_filter=["active", "trialing", "past_due"]
            )
            
            for sub_data in subscriptions:
                try:
                    customer_id = sub_data.get("customer")
                    subscription_id = sub_data.get("id")
                    status_str = sub_data.get("status", "active")
                    
                    # Get customer to find user_id
                    customer = await self._stripe.get_customer(customer_id)
                    if not customer:
                        continue
                    
                    user_id = customer.get("metadata", {}).get("user_id")
                    if not user_id:
                        logger.debug("Customer %s has no user_id metadata", customer_id)
                        continue
                    
                    # Determine tier from price ID
                    items = sub_data.get("items", {}).get("data", [])
                    tier = "free"
                    if items:
                        price_id = items[0].get("price", {}).get("id")
                        tier = self._price_id_to_tier(price_id)
                    
                    # Parse status
                    status = self._parse_stripe_status(status_str)
                    
                    # Create or update subscription
                    self._subscriptions[user_id] = UserSubscription(
                        user_id=user_id,
                        stripe_customer_id=customer_id,
                        stripe_subscription_id=subscription_id,
                        tier=tier,
                        status=status,
                        current_period_end=datetime.fromtimestamp(
                            sub_data.get("current_period_end", 0), tz=timezone.utc
                        ),
                    )
                    loaded += 1
                    
                except Exception as e:
                    logger.warning("Failed to load subscription: %s", e)
                    continue
            
            logger.info("Loaded %d subscriptions from Stripe", loaded)
            
        except Exception as e:
            logger.error("Failed to reload subscriptions from Stripe: %s", e)
        
        return loaded
    
    def _price_id_to_tier(self, price_id: str) -> str:
        """Map Stripe price ID to tier name."""
        for tier, pid in self.TIER_PRICES.items():
            if pid == price_id:
                return tier
        return "free"
    
    async def get_or_create_customer(
        self,
        user_id: str,
        email: str,
        name: Optional[str] = None,
    ) -> Optional[str]:
        """Get existing or create new Stripe customer."""
        # Check if user already has a customer ID
        sub = self._subscriptions.get(user_id)
        if sub and sub.stripe_customer_id:
            return sub.stripe_customer_id
        
        # Create new customer
        customer_id = await self._stripe.create_customer(
            email=email,
            name=name,
            metadata={"user_id": user_id},
        )
        
        if customer_id:
            if user_id not in self._subscriptions:
                self._subscriptions[user_id] = UserSubscription(user_id=user_id)
            self._subscriptions[user_id].stripe_customer_id = customer_id
        
        return customer_id
    
    async def subscribe(
        self,
        user_id: str,
        tier: str,
        email: str,
        trial_days: int = 0,
    ) -> Dict[str, Any]:
        """Subscribe a user to a tier."""
        if tier not in self.TIER_PRICES:
            return {"success": False, "error": f"Unknown tier: {tier}"}
        
        price_id = self.TIER_PRICES[tier]
        if not price_id:
            return {"success": False, "error": f"Price not configured for tier: {tier}"}
        
        # Get or create customer
        customer_id = await self.get_or_create_customer(user_id, email)
        if not customer_id:
            return {"success": False, "error": "Failed to create customer"}
        
        # Create subscription
        result = await self._stripe.create_subscription(
            customer_id=customer_id,
            price_id=price_id,
            trial_days=trial_days,
        )
        
        if not result:
            return {"success": False, "error": "Failed to create subscription"}
        
        # Update local state
        sub = self._subscriptions.get(user_id)
        if sub:
            sub.stripe_subscription_id = result["subscription_id"]
            sub.tier = tier
            sub.status = SubscriptionStatus(result["status"])
            sub.current_period_end = datetime.fromtimestamp(
                result["current_period_end"], tz=timezone.utc
            )
            sub.updated_at = datetime.now(timezone.utc)
        
        # Log event
        self._log_event(
            user_id=user_id,
            event_type=PaymentEvent.SUBSCRIPTION_CREATED,
            metadata={"tier": tier, "subscription_id": result["subscription_id"]},
        )
        
        return {"success": True, "subscription": result}
    
    async def upgrade(
        self,
        user_id: str,
        new_tier: str,
    ) -> Dict[str, Any]:
        """Upgrade a user's subscription with proration."""
        sub = self._subscriptions.get(user_id)
        if not sub or not sub.stripe_subscription_id:
            return {"success": False, "error": "No active subscription"}
        
        if new_tier not in self.TIER_PRICES:
            return {"success": False, "error": f"Unknown tier: {new_tier}"}
        
        price_id = self.TIER_PRICES[new_tier]
        if not price_id:
            return {"success": False, "error": f"Price not configured for tier: {new_tier}"}
        
        result = await self._stripe.update_subscription(
            subscription_id=sub.stripe_subscription_id,
            new_price_id=price_id,
        )
        
        if not result:
            return {"success": False, "error": "Failed to update subscription"}
        
        old_tier = sub.tier
        sub.tier = new_tier
        sub.updated_at = datetime.now(timezone.utc)
        
        # Log event
        self._log_event(
            user_id=user_id,
            event_type=PaymentEvent.SUBSCRIPTION_UPDATED,
            metadata={"old_tier": old_tier, "new_tier": new_tier},
        )
        
        return {"success": True, "subscription": result}
    
    async def cancel(
        self,
        user_id: str,
        at_period_end: bool = True,
    ) -> Dict[str, Any]:
        """Cancel a user's subscription."""
        sub = self._subscriptions.get(user_id)
        if not sub or not sub.stripe_subscription_id:
            return {"success": False, "error": "No active subscription"}
        
        success = await self._stripe.cancel_subscription(
            subscription_id=sub.stripe_subscription_id,
            at_period_end=at_period_end,
        )
        
        if not success:
            return {"success": False, "error": "Failed to cancel subscription"}
        
        if at_period_end:
            # Keep active until period end
            message = f"Your subscription will remain active until {sub.current_period_end}"
        else:
            sub.status = SubscriptionStatus.CANCELED
            sub.tier = "free"
            message = "Your subscription has been canceled"
        
        sub.updated_at = datetime.now(timezone.utc)
        
        # Log event
        self._log_event(
            user_id=user_id,
            event_type=PaymentEvent.SUBSCRIPTION_CANCELED,
            metadata={"at_period_end": at_period_end},
        )
        
        return {"success": True, "message": message}
    
    async def handle_webhook(
        self,
        payload: bytes,
        signature: str,
        webhook_secret: str,
    ) -> Dict[str, Any]:
        """
        Handle incoming Stripe webhook with idempotency.
        
        Security:
        - Verifies signature before processing
        - Deduplicates by event_id to prevent double-processing
        - Uses explicit state machine for transitions
        """
        event = self._stripe.verify_webhook(payload, signature, webhook_secret)
        
        if not event:
            return {"success": False, "error": "Invalid webhook"}
        
        event_id = event["id"]
        event_type = event["type"]
        data = event["data"]
        
        # Atomic idempotency check - prevent race conditions in duplicate processing
        idempotency_store = get_idempotency_store()
        if not idempotency_store.consume_if_new(event_id):
            logger.info("Webhook %s already processed, skipping", event_id)
            return {"success": True, "message": "Already processed", "idempotent": True}
        
        logger.info("Processing webhook: type=%s, id=%s", event_type, event_id)
        
        # Handle different event types
        # Note: consume_if_new already marked the event as "in progress"
        # This prevents duplicate processing even if handler fails
        try:
            if event_type == "invoice.paid":
                result = await self._handle_invoice_paid(data, event_id)
            elif event_type == "invoice.payment_failed":
                result = await self._handle_payment_failed(data, event_id)
            elif event_type == "customer.subscription.updated":
                result = await self._handle_subscription_updated(data, event_id)
            elif event_type == "customer.subscription.deleted":
                result = await self._handle_subscription_deleted(data, event_id)
            else:
                logger.info("Unhandled webhook type: %s", event_type)
                result = {"success": True, "handled": False}
            
            # Event already marked by consume_if_new, no need to mark again
            return result
            
        except Exception as e:
            logger.error("Webhook handler failed for event %s: %s", event_id, type(e).__name__)
            # Event is already marked to prevent duplicate processing
            # Log error for manual investigation - Stripe may retry
            return {"success": False, "error": "Handler failed"}
    
    def _validate_and_transition(
        self,
        sub: UserSubscription,
        new_status: SubscriptionStatus,
        user_id: str,
    ) -> bool:
        """Validate and apply a subscription status transition.
        
        Logs a warning if the transition violates the state machine rules,
        but still applies it (to not ignore valid Stripe events).
        
        Returns:
            True if transition was valid, False if it violated rules
        """
        old_status = sub.status
        
        if not old_status.can_transition_to(new_status):
            logger.warning(
                "Unexpected subscription transition for user %s: %s -> %s",
                user_id, old_status.value, new_status.value
            )
            # Still apply the change to stay in sync with Stripe
            sub.status = new_status
            return False
        
        sub.status = new_status
        return True
    
    async def _handle_invoice_paid(
        self,
        invoice: Dict[str, Any],
        event_id: str,
    ) -> Dict[str, Any]:
        """Handle successful invoice payment."""
        customer_id = invoice.get("customer")
        amount = invoice.get("amount_paid", 0) / 100  # Convert cents
        
        # Find user by customer ID
        user_id = self._find_user_by_customer(customer_id)
        if not user_id:
            logger.warning("User not found for customer %s", customer_id)
            return {"success": True, "message": "User not found"}
        
        sub = self._subscriptions.get(user_id)
        if sub:
            # Validate state transition
            self._validate_and_transition(sub, SubscriptionStatus.ACTIVE, user_id)
            sub.grace_period_end = None
            sub.updated_at = datetime.now(timezone.utc)
        
        self._log_event(
            user_id=user_id,
            event_type=PaymentEvent.PAYMENT_SUCCEEDED,
            amount=amount,
            stripe_event_id=event_id,
        )
        
        logger.info("Payment succeeded for user %s: $%.2f", hash_user_id(user_id), amount)
        return {"success": True}
    
    async def _handle_payment_failed(
        self,
        invoice: Dict[str, Any],
        event_id: str,
    ) -> Dict[str, Any]:
        """Handle failed invoice payment."""
        customer_id = invoice.get("customer")
        
        user_id = self._find_user_by_customer(customer_id)
        if not user_id:
            return {"success": True, "message": "User not found"}
        
        sub = self._subscriptions.get(user_id)
        if sub:
            # Validate state transition
            self._validate_and_transition(sub, SubscriptionStatus.PAST_DUE, user_id)
            
            # Set grace period
            sub.grace_period_end = datetime.now(timezone.utc) + timedelta(
                days=self.GRACE_PERIOD_DAYS
            )
            sub.updated_at = datetime.now(timezone.utc)
        
        self._log_event(
            user_id=user_id,
            event_type=PaymentEvent.PAYMENT_FAILED,
            success=False,
            error_message=invoice.get("last_payment_error", {}).get("message"),
            stripe_event_id=event_id,
        )
        
        logger.warning("Payment failed for user %s", hash_user_id(user_id))
        return {"success": True, "user_notification_required": True}
    
    def _parse_stripe_status(self, stripe_status: str) -> SubscriptionStatus:
        """Parse Stripe subscription status to our enum.
        
        Handles mapping between Stripe's status values and our enum.
        """
        status_map = {
            "active": SubscriptionStatus.ACTIVE,
            "past_due": SubscriptionStatus.PAST_DUE,
            "canceled": SubscriptionStatus.CANCELED,
            "trialing": SubscriptionStatus.TRIALING,
            "unpaid": SubscriptionStatus.UNPAID,
            "paused": SubscriptionStatus.PAUSED,  # Handle Stripe pause feature
            "incomplete": SubscriptionStatus.INCOMPLETE,
            "incomplete_expired": SubscriptionStatus.CANCELED,
            "paused": SubscriptionStatus.PAUSED,
        }
        return status_map.get(stripe_status, SubscriptionStatus.ACTIVE)
    
    async def _handle_subscription_updated(
        self,
        subscription: Dict[str, Any],
        event_id: str,
    ) -> Dict[str, Any]:
        """Handle subscription update."""
        subscription_id = subscription.get("id")
        stripe_status = subscription.get("status")
        
        user_id = self._find_user_by_subscription(subscription_id)
        if not user_id:
            return {"success": True, "message": "User not found"}
        
        sub = self._subscriptions.get(user_id)
        if sub:
            new_status = self._parse_stripe_status(stripe_status)
            # Validate state transition
            self._validate_and_transition(sub, new_status, user_id)
            sub.current_period_end = datetime.fromtimestamp(
                subscription.get("current_period_end", 0), tz=timezone.utc
            )
            sub.updated_at = datetime.now(timezone.utc)
        
        self._log_event(
            user_id=user_id,
            event_type=PaymentEvent.SUBSCRIPTION_UPDATED,
            stripe_event_id=event_id,
            metadata={"status": stripe_status},
        )
        
        return {"success": True}
    
    async def _handle_subscription_deleted(
        self,
        subscription: Dict[str, Any],
        event_id: str,
    ) -> Dict[str, Any]:
        """Handle subscription deletion."""
        subscription_id = subscription.get("id")
        
        user_id = self._find_user_by_subscription(subscription_id)
        if not user_id:
            return {"success": True, "message": "User not found"}
        
        sub = self._subscriptions.get(user_id)
        if sub:
            # Validate state transition
            self._validate_and_transition(sub, SubscriptionStatus.CANCELED, user_id)
            sub.tier = "free"
            sub.stripe_subscription_id = None
            sub.updated_at = datetime.now(timezone.utc)
        
        self._log_event(
            user_id=user_id,
            event_type=PaymentEvent.SUBSCRIPTION_CANCELED,
            stripe_event_id=event_id,
        )
        
        logger.info("Subscription canceled for user %s", hash_user_id(user_id))
        return {"success": True}
    
    def _find_user_by_customer(self, customer_id: str) -> Optional[str]:
        """Find user ID by Stripe customer ID."""
        for user_id, sub in self._subscriptions.items():
            if sub.stripe_customer_id == customer_id:
                return user_id
        return None
    
    def _find_user_by_subscription(self, subscription_id: str) -> Optional[str]:
        """Find user ID by Stripe subscription ID."""
        for user_id, sub in self._subscriptions.items():
            if sub.stripe_subscription_id == subscription_id:
                return user_id
        return None
    
    def _log_event(
        self,
        user_id: str,
        event_type: PaymentEvent,
        amount: Optional[float] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        stripe_event_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Log a payment event."""
        import uuid
        
        log = PaymentLog(
            event_id=str(uuid.uuid4()),
            user_id=user_id,
            event_type=event_type,
            amount=amount,
            success=success,
            error_message=error_message,
            stripe_event_id=stripe_event_id,
            metadata=metadata or {},
        )
        self._payment_logs.append(log)
        
        # Keep logs bounded
        if len(self._payment_logs) > 10000:
            self._payment_logs = self._payment_logs[-10000:]
        
        logger.info(
            "Payment event: user=%s, type=%s, amount=%s, success=%s",
            user_id, event_type.value, amount, success
        )
    
    def get_subscription(self, user_id: str) -> Optional[UserSubscription]:
        """Get user's subscription."""
        return self._subscriptions.get(user_id)
    
    def get_user_tier(self, user_id: str) -> str:
        """Get user's current tier."""
        sub = self._subscriptions.get(user_id)
        if not sub:
            return "free"
        return sub.tier if sub.is_active or sub.in_grace_period else "free"
    
    def get_user_guidance(self, user_id: str) -> Optional[str]:
        """Get user guidance message (e.g., payment issue warning)."""
        sub = self._subscriptions.get(user_id)
        if not sub:
            return None
        
        if sub.status == SubscriptionStatus.PAST_DUE:
            if sub.grace_period_end:
                end_str = sub.grace_period_end.strftime("%B %d, %Y")
                return (
                    f"⚠️ Payment issue: please update your billing information "
                    f"to retain {sub.tier.title()} features. "
                    f"Your access will remain until {end_str}."
                )
            return "⚠️ Payment issue: please update your billing information."
        
        return None
    
    def get_payment_logs(
        self,
        user_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[PaymentLog]:
        """Get payment logs, optionally filtered by user."""
        if user_id:
            logs = [l for l in self._payment_logs if l.user_id == user_id]
        else:
            logs = self._payment_logs
        
        return logs[-limit:]


# ==============================================================================
# FACTORY FUNCTIONS
# ==============================================================================

def create_stripe_client(api_key: Optional[str] = None) -> StripeClient:
    """Create a Stripe client."""
    return StripeClient(api_key)


def create_subscription_manager(
    stripe_client: Optional[StripeClient] = None,
) -> SubscriptionManager:
    """Create a subscription manager."""
    return SubscriptionManager(stripe_client)

