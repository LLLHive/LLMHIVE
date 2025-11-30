"""Billing and subscription management for LLMHive.

Enterprise Monetization: Complete billing system including:
- Tiered pricing (Free, Pro, Enterprise)
- Subscription management
- Usage tracking and metering
- Rate limiting
- Stripe payment integration
- Admin controls
"""
from __future__ import annotations

from .enforcement import PaymentHooks, SubscriptionEnforcer, create_enforcement_error
from .pricing import PricingTier, PricingTierManager, TierLimits, TierName, get_pricing_manager
from .rate_limiting import RateLimiter, get_rate_limiter, rate_limit_middleware
from .subscription import SubscriptionService
from .usage import BillingCalculator, UsageTracker
from .metering import (
    UsageMeter,
    UsageType,
    UsageEvent,
    UsageQuota,
    MeteringResult,
    OverageCharge,
    CostEstimator,
    get_usage_meter,
    get_cost_estimator,
    MODEL_PRICING,
    OVERAGE_RATES,
)

__all__ = [
    # Enforcement
    "PaymentHooks",
    "SubscriptionEnforcer",
    "create_enforcement_error",
    # Pricing
    "PricingTier",
    "PricingTierManager",
    "TierLimits",
    "TierName",
    "get_pricing_manager",
    # Rate Limiting
    "RateLimiter",
    "get_rate_limiter",
    "rate_limit_middleware",
    # Subscription
    "SubscriptionService",
    # Usage
    "BillingCalculator",
    "UsageTracker",
    # Metering
    "UsageMeter",
    "UsageType",
    "UsageEvent",
    "UsageQuota",
    "MeteringResult",
    "OverageCharge",
    "CostEstimator",
    "get_usage_meter",
    "get_cost_estimator",
    "MODEL_PRICING",
    "OVERAGE_RATES",
]
