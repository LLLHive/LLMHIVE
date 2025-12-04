"""Comprehensive tests for LLMHive billing and monetization system."""
from __future__ import annotations

import sys
from pathlib import Path

# Add src to path for imports
_src_path = Path(__file__).parent.parent / "src"
if str(_src_path) not in sys.path:
    sys.path.insert(0, str(_src_path))

import datetime as dt
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from llmhive.app.billing.pricing import (
    PricingTier,
    TierLimits,
    TierName,
    PricingTierManager,
    get_pricing_manager,
)
from llmhive.app.billing.metering import (
    UsageMeter,
    UsageType,
    UsageEvent,
    UsageQuota,
    MeteringResult,
    OverageCharge,
    CostEstimator,
    MODEL_PRICING,
    OVERAGE_RATES,
    get_usage_meter,
    get_cost_estimator,
)


class TestPricingTierManager:
    """Tests for PricingTierManager class."""
    
    def test_default_tiers(self):
        """Test default tiers are initialized."""
        manager = PricingTierManager()
        
        assert len(manager.tiers) == 3
        assert TierName.FREE in manager.tiers
        assert TierName.PRO in manager.tiers
        assert TierName.ENTERPRISE in manager.tiers
    
    def test_get_tier_by_enum(self):
        """Test getting tier by TierName enum."""
        manager = PricingTierManager()
        
        tier = manager.get_tier(TierName.FREE)
        assert tier is not None
        assert tier.name == TierName.FREE
    
    def test_get_tier_by_string(self):
        """Test getting tier by string name."""
        manager = PricingTierManager()
        
        tier = manager.get_tier("pro")
        assert tier is not None
        assert tier.name == TierName.PRO
    
    def test_get_tier_invalid(self):
        """Test getting invalid tier returns None."""
        manager = PricingTierManager()
        
        tier = manager.get_tier("invalid")
        assert tier is None
    
    def test_list_tiers(self):
        """Test listing all tiers."""
        manager = PricingTierManager()
        
        tiers = manager.list_tiers()
        assert len(tiers) == 3
    
    def test_free_tier_limits(self):
        """Test free tier has correct limits."""
        manager = PricingTierManager()
        tier = manager.get_tier(TierName.FREE)
        
        assert tier.limits.max_requests_per_month == 100
        assert tier.limits.max_tokens_per_month == 100_000
        assert tier.limits.max_models_per_request == 2
        assert tier.limits.enable_advanced_features is False
        assert tier.limits.allow_hrm is False
        assert tier.limits.allow_deep_conf is False
    
    def test_pro_tier_limits(self):
        """Test pro tier has correct limits."""
        manager = PricingTierManager()
        tier = manager.get_tier(TierName.PRO)
        
        assert tier.limits.max_requests_per_month == 10_000
        assert tier.limits.max_tokens_per_month == 10_000_000
        assert tier.limits.max_models_per_request == 5
        assert tier.limits.enable_advanced_features is True
        assert tier.limits.allow_hrm is True
        assert tier.limits.allow_deep_conf is True
        assert tier.limits.allow_prompt_diffusion is True
    
    def test_enterprise_tier_unlimited(self):
        """Test enterprise tier has unlimited limits."""
        manager = PricingTierManager()
        tier = manager.get_tier(TierName.ENTERPRISE)
        
        assert tier.limits.max_requests_per_month == 0  # 0 = unlimited
        assert tier.limits.max_tokens_per_month == 0
        assert tier.limits.max_tokens_per_query == 0
        assert tier.limits.enable_priority_support is True
    
    def test_can_access_feature(self):
        """Test feature access check."""
        manager = PricingTierManager()
        
        # Free tier cannot access HRM
        assert manager.can_access_feature(TierName.FREE, "hrm") is False
        
        # Pro tier can access HRM
        assert manager.can_access_feature(TierName.PRO, "hrm") is True
        
        # Enterprise can access everything
        assert manager.can_access_feature(TierName.ENTERPRISE, "sso") is True
    
    def test_check_limits_within_limits(self):
        """Test check_limits returns True when within limits."""
        manager = PricingTierManager()
        
        result = manager.check_limits(
            TierName.FREE,
            requests_this_month=50,
            tokens_this_month=50_000,
            models_in_request=2,
        )
        
        assert result["within_limits"] is True
        assert result["requests_ok"] is True
        assert result["tokens_ok"] is True
        assert result["models_ok"] is True
    
    def test_check_limits_exceeded(self):
        """Test check_limits returns False when limits exceeded."""
        manager = PricingTierManager()
        
        result = manager.check_limits(
            TierName.FREE,
            requests_this_month=150,  # Over limit
            tokens_this_month=50_000,
        )
        
        assert result["within_limits"] is False
        assert result["requests_ok"] is False
        assert result["tokens_ok"] is True
    
    def test_pricing_amounts(self):
        """Test pricing amounts are correct."""
        manager = PricingTierManager()
        
        free = manager.get_tier(TierName.FREE)
        assert free.monthly_price_usd == 0.0
        
        pro = manager.get_tier(TierName.PRO)
        assert pro.monthly_price_usd == 29.99
        assert pro.annual_price_usd == 299.99
        
        enterprise = manager.get_tier(TierName.ENTERPRISE)
        assert enterprise.monthly_price_usd == 199.99


class TestUsageMeter:
    """Tests for UsageMeter class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.meter = UsageMeter()
    
    def test_record_usage(self):
        """Test recording usage."""
        event = self.meter.record_usage(
            user_id="user123",
            usage_type=UsageType.REQUEST,
            amount=1,
        )
        
        assert event.user_id == "user123"
        assert event.usage_type == UsageType.REQUEST
        assert event.amount == 1
        assert event.cost_usd > 0
    
    def test_record_token_usage(self):
        """Test recording token usage."""
        event = self.meter.record_usage(
            user_id="user123",
            usage_type=UsageType.TOKEN_INPUT,
            amount=1000,
            model="gpt-4o-mini",
        )
        
        assert event.amount == 1000
        assert event.cost_usd > 0
    
    def test_cost_calculation_request(self):
        """Test cost calculation for requests."""
        cost = self.meter._calculate_cost(UsageType.REQUEST, 10)
        
        assert cost == 0.01  # $0.001 per request * 10
    
    def test_cost_calculation_tokens(self):
        """Test cost calculation for tokens."""
        # GPT-4o-mini input pricing
        cost = self.meter._calculate_cost(
            UsageType.TOKEN_INPUT,
            1000,
            model="gpt-4o-mini",
        )
        
        expected = MODEL_PRICING["gpt-4o-mini"]["input"]
        assert cost == pytest.approx(expected, rel=0.01)
    
    def test_check_quota_allowed(self):
        """Test quota check when allowed."""
        result = self.meter.check_quota(
            user_id="user123",
            tier_name="free",
            requested_tokens=1000,
            requested_requests=1,
        )
        
        assert result.allowed is True
        assert result.user_id == "user123"
    
    def test_check_quota_alerts(self):
        """Test quota check generates alerts at high usage."""
        # First, record usage to get close to limit
        for _ in range(95):
            self.meter.record_usage(
                user_id="user_high",
                usage_type=UsageType.REQUEST,
                amount=1,
            )
        
        # Now check quota
        result = self.meter.check_quota(
            user_id="user_high",
            tier_name="free",
            requested_requests=1,
        )
        
        assert len(result.alerts) > 0
        assert result.alerts[0]["level"] == "warning"
    
    def test_calculate_overage(self):
        """Test overage calculation."""
        # Record usage over the limit
        for _ in range(150):  # 150 > 100 limit
            self.meter.record_usage(
                user_id="user_over",
                usage_type=UsageType.REQUEST,
                amount=1,
            )
        
        # For pro tier, overage should be calculated
        charges = self.meter.calculate_overage(
            user_id="user_over",
            tier_name="pro",
            period_start=dt.datetime.utcnow() - dt.timedelta(days=30),
            period_end=dt.datetime.utcnow(),
        )
        
        # Pro tier has overage, but requests don't have overage
        # This tests the structure
        assert isinstance(charges, list)
    
    def test_reset_user_usage(self):
        """Test resetting user usage."""
        # Record some usage
        self.meter.record_usage(
            user_id="user_reset",
            usage_type=UsageType.REQUEST,
            amount=10,
        )
        
        # Verify usage exists
        summary = self.meter.get_usage_summary("user_reset")
        assert summary.get("request", 0) > 0
        
        # Reset
        self.meter.reset_user_usage("user_reset")
        
        # Verify usage is cleared
        summary = self.meter.get_usage_summary("user_reset")
        assert summary.get("request", 0) == 0
    
    def test_get_usage_summary(self):
        """Test getting usage summary."""
        self.meter.record_usage(
            user_id="user_summary",
            usage_type=UsageType.REQUEST,
            amount=5,
        )
        self.meter.record_usage(
            user_id="user_summary",
            usage_type=UsageType.TOKEN_INPUT,
            amount=1000,
        )
        
        summary = self.meter.get_usage_summary("user_summary")
        
        assert "request" in summary
        assert "token_input" in summary
        assert summary["request"] == 5
        assert summary["token_input"] == 1000


class TestCostEstimator:
    """Tests for CostEstimator class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.estimator = CostEstimator()
    
    def test_estimate_query_cost(self):
        """Test query cost estimation."""
        result = self.estimator.estimate_query_cost(
            prompt="What is the capital of France?",
            model="gpt-4o-mini",
            expected_output_tokens=100,
            num_models=1,
        )
        
        assert "input_tokens" in result
        assert "output_tokens" in result
        assert "input_cost" in result
        assert "output_cost" in result
        assert "total_cost" in result
        assert result["total_cost"] > 0
    
    def test_estimate_query_cost_ensemble(self):
        """Test query cost estimation for ensemble."""
        single = self.estimator.estimate_query_cost(
            prompt="Test prompt",
            model="gpt-4o-mini",
            expected_output_tokens=100,
            num_models=1,
        )
        
        ensemble = self.estimator.estimate_query_cost(
            prompt="Test prompt",
            model="gpt-4o-mini",
            expected_output_tokens=100,
            num_models=3,
        )
        
        # Ensemble should cost ~3x more
        assert ensemble["total_cost"] == pytest.approx(single["total_cost"] * 3, rel=0.01)
    
    def test_estimate_monthly_cost_free(self):
        """Test monthly cost estimation for free tier."""
        result = self.estimator.estimate_monthly_cost(
            tier_name="free",
            estimated_requests=50,
            avg_tokens_per_request=500,
        )
        
        assert result["subscription_cost"] == 0.0
        assert result["tier"] == "free"
        assert "total_estimated_cost" in result
    
    def test_estimate_monthly_cost_pro(self):
        """Test monthly cost estimation for pro tier."""
        result = self.estimator.estimate_monthly_cost(
            tier_name="pro",
            estimated_requests=5000,
            avg_tokens_per_request=1000,
        )
        
        assert result["subscription_cost"] == 29.99
        assert "estimated_usage_cost" in result
        assert "total_estimated_cost" in result


class TestModelPricing:
    """Tests for model pricing configuration."""
    
    def test_model_pricing_exists(self):
        """Test that model pricing is configured."""
        assert "gpt-4" in MODEL_PRICING
        assert "gpt-4o-mini" in MODEL_PRICING
        assert "claude-3-sonnet" in MODEL_PRICING
        assert "default" in MODEL_PRICING
    
    def test_model_pricing_structure(self):
        """Test model pricing has correct structure."""
        for model, pricing in MODEL_PRICING.items():
            assert "input" in pricing
            assert "output" in pricing
            assert pricing["input"] > 0
            assert pricing["output"] > 0
    
    def test_gpt4o_mini_cheapest(self):
        """Test GPT-4o-mini is cheaper than GPT-4."""
        assert MODEL_PRICING["gpt-4o-mini"]["input"] < MODEL_PRICING["gpt-4"]["input"]
        assert MODEL_PRICING["gpt-4o-mini"]["output"] < MODEL_PRICING["gpt-4"]["output"]


class TestOverageRates:
    """Tests for overage rate configuration."""
    
    def test_free_tier_no_overage(self):
        """Test free tier has no overage billing."""
        assert OVERAGE_RATES[TierName.FREE.value] == 0.0
    
    def test_pro_tier_overage(self):
        """Test pro tier has overage billing."""
        assert OVERAGE_RATES[TierName.PRO.value] > 0
    
    def test_enterprise_discounted_overage(self):
        """Test enterprise tier has discounted overage."""
        assert OVERAGE_RATES[TierName.ENTERPRISE.value] < OVERAGE_RATES[TierName.PRO.value]


class TestGlobalInstances:
    """Tests for global instance functions."""
    
    def test_get_pricing_manager_singleton(self):
        """Test pricing manager is a singleton."""
        manager1 = get_pricing_manager()
        manager2 = get_pricing_manager()
        
        assert manager1 is manager2
    
    def test_get_usage_meter_singleton(self):
        """Test usage meter is a singleton."""
        meter1 = get_usage_meter()
        meter2 = get_usage_meter()
        
        assert meter1 is meter2
    
    def test_get_cost_estimator_singleton(self):
        """Test cost estimator is a singleton."""
        estimator1 = get_cost_estimator()
        estimator2 = get_cost_estimator()
        
        assert estimator1 is estimator2


class TestTierLimits:
    """Tests for TierLimits dataclass."""
    
    def test_default_limits(self):
        """Test default limits."""
        limits = TierLimits()
        
        assert limits.max_requests_per_month == 0  # Default unlimited
        assert limits.max_models_per_request == 1
        assert limits.enable_advanced_features is False
    
    def test_custom_limits(self):
        """Test custom limits."""
        limits = TierLimits(
            max_requests_per_month=1000,
            max_tokens_per_month=500_000,
            enable_advanced_features=True,
            allow_hrm=True,
        )
        
        assert limits.max_requests_per_month == 1000
        assert limits.max_tokens_per_month == 500_000
        assert limits.enable_advanced_features is True
        assert limits.allow_hrm is True


class TestPricingTier:
    """Tests for PricingTier dataclass."""
    
    def test_has_feature(self):
        """Test has_feature method."""
        tier = PricingTier(
            name=TierName.PRO,
            display_name="Pro",
            monthly_price_usd=29.99,
            annual_price_usd=299.99,
            limits=TierLimits(),
            features={"api_access", "hrm", "web_research"},
        )
        
        assert tier.has_feature("api_access") is True
        assert tier.has_feature("sso") is False
    
    def test_can_use_feature_included(self):
        """Test can_use_feature for included feature."""
        tier = PricingTier(
            name=TierName.PRO,
            display_name="Pro",
            monthly_price_usd=29.99,
            annual_price_usd=299.99,
            limits=TierLimits(enable_advanced_features=True),
            features={"api_access"},
        )
        
        assert tier.can_use_feature("api_access") is True
    
    def test_can_use_feature_advanced(self):
        """Test can_use_feature for advanced feature with advanced flag."""
        tier = PricingTier(
            name=TierName.PRO,
            display_name="Pro",
            monthly_price_usd=29.99,
            annual_price_usd=299.99,
            limits=TierLimits(enable_advanced_features=True),
            features=set(),  # No features, but advanced enabled
        )
        
        # Should access HRM via advanced features flag
        assert tier.can_use_feature("hrm") is True
        assert tier.can_use_feature("deep-conf") is True


class TestUsageQuota:
    """Tests for UsageQuota dataclass."""
    
    def test_quota_not_exceeded(self):
        """Test quota that is not exceeded."""
        quota = UsageQuota(
            limit=100,
            used=50,
            remaining=50,
            percentage_used=50.0,
            is_exceeded=False,
            overage_amount=0,
        )
        
        assert quota.is_exceeded is False
        assert quota.remaining == 50
    
    def test_quota_exceeded(self):
        """Test quota that is exceeded."""
        quota = UsageQuota(
            limit=100,
            used=150,
            remaining=0,
            percentage_used=150.0,
            is_exceeded=True,
            overage_amount=50,
        )
        
        assert quota.is_exceeded is True
        assert quota.overage_amount == 50


class TestMeteringResult:
    """Tests for MeteringResult dataclass."""
    
    def test_allowed_result(self):
        """Test allowed metering result."""
        result = MeteringResult(
            allowed=True,
            user_id="user123",
            usage_type=UsageType.REQUEST,
            quotas={},
            cost_estimate=0.01,
        )
        
        assert result.allowed is True
        assert result.user_id == "user123"
    
    def test_blocked_result(self):
        """Test blocked metering result."""
        result = MeteringResult(
            allowed=False,
            user_id="user123",
            usage_type=UsageType.REQUEST,
            quotas={},
            cost_estimate=0.0,
            message="Limit exceeded",
            alerts=[{"level": "critical", "message": "Over limit"}],
        )
        
        assert result.allowed is False
        assert result.message == "Limit exceeded"
        assert len(result.alerts) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

