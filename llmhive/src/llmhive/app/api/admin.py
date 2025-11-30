"""Admin API endpoints for subscription and tier management.

Enterprise Admin: Provides administrative endpoints for:
- Tier configuration and pricing updates
- User subscription management
- Usage analytics and reporting
- System-wide billing configuration
"""
from __future__ import annotations

import datetime as dt
import logging
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from ..config import settings
from ..database import get_db
from ..billing.pricing import (
    PricingTier,
    TierLimits,
    TierName,
    get_pricing_manager,
)
from ..billing.subscription import SubscriptionService
from ..billing.usage import UsageTracker, BillingCalculator
from ..billing.enforcement import SubscriptionEnforcer
from ..models import Subscription, SubscriptionStatus, UsageRecord

logger = logging.getLogger(__name__)

router = APIRouter()


# ==============================================================================
# Request/Response Models
# ==============================================================================

class TierConfigUpdate(BaseModel):
    """Request to update tier configuration."""
    
    max_requests_per_month: Optional[int] = None
    max_tokens_per_month: Optional[int] = None
    max_models_per_request: Optional[int] = None
    max_concurrent_requests: Optional[int] = None
    max_storage_mb: Optional[int] = None
    max_tokens_per_query: Optional[int] = None
    enable_advanced_features: Optional[bool] = None
    enable_api_access: Optional[bool] = None
    enable_priority_support: Optional[bool] = None
    max_team_members: Optional[int] = None
    allow_parallel_retrieval: Optional[bool] = None
    allow_deep_conf: Optional[bool] = None
    allow_prompt_diffusion: Optional[bool] = None
    allow_adaptive_ensemble: Optional[bool] = None
    allow_hrm: Optional[bool] = None
    allow_loopback_refinement: Optional[bool] = None
    monthly_price_usd: Optional[float] = None
    annual_price_usd: Optional[float] = None


class CreateCustomTierRequest(BaseModel):
    """Request to create a custom tier."""
    
    name: str = Field(..., description="Unique tier name (lowercase)")
    display_name: str = Field(..., description="Display name for UI")
    description: str = Field(default="", description="Tier description")
    monthly_price_usd: float = Field(..., ge=0, description="Monthly price in USD")
    annual_price_usd: float = Field(..., ge=0, description="Annual price in USD")
    limits: TierConfigUpdate = Field(default_factory=TierConfigUpdate)
    features: List[str] = Field(default_factory=list, description="List of feature keys")


class UsageStatsResponse(BaseModel):
    """Usage statistics response."""
    
    total_users: int
    active_subscriptions: int
    subscriptions_by_tier: Dict[str, int]
    total_requests_today: int
    total_tokens_today: int
    total_revenue_mtd: float


class UserOverrideRequest(BaseModel):
    """Request to override user limits."""
    
    user_id: str
    override_type: str = Field(..., description="Type: 'limit' or 'feature'")
    key: str = Field(..., description="Limit or feature key")
    value: int | bool | str = Field(..., description="Override value")
    expires_at: Optional[dt.datetime] = None


# ==============================================================================
# Admin Tier Management
# ==============================================================================

@router.get("/tiers", status_code=status.HTTP_200_OK)
def admin_list_tiers() -> dict:
    """Enterprise Admin: List all pricing tiers with full configuration.
    
    Final path: /api/v1/admin/tiers
    """
    pricing_manager = get_pricing_manager()
    tiers = pricing_manager.list_tiers()
    
    return {
        "tiers": [
            {
                "name": tier.name.value if hasattr(tier.name, "value") else tier.name,
                "display_name": tier.display_name,
                "description": tier.description,
                "monthly_price_usd": tier.monthly_price_usd,
                "annual_price_usd": tier.annual_price_usd,
                "features": list(tier.features),
                "limits": {
                    "max_requests_per_month": tier.limits.max_requests_per_month,
                    "max_tokens_per_month": tier.limits.max_tokens_per_month,
                    "max_models_per_request": tier.limits.max_models_per_request,
                    "max_concurrent_requests": tier.limits.max_concurrent_requests,
                    "max_storage_mb": tier.limits.max_storage_mb,
                    "max_tokens_per_query": tier.limits.max_tokens_per_query,
                    "enable_advanced_features": tier.limits.enable_advanced_features,
                    "enable_api_access": tier.limits.enable_api_access,
                    "enable_priority_support": tier.limits.enable_priority_support,
                    "max_team_members": tier.limits.max_team_members,
                    "allow_parallel_retrieval": tier.limits.allow_parallel_retrieval,
                    "allow_deep_conf": tier.limits.allow_deep_conf,
                    "allow_prompt_diffusion": tier.limits.allow_prompt_diffusion,
                    "allow_adaptive_ensemble": tier.limits.allow_adaptive_ensemble,
                    "allow_hrm": tier.limits.allow_hrm,
                    "allow_loopback_refinement": tier.limits.allow_loopback_refinement,
                },
            }
            for tier in tiers
        ]
    }


@router.patch("/tiers/{tier_name}", status_code=status.HTTP_200_OK)
def admin_update_tier(
    tier_name: str,
    update: TierConfigUpdate,
) -> dict:
    """Enterprise Admin: Update tier configuration.
    
    Note: Changes are in-memory only. For persistent changes, update the pricing.py file
    or store in database.
    
    Final path: /api/v1/admin/tiers/{tier_name}
    """
    pricing_manager = get_pricing_manager()
    tier = pricing_manager.get_tier(tier_name)
    
    if tier is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tier '{tier_name}' not found",
        )
    
    # Update limits
    update_dict = update.model_dump(exclude_none=True)
    
    for key, value in update_dict.items():
        if hasattr(tier.limits, key):
            setattr(tier.limits, key, value)
        elif key == "monthly_price_usd":
            tier.monthly_price_usd = value
        elif key == "annual_price_usd":
            tier.annual_price_usd = value
    
    logger.info("Enterprise Admin: Updated tier %s: %s", tier_name, update_dict)
    
    return {
        "message": f"Tier '{tier_name}' updated successfully",
        "updated_fields": list(update_dict.keys()),
    }


# ==============================================================================
# Admin Usage Statistics
# ==============================================================================

@router.get("/stats", status_code=status.HTTP_200_OK)
def admin_get_stats(
    db: Session = Depends(get_db),
) -> UsageStatsResponse:
    """Enterprise Admin: Get system-wide usage statistics.
    
    Final path: /api/v1/admin/stats
    """
    try:
        # Count total subscriptions
        total_subs = db.query(func.count(Subscription.id)).scalar() or 0
        
        # Count active subscriptions
        active_subs = (
            db.query(func.count(Subscription.id))
            .filter(Subscription.status == SubscriptionStatus.ACTIVE)
            .scalar() or 0
        )
        
        # Count by tier
        tier_counts = (
            db.query(Subscription.tier_name, func.count(Subscription.id))
            .filter(Subscription.status == SubscriptionStatus.ACTIVE)
            .group_by(Subscription.tier_name)
            .all()
        )
        subscriptions_by_tier = {tier: count for tier, count in tier_counts}
        
        # Today's usage
        today = dt.date.today()
        today_start = dt.datetime.combine(today, dt.time.min)
        
        today_usage = (
            db.query(
                func.sum(UsageRecord.requests_count),
                func.sum(UsageRecord.tokens_count),
            )
            .filter(UsageRecord.period_start >= today_start)
            .first()
        )
        
        total_requests_today = today_usage[0] or 0
        total_tokens_today = today_usage[1] or 0
        
        # Month-to-date revenue (simplified - based on active subscriptions)
        pricing_manager = get_pricing_manager()
        mtd_revenue = 0.0
        for tier_name, count in subscriptions_by_tier.items():
            tier = pricing_manager.get_tier(tier_name)
            if tier:
                mtd_revenue += tier.monthly_price_usd * count
        
        return UsageStatsResponse(
            total_users=total_subs,
            active_subscriptions=active_subs,
            subscriptions_by_tier=subscriptions_by_tier,
            total_requests_today=total_requests_today,
            total_tokens_today=total_tokens_today,
            total_revenue_mtd=round(mtd_revenue, 2),
        )
        
    except Exception as exc:
        logger.exception("Enterprise Admin: Failed to get stats: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve statistics",
        ) from exc


@router.get("/usage/top-users", status_code=status.HTTP_200_OK)
def admin_get_top_users(
    limit: int = 10,
    metric: str = "requests",
    db: Session = Depends(get_db),
) -> dict:
    """Enterprise Admin: Get top users by usage.
    
    Final path: /api/v1/admin/usage/top-users?limit=10&metric=requests
    
    Args:
        limit: Number of users to return
        metric: "requests" or "tokens"
    """
    try:
        if metric == "tokens":
            order_by = UsageRecord.tokens_count
        else:
            order_by = UsageRecord.requests_count
        
        # Get current month's top users
        first_of_month = dt.date.today().replace(day=1)
        month_start = dt.datetime.combine(first_of_month, dt.time.min)
        
        top_users = (
            db.query(
                UsageRecord.user_id,
                func.sum(UsageRecord.requests_count).label("total_requests"),
                func.sum(UsageRecord.tokens_count).label("total_tokens"),
                func.sum(UsageRecord.cost_usd).label("total_cost"),
            )
            .filter(UsageRecord.period_start >= month_start)
            .group_by(UsageRecord.user_id)
            .order_by(func.sum(order_by).desc())
            .limit(limit)
            .all()
        )
        
        return {
            "metric": metric,
            "period": f"{first_of_month.isoformat()} to present",
            "top_users": [
                {
                    "user_id": user[0],
                    "total_requests": user[1],
                    "total_tokens": user[2],
                    "total_cost": round(user[3], 2) if user[3] else 0.0,
                }
                for user in top_users
            ],
        }
        
    except Exception as exc:
        logger.exception("Enterprise Admin: Failed to get top users: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve top users",
        ) from exc


# ==============================================================================
# Admin User Management
# ==============================================================================

@router.get("/users/{user_id}", status_code=status.HTTP_200_OK)
def admin_get_user_details(
    user_id: str,
    db: Session = Depends(get_db),
) -> dict:
    """Enterprise Admin: Get detailed user information including subscription and usage.
    
    Final path: /api/v1/admin/users/{user_id}
    """
    try:
        service = SubscriptionService(db)
        tracker = UsageTracker(db)
        enforcer = SubscriptionEnforcer(db)
        
        subscription = service.get_user_subscription(user_id)
        usage = tracker.get_current_period_usage(user_id)
        tier_name = enforcer.get_user_tier(user_id)
        
        pricing_manager = get_pricing_manager()
        tier = pricing_manager.get_tier(tier_name)
        
        return {
            "user_id": user_id,
            "tier": tier_name,
            "subscription": {
                "id": subscription.id if subscription else None,
                "status": subscription.status.value if subscription else "none",
                "billing_cycle": subscription.billing_cycle if subscription else None,
                "current_period_start": subscription.current_period_start if subscription else None,
                "current_period_end": subscription.current_period_end if subscription else None,
                "cancel_at_period_end": subscription.cancel_at_period_end if subscription else False,
            } if subscription else None,
            "usage": usage,
            "limits": {
                "max_requests_per_month": tier.limits.max_requests_per_month if tier else 100,
                "max_tokens_per_month": tier.limits.max_tokens_per_month if tier else 100_000,
                "remaining_requests": max(0, (tier.limits.max_requests_per_month if tier else 100) - usage.get("requests_count", 0)),
                "remaining_tokens": max(0, (tier.limits.max_tokens_per_month if tier else 100_000) - usage.get("tokens_count", 0)),
            },
        }
        
    except Exception as exc:
        logger.exception("Enterprise Admin: Failed to get user details: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user details",
        ) from exc


@router.post("/users/{user_id}/grant-tier", status_code=status.HTTP_200_OK)
def admin_grant_tier(
    user_id: str,
    tier_name: str,
    billing_cycle: str = "monthly",
    days: int = 30,
    db: Session = Depends(get_db),
) -> dict:
    """Enterprise Admin: Grant a tier to a user (for promotional or testing purposes).
    
    Final path: /api/v1/admin/users/{user_id}/grant-tier?tier_name={tier}&billing_cycle={cycle}&days={days}
    """
    try:
        service = SubscriptionService(db)
        pricing_manager = get_pricing_manager()
        
        tier = pricing_manager.get_tier(tier_name)
        if tier is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid tier: {tier_name}",
            )
        
        # Check for existing subscription
        existing = service.get_user_subscription(user_id)
        if existing and existing.is_active():
            # Cancel existing subscription
            service.cancel_subscription(existing.id, cancel_immediately=True)
        
        # Create new subscription
        subscription = service.create_subscription(
            user_id=user_id,
            tier_name=tier_name,
            billing_cycle=billing_cycle,
        )
        
        # Set custom period end
        now = dt.datetime.utcnow()
        subscription.current_period_end = now + dt.timedelta(days=days)
        
        db.commit()
        
        logger.info(
            "Enterprise Admin: Granted tier %s to user %s for %d days",
            tier_name,
            user_id,
            days,
        )
        
        return {
            "message": f"Granted {tier_name} tier to user {user_id} for {days} days",
            "subscription_id": subscription.id,
            "expires_at": subscription.current_period_end.isoformat(),
        }
        
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Enterprise Admin: Failed to grant tier: %s", exc)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to grant tier",
        ) from exc


@router.post("/users/{user_id}/reset-usage", status_code=status.HTTP_200_OK)
def admin_reset_usage(
    user_id: str,
    db: Session = Depends(get_db),
) -> dict:
    """Enterprise Admin: Reset user's usage counters.
    
    Final path: /api/v1/admin/users/{user_id}/reset-usage
    """
    try:
        service = SubscriptionService(db)
        subscription = service.get_user_subscription(user_id)
        
        if subscription:
            # Delete usage records for current period
            db.query(UsageRecord).filter(
                UsageRecord.subscription_id == subscription.id,
                UsageRecord.period_start >= subscription.current_period_start,
            ).delete()
            db.commit()
            
            logger.info("Enterprise Admin: Reset usage for user %s", user_id)
            
            return {"message": f"Usage reset for user {user_id}"}
        else:
            return {"message": f"No subscription found for user {user_id}"}
        
    except Exception as exc:
        logger.exception("Enterprise Admin: Failed to reset usage: %s", exc)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reset usage",
        ) from exc


# ==============================================================================
# Admin Subscription Management
# ==============================================================================

@router.get("/subscriptions", status_code=status.HTTP_200_OK)
def admin_list_subscriptions(
    tier: Optional[str] = None,
    status_filter: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
) -> dict:
    """Enterprise Admin: List subscriptions with filters.
    
    Final path: /api/v1/admin/subscriptions?tier={tier}&status={status}&limit=50&offset=0
    """
    try:
        query = db.query(Subscription).order_by(Subscription.created_at.desc())
        
        if tier:
            query = query.filter(Subscription.tier_name == tier.lower())
        
        if status_filter:
            try:
                sub_status = SubscriptionStatus(status_filter.lower())
                query = query.filter(Subscription.status == sub_status)
            except ValueError:
                pass
        
        total = query.count()
        subscriptions = query.offset(offset).limit(limit).all()
        
        return {
            "total": total,
            "offset": offset,
            "limit": limit,
            "subscriptions": [
                {
                    "id": sub.id,
                    "user_id": sub.user_id,
                    "tier_name": sub.tier_name,
                    "status": sub.status.value,
                    "billing_cycle": sub.billing_cycle,
                    "current_period_start": sub.current_period_start.isoformat() if sub.current_period_start else None,
                    "current_period_end": sub.current_period_end.isoformat() if sub.current_period_end else None,
                    "created_at": sub.created_at.isoformat() if sub.created_at else None,
                }
                for sub in subscriptions
            ],
        }
        
    except Exception as exc:
        logger.exception("Enterprise Admin: Failed to list subscriptions: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list subscriptions",
        ) from exc


@router.post("/subscriptions/{subscription_id}/extend", status_code=status.HTTP_200_OK)
def admin_extend_subscription(
    subscription_id: int,
    days: int = 30,
    db: Session = Depends(get_db),
) -> dict:
    """Enterprise Admin: Extend a subscription's period.
    
    Final path: /api/v1/admin/subscriptions/{subscription_id}/extend?days=30
    """
    try:
        service = SubscriptionService(db)
        subscription = service.get_subscription(subscription_id)
        
        if subscription is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Subscription {subscription_id} not found",
            )
        
        old_end = subscription.current_period_end
        new_end = old_end + dt.timedelta(days=days)
        subscription.current_period_end = new_end
        
        if subscription.status != SubscriptionStatus.ACTIVE:
            subscription.status = SubscriptionStatus.ACTIVE
        
        db.commit()
        
        logger.info(
            "Enterprise Admin: Extended subscription %d by %d days (new end: %s)",
            subscription_id,
            days,
            new_end.isoformat(),
        )
        
        return {
            "message": f"Extended subscription {subscription_id} by {days} days",
            "old_period_end": old_end.isoformat(),
            "new_period_end": new_end.isoformat(),
        }
        
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Enterprise Admin: Failed to extend subscription: %s", exc)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to extend subscription",
        ) from exc


# ==============================================================================
# Admin Configuration
# ==============================================================================

@router.get("/config", status_code=status.HTTP_200_OK)
def admin_get_config() -> dict:
    """Enterprise Admin: Get billing system configuration.
    
    Final path: /api/v1/admin/config
    """
    return {
        "stripe_available": bool(settings.stripe_api_key),
        "stripe_webhook_configured": bool(settings.stripe_webhook_secret),
        "rate_limits": {
            "free": 5,
            "pro": 20,
            "enterprise": 100,
        },
        "default_billing_cycle": "monthly",
        "trial_days": 14,
        "grace_period_days": 7,
    }


@router.get("/audit-log", status_code=status.HTTP_200_OK)
def admin_get_audit_log(
    user_id: Optional[str] = None,
    action: Optional[str] = None,
    limit: int = 100,
    db: Session = Depends(get_db),
) -> dict:
    """Enterprise Admin: Get audit log for billing actions.
    
    Note: This is a placeholder. In production, implement actual audit logging.
    
    Final path: /api/v1/admin/audit-log?user_id={user_id}&action={action}&limit=100
    """
    # Placeholder - in production, this would query an audit log table
    return {
        "message": "Audit log endpoint placeholder",
        "note": "Implement audit logging table for production",
        "filters": {
            "user_id": user_id,
            "action": action,
            "limit": limit,
        },
        "entries": [],
    }

