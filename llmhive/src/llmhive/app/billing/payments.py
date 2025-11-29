"""Payment processing integration with Stripe for LLMHive."""
from __future__ import annotations

import datetime as dt
import logging
import os
from typing import Optional

from sqlalchemy.orm import Session

from ..billing.pricing import TierName, get_pricing_manager
from ..billing.subscription import SubscriptionService
from ..models import Subscription, SubscriptionStatus

logger = logging.getLogger(__name__)

# Stripe integration (optional - will fail gracefully if not installed)
try:
    import stripe
    STRIPE_AVAILABLE = True
except ImportError:
    STRIPE_AVAILABLE = False
    stripe = None  # type: ignore
    logger.warning("Stripe SDK not available. Install with: pip install stripe")


class StripePaymentProcessor:
    """Handles payment processing via Stripe."""

    def __init__(self, api_key: Optional[str] = None) -> None:
        if not STRIPE_AVAILABLE:
            raise RuntimeError("Stripe SDK not available. Install with: pip install stripe")

        self.api_key = api_key or os.getenv("STRIPE_SECRET_KEY") or os.getenv("STRIPE_API_KEY")
        if not self.api_key:
            raise ValueError("Stripe API key not provided. Set STRIPE_SECRET_KEY environment variable.")

        stripe.api_key = self.api_key
        logger.info("Stripe payment processor initialized")

    def create_customer(
        self,
        user_id: str,
        email: str,
        name: Optional[str] = None,
    ) -> dict:
        """Create a Stripe customer.

        Args:
            user_id: Internal user identifier
            email: Customer email
            name: Customer name (optional)

        Returns:
            Stripe customer object
        """
        try:
            customer = stripe.Customer.create(
                email=email,
                name=name,
                metadata={"user_id": user_id},
            )
            logger.info("Created Stripe customer %s for user %s", customer.id, user_id)
            return customer
        except Exception as exc:
            logger.error("Failed to create Stripe customer: %s", exc)
            raise

    def create_subscription(
        self,
        customer_id: str,
        tier_name: TierName | str,
        billing_cycle: str = "monthly",
    ) -> dict:
        """Create a Stripe subscription.

        Args:
            customer_id: Stripe customer ID
            tier_name: Pricing tier name
            billing_cycle: "monthly" or "annual"

        Returns:
            Stripe subscription object
        """
        pricing_manager = get_pricing_manager()
        tier = pricing_manager.get_tier(tier_name)
        if tier is None:
            raise ValueError(f"Invalid tier name: {tier_name}")

        # Determine price based on billing cycle
        if billing_cycle == "annual":
            price_amount = int(tier.annual_price_usd * 100)  # Convert to cents
        else:
            price_amount = int(tier.monthly_price_usd * 100)  # Convert to cents

        # Create price ID (in production, these would be pre-created in Stripe)
        # For now, we'll create a one-time price
        try:
            price = stripe.Price.create(
                unit_amount=price_amount,
                currency="usd",
                recurring={"interval": "month" if billing_cycle == "monthly" else "year"},
                product_data={
                    "name": f"LLMHive {tier.display_name}",
                    "description": tier.description,
                },
            )

            subscription = stripe.Subscription.create(
                customer=customer_id,
                items=[{"price": price.id}],
                metadata={"tier_name": tier.name.value if hasattr(tier.name, "value") else str(tier_name)},
            )

            logger.info(
                "Created Stripe subscription %s for customer %s: tier=%s, cycle=%s",
                subscription.id,
                customer_id,
                tier_name,
                billing_cycle,
            )

            return subscription
        except Exception as exc:
            logger.error("Failed to create Stripe subscription: %s", exc)
            raise

    def update_subscription(
        self,
        subscription_id: str,
        new_tier_name: TierName | str,
    ) -> dict:
        """Update a Stripe subscription to a new tier.

        Args:
            subscription_id: Stripe subscription ID
            new_tier_name: New tier name

        Returns:
            Updated Stripe subscription object
        """
        pricing_manager = get_pricing_manager()
        new_tier = pricing_manager.get_tier(new_tier_name)
        if new_tier is None:
            raise ValueError(f"Invalid tier name: {new_tier_name}")

        try:
            # Get current subscription
            subscription = stripe.Subscription.retrieve(subscription_id)

            # Create new price for the tier
            price_amount = int(new_tier.monthly_price_usd * 100)
            price = stripe.Price.create(
                unit_amount=price_amount,
                currency="usd",
                recurring={"interval": subscription.items.data[0].price.recurring.interval},
                product_data={
                    "name": f"LLMHive {new_tier.display_name}",
                    "description": new_tier.description,
                },
            )

            # Update subscription
            updated = stripe.Subscription.modify(
                subscription_id,
                items=[{"id": subscription.items.data[0].id, "price": price.id}],
                metadata={"tier_name": new_tier.name.value if hasattr(new_tier.name, "value") else str(new_tier_name)},
            )

            logger.info("Updated Stripe subscription %s to tier %s", subscription_id, new_tier_name)
            return updated
        except Exception as exc:
            logger.error("Failed to update Stripe subscription: %s", exc)
            raise

    def cancel_subscription(
        self,
        subscription_id: str,
        cancel_immediately: bool = False,
    ) -> dict:
        """Cancel a Stripe subscription.

        Args:
            subscription_id: Stripe subscription ID
            cancel_immediately: If True, cancel now; if False, cancel at period end

        Returns:
            Cancelled Stripe subscription object
        """
        try:
            if cancel_immediately:
                subscription = stripe.Subscription.delete(subscription_id)
            else:
                subscription = stripe.Subscription.modify(
                    subscription_id,
                    cancel_at_period_end=True,
                )

            logger.info(
                "Cancelled Stripe subscription %s: immediately=%s",
                subscription_id,
                cancel_immediately,
            )
            return subscription
        except Exception as exc:
            logger.error("Failed to cancel Stripe subscription: %s", exc)
            raise

    def create_payment_intent(
        self,
        amount: float,
        currency: str = "usd",
        customer_id: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> dict:
        """Create a payment intent for one-time payments.

        Args:
            amount: Amount in dollars
            currency: Currency code (default: "usd")
            customer_id: Optional Stripe customer ID
            metadata: Optional metadata dict

        Returns:
            Stripe payment intent object
        """
        try:
            intent = stripe.PaymentIntent.create(
                amount=int(amount * 100),  # Convert to cents
                currency=currency,
                customer=customer_id,
                metadata=metadata or {},
            )
            logger.info("Created payment intent %s for amount %.2f %s", intent.id, amount, currency)
            return intent
        except Exception as exc:
            logger.error("Failed to create payment intent: %s", exc)
            raise

    def handle_webhook(
        self,
        payload: bytes,
        signature: str,
        webhook_secret: Optional[str] = None,
        db_session: Optional[Session] = None,
    ) -> dict:
        """Handle a Stripe webhook event.

        Args:
            payload: Raw webhook payload
            signature: Stripe signature header
            webhook_secret: Webhook secret (from STRIPE_WEBHOOK_SECRET env var)
            db_session: Optional database session for updating subscriptions

        Returns:
            Processed event data
        """
        if not STRIPE_AVAILABLE:
            raise RuntimeError("Stripe SDK not available")

        webhook_secret = webhook_secret or os.getenv("STRIPE_WEBHOOK_SECRET")
        if not webhook_secret:
            raise ValueError("Stripe webhook secret not provided. Set STRIPE_WEBHOOK_SECRET environment variable.")

        try:
            event = stripe.Webhook.construct_event(payload, signature, webhook_secret)
        except ValueError as exc:
            logger.error("Invalid webhook payload: %s", exc)
            raise
        except stripe.error.SignatureVerificationError as exc:
            logger.error("Invalid webhook signature: %s", exc)
            raise

        event_type = event["type"]
        event_data = event["data"]["object"]

        logger.info("Processing Stripe webhook: %s", event_type)

        # Handle different event types
        if db_session:
            service = SubscriptionService(db_session)

            if event_type == "customer.subscription.created":
                # New subscription created
                stripe_sub_id = event_data.get("id")
                customer_id = event_data.get("customer")
                metadata = event_data.get("metadata", {})
                user_id = metadata.get("user_id")

                if user_id and stripe_sub_id:
                    # Find or create subscription in our DB
                    subscription = (
                        db_session.query(Subscription)
                        .filter(Subscription.stripe_subscription_id == stripe_sub_id)
                        .first()
                    )
                    if not subscription:
                        logger.warning("Subscription %s not found in DB for Stripe subscription %s", user_id, stripe_sub_id)

            elif event_type == "customer.subscription.updated":
                # Subscription updated
                stripe_sub_id = event_data.get("id")
                subscription = (
                    db_session.query(Subscription)
                    .filter(Subscription.stripe_subscription_id == stripe_sub_id)
                    .first()
                )
                if subscription:
                    # Update period dates
                    period_start = dt.datetime.fromtimestamp(event_data.get("current_period_start", 0), tz=dt.timezone.utc)
                    period_end = dt.datetime.fromtimestamp(event_data.get("current_period_end", 0), tz=dt.timezone.utc)
                    # Convert to UTC naive for database
                    period_start = period_start.replace(tzinfo=None)
                    period_end = period_end.replace(tzinfo=None)
                    service.update_subscription_period(subscription.id, period_start, period_end)

                    # Update status
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

                    db_session.commit()

            elif event_type == "customer.subscription.deleted":
                # Subscription cancelled
                stripe_sub_id = event_data.get("id")
                subscription = (
                    db_session.query(Subscription)
                    .filter(Subscription.stripe_subscription_id == stripe_sub_id)
                    .first()
                )
                if subscription:
                    service.update_subscription_status(subscription.id, SubscriptionStatus.CANCELLED)
                    db_session.commit()

            elif event_type == "invoice.payment_succeeded":
                # Payment succeeded
                stripe_sub_id = event_data.get("subscription")
                if stripe_sub_id:
                    subscription = (
                        db_session.query(Subscription)
                        .filter(Subscription.stripe_subscription_id == stripe_sub_id)
                        .first()
                    )
                    if subscription:
                        # Ensure subscription is active
                        if subscription.status != SubscriptionStatus.ACTIVE:
                            service.update_subscription_status(subscription.id, SubscriptionStatus.ACTIVE)
                        db_session.commit()

            elif event_type == "invoice.payment_failed":
                # Payment failed
                stripe_sub_id = event_data.get("subscription")
                if stripe_sub_id:
                    subscription = (
                        db_session.query(Subscription)
                        .filter(Subscription.stripe_subscription_id == stripe_sub_id)
                        .first()
                    )
                    if subscription:
                        service.update_subscription_status(subscription.id, SubscriptionStatus.PAST_DUE)
                        db_session.commit()

        return {"event_type": event_type, "processed": True}

    def generate_invoice(
        self,
        subscription_id: str,
        period_start: Optional[int] = None,
        period_end: Optional[int] = None,
    ) -> dict:
        """Generate an invoice for a subscription.

        Args:
            subscription_id: Stripe subscription ID
            period_start: Period start timestamp (optional)
            period_end: Period end timestamp (optional)

        Returns:
            Stripe invoice object
        """
        try:
            invoice = stripe.Invoice.create(
                subscription=subscription_id,
                auto_advance=True,  # Automatically finalize and attempt payment
            )
            logger.info("Generated invoice %s for subscription %s", invoice.id, subscription_id)
            return invoice
        except Exception as exc:
            logger.error("Failed to generate invoice: %s", exc)
            raise


# Global payment processor instance (lazy initialization)
_payment_processor: Optional[StripePaymentProcessor] = None


def get_payment_processor() -> Optional[StripePaymentProcessor]:
    """Get the global payment processor instance."""
    global _payment_processor
    if _payment_processor is None and STRIPE_AVAILABLE:
        try:
            _payment_processor = StripePaymentProcessor()
        except (ValueError, RuntimeError) as exc:
            logger.warning("Payment processor not available: %s", exc)
            return None
    return _payment_processor

