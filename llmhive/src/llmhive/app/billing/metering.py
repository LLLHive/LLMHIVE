"""Usage Metering and Overage Billing for LLMHive.

Enterprise Metering: Provides comprehensive usage metering including:
- Real-time usage tracking
- Overage detection and billing
- Usage alerts and notifications
- Cost calculation per request
- Model-specific pricing
"""
from __future__ import annotations

import datetime as dt
from datetime import timezone
import logging
import threading
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from .pricing import TierName, get_pricing_manager

logger = logging.getLogger(__name__)


# ==============================================================================
# Enums and Types
# ==============================================================================

class UsageType(str, Enum):
    """Type of usage being metered."""
    REQUEST = "request"
    TOKEN_INPUT = "token_input"
    TOKEN_OUTPUT = "token_output"
    STORAGE = "storage"
    COMPUTE_TIME = "compute_time"


class AlertLevel(str, Enum):
    """Alert severity level."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


# ==============================================================================
# Data Classes
# ==============================================================================

@dataclass(slots=True)
class UsageEvent:
    """A single usage event."""
    user_id: str
    usage_type: UsageType
    amount: int
    model: Optional[str] = None
    timestamp: dt.datetime = field(default_factory=lambda: dt.datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)
    cost_usd: float = 0.0


@dataclass(slots=True)
class UsageQuota:
    """Usage quota for a user/tier."""
    limit: int
    used: int
    remaining: int
    percentage_used: float
    is_exceeded: bool
    overage_amount: int


@dataclass(slots=True)
class MeteringResult:
    """Result of metering check."""
    allowed: bool
    user_id: str
    usage_type: UsageType
    quotas: Dict[str, UsageQuota]
    cost_estimate: float
    message: Optional[str] = None
    alerts: List[Dict] = field(default_factory=list)


@dataclass(slots=True)
class OverageCharge:
    """Overage billing charge."""
    user_id: str
    usage_type: UsageType
    overage_amount: int
    rate_per_unit: float
    total_charge: float
    period_start: dt.datetime
    period_end: dt.datetime


# ==============================================================================
# Model Pricing Configuration
# ==============================================================================

# Cost per 1K tokens for different models
MODEL_PRICING = {
    # OpenAI models
    "gpt-4": {"input": 0.03, "output": 0.06},
    "gpt-4-turbo": {"input": 0.01, "output": 0.03},
    "gpt-4o": {"input": 0.005, "output": 0.015},
    "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
    "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
    # Anthropic models
    "claude-3-opus": {"input": 0.015, "output": 0.075},
    "claude-3-sonnet": {"input": 0.003, "output": 0.015},
    "claude-3-haiku": {"input": 0.00025, "output": 0.00125},
    "claude-3-5-sonnet": {"input": 0.003, "output": 0.015},
    # Default pricing
    "default": {"input": 0.002, "output": 0.006},
}

# Overage rates per tier (price per 1K tokens above limit) - SIMPLIFIED 4 TIERS
OVERAGE_RATES = {
    TierName.LITE.value: 0.0,  # No overage for Lite (throttle instead)
    TierName.PRO.value: 0.01,  # $0.01 per 1K tokens
    TierName.ENTERPRISE.value: 0.005,  # $0.005 per 1K tokens (discounted)
    TierName.MAXIMUM.value: 0.0,  # No overage (unlimited)
    "lite": 0.0,
    "pro": 0.01,
    "enterprise": 0.005,
    "maximum": 0.0,
}


# ==============================================================================
# Usage Meter
# ==============================================================================

class UsageMeter:
    """Real-time usage metering with overage tracking.
    
    Enterprise Metering: Tracks usage in real-time and calculates costs.
    """
    
    def __init__(self):
        self._lock = threading.RLock()
        # In-memory usage tracking (for real-time checks)
        # In production, this would be backed by Redis or similar
        self._usage_cache: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self._last_reset: Dict[str, dt.datetime] = {}
        self._alert_callbacks: List[Callable[[str, AlertLevel, str], None]] = []
        
        self.pricing_manager = get_pricing_manager()
    
    def record_usage(
        self,
        user_id: str,
        usage_type: UsageType,
        amount: int,
        *,
        model: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> UsageEvent:
        """
        Record a usage event.
        
        Args:
            user_id: User identifier
            usage_type: Type of usage
            amount: Amount used
            model: Model used (for token pricing)
            metadata: Additional metadata
            
        Returns:
            UsageEvent with cost calculation
        """
        # Calculate cost
        cost = self._calculate_cost(usage_type, amount, model)
        
        event = UsageEvent(
            user_id=user_id,
            usage_type=usage_type,
            amount=amount,
            model=model,
            cost_usd=cost,
            metadata=metadata or {},
        )
        
        # Update in-memory cache
        with self._lock:
            self._usage_cache[user_id][usage_type.value] += amount
        
        logger.debug(
            "Enterprise Metering: Recorded usage - user=%s, type=%s, amount=%d, cost=$%.4f",
            user_id,
            usage_type.value,
            amount,
            cost,
        )
        
        return event
    
    def _calculate_cost(
        self,
        usage_type: UsageType,
        amount: int,
        model: Optional[str] = None,
    ) -> float:
        """Calculate cost for usage."""
        if usage_type == UsageType.REQUEST:
            # Fixed cost per request
            return amount * 0.001  # $0.001 per request
        
        if usage_type in (UsageType.TOKEN_INPUT, UsageType.TOKEN_OUTPUT):
            # Token-based pricing
            pricing = MODEL_PRICING.get(model or "default", MODEL_PRICING["default"])
            rate_key = "input" if usage_type == UsageType.TOKEN_INPUT else "output"
            rate = pricing[rate_key]
            return (amount / 1000.0) * rate
        
        if usage_type == UsageType.STORAGE:
            # Storage pricing: $0.10 per GB-month
            return (amount / 1024.0) * 0.10
        
        if usage_type == UsageType.COMPUTE_TIME:
            # Compute pricing: $0.001 per second
            return amount * 0.001
        
        return 0.0
    
    def check_quota(
        self,
        user_id: str,
        tier_name: str,
        *,
        requested_tokens: int = 0,
        requested_requests: int = 1,
    ) -> MeteringResult:
        """
        Check if user is within quota.
        
        Args:
            user_id: User identifier
            tier_name: User's tier
            requested_tokens: Tokens to be used
            requested_requests: Requests to be made
            
        Returns:
            MeteringResult with quota status
        """
        tier = self.pricing_manager.get_tier(tier_name)
        if tier is None:
            tier = self.pricing_manager.get_tier(TierName.LITE)
            tier_name = TierName.LITE.value
        
        # Get current usage from cache
        with self._lock:
            current_tokens = self._usage_cache[user_id].get("token_input", 0) + \
                           self._usage_cache[user_id].get("token_output", 0)
            current_requests = self._usage_cache[user_id].get("request", 0)
        
        quotas = {}
        alerts = []
        allowed = True
        
        # Check token quota
        if tier.limits.max_tokens_per_month > 0:
            projected_tokens = current_tokens + requested_tokens
            token_quota = UsageQuota(
                limit=tier.limits.max_tokens_per_month,
                used=current_tokens,
                remaining=max(0, tier.limits.max_tokens_per_month - current_tokens),
                percentage_used=(current_tokens / tier.limits.max_tokens_per_month) * 100,
                is_exceeded=projected_tokens > tier.limits.max_tokens_per_month,
                overage_amount=max(0, projected_tokens - tier.limits.max_tokens_per_month),
            )
            quotas["tokens"] = token_quota
            
            if token_quota.percentage_used >= 90:
                alerts.append({
                    "level": AlertLevel.WARNING.value,
                    "message": f"Token usage at {token_quota.percentage_used:.1f}% of limit",
                })
            
            if tier_name == TierName.LITE.value and token_quota.is_exceeded:
                allowed = False  # Lite tier throttles when exceeded
        
        # Check request quota
        if tier.limits.max_requests_per_month > 0:
            projected_requests = current_requests + requested_requests
            request_quota = UsageQuota(
                limit=tier.limits.max_requests_per_month,
                used=current_requests,
                remaining=max(0, tier.limits.max_requests_per_month - current_requests),
                percentage_used=(current_requests / tier.limits.max_requests_per_month) * 100,
                is_exceeded=projected_requests > tier.limits.max_requests_per_month,
                overage_amount=max(0, projected_requests - tier.limits.max_requests_per_month),
            )
            quotas["requests"] = request_quota
            
            if request_quota.percentage_used >= 90:
                alerts.append({
                    "level": AlertLevel.WARNING.value,
                    "message": f"Request usage at {request_quota.percentage_used:.1f}% of limit",
                })
            
            if tier_name == TierName.LITE.value and request_quota.is_exceeded:
                allowed = False  # Lite tier throttles when exceeded
        
        # Calculate cost estimate
        cost_estimate = self._calculate_cost(UsageType.TOKEN_INPUT, requested_tokens // 2)
        cost_estimate += self._calculate_cost(UsageType.TOKEN_OUTPUT, requested_tokens // 2)
        cost_estimate += self._calculate_cost(UsageType.REQUEST, requested_requests)
        
        # Generate message
        message = None
        if not allowed:
            message = "Usage limit exceeded for your tier. Please upgrade to continue."
        elif alerts:
            message = "You are approaching your usage limits."
        
        return MeteringResult(
            allowed=allowed,
            user_id=user_id,
            usage_type=UsageType.REQUEST,
            quotas=quotas,
            cost_estimate=cost_estimate,
            message=message,
            alerts=alerts,
        )
    
    def calculate_overage(
        self,
        user_id: str,
        tier_name: str,
        period_start: dt.datetime,
        period_end: dt.datetime,
    ) -> List[OverageCharge]:
        """
        Calculate overage charges for a billing period.
        
        Args:
            user_id: User identifier
            tier_name: User's tier
            period_start: Billing period start
            period_end: Billing period end
            
        Returns:
            List of overage charges
        """
        tier = self.pricing_manager.get_tier(tier_name)
        if tier is None:
            return []
        
        charges = []
        overage_rate = OVERAGE_RATES.get(tier_name.lower(), 0.0)
        
        if overage_rate == 0.0:
            return []  # No overage billing for this tier
        
        with self._lock:
            token_usage = self._usage_cache[user_id].get("token_input", 0) + \
                         self._usage_cache[user_id].get("token_output", 0)
        
        if tier.limits.max_tokens_per_month > 0:
            overage = max(0, token_usage - tier.limits.max_tokens_per_month)
            if overage > 0:
                charge = OverageCharge(
                    user_id=user_id,
                    usage_type=UsageType.TOKEN_INPUT,
                    overage_amount=overage,
                    rate_per_unit=overage_rate,
                    total_charge=(overage / 1000.0) * overage_rate,
                    period_start=period_start,
                    period_end=period_end,
                )
                charges.append(charge)
                
                logger.info(
                    "Enterprise Metering: Overage charge for user %s: %d tokens @ $%.4f/1K = $%.2f",
                    user_id,
                    overage,
                    overage_rate,
                    charge.total_charge,
                )
        
        return charges
    
    def reset_user_usage(self, user_id: str) -> None:
        """Reset usage for a user (called at period start)."""
        with self._lock:
            self._usage_cache[user_id].clear()
            self._last_reset[user_id] = dt.datetime.now(dt.timezone.utc)
        
        logger.info("Enterprise Metering: Reset usage for user %s", user_id)
    
    def get_usage_summary(self, user_id: str) -> Dict[str, int]:
        """Get current usage summary for a user."""
        with self._lock:
            return dict(self._usage_cache.get(user_id, {}))
    
    def register_alert_callback(
        self,
        callback: Callable[[str, AlertLevel, str], None],
    ) -> None:
        """Register a callback for usage alerts."""
        self._alert_callbacks.append(callback)
    
    def _trigger_alerts(
        self,
        user_id: str,
        level: AlertLevel,
        message: str,
    ) -> None:
        """Trigger alert callbacks."""
        for callback in self._alert_callbacks:
            try:
                callback(user_id, level, message)
            except Exception as exc:
                logger.error("Enterprise Metering: Alert callback failed: %s", exc)


# ==============================================================================
# Cost Estimator
# ==============================================================================

class CostEstimator:
    """Estimate costs for queries before execution.
    
    Enterprise Metering: Provides cost estimates for budgeting.
    """
    
    def __init__(self):
        self.pricing_manager = get_pricing_manager()
    
    def estimate_query_cost(
        self,
        prompt: str,
        *,
        model: str = "gpt-4o-mini",
        expected_output_tokens: int = 500,
        num_models: int = 1,
    ) -> Dict[str, float]:
        """
        Estimate cost for a query.
        
        Args:
            prompt: Input prompt
            model: Model to use
            expected_output_tokens: Expected output tokens
            num_models: Number of models (for ensemble)
            
        Returns:
            Cost breakdown dict
        """
        # Estimate input tokens (rough: 4 chars per token)
        input_tokens = len(prompt) // 4
        
        # Get model pricing
        pricing = MODEL_PRICING.get(model, MODEL_PRICING["default"])
        
        # Calculate costs
        input_cost = (input_tokens / 1000.0) * pricing["input"]
        output_cost = (expected_output_tokens / 1000.0) * pricing["output"]
        
        # Multiply by number of models
        total_cost = (input_cost + output_cost) * num_models
        
        return {
            "input_tokens": input_tokens,
            "output_tokens": expected_output_tokens,
            "input_cost": round(input_cost, 6),
            "output_cost": round(output_cost, 6),
            "total_cost": round(total_cost, 6),
            "model": model,
            "num_models": num_models,
        }
    
    def estimate_monthly_cost(
        self,
        tier_name: str,
        estimated_requests: int,
        avg_tokens_per_request: int = 1000,
        model: str = "gpt-4o-mini",
    ) -> Dict[str, float]:
        """
        Estimate monthly cost for a user.
        
        Args:
            tier_name: Pricing tier
            estimated_requests: Expected requests per month
            avg_tokens_per_request: Average tokens per request
            model: Primary model to use
            
        Returns:
            Monthly cost estimate
        """
        tier = self.pricing_manager.get_tier(tier_name)
        if tier is None:
            return {"error": "Invalid tier"}
        
        # Base subscription cost
        subscription_cost = tier.monthly_price_usd
        
        # Usage cost
        total_tokens = estimated_requests * avg_tokens_per_request
        pricing = MODEL_PRICING.get(model, MODEL_PRICING["default"])
        
        # Assume 50/50 input/output split
        token_cost = (total_tokens / 1000.0) * ((pricing["input"] + pricing["output"]) / 2)
        
        # Overage cost (if applicable)
        overage_cost = 0.0
        if tier.limits.max_tokens_per_month > 0:
            overage_tokens = max(0, total_tokens - tier.limits.max_tokens_per_month)
            overage_rate = OVERAGE_RATES.get(tier_name.lower(), 0.0)
            overage_cost = (overage_tokens / 1000.0) * overage_rate
        
        return {
            "tier": tier_name,
            "subscription_cost": subscription_cost,
            "estimated_usage_cost": round(token_cost, 2),
            "estimated_overage_cost": round(overage_cost, 2),
            "total_estimated_cost": round(subscription_cost + token_cost + overage_cost, 2),
            "estimated_requests": estimated_requests,
            "estimated_tokens": total_tokens,
        }


# ==============================================================================
# Global Instances
# ==============================================================================

_usage_meter: Optional[UsageMeter] = None
_cost_estimator: Optional[CostEstimator] = None


def get_usage_meter() -> UsageMeter:
    """Get the global usage meter instance."""
    global _usage_meter
    if _usage_meter is None:
        _usage_meter = UsageMeter()
    return _usage_meter


def get_cost_estimator() -> CostEstimator:
    """Get the global cost estimator instance."""
    global _cost_estimator
    if _cost_estimator is None:
        _cost_estimator = CostEstimator()
    return _cost_estimator

