"""Comprehensive subscription enforcement for LLMHive."""
from __future__ import annotations

import datetime as dt
import logging
from dataclasses import dataclass
from typing import Dict, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from ..models import Subscription
from .pricing import TierName, get_pricing_manager
from .subscription import SubscriptionService
from .usage import UsageTracker

logger = logging.getLogger(__name__)


@dataclass
class EnforcementResult:
    """Result of subscription enforcement check."""
    
    allowed: bool
    reason: Optional[str] = None
    tier_name: str = "free"
    limit_type: Optional[str] = None  # "requests", "tokens", "models", "rate", "feature"
    current_usage: Optional[Dict] = None
    tier_limits: Optional[Dict] = None
    upgrade_message: Optional[str] = None


class SubscriptionEnforcer:
    """Comprehensive subscription enforcement system."""
    
    def __init__(self, session: Session):
        """
        Initialize subscription enforcer.
        
        Args:
            session: Database session
        """
        self.session = session
        self.subscription_service = SubscriptionService(session)
        self.usage_tracker = UsageTracker(session)
        self.pricing_manager = get_pricing_manager()
    
    def enforce_request(
        self,
        user_id: str,
        *,
        requested_models: int = 1,
        estimated_tokens: int = 0,
        protocol: Optional[str] = None,
        feature: Optional[str] = None,
    ) -> EnforcementResult:
        """
        Enforce subscription limits for a request.
        
        Args:
            user_id: User identifier
            requested_models: Number of models requested
            estimated_tokens: Estimated tokens for this request
            protocol: Protocol being used (for feature gating)
            feature: Specific feature being used (for feature gating)
            
        Returns:
            EnforcementResult with enforcement decision
        """
        # Get user's subscription
        subscription = self.subscription_service.get_user_subscription(user_id)
        if subscription is None:
            tier_name = TierName.FREE.value
        else:
            tier_name = subscription.tier_name.lower()
        
        tier = self.pricing_manager.get_tier(tier_name)
        if tier is None:
            tier = self.pricing_manager.get_tier(TierName.FREE)
            tier_name = TierName.FREE.value
        
        # Get current usage
        current_usage = self.usage_tracker.get_current_period_usage(user_id)
        
        # Check 1: Monthly request limit
        if tier.limits.max_requests_per_month > 0:
            current_requests = current_usage.get("requests_count", 0)
            if current_requests >= tier.limits.max_requests_per_month:
                logger.warning(
                    "Subscription Enforcement: User %s exceeded monthly request limit (%d/%d)",
                    user_id,
                    current_requests,
                    tier.limits.max_requests_per_month,
                )
                return EnforcementResult(
                    allowed=False,
                    reason="Monthly request limit exceeded",
                    tier_name=tier_name,
                    limit_type="requests",
                    current_usage=current_usage,
                    tier_limits={"max_requests_per_month": tier.limits.max_requests_per_month},
                    upgrade_message=f"You've reached your monthly request limit ({tier.limits.max_requests_per_month} requests). Please upgrade to continue.",
                )
        
        # Check 2: Monthly token limit
        if tier.limits.max_tokens_per_month > 0:
            current_tokens = current_usage.get("tokens_count", 0)
            projected_tokens = current_tokens + estimated_tokens
            if projected_tokens >= tier.limits.max_tokens_per_month:
                logger.warning(
                    "Subscription Enforcement: User %s would exceed monthly token limit (%d/%d)",
                    user_id,
                    projected_tokens,
                    tier.limits.max_tokens_per_month,
                )
                return EnforcementResult(
                    allowed=False,
                    reason="Monthly token limit would be exceeded",
                    tier_name=tier_name,
                    limit_type="tokens",
                    current_usage=current_usage,
                    tier_limits={"max_tokens_per_month": tier.limits.max_tokens_per_month},
                    upgrade_message=f"You've reached your monthly token limit ({tier.limits.max_tokens_per_month:,} tokens). Please upgrade to continue.",
                )
        
        # Check 3: Tokens per query limit
        if tier.limits.max_tokens_per_query > 0:
            if estimated_tokens > tier.limits.max_tokens_per_query:
                logger.warning(
                    "Subscription Enforcement: User %s exceeded tokens per query limit (%d > %d)",
                    user_id,
                    estimated_tokens,
                    tier.limits.max_tokens_per_query,
                )
                return EnforcementResult(
                    allowed=False,
                    reason="Query exceeds tokens per query limit",
                    tier_name=tier_name,
                    limit_type="tokens_per_query",
                    current_usage=current_usage,
                    tier_limits={"max_tokens_per_query": tier.limits.max_tokens_per_query},
                    upgrade_message=f"This query exceeds your tier's token limit per query ({tier.limits.max_tokens_per_query:,} tokens). Please upgrade or simplify your query.",
                )
        
        # Check 4: Models per request limit
        if requested_models > tier.limits.max_models_per_request:
            logger.warning(
                "Subscription Enforcement: User %s exceeded models per request limit (%d > %d)",
                user_id,
                requested_models,
                tier.limits.max_models_per_request,
            )
            return EnforcementResult(
                allowed=False,
                reason="Too many models requested",
                tier_name=tier_name,
                limit_type="models",
                current_usage=current_usage,
                tier_limits={"max_models_per_request": tier.limits.max_models_per_request},
                upgrade_message=f"Your tier allows up to {tier.limits.max_models_per_request} model(s) per request. Please upgrade to use more models.",
            )
        
        # Check 5: Feature access (protocol gating)
        if protocol:
            protocol_features = {
                "hrm": "allow_hrm",
                "prompt-diffusion": "allow_prompt_diffusion",
                "deep-conf": "allow_deep_conf",
                "adaptive-ensemble": "allow_adaptive_ensemble",
            }
            
            feature_flag = protocol_features.get(protocol.lower())
            if feature_flag:
                if not getattr(tier.limits, feature_flag, False):
                    logger.warning(
                        "Subscription Enforcement: User %s attempted to use restricted protocol '%s'",
                        user_id,
                        protocol,
                    )
                    return EnforcementResult(
                        allowed=False,
                        reason=f"Protocol '{protocol}' not available for {tier_name} tier",
                        tier_name=tier_name,
                        limit_type="feature",
                        current_usage=current_usage,
                        tier_limits={feature_flag: False},
                        upgrade_message=f"The '{protocol}' protocol is not available for {tier.display_name} tier. Please upgrade to access advanced features.",
                    )
        
        # Check 6: Specific feature access
        if feature:
            if not tier.can_use_feature(feature):
                logger.warning(
                    "Subscription Enforcement: User %s attempted to use restricted feature '%s'",
                    user_id,
                    feature,
                )
                return EnforcementResult(
                    allowed=False,
                    reason=f"Feature '{feature}' not available for {tier_name} tier",
                    tier_name=tier_name,
                    limit_type="feature",
                    current_usage=current_usage,
                    tier_limits={feature: False},
                    upgrade_message=f"The '{feature}' feature is not available for {tier.display_name} tier. Please upgrade to access this feature.",
                )
        
        # All checks passed
        logger.debug(
            "Subscription Enforcement: User %s (tier=%s) request allowed",
            user_id,
            tier_name,
        )
        return EnforcementResult(
            allowed=True,
            tier_name=tier_name,
            current_usage=current_usage,
        )
    
    def check_daily_limit(
        self,
        user_id: str,
    ) -> EnforcementResult:
        """
        Check daily request limit (separate from monthly limit).
        
        Args:
            user_id: User identifier
            
        Returns:
            EnforcementResult with daily limit check
        """
        # Get user's subscription
        subscription = self.subscription_service.get_user_subscription(user_id)
        if subscription is None:
            tier_name = TierName.FREE.value
        else:
            tier_name = subscription.tier_name.lower()
        
        tier = self.pricing_manager.get_tier(tier_name)
        if tier is None:
            tier = self.pricing_manager.get_tier(TierName.FREE)
            tier_name = TierName.FREE.value
        
        # Calculate daily limit (monthly limit / 30, or fixed daily limit)
        # For Free tier: 100/month ≈ 3/day, but we'll use a fixed 5/day for better UX
        daily_limits = {
            TierName.FREE.value: 5,  # 5 requests per day for free tier
            TierName.PRO.value: 500,  # 500 requests per day for pro tier
            TierName.ENTERPRISE.value: 0,  # Unlimited for enterprise
        }
        
        daily_limit = daily_limits.get(tier_name, 5)
        if daily_limit == 0:
            # Unlimited
            return EnforcementResult(allowed=True, tier_name=tier_name)
        
        # Count requests today
        today = dt.date.today()
        today_start = dt.datetime.combine(today, dt.time.min)
        today_end = dt.datetime.combine(today, dt.time.max)
        
        # Get usage records for today
        from sqlalchemy import select
        from ..models import UsageRecord
        
        if subscription:
            stmt = (
                select(UsageRecord)
                .filter(
                    UsageRecord.subscription_id == subscription.id,
                    UsageRecord.period_start >= today_start,
                    UsageRecord.period_start <= today_end,
                )
            )
            today_records = list(self.session.scalars(stmt).all())
            today_requests = sum(record.requests_count for record in today_records)
        else:
            # For users without subscription, we'd need a different tracking mechanism
            # For now, use monthly limit / 30 as approximation
            today_requests = 0
        
        if today_requests >= daily_limit:
            logger.warning(
                "Subscription Enforcement: User %s exceeded daily request limit (%d/%d)",
                user_id,
                today_requests,
                daily_limit,
            )
            return EnforcementResult(
                allowed=False,
                reason="Daily request limit exceeded",
                tier_name=tier_name,
                limit_type="daily_requests",
                current_usage={"daily_requests": today_requests},
                tier_limits={"max_requests_per_day": daily_limit},
                upgrade_message=f"You've reached your daily request limit ({daily_limit} requests). Please upgrade or try again tomorrow.",
            )
        
        return EnforcementResult(allowed=True, tier_name=tier_name)
    
    def get_user_tier(self, user_id: str) -> str:
        """Get user's tier name."""
        subscription = self.subscription_service.get_user_subscription(user_id)
        if subscription is None:
            return TierName.FREE.value
        return subscription.tier_name.lower()
    
    def can_access_feature(self, user_id: str, feature: str) -> bool:
        """Check if user can access a specific feature."""
        return self.subscription_service.can_access_feature(user_id, feature)


def create_enforcement_error(result: EnforcementResult) -> HTTPException:
    """
    Create HTTP exception from enforcement result.
    
    Args:
        result: EnforcementResult
        
    Returns:
        HTTPException with appropriate status code and detail
    """
    # Use HTTP 402 Payment Required for subscription-related errors
    # (though some clients don't support 402, so we'll use 403)
    status_code = status.HTTP_403_FORBIDDEN
    
    detail = {
        "error": "subscription_limit_exceeded",
        "message": result.reason or "Subscription limit exceeded",
        "tier": result.tier_name,
        "limit_type": result.limit_type,
        "upgrade_message": result.upgrade_message,
    }
    
    if result.current_usage:
        detail["current_usage"] = result.current_usage
    
    if result.tier_limits:
        detail["tier_limits"] = result.tier_limits
    
    return HTTPException(status_code=status_code, detail=detail)


# Payment hooks (for future Stripe integration)
class PaymentHooks:
    """Hooks for payment processing integration."""
    
    @staticmethod
    def on_subscription_created(user_id: str, tier_name: str, subscription_id: int) -> None:
        """Called when a subscription is created (hook for payment processing)."""
        logger.info(
            "Payment Hook: Subscription created - user=%s, tier=%s, subscription_id=%d",
            user_id,
            tier_name,
            subscription_id,
        )
        # Future: Integrate with Stripe to create subscription
    
    @staticmethod
    def on_subscription_upgraded(user_id: str, old_tier: str, new_tier: str) -> None:
        """Called when a subscription is upgraded (hook for payment processing)."""
        logger.info(
            "Payment Hook: Subscription upgraded - user=%s, %s -> %s",
            user_id,
            old_tier,
            new_tier,
        )
        # Future: Integrate with Stripe to upgrade subscription
    
    @staticmethod
    def on_subscription_cancelled(user_id: str, tier_name: str) -> None:
        """Called when a subscription is cancelled (hook for payment processing)."""
        logger.info(
            "Payment Hook: Subscription cancelled - user=%s, tier=%s",
            user_id,
            tier_name,
        )
        # Future: Integrate with Stripe to cancel subscription
    
    @staticmethod
    def on_payment_recorded(user_id: str, amount: float, currency: str = "USD") -> None:
        """Called when a payment is recorded (hook for payment processing)."""
        logger.info(
            "Payment Hook: Payment recorded - user=%s, amount=%.2f %s",
            user_id,
            amount,
            currency,
        )
        # Future: Integrate with Stripe to record payment

