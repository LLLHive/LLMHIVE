"""Subscription Tier Check Middleware.

Checks user subscription tier before allowing access to premium features.
Uses Firestore for subscription data.

Usage:
    from ..middleware.tier_check import require_tier, TierName
    
    @app.get("/premium-feature")
    @require_tier(TierName.PRO)
    async def premium_feature(user_id: str = Depends(get_current_user)):
        return {"message": "Welcome to premium!"}
"""
from __future__ import annotations

import logging
from enum import Enum
from functools import wraps
from typing import Any, Callable, List, Optional

from fastapi import HTTPException, Request, status

from ..firestore_db import FirestoreSubscriptionService, is_firestore_available

logger = logging.getLogger(__name__)


class TierName(str, Enum):
    """Subscription tier names."""
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


# Tier hierarchy (higher index = more permissions)
TIER_HIERARCHY = [TierName.FREE, TierName.PRO, TierName.ENTERPRISE]


class TierConfig:
    """Configuration for each tier."""
    
    LIMITS = {
        TierName.FREE: {
            "queries_per_month": 100,
            "tokens_per_request": 4000,
            "max_models": 1,
            "image_generation": False,
            "audio_processing": False,
            "fine_tuning": False,
            "priority_support": False,
            "api_access": False,
            "rlhf_feedback": True,  # Everyone can give feedback
        },
        TierName.PRO: {
            "queries_per_month": 5000,
            "tokens_per_request": 16000,
            "max_models": 5,
            "image_generation": True,
            "audio_processing": True,
            "fine_tuning": False,
            "priority_support": True,
            "api_access": True,
            "rlhf_feedback": True,
        },
        TierName.ENTERPRISE: {
            "queries_per_month": -1,  # Unlimited
            "tokens_per_request": 32000,
            "max_models": -1,  # Unlimited
            "image_generation": True,
            "audio_processing": True,
            "fine_tuning": True,
            "priority_support": True,
            "api_access": True,
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
            # Try to get user_id from kwargs or request
            user_id = kwargs.get("user_id")
            
            if not user_id:
                # Try to get from request header
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
                        "upgrade_url": "/api/v1/payments/checkout",
                    },
                )
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


def require_feature(feature: str):
    """Decorator to require a specific feature.
    
    Usage:
        @require_feature("image_generation")
        async def generate_image(request: Request, user_id: str):
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
                        "upgrade_url": "/api/v1/payments/checkout",
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
                    "upgrade_url": "/api/v1/payments/checkout",
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
                    "upgrade_url": "/api/v1/payments/checkout",
                },
            )


# Convenience dependencies
RequirePro = TierCheckDependency(TierName.PRO)
RequireEnterprise = TierCheckDependency(TierName.ENTERPRISE)
RequireImageGeneration = FeatureCheckDependency("image_generation")
RequireAudioProcessing = FeatureCheckDependency("audio_processing")
RequireFineTuning = FeatureCheckDependency("fine_tuning")

