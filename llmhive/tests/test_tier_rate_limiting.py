"""Unit tests for tier-aware rate limiting."""
from __future__ import annotations

import sys
from pathlib import Path

# Add src to path for imports
_src_path = Path(__file__).parent.parent / "src"
if str(_src_path) not in sys.path:
    sys.path.insert(0, str(_src_path))

import pytest
import time

from llmhive.app.tier_rate_limiting import TierRateLimiter, get_tier_rate_limiter
from llmhive.app.tier_limits import get_tier_limits, TierLimits, TIER_LIMITS, is_feature_enabled
from llmhive.app.models import User, AccountTier


@pytest.fixture
def rate_limiter() -> TierRateLimiter:
    """Provide a fresh rate limiter instance for each test."""
    return TierRateLimiter()


class TestTierLimitsConfig:
    """Test tier limit configurations."""

    def test_free_tier_limits(self) -> None:
        """Test Free tier limits are configured correctly."""
        limits = get_tier_limits("free")
        assert limits.requests_per_minute == 5
        assert limits.requests_per_day == 100
        assert "basic_orchestration" in limits.enabled_features
        assert "advanced_orchestration" not in limits.enabled_features

    def test_pro_tier_limits(self) -> None:
        """Test Pro tier limits are configured correctly."""
        limits = get_tier_limits("pro")
        assert limits.requests_per_minute == 20
        assert limits.requests_per_day == 1000
        assert "advanced_orchestration" in limits.enabled_features
        assert "deep_verification" in limits.enabled_features

    def test_enterprise_tier_limits(self) -> None:
        """Test Enterprise tier limits are configured correctly."""
        limits = get_tier_limits("enterprise")
        assert limits.requests_per_minute == 60
        assert limits.requests_per_day is None  # Unlimited
        assert "custom_models" in limits.enabled_features
        assert "priority_support" in limits.enabled_features

    def test_unknown_tier_defaults_to_free(self) -> None:
        """Test that unknown tiers default to Free tier limits."""
        limits = get_tier_limits("unknown_tier")
        free_limits = get_tier_limits("free")
        assert limits.requests_per_minute == free_limits.requests_per_minute
        assert limits.requests_per_day == free_limits.requests_per_day

    def test_tier_case_insensitivity(self) -> None:
        """Test that tier names are case-insensitive."""
        assert get_tier_limits("FREE").requests_per_minute == get_tier_limits("free").requests_per_minute
        assert get_tier_limits("Pro").requests_per_minute == get_tier_limits("pro").requests_per_minute
        assert get_tier_limits("ENTERPRISE").requests_per_minute == get_tier_limits("enterprise").requests_per_minute


class TestFreeTierRateLimiting:
    """Test rate limiting for Free tier users."""

    def test_free_tier_allows_requests_within_limit(self, rate_limiter: TierRateLimiter) -> None:
        """Test that Free tier users can make requests within limit."""
        identifier = "test_free_user"
        tier = "free"
        limits = get_tier_limits(tier)
        
        # Make requests up to the limit
        for i in range(limits.requests_per_minute):
            allowed, limit_info = rate_limiter.check_rate_limit(identifier, tier)
            assert allowed, f"Request {i+1} should be allowed (within limit)"

    def test_free_tier_blocks_requests_over_limit(self, rate_limiter: TierRateLimiter) -> None:
        """Test that Free tier users are blocked after exceeding limit."""
        identifier = "test_free_user_block"
        tier = "free"
        limits = get_tier_limits(tier)
        
        # Exhaust the limit
        for i in range(limits.requests_per_minute):
            rate_limiter.check_rate_limit(identifier, tier)
        
        # Next request should be blocked
        allowed, limit_info = rate_limiter.check_rate_limit(identifier, tier)
        assert not allowed, "Request should be blocked (over limit)"
        assert limit_info["remaining"] == 0

    def test_free_tier_rate_limit_info(self, rate_limiter: TierRateLimiter) -> None:
        """Test rate limit info for Free tier."""
        identifier = "test_free_user_info"
        tier = "free"
        
        allowed, limit_info = rate_limiter.check_rate_limit(identifier, tier)
        
        assert allowed
        assert limit_info["tier"] == "free"
        assert limit_info["limit"] == 5
        assert limit_info["daily_limit"] == 100


class TestProTierRateLimiting:
    """Test rate limiting for Pro tier users."""

    def test_pro_tier_higher_limit(self, rate_limiter: TierRateLimiter) -> None:
        """Test that Pro tier has higher rate limit than Free."""
        identifier = "test_pro_user"
        tier = "pro"
        limits = get_tier_limits(tier)
        
        # Pro tier should allow more requests
        for i in range(10):  # More than Free tier limit (5)
            allowed, limit_info = rate_limiter.check_rate_limit(identifier, tier)
            assert allowed, f"Request {i+1} should be allowed for Pro tier"

    def test_pro_tier_rate_limit_info(self, rate_limiter: TierRateLimiter) -> None:
        """Test rate limit info for Pro tier."""
        identifier = "test_pro_user_info"
        tier = "pro"
        
        allowed, limit_info = rate_limiter.check_rate_limit(identifier, tier)
        
        assert allowed
        assert limit_info["tier"] == "pro"
        assert limit_info["limit"] == 20
        assert limit_info["daily_limit"] == 1000


class TestEnterpriseTierRateLimiting:
    """Test rate limiting for Enterprise tier users."""

    def test_enterprise_tier_highest_limit(self, rate_limiter: TierRateLimiter) -> None:
        """Test that Enterprise tier has highest rate limit."""
        identifier = "test_enterprise_user"
        tier = "enterprise"
        
        # Enterprise should allow many requests
        for i in range(50):  # More than Pro tier limit (20)
            allowed, limit_info = rate_limiter.check_rate_limit(identifier, tier)
            assert allowed, f"Request {i+1} should be allowed for Enterprise tier"

    def test_enterprise_tier_unlimited_daily(self, rate_limiter: TierRateLimiter) -> None:
        """Test that Enterprise tier has unlimited daily requests."""
        identifier = "test_enterprise_daily"
        tier = "enterprise"
        
        allowed, limit_info = rate_limiter.check_rate_limit(identifier, tier)
        
        assert allowed
        assert limit_info["daily_limit"] is None  # Unlimited


class TestRateLimiterState:
    """Test rate limiter state management."""

    def test_different_users_have_separate_limits(self, rate_limiter: TierRateLimiter) -> None:
        """Test that different users have independent rate limits."""
        tier = "free"
        limits = get_tier_limits(tier)
        
        # Exhaust limit for user 1
        for _ in range(limits.requests_per_minute):
            rate_limiter.check_rate_limit("user_1", tier)
        
        # User 2 should still be able to make requests
        allowed, _ = rate_limiter.check_rate_limit("user_2", tier)
        assert allowed, "User 2 should have their own limit"

    def test_get_rate_limit_info_without_incrementing(self, rate_limiter: TierRateLimiter) -> None:
        """Test getting rate limit info doesn't increment counter."""
        identifier = "test_info_user"
        tier = "free"
        
        # Get info (should not increment)
        info1 = rate_limiter.get_rate_limit_info(identifier, tier)
        info2 = rate_limiter.get_rate_limit_info(identifier, tier)
        
        # Remaining should be the same
        assert info1["remaining"] == info2["remaining"]

    def test_global_rate_limiter_singleton(self) -> None:
        """Test that get_tier_rate_limiter returns singleton."""
        limiter1 = get_tier_rate_limiter()
        limiter2 = get_tier_rate_limiter()
        
        assert limiter1 is limiter2


class TestFeatureAccess:
    """Test feature access by tier."""

    def test_free_tier_features(self) -> None:
        """Test Free tier has basic features only."""
        assert is_feature_enabled("free", "basic_orchestration")
        assert is_feature_enabled("free", "standard_models")
        assert not is_feature_enabled("free", "advanced_orchestration")
        assert not is_feature_enabled("free", "custom_models")

    def test_pro_tier_features(self) -> None:
        """Test Pro tier has additional features."""
        assert is_feature_enabled("pro", "basic_orchestration")
        assert is_feature_enabled("pro", "advanced_orchestration")
        assert is_feature_enabled("pro", "deep_verification")
        assert not is_feature_enabled("pro", "custom_models")

    def test_enterprise_tier_features(self) -> None:
        """Test Enterprise tier has all features."""
        assert is_feature_enabled("enterprise", "basic_orchestration")
        assert is_feature_enabled("enterprise", "advanced_orchestration")
        assert is_feature_enabled("enterprise", "custom_models")
        assert is_feature_enabled("enterprise", "priority_support")


class TestAccountTierModel:
    """Test AccountTier enum and User model."""

    def test_account_tier_enum_values(self) -> None:
        """Test AccountTier enum has expected values."""
        assert AccountTier.FREE.value == "free"
        assert AccountTier.PRO.value == "pro"
        assert AccountTier.ENTERPRISE.value == "enterprise"

    def test_account_tier_enum_members(self) -> None:
        """Test AccountTier enum has all expected members."""
        members = list(AccountTier)
        assert len(members) == 3
        assert AccountTier.FREE in members
        assert AccountTier.PRO in members
        assert AccountTier.ENTERPRISE in members
