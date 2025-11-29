"""Billing API endpoints for subscriptions and payments."""
from __future__ import annotations

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..billing.pricing import TierName
from ..billing.subscription import SubscriptionService
from ..billing.payments import get_payment_processor, STRIPE_AVAILABLE
from ..billing.usage import UsageTracker, BillingCalculator
from ..database import get_db
from ..models import Subscription, SubscriptionStatus

logger = logging.getLogger(__name__)

router = APIRouter()


# Request/Response Models
class CreateSubscriptionRequest(BaseModel):
    """Request to create a subscription."""

    tier_name: str = Field(..., description="Pricing tier name (free, pro, enterprise)")
    billing_cycle: str = Field(default="monthly", description="Billing cycle: 'monthly' or 'annual'")
    stripe_customer_id: str | None = Field(default=None, description="Stripe customer ID (if available)")
    stripe_subscription_id: str | None = Field(default=None, description="Stripe subscription ID (if available)")


class UpdateSubscriptionRequest(BaseModel):
    """Request to update a subscription."""

    tier_name: str | None = Field(default=None, description="New tier name")
    billing_cycle: str | None = Field(default=None, description="New billing cycle")
    status: str | None = Field(default=None, description="New status")


class CancelSubscriptionRequest(BaseModel):
    """Request to cancel a subscription."""

    cancel_immediately: bool = Field(default=False, description="Cancel immediately or at period end")


class SubscriptionResponse(BaseModel):
    """Subscription response model."""

    id: int
    user_id: str
    tier_name: str
    status: str
    billing_cycle: str
    current_period_start: datetime
    current_period_end: datetime
    cancel_at_period_end: bool
    cancelled_at: datetime | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_orm(cls, subscription: Subscription) -> SubscriptionResponse:
        """Create response from ORM model."""
        return cls(
            id=subscription.id,
            user_id=subscription.user_id,
            tier_name=subscription.tier_name,
            status=subscription.status.value,
            billing_cycle=subscription.billing_cycle,
            current_period_start=subscription.current_period_start,
            current_period_end=subscription.current_period_end,
            cancel_at_period_end=subscription.cancel_at_period_end,
            cancelled_at=subscription.cancelled_at,
            created_at=subscription.created_at,
            updated_at=subscription.updated_at,
        )


@router.post("/subscriptions", response_model=SubscriptionResponse, status_code=status.HTTP_201_CREATED)
def create_subscription(
    user_id: str,
    request: CreateSubscriptionRequest,
    db: Session = Depends(get_db),
) -> SubscriptionResponse:
    """Create a new subscription for a user.
    
    Subscription tiers: Creates subscription and logs tier change for audit.

    Final path: /api/v1/billing/subscriptions?user_id={user_id}
    """
    try:
        service = SubscriptionService(db)
        subscription = service.create_subscription(
            user_id=user_id,
            tier_name=request.tier_name,
            billing_cycle=request.billing_cycle,
            stripe_customer_id=request.stripe_customer_id,
            stripe_subscription_id=request.stripe_subscription_id,
        )
        db.commit()
        
        # Subscription tiers: Log subscription change for audit
        logger.info(
            "Subscription tiers: Created subscription for user %s: tier=%s, cycle=%s",
            user_id,
            request.tier_name,
            request.billing_cycle
        )
        
        return SubscriptionResponse.from_orm(subscription)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Failed to create subscription: %s", exc)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create subscription",
        ) from exc


@router.get("/subscriptions/{subscription_id}", response_model=SubscriptionResponse)
def get_subscription(
    subscription_id: int,
    db: Session = Depends(get_db),
) -> SubscriptionResponse:
    """Get a subscription by ID.

    Final path: /api/v1/billing/subscriptions/{subscription_id}
    """
    service = SubscriptionService(db)
    subscription = service.get_subscription(subscription_id)
    if subscription is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Subscription {subscription_id} not found",
        )
    return SubscriptionResponse.from_orm(subscription)


@router.get("/subscriptions/user/{user_id}", response_model=SubscriptionResponse | None)
def get_user_subscription(
    user_id: str,
    db: Session = Depends(get_db),
) -> SubscriptionResponse | None:
    """Get the active subscription for a user.

    Final path: /api/v1/billing/subscriptions/user/{user_id}
    """
    service = SubscriptionService(db)
    subscription = service.get_user_subscription(user_id)
    if subscription is None:
        return None
    return SubscriptionResponse.from_orm(subscription)


@router.get("/subscription", response_model=dict)
def get_subscription_info(
    user_id: str,
    db: Session = Depends(get_db),
) -> dict:
    """Get current subscription info for a user (for frontend).
    
    Subscription tiers: Returns tier info with feature flags and limits.
    
    Final path: /api/v1/billing/subscription?user_id={user_id}
    """
    try:
        service = SubscriptionService(db)
        subscription = service.get_user_subscription(user_id)
        pricing_manager = service.pricing_manager
        
        if subscription is None:
            # No subscription = free tier
            tier = pricing_manager.get_tier("free")
            return {
                "user_id": user_id,
                "tier": "free",
                "status": "active",
                "is_active": True,
                "features": list(tier.features) if tier else [],
                "limits": {
                    "max_requests_per_month": tier.limits.max_requests_per_month if tier else 100,
                    "max_tokens_per_month": tier.limits.max_tokens_per_month if tier else 100_000,
                    "max_models_per_request": tier.limits.max_models_per_request if tier else 2,
                    "allow_parallel_retrieval": tier.limits.allow_parallel_retrieval if tier else False,
                    "allow_deep_conf": tier.limits.allow_deep_conf if tier else False,
                    "allow_prompt_diffusion": tier.limits.allow_prompt_diffusion if tier else False,
                    "allow_adaptive_ensemble": tier.limits.allow_adaptive_ensemble if tier else False,
                    "allow_hrm": tier.limits.allow_hrm if tier else False,
                    "allow_loopback_refinement": tier.limits.allow_loopback_refinement if tier else False,
                } if tier else {},
            }
        
        tier = pricing_manager.get_tier(subscription.tier_name)
        return {
            "user_id": user_id,
            "tier": subscription.tier_name,
            "status": subscription.status.value,
            "is_active": subscription.is_active(),
            "billing_cycle": subscription.billing_cycle,
            "current_period_start": subscription.current_period_start,
            "current_period_end": subscription.current_period_end,
            "features": list(tier.features) if tier else [],
            "limits": {
                "max_requests_per_month": tier.limits.max_requests_per_month if tier else 0,
                "max_tokens_per_month": tier.limits.max_tokens_per_month if tier else 0,
                "max_models_per_request": tier.limits.max_models_per_request if tier else 1,
                "allow_parallel_retrieval": tier.limits.allow_parallel_retrieval if tier else False,
                "allow_deep_conf": tier.limits.allow_deep_conf if tier else False,
                "allow_prompt_diffusion": tier.limits.allow_prompt_diffusion if tier else False,
                "allow_adaptive_ensemble": tier.limits.allow_adaptive_ensemble if tier else False,
                "allow_hrm": tier.limits.allow_hrm if tier else False,
                "allow_loopback_refinement": tier.limits.allow_loopback_refinement if tier else False,
            } if tier else {},
        }
    except Exception as exc:
        logger.exception("Failed to get subscription info: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get subscription info",
        ) from exc


@router.patch("/subscriptions/{subscription_id}", response_model=SubscriptionResponse)
def update_subscription(
    subscription_id: int,
    request: UpdateSubscriptionRequest,
    db: Session = Depends(get_db),
) -> SubscriptionResponse:
    """Update a subscription.

    Final path: /api/v1/billing/subscriptions/{subscription_id}
    """
    try:
        service = SubscriptionService(db)
        subscription = service.get_subscription(subscription_id)
        if subscription is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Subscription {subscription_id} not found",
            )

        # Update tier if provided
        if request.tier_name:
            current_tier = service.pricing_manager.get_tier(subscription.tier_name)
            new_tier = service.pricing_manager.get_tier(request.tier_name)
            if current_tier and new_tier:
                if new_tier.monthly_price_usd > current_tier.monthly_price_usd:
                    subscription = service.upgrade_subscription(subscription_id, request.tier_name)
                elif new_tier.monthly_price_usd < current_tier.monthly_price_usd:
                    subscription = service.downgrade_subscription(subscription_id, request.tier_name)
                else:
                    # Same price, just update tier name
                    subscription.tier_name = request.tier_name

        # Update billing cycle if provided
        if request.billing_cycle:
            subscription.billing_cycle = request.billing_cycle

        # Update status if provided
        if request.status:
            try:
                new_status = SubscriptionStatus(request.status.lower())
                subscription = service.update_subscription_status(subscription_id, new_status)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid status: {request.status}",
                ) from None

        db.commit()
        return SubscriptionResponse.from_orm(subscription)
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Failed to update subscription: %s", exc)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update subscription",
        ) from exc


@router.post("/subscriptions/{subscription_id}/cancel", response_model=SubscriptionResponse)
def cancel_subscription(
    subscription_id: int,
    request: CancelSubscriptionRequest,
    db: Session = Depends(get_db),
) -> SubscriptionResponse:
    """Cancel a subscription.

    Final path: /api/v1/billing/subscriptions/{subscription_id}/cancel
    """
    try:
        service = SubscriptionService(db)
        subscription = service.cancel_subscription(
            subscription_id,
            cancel_immediately=request.cancel_immediately,
        )
        db.commit()
        return SubscriptionResponse.from_orm(subscription)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Failed to cancel subscription: %s", exc)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cancel subscription",
        ) from exc


@router.post("/subscriptions/{subscription_id}/upgrade", response_model=SubscriptionResponse)
def upgrade_subscription(
    subscription_id: int,
    new_tier_name: str,
    db: Session = Depends(get_db),
) -> SubscriptionResponse:
    """Upgrade a subscription to a higher tier.
    
    Subscription tiers: Upgrades subscription and logs tier change for audit.

    Final path: /api/v1/billing/subscriptions/{subscription_id}/upgrade?new_tier_name={tier}
    """
    try:
        service = SubscriptionService(db)
        old_tier = service.get_subscription(subscription_id)
        old_tier_name = old_tier.tier_name if old_tier else "unknown"
        
        subscription = service.upgrade_subscription(subscription_id, new_tier_name)
        db.commit()
        
        # Subscription tiers: Log tier change for audit
        logger.info(
            "Subscription tiers: Upgraded subscription %d: %s -> %s (user: %s)",
            subscription_id,
            old_tier_name,
            new_tier_name,
            subscription.user_id
        )
        
        return SubscriptionResponse.from_orm(subscription)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Failed to upgrade subscription: %s", exc)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upgrade subscription",
        ) from exc


@router.post("/subscriptions/{subscription_id}/downgrade", response_model=SubscriptionResponse)
def downgrade_subscription(
    subscription_id: int,
    new_tier_name: str,
    db: Session = Depends(get_db),
) -> SubscriptionResponse:
    """Downgrade a subscription to a lower tier.
    
    Subscription tiers: Downgrades subscription and logs tier change for audit.

    Final path: /api/v1/billing/subscriptions/{subscription_id}/downgrade?new_tier_name={tier}
    """
    try:
        service = SubscriptionService(db)
        old_tier = service.get_subscription(subscription_id)
        old_tier_name = old_tier.tier_name if old_tier else "unknown"
        
        subscription = service.downgrade_subscription(subscription_id, new_tier_name)
        db.commit()
        
        # Subscription tiers: Log tier change for audit
        logger.info(
            "Subscription tiers: Downgraded subscription %d: %s -> %s (user: %s)",
            subscription_id,
            old_tier_name,
            new_tier_name,
            subscription.user_id
        )
        
        return SubscriptionResponse.from_orm(subscription)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Failed to downgrade subscription: %s", exc)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to downgrade subscription",
        ) from exc


@router.get("/tiers", status_code=status.HTTP_200_OK)
def list_pricing_tiers():
    """List all available pricing tiers.

    Final path: /api/v1/billing/tiers
    """
    from ..billing.pricing import get_pricing_manager

    pricing_manager = get_pricing_manager()
    tiers = pricing_manager.list_tiers()

    return {
        "tiers": [
            {
                "name": tier.name.value,
                "display_name": tier.display_name,
                "monthly_price_usd": tier.monthly_price_usd,
                "annual_price_usd": tier.annual_price_usd,
                "description": tier.description,
                "features": list(tier.features),
                "limits": {
                    "max_requests_per_month": tier.limits.max_requests_per_month,
                    "max_tokens_per_month": tier.limits.max_tokens_per_month,
                    "max_models_per_request": tier.limits.max_models_per_request,
                    "max_concurrent_requests": tier.limits.max_concurrent_requests,
                    "max_storage_mb": tier.limits.max_storage_mb,
                    "enable_advanced_features": tier.limits.enable_advanced_features,
                    "enable_api_access": tier.limits.enable_api_access,
                    "enable_priority_support": tier.limits.enable_priority_support,
                    "max_team_members": tier.limits.max_team_members,
                },
            }
            for tier in tiers
        ]
    }


@router.post("/webhooks/stripe", status_code=status.HTTP_200_OK)
async def stripe_webhook(
    request: Request,
    db: Session = Depends(get_db),
) -> dict:
    """Handle Stripe webhook events.

    Final path: /api/v1/billing/webhooks/stripe

    This endpoint should be configured in Stripe dashboard to receive webhook events.
    """
    if not STRIPE_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Stripe integration not available",
        )

    processor = get_payment_processor()
    if processor is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Payment processor not configured",
        )

    # Get webhook signature from headers
    signature = request.headers.get("stripe-signature")
    if not signature:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing stripe-signature header",
        )

    # Get raw payload
    payload = await request.body()

    try:
        result = processor.handle_webhook(
            payload=payload,
            signature=signature,
            db_session=db,
        )
        db.commit()
        return result
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Failed to process Stripe webhook: %s", exc)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process webhook",
        ) from exc


@router.get("/usage/{user_id}", status_code=status.HTTP_200_OK)
def get_usage_summary(
    user_id: str,
    db: Session = Depends(get_db),
) -> dict:
    """Get usage summary for a user.

    Final path: /api/v1/billing/usage/{user_id}
    """
    try:
        tracker = UsageTracker(db)
        summary = tracker.get_current_period_usage(user_id)
        return summary
    except Exception as exc:
        logger.exception("Failed to get usage summary: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get usage summary",
        ) from exc


@router.get("/usage/{user_id}/history", status_code=status.HTTP_200_OK)
def get_usage_history(
    user_id: str,
    limit: int = 10,
    db: Session = Depends(get_db),
) -> dict:
    """Get usage history for a user.

    Final path: /api/v1/billing/usage/{user_id}/history?limit={limit}
    """
    try:
        tracker = UsageTracker(db)
        history = tracker.get_usage_history(user_id, limit=limit)
        return {"user_id": user_id, "history": history}
    except Exception as exc:
        logger.exception("Failed to get usage history: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get usage history",
        ) from exc


@router.get("/usage/{user_id}/limits", status_code=status.HTTP_200_OK)
def check_usage_limits(
    user_id: str,
    requested_tokens: int = 0,
    requested_models: int = 1,
    db: Session = Depends(get_db),
) -> dict:
    """Check if user's requested usage is within their tier limits.

    Final path: /api/v1/billing/usage/{user_id}/limits?requested_tokens={tokens}&requested_models={models}
    """
    try:
        tracker = UsageTracker(db)
        limits_check = tracker.check_usage_limits(
            user_id,
            requested_tokens=requested_tokens,
            requested_models=requested_models,
        )
        return limits_check
    except Exception as exc:
        logger.exception("Failed to check usage limits: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check usage limits",
        ) from exc


@router.get("/billing/estimate", status_code=status.HTTP_200_OK)
def estimate_cost(
    tier_name: str,
    estimated_tokens_per_month: int,
    estimated_requests_per_month: int,
    db: Session = Depends(get_db),
) -> dict:
    """Estimate monthly cost for a tier and expected usage.

    Final path: /api/v1/billing/billing/estimate?tier_name={tier}&estimated_tokens_per_month={tokens}&estimated_requests_per_month={requests}
    """
    try:
        calculator = BillingCalculator(db)
        estimate = calculator.estimate_cost(
            tier_name,
            estimated_tokens_per_month,
            estimated_requests_per_month,
        )
        return estimate
    except Exception as exc:
        logger.exception("Failed to estimate cost: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to estimate cost",
        ) from exc

