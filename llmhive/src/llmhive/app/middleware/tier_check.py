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
    """Subscription tier names."""
    FREE = "free"
    LITE = "lite"
    PRO = "pro"
    TEAM = "team"
    ENTERPRISE = "enterprise"
    ENTERPRISE_PLUS = "enterprise_plus"
    MAXIMUM = "maximum"


class OrchestrationTier(str, Enum):
    """Orchestration quality tiers."""
    MAXIMUM = "maximum"    # Beats competition by +5%
    ELITE = "elite"        # #1 in ALL 10 categories
    STANDARD = "standard"  # #1 in 8 categories
    BUDGET = "budget"      # #1 in 6 categories


# Tier hierarchy (higher index = more permissions)
TIER_HIERARCHY = [
    TierName.FREE,
    TierName.LITE,
    TierName.PRO,
    TierName.TEAM,
    TierName.ENTERPRISE,
    TierName.ENTERPRISE_PLUS,
    TierName.MAXIMUM,
]


@dataclass
class TierQuota:
    """Quota configuration for a subscription tier."""
    elite_queries: int          # Number of ELITE queries per month
    maximum_queries: int        # Number of MAXIMUM queries per month (Maximum tier only)
    after_quota_tier: str       # "standard", "budget", or "elite"
    total_queries: int          # Total queries per month
    team_members: int           # Number of team members (for Team tier)
    is_pooled: bool             # Whether quota is pooled across team


# Tier quota definitions
TIER_QUOTAS: Dict[TierName, TierQuota] = {
    TierName.FREE: TierQuota(
        elite_queries=50,
        maximum_queries=0,
        after_quota_tier="end",  # Trial ends
        total_queries=50,
        team_members=1,
        is_pooled=False,
    ),
    TierName.LITE: TierQuota(
        elite_queries=100,
        maximum_queries=0,
        after_quota_tier="budget",
        total_queries=500,
        team_members=1,
        is_pooled=False,
    ),
    TierName.PRO: TierQuota(
        elite_queries=400,
        maximum_queries=0,
        after_quota_tier="standard",
        total_queries=1000,
        team_members=1,
        is_pooled=False,
    ),
    TierName.TEAM: TierQuota(
        elite_queries=500,
        maximum_queries=0,
        after_quota_tier="standard",
        total_queries=2000,
        team_members=3,
        is_pooled=True,
    ),
    TierName.ENTERPRISE: TierQuota(
        elite_queries=300,  # Per seat
        maximum_queries=0,
        after_quota_tier="standard",
        total_queries=500,  # Per seat
        team_members=0,  # Unlimited (seat-based)
        is_pooled=False,
    ),
    TierName.ENTERPRISE_PLUS: TierQuota(
        elite_queries=800,  # Per seat
        maximum_queries=0,
        after_quota_tier="standard",
        total_queries=1500,  # Per seat
        team_members=0,  # Unlimited
        is_pooled=False,
    ),
    TierName.MAXIMUM: TierQuota(
        elite_queries=500,
        maximum_queries=200,
        after_quota_tier="elite",  # Falls back to ELITE (still #1 in ALL)
        total_queries=700,
        team_members=10,
        is_pooled=False,
    ),
}


class TierConfig:
    """Configuration for each tier with quota-based limits."""
    
    LIMITS = {
        TierName.FREE: {
            "queries_per_month": 50,
            "tokens_per_request": 25000,
            "max_models": 3,
            "elite_queries": 50,
            "image_generation": False,
            "audio_processing": False,
            "fine_tuning": False,
            "priority_support": False,
            "api_access": False,
            "knowledge_base": False,
            "deep_conf": False,
            "rlhf_feedback": True,
        },
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
            "queries_per_month": 1000,
            "tokens_per_request": 100000,
            "max_models": 5,
            "elite_queries": 400,
            "image_generation": True,
            "audio_processing": True,
            "fine_tuning": False,
            "priority_support": True,
            "api_access": True,
            "knowledge_base": True,
            "deep_conf": True,
            "rlhf_feedback": True,
        },
        TierName.TEAM: {
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
            "elite_queries": 300,  # Per seat
            "image_generation": True,
            "audio_processing": True,
            "fine_tuning": True,
            "priority_support": True,
            "api_access": True,
            "knowledge_base": True,
            "deep_conf": True,
            "rlhf_feedback": True,
        },
        TierName.ENTERPRISE_PLUS: {
            "queries_per_month": -1,
            "tokens_per_request": -1,
            "max_models": 10,
            "elite_queries": 800,  # Per seat
            "image_generation": True,
            "audio_processing": True,
            "fine_tuning": True,
            "priority_support": True,
            "api_access": True,
            "knowledge_base": True,
            "deep_conf": True,
            "rlhf_feedback": True,
        },
        TierName.MAXIMUM: {
            "queries_per_month": 700,
            "tokens_per_request": -1,
            "max_models": 10,
            "elite_queries": 500,
            "maximum_queries": 200,
            "image_generation": True,
            "audio_processing": True,
            "fine_tuning": True,
            "priority_support": True,
            "api_access": True,
            "knowledge_base": True,
            "deep_conf": True,
            "rlhf_feedback": True,
        },
    }
    
    @classmethod
    def get_limit(cls, tier: TierName, feature: str) -> Any:
        """Get limit for a feature at a given tier."""
        return cls.LIMITS.get(tier, cls.LIMITS[TierName.FREE]).get(feature)
    
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
        return TIER_QUOTAS.get(tier, TIER_QUOTAS[TierName.FREE])


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
            Dict with elite_used, standard_used, budget_used, maximum_used
        """
        if not self.subscription_service:
            return {"elite_used": 0, "standard_used": 0, "budget_used": 0, "maximum_used": 0}
        
        try:
            usage = self.subscription_service.get_user_usage(self.user_id)
            return {
                "elite_used": usage.get("elite_queries_used", 0),
                "standard_used": usage.get("standard_queries_used", 0),
                "budget_used": usage.get("budget_queries_used", 0),
                "maximum_used": usage.get("maximum_queries_used", 0),
            }
        except Exception as e:
            logger.error("Failed to get usage for user %s: %s", self.user_id, e)
            return {"elite_used": 0, "standard_used": 0, "budget_used": 0, "maximum_used": 0}
    
    def get_remaining_elite(self) -> int:
        """Get remaining ELITE queries for this period."""
        tier = get_user_tier(self.user_id)
        quota = TierConfig.get_quota(tier)
        usage = self.get_usage()
        return max(0, quota.elite_queries - usage["elite_used"])
    
    def get_remaining_maximum(self) -> int:
        """Get remaining MAXIMUM queries for this period."""
        tier = get_user_tier(self.user_id)
        quota = TierConfig.get_quota(tier)
        usage = self.get_usage()
        return max(0, quota.maximum_queries - usage["maximum_used"])
    
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
        
        return {
            "tier": tier.value,
            "elite": {
                "limit": quota.elite_queries,
                "used": usage["elite_used"],
                "remaining": max(0, quota.elite_queries - usage["elite_used"]),
            },
            "maximum": {
                "limit": quota.maximum_queries,
                "used": usage["maximum_used"],
                "remaining": max(0, quota.maximum_queries - usage["maximum_used"]),
            },
            "after_quota_tier": quota.after_quota_tier,
            "total_queries": quota.total_queries,
            "is_pooled": quota.is_pooled,
        }


def get_user_tier(user_id: str) -> TierName:
    """Get user's subscription tier from Firestore.
    
    Args:
        user_id: User identifier
        
    Returns:
        TierName (defaults to FREE if not found)
    """
    if not is_firestore_available():
        logger.warning("Firestore not available, defaulting to FREE tier")
        return TierName.FREE
    
    try:
        service = FirestoreSubscriptionService()
        subscription = service.get_user_subscription(user_id)
        
        if subscription and subscription.get("status") == "active":
            tier_name = subscription.get("tier_name", "free").lower()
            try:
                return TierName(tier_name)
            except ValueError:
                logger.warning("Unknown tier name: %s, defaulting to FREE", tier_name)
                return TierName.FREE
        
        return TierName.FREE
        
    except Exception as e:
        logger.error("Failed to get user tier: %s", e)
        return TierName.FREE


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
    tracker = QuotaTracker(user_id)
    
    # Maximum tier users: check MAXIMUM quota first
    if tier == TierName.MAXIMUM:
        if tracker.get_remaining_maximum() > 0:
            return "maximum"
        # Fall through to ELITE check
    
    # Check ELITE quota
    if tracker.get_remaining_elite() > 0:
        return "elite"
    
    # ELITE exhausted - use after-quota tier
    after_tier = quota.after_quota_tier
    
    if after_tier == "end":
        # Free trial ended
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "Free trial ended",
                "message": "Your 50 free ELITE queries have been used. Upgrade to continue!",
                "upgrade_url": "/pricing",
            },
        )
    
    return after_tier


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


# Convenience dependencies
RequireLite = TierCheckDependency(TierName.LITE)
RequirePro = TierCheckDependency(TierName.PRO)
RequireTeam = TierCheckDependency(TierName.TEAM)
RequireEnterprise = TierCheckDependency(TierName.ENTERPRISE)
RequireEnterprisePlus = TierCheckDependency(TierName.ENTERPRISE_PLUS)
RequireMaximum = TierCheckDependency(TierName.MAXIMUM)

RequireAPIAccess = FeatureCheckDependency("api_access")
RequireKnowledgeBase = FeatureCheckDependency("knowledge_base")
RequireDeepConf = FeatureCheckDependency("deep_conf")
RequireImageGeneration = FeatureCheckDependency("image_generation")
RequireAudioProcessing = FeatureCheckDependency("audio_processing")
RequireFineTuning = FeatureCheckDependency("fine_tuning")
