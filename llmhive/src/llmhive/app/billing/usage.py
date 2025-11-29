"""Usage tracking and billing calculation for LLMHive."""
from __future__ import annotations

import datetime as dt
import logging
from typing import Dict, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import Subscription, UsageRecord
from .pricing import get_pricing_manager
from .subscription import SubscriptionService

logger = logging.getLogger(__name__)


class UsageTracker:
    """Tracks user usage for billing purposes."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.pricing_manager = get_pricing_manager()
        self.subscription_service = SubscriptionService(session)

    def record_usage(
        self,
        user_id: str,
        *,
        tokens: int = 0,
        requests: int = 1,
        models_used: Optional[list[str]] = None,
        cost_usd: float = 0.0,
        metadata: Optional[Dict] = None,
    ) -> UsageRecord:
        """Record usage for a user.

        Args:
            user_id: User identifier
            tokens: Number of tokens used
            requests: Number of requests (default: 1)
            models_used: List of models used (optional)
            cost_usd: Cost in USD (optional, will be calculated if not provided)
            metadata: Additional metadata (optional)

        Returns:
            Created UsageRecord
        """
        # Get user's subscription
        subscription = self.subscription_service.get_user_subscription(user_id)
        if subscription is None:
            # No subscription = free tier, but we still track usage
            # Create a temporary subscription record or use a default
            logger.warning("User %s has no subscription, usage will not be tracked", user_id)
            return None  # type: ignore

        # Get current billing period
        period_start = subscription.current_period_start
        period_end = subscription.current_period_end

        # Get or create usage record for this period
        usage_record = (
            self.session.query(UsageRecord)
            .filter(
                UsageRecord.subscription_id == subscription.id,
                UsageRecord.period_start == period_start,
                UsageRecord.period_end == period_end,
            )
            .first()
        )

        if usage_record is None:
            usage_record = UsageRecord(
                subscription_id=subscription.id,
                user_id=user_id,
                period_start=period_start,
                period_end=period_end,
                requests_count=0,
                tokens_count=0,
                cost_usd=0.0,
                usage_metadata={},
            )
            self.session.add(usage_record)

        # Update usage
        usage_record.requests_count += requests
        usage_record.tokens_count += tokens

        # Calculate cost if not provided
        if cost_usd == 0.0:
            cost_usd = self._calculate_cost(subscription.tier_name, tokens, requests)

        usage_record.cost_usd += cost_usd

        # Update metadata
        if metadata:
            if models_used:
                metadata["models_used"] = models_used
            usage_record.usage_metadata.update(metadata)

        self.session.flush()

        logger.debug(
            "Recorded usage for user %s: %d tokens, %d requests, $%.2f cost",
            user_id,
            tokens,
            requests,
            cost_usd,
        )

        return usage_record

    def _calculate_cost(
        self,
        tier_name: str,
        tokens: int,
        requests: int,
    ) -> float:
        """Calculate cost based on tier and usage.

        This is a simplified calculation. In production, you would:
        - Use actual provider costs
        - Apply tier-based pricing
        - Consider overage charges
        """
        # Base cost per 1K tokens (simplified)
        # In production, this would be calculated from actual provider costs
        cost_per_1k_tokens = 0.002  # $0.002 per 1K tokens

        token_cost = (tokens / 1000.0) * cost_per_1k_tokens
        request_cost = requests * 0.001  # $0.001 per request

        total_cost = token_cost + request_cost

        # Apply tier-based pricing (Enterprise gets discounts, etc.)
        tier = self.pricing_manager.get_tier(tier_name)
        if tier:
            # Enterprise tier gets 20% discount
            if tier.name == "enterprise":
                total_cost *= 0.8

        return round(total_cost, 4)

    def get_usage_summary(
        self,
        user_id: str,
        period_start: Optional[dt.datetime] = None,
        period_end: Optional[dt.datetime] = None,
    ) -> Dict:
        """Get usage summary for a user.

        Args:
            user_id: User identifier
            period_start: Period start (optional, defaults to current period)
            period_end: Period end (optional, defaults to current period)

        Returns:
            Usage summary dict
        """
        subscription = self.subscription_service.get_user_subscription(user_id)
        if subscription is None:
            return {
                "user_id": user_id,
                "subscription": None,
                "period_start": None,
                "period_end": None,
                "requests_count": 0,
                "tokens_count": 0,
                "cost_usd": 0.0,
                "within_limits": True,
            }

        # Use subscription period if not specified
        if period_start is None:
            period_start = subscription.current_period_start
        if period_end is None:
            period_end = subscription.current_period_end

        # Get usage records for the period
        stmt = (
            select(UsageRecord)
            .filter(
                UsageRecord.subscription_id == subscription.id,
                UsageRecord.period_start >= period_start,
                UsageRecord.period_end <= period_end,
            )
        )
        usage_records = list(self.session.scalars(stmt).all())

        # Aggregate usage
        total_requests = sum(record.requests_count for record in usage_records)
        total_tokens = sum(record.tokens_count for record in usage_records)
        total_cost = sum(record.cost_usd for record in usage_records)

        # Check limits
        limits_check = self.subscription_service.check_usage_limits(
            user_id,
            requests_this_month=total_requests,
            tokens_this_month=total_tokens,
        )

        return {
            "user_id": user_id,
            "subscription_id": subscription.id,
            "tier_name": subscription.tier_name,
            "period_start": period_start,
            "period_end": period_end,
            "requests_count": total_requests,
            "tokens_count": total_tokens,
            "cost_usd": round(total_cost, 2),
            "within_limits": limits_check["within_limits"],
            "limit_details": limits_check,
        }

    def get_current_period_usage(self, user_id: str) -> Dict:
        """Get usage for the current billing period."""
        subscription = self.subscription_service.get_user_subscription(user_id)
        if subscription is None:
            return self.get_usage_summary(user_id)

        return self.get_usage_summary(
            user_id,
            period_start=subscription.current_period_start,
            period_end=subscription.current_period_end,
        )

    def get_usage_history(
        self,
        user_id: str,
        limit: int = 10,
    ) -> list[Dict]:
        """Get usage history for a user.

        Args:
            user_id: User identifier
            limit: Maximum number of periods to return

        Returns:
            List of usage summaries
        """
        subscription = self.subscription_service.get_user_subscription(user_id)
        if subscription is None:
            return []

        # Get all usage records for this subscription
        stmt = (
            select(UsageRecord)
            .filter(UsageRecord.subscription_id == subscription.id)
            .order_by(UsageRecord.period_start.desc())
            .limit(limit)
        )
        usage_records = list(self.session.scalars(stmt).all())

        return [
            {
                "period_start": record.period_start,
                "period_end": record.period_end,
                "requests_count": record.requests_count,
                "tokens_count": record.tokens_count,
                "cost_usd": round(record.cost_usd, 2),
            }
            for record in usage_records
        ]

    def check_usage_limits(
        self,
        user_id: str,
        *,
        requested_tokens: int = 0,
        requested_models: int = 1,
    ) -> Dict:
        """Check if a user's requested usage is within their tier limits.

        Args:
            user_id: User identifier
            requested_tokens: Tokens the user wants to use
            requested_models: Number of models the user wants to use

        Returns:
            Dict with limit check results and current usage
        """
        # Get current usage
        current_usage = self.get_current_period_usage(user_id)

        # Check limits
        limits_check = self.subscription_service.check_usage_limits(
            user_id,
            requests_this_month=current_usage.get("requests_count", 0),
            tokens_this_month=current_usage.get("tokens_count", 0) + requested_tokens,
            models_in_request=requested_models,
        )

        return {
            **limits_check,
            "current_usage": current_usage,
            "requested_tokens": requested_tokens,
            "requested_models": requested_models,
        }


class BillingCalculator:
    """Calculates billing amounts and costs."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.pricing_manager = get_pricing_manager()

    def calculate_monthly_cost(
        self,
        tier_name: str,
        tokens: int,
        requests: int,
    ) -> float:
        """Calculate monthly cost for a tier and usage.

        Args:
            tier_name: Pricing tier name
            tokens: Number of tokens used
            requests: Number of requests

        Returns:
            Total cost in USD
        """
        tier = self.pricing_manager.get_tier(tier_name)
        if tier is None:
            return 0.0

        # Base subscription cost
        subscription_cost = tier.monthly_price_usd

        # Usage-based cost (simplified)
        # In production, this would use actual provider costs
        usage_cost = (tokens / 1000.0) * 0.002 + requests * 0.001

        # Apply tier discounts
        if tier.name == "enterprise":
            usage_cost *= 0.8  # 20% discount

        return round(subscription_cost + usage_cost, 2)

    def estimate_cost(
        self,
        tier_name: str,
        estimated_tokens_per_month: int,
        estimated_requests_per_month: int,
    ) -> Dict:
        """Estimate monthly cost for a tier and expected usage.

        Returns:
            Dict with cost breakdown
        """
        tier = self.pricing_manager.get_tier(tier_name)
        if tier is None:
            return {"error": "Invalid tier name"}

        subscription_cost = tier.monthly_price_usd
        usage_cost = self.calculate_monthly_cost(tier_name, estimated_tokens_per_month, estimated_requests_per_month) - subscription_cost
        total_cost = subscription_cost + usage_cost

        return {
            "tier_name": tier_name,
            "subscription_cost": subscription_cost,
            "estimated_usage_cost": round(usage_cost, 2),
            "total_estimated_cost": round(total_cost, 2),
            "estimated_tokens": estimated_tokens_per_month,
            "estimated_requests": estimated_requests_per_month,
        }

