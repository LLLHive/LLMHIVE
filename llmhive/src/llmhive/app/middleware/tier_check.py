"""Subscription Tier Check Middleware with Quota Tracking.

Quota-Based Pricing System (Jan 2026):
- ALL tiers get ELITE quality (#1 in ALL 10 categories)
- Quota determines how many ELITE queries before throttling
- When ELITE exhausted → throttle to STANDARD/BUDGET (still great quality)

Usage:
    from ..middleware.tier_check import get_user_tier, get_orchestration_tier, QuotaTracker
    
    # Get user's subscription tier
    tier = get_user_tier(user_id)
    
    # Get appropriate orchestration tier based on quota
    orch_tier = get_orchestration_tier(user_id)  # Returns "elite", "standard", or "budget"
"""
from __future__ import annotations

import logging
from enum import Enum
from functools import wraps
from typing import Any, Callable, Dict, Optional
from dataclasses import dataclass

from fastapi import HTTPException, Request, status

from ..firestore_db import FirestoreSubscriptionService, is_firestore_available

logger = logging.getLogger(__name__)


class TierName(str, Enum):
    """Subscription tier names - Simplified 4-tier structure (January 2026)."""
    LITE = "lite"           # Entry-level: $9.99/mo
    PRO = "pro"             # Power users: $29.99/mo
    ENTERPRISE = "enterprise"  # Organizations: $35/seat/mo (min 5 seats)
    MAXIMUM = "maximum"     # Mission-critical: $499/mo (never throttle)


class OrchestrationTier(str, Enum):
    """Orchestration quality tiers."""
    MAXIMUM = "maximum"    # Beats competition by +5%
    ELITE = "elite"        # #1 in ALL 10 categories
    STANDARD = "standard"  # #1 in 8 categories
    BUDGET = "budget"      # #1 in 6 categories


# Tier hierarchy (higher index = more permissions)
TIER_HIERARCHY = [
    TierName.LITE,
    TierName.PRO,
    TierName.ENTERPRISE,
    TierName.MAXIMUM,
]


@dataclass
class TierQuota:
    """Quota configuration for a subscription tier."""
    elite_queries: int          # Number of ELITE queries per month (0 = unlimited)
    after_quota_tier: str       # "standard", "budget", or "maximum" (for never throttle)
    total_queries: int          # Total queries per month (0 = unlimited)
    team_members: int           # Number of team members included
    never_throttle: bool = False  # Whether this tier never throttles


# Tier quota definitions - SIMPLIFIED 4 TIERS
TIER_QUOTAS: Dict[TierName, TierQuota] = {
    TierName.LITE: TierQuota(
        elite_queries=100,
        after_quota_tier="budget",
        total_queries=500,
        team_members=1,
    ),
    TierName.PRO: TierQuota(
        elite_queries=500,
        after_quota_tier="standard",
        total_queries=2000,
        team_members=1,
    ),
    TierName.ENTERPRISE: TierQuota(
        elite_queries=400,  # Per seat
        after_quota_tier="standard",
        total_queries=800,  # Per seat
        team_members=0,  # Unlimited (seat-based)
    ),
    TierName.MAXIMUM: TierQuota(
        elite_queries=0,  # Unlimited
        after_quota_tier="maximum",  # Never drops
        total_queries=0,  # Unlimited
        team_members=25,  # Team included
        never_throttle=True,
    ),
}


class TierConfig:
    """Configuration for each tier with quota-based limits - SIMPLIFIED 4 TIERS."""
    
    LIMITS = {
        TierName.LITE: {
            "queries_per_month": 500,
            "tokens_per_request": 25000,
            "max_models": 3,
            "elite_queries": 100,
            "image_generation": False,
            "audio_processing": False,
            "fine_tuning": False,
            "priority_support": False,
            "api_access": False,
            "knowledge_base": True,
            "deep_conf": False,
            "rlhf_feedback": True,
        },
        TierName.PRO: {
            "queries_per_month": 2000,
            "tokens_per_request": 100000,
            "max_models": 5,
            "elite_queries": 500,
            "image_generation": True,
            "audio_processing": True,
            "fine_tuning": False,
            "priority_support": True,
            "api_access": True,
            "knowledge_base": True,
            "deep_conf": True,
            "rlhf_feedback": True,
        },
        TierName.ENTERPRISE: {
            "queries_per_month": -1,  # Unlimited (per seat limits)
            "tokens_per_request": -1,  # Unlimited
            "max_models": 10,
            "elite_queries": 400,  # Per seat
            "image_generation": True,
            "audio_processing": True,
            "fine_tuning": True,
            "priority_support": True,
            "api_access": True,
            "knowledge_base": True,
            "deep_conf": True,
            "rlhf_feedback": True,
            "sso": True,
            "audit_logs": True,
            "compliance": True,
        },
        TierName.MAXIMUM: {
            "queries_per_month": -1,  # Unlimited
            "tokens_per_request": -1,  # Unlimited
            "max_models": 10,
            "elite_queries": -1,  # Unlimited (never throttle)
            "image_generation": True,
            "audio_processing": True,
            "fine_tuning": True,
            "priority_support": True,
            "api_access": True,
            "knowledge_base": True,
            "deep_conf": True,
            "rlhf_feedback": True,
            "sso": True,
            "audit_logs": True,
            "compliance": True,
            "never_throttle": True,
        },
    }
    
    @classmethod
    def get_limit(cls, tier: TierName, feature: str) -> Any:
        """Get limit for a feature at a given tier."""
        return cls.LIMITS.get(tier, cls.LIMITS[TierName.LITE]).get(feature)
    
    @classmethod
    def has_feature(cls, tier: TierName, feature: str) -> bool:
        """Check if tier has access to a feature."""
        limit = cls.get_limit(tier, feature)
        if isinstance(limit, bool):
            return limit
        return limit != 0
    
    @classmethod
    def get_quota(cls, tier: TierName) -> TierQuota:
        """Get quota configuration for a tier."""
        return TIER_QUOTAS.get(tier, TIER_QUOTAS[TierName.LITE])


class QuotaTracker:
    """Tracks user quota usage for ELITE/STANDARD/BUDGET queries."""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self._subscription_service = None
    
    @property
    def subscription_service(self):
        if self._subscription_service is None:
            if is_firestore_available():
                self._subscription_service = FirestoreSubscriptionService()
        return self._subscription_service
    
    def get_usage(self) -> Dict[str, int]:
        """Get current usage for this billing period.
        
        Returns:
            Dict with elite_used, standard_used, budget_used
        """
        if not self.subscription_service:
            return {"elite_used": 0, "standard_used": 0, "budget_used": 0}
        
        try:
            usage = self.subscription_service.get_user_usage(self.user_id)
            return {
                "elite_used": usage.get("elite_queries_used", 0),
                "standard_used": usage.get("standard_queries_used", 0),
                "budget_used": usage.get("budget_queries_used", 0),
            }
        except Exception as e:
            logger.error("Failed to get usage for user %s: %s", self.user_id, e)
            return {"elite_used": 0, "standard_used": 0, "budget_used": 0}
    
    def get_remaining_elite(self) -> int:
        """Get remaining ELITE queries for this period.
        
        Returns -1 for unlimited (Maximum tier).
        """
        tier = get_user_tier(self.user_id)
        quota = TierConfig.get_quota(tier)
        
        # Maximum tier has unlimited ELITE
        if quota.never_throttle or quota.elite_queries == 0:
            return -1  # Unlimited
        
        usage = self.get_usage()
        return max(0, quota.elite_queries - usage["elite_used"])
    
    def record_query(self, orchestration_tier: str) -> bool:
        """Record a query at the given orchestration tier.
        
        Args:
            orchestration_tier: "maximum", "elite", "standard", or "budget"
            
        Returns:
            True if recorded successfully
        """
        if not self.subscription_service:
            return False
        
        try:
            return self.subscription_service.record_query_usage(
                self.user_id,
                orchestration_tier=orchestration_tier,
            )
        except Exception as e:
            logger.error("Failed to record query for user %s: %s", self.user_id, e)
            return False
    
    def get_quota_status(self) -> Dict:
        """Get complete quota status for dashboard display.
        
        Returns:
            Dict with quota limits, usage, and remaining
        """
        tier = get_user_tier(self.user_id)
        quota = TierConfig.get_quota(tier)
        usage = self.get_usage()
        
        is_unlimited = quota.never_throttle or quota.elite_queries == 0
        
        return {
            "tier": tier.value,
            "elite": {
                "limit": -1 if is_unlimited else quota.elite_queries,
                "used": usage["elite_used"],
                "remaining": -1 if is_unlimited else max(0, quota.elite_queries - usage["elite_used"]),
            },
            "after_quota_tier": quota.after_quota_tier,
            "total_queries": -1 if is_unlimited else quota.total_queries,
            "never_throttle": quota.never_throttle,
        }


def get_user_tier(user_id: str) -> TierName:
    """Get user's subscription tier from Firestore.
    
    Args:
        user_id: User identifier
        
    Returns:
        TierName (defaults to LITE if not found)
    """
    if not is_firestore_available():
        logger.warning("Firestore not available, defaulting to LITE tier")
        return TierName.LITE
    
    try:
        service = FirestoreSubscriptionService()
        subscription = service.get_user_subscription(user_id)
        
        if subscription and subscription.get("status") == "active":
            tier_name = subscription.get("tier_name", "lite").lower()
            try:
                return TierName(tier_name)
            except ValueError:
                logger.warning("Unknown tier name: %s, defaulting to LITE", tier_name)
                return TierName.LITE
        
        return TierName.LITE
        
    except Exception as e:
        logger.error("Failed to get user tier: %s", e)
        return TierName.LITE


def get_orchestration_tier(user_id: str) -> str:
    """Get the appropriate orchestration tier based on user's quota.
    
    This determines whether to use MAXIMUM, ELITE, STANDARD, or BUDGET orchestration.
    
    Args:
        user_id: User identifier
        
    Returns:
        Orchestration tier: "maximum", "elite", "standard", or "budget"
    """
    tier = get_user_tier(user_id)
    quota = TierConfig.get_quota(tier)
    
    # Maximum tier: NEVER throttle
    if quota.never_throttle or tier == TierName.MAXIMUM:
        return "maximum"
    
    # Check ELITE quota
    tracker = QuotaTracker(user_id)
    remaining = tracker.get_remaining_elite()
    
    if remaining == -1 or remaining > 0:  # -1 = unlimited
        return "elite"
    
    # ELITE exhausted - use after-quota tier
    return quota.after_quota_tier


def tier_has_access(user_tier: TierName, required_tier: TierName) -> bool:
    """Check if user tier has access to required tier features.
    
    Args:
        user_tier: User's current tier
        required_tier: Minimum required tier
        
    Returns:
        True if user has access
    """
    try:
        user_index = TIER_HIERARCHY.index(user_tier)
        required_index = TIER_HIERARCHY.index(required_tier)
        return user_index >= required_index
    except ValueError:
        return False


def require_tier(required_tier: TierName):
    """Decorator to require a minimum subscription tier.
    
    Usage:
        @require_tier(TierName.PRO)
        async def premium_endpoint(request: Request, user_id: str):
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            user_id = kwargs.get("user_id")
            
            if not user_id:
                request = kwargs.get("request")
                if request and hasattr(request, "headers"):
                    user_id = request.headers.get("X-User-ID")
            
            if not user_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User ID required for tier check",
                )
            
            user_tier = get_user_tier(user_id)
            
            if not tier_has_access(user_tier, required_tier):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "error": "Insufficient subscription tier",
                        "current_tier": user_tier.value,
                        "required_tier": required_tier.value,
                        "upgrade_url": "/pricing",
                    },
                )
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


def require_feature(feature: str):
    """Decorator to require a specific feature.
    
    Usage:
        @require_feature("api_access")
        async def api_endpoint(request: Request, user_id: str):
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            user_id = kwargs.get("user_id")
            
            if not user_id:
                request = kwargs.get("request")
                if request and hasattr(request, "headers"):
                    user_id = request.headers.get("X-User-ID")
            
            if not user_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User ID required for feature check",
                )
            
            user_tier = get_user_tier(user_id)
            
            if not TierConfig.has_feature(user_tier, feature):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "error": f"Feature '{feature}' not available in your plan",
                        "current_tier": user_tier.value,
                        "upgrade_url": "/pricing",
                    },
                )
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


class TierCheckDependency:
    """FastAPI dependency for tier checking.
    
    Usage:
        @app.get("/premium")
        async def premium(
            user_id: str,
            tier_check: None = Depends(TierCheckDependency(TierName.PRO)),
        ):
            ...
    """
    
    def __init__(self, required_tier: TierName):
        self.required_tier = required_tier
    
    async def __call__(self, request: Request) -> None:
        user_id = request.headers.get("X-User-ID")
        
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="X-User-ID header required",
            )
        
        user_tier = get_user_tier(user_id)
        
        if not tier_has_access(user_tier, self.required_tier):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "Insufficient subscription tier",
                    "current_tier": user_tier.value,
                    "required_tier": self.required_tier.value,
                    "upgrade_url": "/pricing",
                },
            )


class FeatureCheckDependency:
    """FastAPI dependency for feature checking.
    
    Usage:
        @app.get("/generate-image")
        async def generate_image(
            user_id: str,
            feature_check: None = Depends(FeatureCheckDependency("image_generation")),
        ):
            ...
    """
    
    def __init__(self, feature: str):
        self.feature = feature
    
    async def __call__(self, request: Request) -> None:
        user_id = request.headers.get("X-User-ID")
        
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="X-User-ID header required",
            )
        
        user_tier = get_user_tier(user_id)
        
        if not TierConfig.has_feature(user_tier, self.feature):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": f"Feature '{self.feature}' not available in your plan",
                    "current_tier": user_tier.value,
                    "upgrade_url": "/pricing",
                },
            )


# Convenience dependencies - SIMPLIFIED 4 TIERS
RequireLite = TierCheckDependency(TierName.LITE)
RequirePro = TierCheckDependency(TierName.PRO)
RequireEnterprise = TierCheckDependency(TierName.ENTERPRISE)
RequireMaximum = TierCheckDependency(TierName.MAXIMUM)

RequireAPIAccess = FeatureCheckDependency("api_access")
RequireKnowledgeBase = FeatureCheckDependency("knowledge_base")
RequireDeepConf = FeatureCheckDependency("deep_conf")
RequireImageGeneration = FeatureCheckDependency("image_generation")
RequireAudioProcessing = FeatureCheckDependency("audio_processing")
RequireFineTuning = FeatureCheckDependency("fine_tuning")
RequireSSO = FeatureCheckDependency("sso")
RequireCompliance = FeatureCheckDependency("compliance")
