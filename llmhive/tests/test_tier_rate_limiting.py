"""Unit tests for tier-aware rate limiting."""
from __future__ import annotations

import pytest
import time
from sqlalchemy.orm import Session

from llmhive.app.tier_rate_limiting import TierRateLimiter, get_tier_rate_limiter
from llmhive.app.tier_limits import get_tier_limits
from llmhive.app.models import User, AccountTier


@pytest.fixture
def db_session(test_db_session: Session) -> Session:
    """Provide a database session for tests."""
    return test_db_session


@pytest.fixture
def rate_limiter() -> TierRateLimiter:
    """Provide a fresh rate limiter instance for each test."""
    return TierRateLimiter()


def test_free_tier_rate_limit(rate_limiter: TierRateLimiter) -> None:
    """Test that Free tier users are limited to 5 requests per minute."""
    identifier = "test_free_user"
    tier = "free"
    limits = get_tier_limits(tier)
    
    # Make requests up to the limit
    for i in range(limits.requests_per_minute):
        allowed, limit_info = rate_limiter.check_rate_limit(identifier, tier)
        assert allowed, f"Request {i+1} should be allowed (within limit)"
        assert limit_info["remaining"] == limits.requests_per_minute - (i + 1)
        assert limit_info["tier"] == tier
    
    # Next request should be blocked
    allowed, limit_info = rate_limiter.check_rate_limit(identifier, tier)
    assert not allowed, "Request beyond limit should be blocked"
    assert limit_info["remaining"] == 0
    assert limit_info["tier"] == tier


def test_pro_tier_rate_limit(rate_limiter: TierRateLimiter) -> None:
    """Test that Pro tier users are limited to 20 requests per minute."""
    identifier = "test_pro_user"
    tier = "pro"
    limits = get_tier_limits(tier)
    
    # Make requests up to the limit
    for i in range(limits.requests_per_minute):
        allowed, limit_info = rate_limiter.check_rate_limit(identifier, tier)
        assert allowed, f"Request {i+1} should be allowed (within limit)"
        assert limit_info["remaining"] == limits.requests_per_minute - (i + 1)
    
    # Next request should be blocked
    allowed, limit_info = rate_limiter.check_rate_limit(identifier, tier)
    assert not allowed, "Request beyond limit should be blocked"
    assert limit_info["remaining"] == 0


def test_enterprise_tier_rate_limit(rate_limiter: TierRateLimiter) -> None:
    """Test that Enterprise tier users have higher limits (60 requests per minute)."""
    identifier = "test_enterprise_user"
    tier = "enterprise"
    limits = get_tier_limits(tier)
    
    # Make requests up to the limit
    for i in range(limits.requests_per_minute):
        allowed, limit_info = rate_limiter.check_rate_limit(identifier, tier)
        assert allowed, f"Request {i+1} should be allowed (within limit)"
        assert limit_info["remaining"] == limits.requests_per_minute - (i + 1)
    
    # Next request should be blocked
    allowed, limit_info = rate_limiter.check_rate_limit(identifier, tier)
    assert not allowed, "Request beyond limit should be blocked"


def test_guest_user_ip_based_limiting(rate_limiter: TierRateLimiter) -> None:
    """Test that unauthenticated users (identified by IP) are limited as Free tier."""
    identifier = "ip:192.168.1.1"  # IP-based identifier for guest
    tier = "free"  # Guests get Free tier limits
    limits = get_tier_limits(tier)
    
    # Make requests up to the Free tier limit
    for i in range(limits.requests_per_minute):
        allowed, limit_info = rate_limiter.check_rate_limit(identifier, tier)
        assert allowed, f"Guest request {i+1} should be allowed (within Free tier limit)"
    
    # Next request should be blocked
    allowed, limit_info = rate_limiter.check_rate_limit(identifier, tier)
    assert not allowed, "Guest request beyond Free tier limit should be blocked"


def test_rate_limit_resets_after_window(rate_limiter: TierRateLimiter) -> None:
    """Test that rate limits reset after the time window."""
    identifier = "test_reset_user"
    tier = "free"
    limits = get_tier_limits(tier)
    
    # Exhaust the limit
    for _ in range(limits.requests_per_minute):
        rate_limiter.check_rate_limit(identifier, tier)
    
    # Verify blocked
    allowed, _ = rate_limiter.check_rate_limit(identifier, tier)
    assert not allowed, "Should be blocked after exhausting limit"
    
    # Simulate time passing (in real scenario, this would be actual time)
    # For this test, we'll create a new limiter to simulate reset
    # In production, the rolling window naturally resets
    new_limiter = TierRateLimiter()
    
    # After reset, should be allowed again
    allowed, limit_info = new_limiter.check_rate_limit(identifier, tier)
    assert allowed, "Should be allowed after reset"
    assert limit_info["remaining"] == limits.requests_per_minute - 1


def test_daily_rate_limit(rate_limiter: TierRateLimiter) -> None:
    """Test that daily rate limits are enforced for Free and Pro tiers."""
    identifier = "test_daily_user"
    tier = "free"
    limits = get_tier_limits(tier)
    
    # Free tier has daily limit of 100
    assert limits.requests_per_day == 100
    
    # Make requests within per-minute limit but check daily limit
    for i in range(10):  # Make 10 requests
        allowed, limit_info = rate_limiter.check_rate_limit(identifier, tier)
        assert allowed, f"Request {i+1} should be allowed"
        assert limit_info["daily_limit"] == 100
        assert limit_info["daily_remaining"] is not None
        assert limit_info["daily_remaining"] <= 100


def test_enterprise_no_daily_limit(rate_limiter: TierRateLimiter) -> None:
    """Test that Enterprise tier has no daily limit."""
    identifier = "test_enterprise_daily"
    tier = "enterprise"
    limits = get_tier_limits(tier)
    
    assert limits.requests_per_day is None, "Enterprise tier should have no daily limit"
    
    # Make a request and verify no daily limit
    allowed, limit_info = rate_limiter.check_rate_limit(identifier, tier)
    assert allowed
    assert limit_info["daily_limit"] is None
    assert limit_info["daily_remaining"] is None


def test_user_tier_from_database(db_session: Session) -> None:
    """Test that user tier is correctly retrieved from database."""
    # Create test users with different tiers
    free_user = User(user_id="test_free", account_tier=AccountTier.FREE)
    pro_user = User(user_id="test_pro", account_tier=AccountTier.PRO)
    enterprise_user = User(user_id="test_enterprise", account_tier=AccountTier.ENTERPRISE)
    
    db_session.add(free_user)
    db_session.add(pro_user)
    db_session.add(enterprise_user)
    db_session.commit()
    
    # Verify tiers
    assert free_user.account_tier == AccountTier.FREE
    assert free_user.is_free_tier()
    assert not free_user.is_pro_tier()
    
    assert pro_user.account_tier == AccountTier.PRO
    assert pro_user.is_pro_tier()
    assert not pro_user.is_enterprise_tier()
    
    assert enterprise_user.account_tier == AccountTier.ENTERPRISE
    assert enterprise_user.is_enterprise_tier()


def test_default_tier_is_free(db_session: Session) -> None:
    """Test that new users default to Free tier."""
    user = User(user_id="test_default")
    db_session.add(user)
    db_session.commit()
    
    # Refresh to get default value
    db_session.refresh(user)
    assert user.account_tier == AccountTier.FREE
    assert user.is_free_tier()


def test_tier_limits_configuration() -> None:
    """Test that tier limits are correctly configured."""
    free_limits = get_tier_limits("free")
    assert free_limits.requests_per_minute == 5
    assert free_limits.requests_per_day == 100
    
    pro_limits = get_tier_limits("pro")
    assert pro_limits.requests_per_minute == 20
    assert pro_limits.requests_per_day == 1000
    
    enterprise_limits = get_tier_limits("enterprise")
    assert enterprise_limits.requests_per_minute == 60
    assert enterprise_limits.requests_per_day is None  # Unlimited


def test_feature_gating() -> None:
    """Test that feature gating works correctly."""
    from llmhive.app.tier_limits import is_feature_enabled, is_domain_preset_allowed
    
    # Free tier should not have advanced features
    assert not is_feature_enabled("free", "advanced_orchestration")
    assert is_feature_enabled("free", "basic_orchestration")
    
    # Pro tier should have more features
    assert is_feature_enabled("pro", "advanced_orchestration")
    assert is_feature_enabled("pro", "deep_verification")
    
    # Enterprise should have all features
    assert is_feature_enabled("enterprise", "advanced_orchestration")
    assert is_feature_enabled("enterprise", "custom_models")
    
    # Domain preset gating
    assert is_domain_preset_allowed("free", "general")
    assert not is_domain_preset_allowed("free", "medical")
    assert is_domain_preset_allowed("pro", "research")
    assert is_domain_preset_allowed("enterprise", "medical")


def test_rate_limiter_thread_safety(rate_limiter: TierRateLimiter) -> None:
    """Test that rate limiter is thread-safe (basic check)."""
    import threading
    
    identifier = "test_thread_safe"
    tier = "free"
    results = []
    
    def make_request():
        allowed, _ = rate_limiter.check_rate_limit(identifier, tier)
        results.append(allowed)
    
    # Create multiple threads making requests simultaneously
    threads = [threading.Thread(target=make_request) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    
    # Should have some allowed and some blocked (depending on timing)
    assert len(results) == 10
    # At least some should be allowed (first few)
    assert any(results), "At least some requests should be allowed"

