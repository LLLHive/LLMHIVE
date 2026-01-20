"""Subscription management service for LLMHive billing system."""
from __future__ import annotations

import datetime as dt
import logging
from typing import Optional

from sqlalchemy.orm import Session

from ..models import Subscription, SubscriptionStatus
from .pricing import PricingTier, TierName, get_pricing_manager

logger = logging.getLogger(__name__)


class SubscriptionService:
    """Manages subscription lifecycle and operations."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.pricing_manager = get_pricing_manager()

    def create_subscription(
        self,
        user_id: str,
        tier_name: TierName | str,
        billing_cycle: str = "monthly",
        *,
        stripe_customer_id: Optional[str] = None,
        stripe_subscription_id: Optional[str] = None,
    ) -> Subscription:
        """Create a new subscription for a user.

        Args:
            user_id: User identifier
            tier_name: Pricing tier name
            billing_cycle: "monthly" or "annual"
            stripe_customer_id: Optional Stripe customer ID
            stripe_subscription_id: Optional Stripe subscription ID

        Returns:
            Created Subscription object

        Raises:
            ValueError: If tier_name is invalid or user already has active subscription
        """
        # Check if user already has an active subscription
        existing = self.get_user_subscription(user_id)
        if existing and existing.is_active():
            raise ValueError(
                f"User {user_id} already has an active subscription. "
                "Cancel existing subscription before creating a new one."
            )

        # Validate tier
        tier = self.pricing_manager.get_tier(tier_name)
        if tier is None:
            raise ValueError(f"Invalid tier name: {tier_name}")

        # Validate billing cycle
        if billing_cycle not in ("monthly", "annual"):
            raise ValueError(f"Invalid billing cycle: {billing_cycle}. Must be 'monthly' or 'annual'")

        # Calculate period dates
        now = dt.datetime.now(dt.timezone.utc)
        if billing_cycle == "annual":
            period_end = now + dt.timedelta(days=365)
        else:
            period_end = now + dt.timedelta(days=30)

        # Create subscription
        subscription = Subscription(
            user_id=user_id,
            tier_name=tier.name.value if isinstance(tier.name, TierName) else str(tier_name).lower(),
            status=SubscriptionStatus.ACTIVE,
            billing_cycle=billing_cycle,
            current_period_start=now,
            current_period_end=period_end,
            cancel_at_period_end=False,
            stripe_customer_id=stripe_customer_id,
            stripe_subscription_id=stripe_subscription_id,
        )

        self.session.add(subscription)
        self.session.flush()

        logger.info(
            "Created subscription for user %s: tier=%s, cycle=%s, period_end=%s",
            user_id,
            tier_name,
            billing_cycle,
            period_end,
        )
        
        # Subscription Enforcement: Call payment hook
        try:
            from .enforcement import PaymentHooks
            PaymentHooks.on_subscription_created(user_id, str(tier_name), subscription.id)
        except Exception as exc:
            logger.debug("Payment hook not available: %s", exc)

        return subscription

    def get_user_subscription(self, user_id: str) -> Optional[Subscription]:
        """Get the active subscription for a user.

        Returns the most recent active subscription, or None if no active subscription exists.
        """
        stmt = (
            self.session.query(Subscription)
            .filter(Subscription.user_id == user_id)
            .order_by(Subscription.created_at.desc())
        )
        subscriptions = stmt.all()

        # Return first active subscription, or most recent if none active
        for sub in subscriptions:
            if sub.is_active():
                return sub

        return subscriptions[0] if subscriptions else None

    def get_subscription(self, subscription_id: int) -> Optional[Subscription]:
        """Get a subscription by ID."""
        return self.session.query(Subscription).filter(Subscription.id == subscription_id).first()

    def renew_subscription(self, subscription_id: int) -> Subscription:
        """Renew a subscription for another billing period.

        Args:
            subscription_id: Subscription ID to renew

        Returns:
            Updated Subscription object

        Raises:
            ValueError: If subscription not found or cannot be renewed
        """
        subscription = self.get_subscription(subscription_id)
        if subscription is None:
            raise ValueError(f"Subscription {subscription_id} not found")

        if subscription.status != SubscriptionStatus.ACTIVE:
            raise ValueError(f"Cannot renew subscription {subscription_id}: status is {subscription.status}")

        # Calculate new period
        now = dt.datetime.now(dt.timezone.utc)
        if subscription.billing_cycle == "annual":
            period_duration = dt.timedelta(days=365)
        else:
            period_duration = dt.timedelta(days=30)

        # Set new period
        subscription.current_period_start = now
        subscription.current_period_end = now + period_duration
        subscription.status = SubscriptionStatus.ACTIVE
        subscription.cancel_at_period_end = False

        self.session.flush()

        logger.info(
            "Renewed subscription %d: new period_end=%s",
            subscription_id,
            subscription.current_period_end,
        )

        return subscription

    def cancel_subscription(
        self,
        subscription_id: int,
        cancel_immediately: bool = False,
    ) -> Subscription:
        """Cancel a subscription.

        Args:
            subscription_id: Subscription ID to cancel
            cancel_immediately: If True, cancel now; if False, cancel at period end

        Returns:
            Updated Subscription object

        Raises:
            ValueError: If subscription not found
        """
        subscription = self.get_subscription(subscription_id)
        if subscription is None:
            raise ValueError(f"Subscription {subscription_id} not found")

        if cancel_immediately:
            subscription.status = SubscriptionStatus.CANCELLED
            subscription.cancelled_at = dt.datetime.now(dt.timezone.utc)
            subscription.current_period_end = dt.datetime.now(dt.timezone.utc)
            subscription.cancel_at_period_end = False
        else:
            subscription.cancel_at_period_end = True
            # Status remains ACTIVE until period end

        self.session.flush()

        logger.info(
            "Cancelled subscription %d: immediately=%s, period_end=%s",
            subscription_id,
            cancel_immediately,
            subscription.current_period_end,
        )
        
        # Subscription Enforcement: Call payment hook
        try:
            from .enforcement import PaymentHooks
            PaymentHooks.on_subscription_cancelled(subscription.user_id, subscription.tier_name)
        except Exception as exc:
            logger.debug("Payment hook not available: %s", exc)

        return subscription

    def upgrade_subscription(
        self,
        subscription_id: int,
        new_tier_name: TierName | str,
    ) -> Subscription:
        """Upgrade a subscription to a higher tier.

        Args:
            subscription_id: Subscription ID to upgrade
            new_tier_name: New tier name

        Returns:
            Updated Subscription object

        Raises:
            ValueError: If subscription not found or tier is invalid
        """
        subscription = self.get_subscription(subscription_id)
        if subscription is None:
            raise ValueError(f"Subscription {subscription_id} not found")

        # Validate new tier
        new_tier = self.pricing_manager.get_tier(new_tier_name)
        if new_tier is None:
            raise ValueError(f"Invalid tier name: {new_tier_name}")

        # Check if it's actually an upgrade
        current_tier = self.pricing_manager.get_tier(subscription.tier_name)
        if current_tier is None:
            raise ValueError(f"Current tier {subscription.tier_name} is invalid")

        # Simple upgrade check: compare monthly prices
        if new_tier.monthly_price_usd < current_tier.monthly_price_usd:
            raise ValueError(
                f"Cannot upgrade to {new_tier_name}: it's cheaper than current tier {subscription.tier_name}. "
                "Use downgrade_subscription instead."
            )

        # Update tier
        old_tier = subscription.tier_name
        subscription.tier_name = new_tier.name.value if isinstance(new_tier.name, TierName) else str(new_tier_name).lower()

        self.session.flush()

        logger.info(
            "Upgraded subscription %d: %s -> %s",
            subscription_id,
            old_tier,
            subscription.tier_name,
        )
        
        # Subscription Enforcement: Call payment hook
        try:
            from .enforcement import PaymentHooks
            PaymentHooks.on_subscription_upgraded(subscription.user_id, old_tier, subscription.tier_name)
        except Exception as exc:
            logger.debug("Payment hook not available: %s", exc)

        return subscription

    def downgrade_subscription(
        self,
        subscription_id: int,
        new_tier_name: TierName | str,
    ) -> Subscription:
        """Downgrade a subscription to a lower tier.

        Args:
            subscription_id: Subscription ID to downgrade
            new_tier_name: New tier name

        Returns:
            Updated Subscription object

        Raises:
            ValueError: If subscription not found or tier is invalid
        """
        subscription = self.get_subscription(subscription_id)
        if subscription is None:
            raise ValueError(f"Subscription {subscription_id} not found")

        # Validate new tier
        new_tier = self.pricing_manager.get_tier(new_tier_name)
        if new_tier is None:
            raise ValueError(f"Invalid tier name: {new_tier_name}")

        # Check if it's actually a downgrade
        current_tier = self.pricing_manager.get_tier(subscription.tier_name)
        if current_tier is None:
            raise ValueError(f"Current tier {subscription.tier_name} is invalid")

        # Simple downgrade check: compare monthly prices
        if new_tier.monthly_price_usd > current_tier.monthly_price_usd:
            raise ValueError(
                f"Cannot downgrade to {new_tier_name}: it's more expensive than current tier {subscription.tier_name}. "
                "Use upgrade_subscription instead."
            )

        # Update tier
        old_tier = subscription.tier_name
        subscription.tier_name = new_tier.name.value if isinstance(new_tier.name, TierName) else str(new_tier_name).lower()

        self.session.flush()

        logger.info(
            "Downgraded subscription %d: %s -> %s",
            subscription_id,
            old_tier,
            subscription.tier_name,
        )

        return subscription

    def update_subscription_status(
        self,
        subscription_id: int,
        status: SubscriptionStatus,
    ) -> Subscription:
        """Update subscription status (typically called by webhooks).

        Args:
            subscription_id: Subscription ID
            status: New status

        Returns:
            Updated Subscription object

        Raises:
            ValueError: If subscription not found
        """
        subscription = self.get_subscription(subscription_id)
        if subscription is None:
            raise ValueError(f"Subscription {subscription_id} not found")

        old_status = subscription.status
        subscription.status = status

        if status == SubscriptionStatus.CANCELLED and subscription.cancelled_at is None:
            subscription.cancelled_at = dt.datetime.now(dt.timezone.utc)

        self.session.flush()

        logger.info(
            "Updated subscription %d status: %s -> %s",
            subscription_id,
            old_status,
            status,
        )

        return subscription

    def update_subscription_period(
        self,
        subscription_id: int,
        period_start: dt.datetime,
        period_end: dt.datetime,
    ) -> Subscription:
        """Update subscription billing period (typically called by webhooks).

        Args:
            subscription_id: Subscription ID
            period_start: New period start date
            period_end: New period end date

        Returns:
            Updated Subscription object

        Raises:
            ValueError: If subscription not found
        """
        subscription = self.get_subscription(subscription_id)
        if subscription is None:
            raise ValueError(f"Subscription {subscription_id} not found")

        subscription.current_period_start = period_start
        subscription.current_period_end = period_end

        self.session.flush()

        logger.info(
            "Updated subscription %d period: %s to %s",
            subscription_id,
            period_start,
            period_end,
        )

        return subscription

    def can_access_feature(self, user_id: str, feature: str) -> bool:
        """Check if a user can access a specific feature based on their subscription.

        Args:
            user_id: User identifier
            feature: Feature name to check

        Returns:
            True if user can access the feature, False otherwise
        """
        subscription = self.get_user_subscription(user_id)
        if subscription is None:
            # No subscription = Lite tier (default)
            return self.pricing_manager.can_access_feature(TierName.LITE, feature)

        tier = self.pricing_manager.get_tier(subscription.tier_name)
        if tier is None:
            return False

        return tier.can_use_feature(feature)

    def check_usage_limits(
        self,
        user_id: str,
        *,
        requests_this_month: int = 0,
        tokens_this_month: int = 0,
        models_in_request: int = 1,
        concurrent_requests: int = 1,
        storage_mb: int = 0,
    ) -> dict:
        """Check if user's usage is within their tier limits.

        Returns a dict with limit check results.
        """
        subscription = self.get_user_subscription(user_id)
        if subscription is None:
            # No subscription = Lite tier (default)
            tier_name = TierName.LITE
        else:
            tier_name = subscription.tier_name

        return self.pricing_manager.check_limits(
            tier_name,
            requests_this_month=requests_this_month,
            tokens_this_month=tokens_this_month,
            models_in_request=models_in_request,
            concurrent_requests=concurrent_requests,
            storage_mb=storage_mb,
        )

