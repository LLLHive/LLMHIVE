"""Usage tracking and limit enforcement for LLMHive.

Usage tracking: This module provides functions to log usage and check limits.
It integrates with the billing system to track tokens and requests per user.
"""
from __future__ import annotations

import datetime as dt
import logging
from typing import Dict, Optional, Any
from threading import Lock

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .models import UsageRecord, Subscription
from .billing.pricing import get_pricing_manager, TierName
from .billing.subscription import SubscriptionService

logger = logging.getLogger(__name__)

# Usage tracking: Thread-safe lock for concurrent usage logging
_usage_lock = Lock()


def log_usage(
    session: Session,
    user_id: str,
    tokens_used: int = 0,
    requests: int = 1,
    models_used: Optional[list[str]] = None,
    metadata: Optional[Dict] = None,
) -> Optional[UsageRecord]:
    """Usage tracking: Log usage for a user.
    
    Records usage in the database, aggregating by billing period.
    Thread-safe for concurrent requests.
    
    Args:
        session: Database session
        user_id: User identifier
        tokens_used: Number of tokens used (default: 0)
        requests: Number of requests (default: 1)
        models_used: List of models used (optional)
        metadata: Additional metadata (optional)
    
    Returns:
        UsageRecord if successful, None if user has no subscription
    """
    # Usage tracking: Thread-safe logging
    with _usage_lock:
        try:
            subscription_service = SubscriptionService(session)
            subscription = subscription_service.get_user_subscription(user_id)
            
            if subscription is None:
                # Usage tracking: No subscription = free tier, still track usage
                # For free tier, we'll track in a special way or create a default subscription
                logger.debug(
                    "Usage tracking: User %s has no subscription, logging as free tier",
                    user_id
                )
                # For now, we still need a subscription to track usage
                # In production, you might want to create a default free subscription
                return None
            
            # Usage tracking: Get current billing period
            period_start = subscription.current_period_start
            period_end = subscription.current_period_end
            
            # Usage tracking: Get or create usage record for this period
            stmt = (
                select(UsageRecord)
                .filter(
                    UsageRecord.subscription_id == subscription.id,
                    UsageRecord.period_start == period_start,
                    UsageRecord.period_end == period_end,
                )
            )
            usage_record = session.scalar(stmt)
            
            if usage_record is None:
                # Usage tracking: Create new usage record for this period
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
                session.add(usage_record)
            
            # Usage tracking: Update usage counts
            usage_record.requests_count += requests
            usage_record.tokens_count += tokens_used
            
            # Usage tracking: Update metadata
            if metadata:
                if models_used:
                    metadata["models_used"] = models_used
                usage_record.usage_metadata.update(metadata)
            
            session.flush()
            
            logger.debug(
                "Usage tracking: Logged usage for user %s: %d tokens, %d requests",
                user_id,
                tokens_used,
                requests
            )
            
            return usage_record
            
        except Exception as exc:
            logger.error(
                "Usage tracking: Failed to log usage for user %s: %s",
                user_id,
                exc,
                exc_info=True
            )
            session.rollback()
            return None


def get_monthly_usage(
    session: Session,
    user_id: str,
    period_start: Optional[dt.datetime] = None,
    period_end: Optional[dt.datetime] = None,
) -> Dict[str, int]:
    """Usage tracking: Get monthly usage for a user.
    
    Returns aggregated usage for the current billing period or specified period.
    
    Args:
        session: Database session
        user_id: User identifier
        period_start: Period start (optional, defaults to current period)
        period_end: Period end (optional, defaults to current period)
    
    Returns:
        Dict with 'tokens' and 'requests' counts
    """
    try:
        subscription_service = SubscriptionService(session)
        subscription = subscription_service.get_user_subscription(user_id)
        
        if subscription is None:
            # Usage tracking: No subscription = free tier, return zero usage
            return {"tokens": 0, "requests": 0}
        
        # Usage tracking: Use subscription period if not specified
        if period_start is None:
            period_start = subscription.current_period_start
        if period_end is None:
            period_end = subscription.current_period_end
        
        # Usage tracking: Query usage records for the period
        stmt = (
            select(
                func.sum(UsageRecord.tokens_count).label("total_tokens"),
                func.sum(UsageRecord.requests_count).label("total_requests"),
            )
            .filter(
                UsageRecord.subscription_id == subscription.id,
                UsageRecord.period_start >= period_start,
                UsageRecord.period_end <= period_end,
            )
        )
        result = session.execute(stmt).first()
        
        tokens = int(result.total_tokens or 0) if result else 0
        requests = int(result.total_requests or 0) if result else 0
        
        return {
            "tokens": tokens,
            "requests": requests,
        }
        
    except Exception as exc:
        logger.error(
            "Usage tracking: Failed to get monthly usage for user %s: %s",
            user_id,
            exc,
            exc_info=True
        )
        return {"tokens": 0, "requests": 0}


def check_usage_limit(
    session: Session,
    user_id: str,
    requested_tokens: int = 0,
    requested_requests: int = 1,
) -> Dict[str, Any]:
    """Usage tracking: Check if user's usage is within tier limits.
    
    Compares current usage + requested usage against tier limits.
    
    Args:
        session: Database session
        user_id: User identifier
        requested_tokens: Tokens requested for this query (default: 0)
        requested_requests: Requests for this query (default: 1)
    
    Returns:
        Dict with:
        - 'within_limits': bool
        - 'tokens_ok': bool
        - 'requests_ok': bool
        - 'current_tokens': int
        - 'current_requests': int
        - 'tier_limits': dict with tier limits
        - 'message': str (error message if limit exceeded)
    """
    try:
        subscription_service = SubscriptionService(session)
        subscription = subscription_service.get_user_subscription(user_id)
        pricing_manager = get_pricing_manager()
        
        # Usage tracking: Determine tier
        # Unsubscribed users default to FREE tier
        if subscription is None:
            tier_name = TierName.FREE
        else:
            tier_name = subscription.tier_name
        
        tier = pricing_manager.get_tier(tier_name)
        if tier is None:
            logger.warning(
                "Usage tracking: Invalid tier '%s' for user %s",
                tier_name,
                user_id
            )
            return {
                "within_limits": False,
                "tokens_ok": False,
                "requests_ok": False,
                "current_tokens": 0,
                "current_requests": 0,
                "tier_limits": {},
                "message": "Invalid subscription tier",
            }
        
        # Usage tracking: Get current usage
        current_usage = get_monthly_usage(session, user_id)
        current_tokens = current_usage["tokens"]
        current_requests = current_usage["requests"]
        
        # Usage tracking: Calculate projected usage
        projected_tokens = current_tokens + requested_tokens
        projected_requests = current_requests + requested_requests
        
        # Usage tracking: Check limits
        limits = tier.limits
        tokens_ok = (
            limits.max_tokens_per_month == 0
            or projected_tokens <= limits.max_tokens_per_month
        )
        requests_ok = (
            limits.max_requests_per_month == 0
            or projected_requests <= limits.max_requests_per_month
        )
        
        within_limits = tokens_ok and requests_ok
        
        # Usage tracking: Build error message if limit exceeded
        message = None
        if not within_limits:
            details = []
            if not tokens_ok:
                details.append(
                    f"Token limit exceeded ({projected_tokens:,} / {limits.max_tokens_per_month:,})"
                )
            if not requests_ok:
                details.append(
                    f"Request limit exceeded ({projected_requests:,} / {limits.max_requests_per_month:,})"
                )
            message = f"Usage limit reached for this month. {' '.join(details)} Please upgrade."
        
        return {
            "within_limits": within_limits,
            "tokens_ok": tokens_ok,
            "requests_ok": requests_ok,
            "current_tokens": current_tokens,
            "current_requests": current_requests,
            "projected_tokens": projected_tokens,
            "projected_requests": projected_requests,
            "tier_limits": {
                "max_tokens_per_month": limits.max_tokens_per_month,
                "max_requests_per_month": limits.max_requests_per_month,
            },
            "tier_name": tier_name.value if isinstance(tier_name, TierName) else str(tier_name),
            "message": message,
        }
        
    except Exception as exc:
        logger.error(
            "Usage tracking: Failed to check usage limit for user %s: %s",
            user_id,
            exc,
            exc_info=True
        )
        return {
            "within_limits": False,
            "tokens_ok": False,
            "requests_ok": False,
            "current_tokens": 0,
            "current_requests": 0,
            "tier_limits": {},
            "message": "Error checking usage limits",
        }


def prepare_stripe_usage_record(
    session: Session,
    user_id: str,
    tokens_used: int,
) -> Optional[Dict[str, Any]]:
    """Usage tracking: Prepare usage record for Stripe metered billing.
    
    This function prepares usage data that can be sent to Stripe's Reporting API
    for metered billing. The actual Stripe API call should be made separately
    (e.g., via a background job or webhook handler).
    
    Args:
        session: Database session
        user_id: User identifier
        tokens_used: Number of tokens used
    
    Returns:
        Dict with Stripe usage record data, or None if not applicable
    
    Note:
        This is a placeholder for Stripe integration. In production, you would:
        1. Get the Stripe subscription item ID from the subscription record
        2. Format the usage data according to Stripe's API
        3. Call stripe.UsageRecords.create() or stripe.Reporting.UsageRecords.create()
        4. Handle errors and retries appropriately
    
    Example Stripe API call:
        import stripe
        stripe.UsageRecords.create(
            subscription_item=subscription_item_id,
            quantity=tokens_used,
            timestamp=int(dt.datetime.now(dt.timezone.utc).timestamp()),
        )
    """
    try:
        subscription_service = SubscriptionService(session)
        subscription = subscription_service.get_user_subscription(user_id)
        
        if subscription is None:
            return None
        
        # Usage tracking: Check if subscription has Stripe integration
        if not subscription.stripe_subscription_id:
            return None
        
        # Usage tracking: Prepare usage record for Stripe
        # In production, you would:
        # 1. Get the subscription item ID from Stripe subscription
        # 2. Format usage according to Stripe's metered billing requirements
        # 3. Queue for background processing or send immediately
        
        return {
            "stripe_subscription_id": subscription.stripe_subscription_id,
            "stripe_customer_id": subscription.stripe_customer_id,
            "quantity": tokens_used,  # Or requests, depending on your metering
            "timestamp": int(dt.datetime.now(dt.timezone.utc).timestamp()),
            "action": "increment",  # or "set" depending on your billing model
        }
        
    except Exception as exc:
        logger.error(
            "Usage tracking: Failed to prepare Stripe usage record for user %s: %s",
            user_id,
            exc,
            exc_info=True
        )
        return None

