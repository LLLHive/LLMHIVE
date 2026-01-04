"""Tests for Stripe webhook security and idempotency.

Tests cover:
- Webhook signature verification
- Idempotent event processing
- Subscription state machine transitions
- Grace period handling
"""
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch


class TestWebhookIdempotencyStore:
    """Tests for webhook idempotency store."""
    
    def test_new_event_not_processed(self):
        """New events are not marked as processed."""
        from llmhive.app.payments.subscription_manager import WebhookIdempotencyStore
        
        store = WebhookIdempotencyStore()
        
        assert not store.is_processed("evt_new_123")
    
    def test_marks_event_as_processed(self):
        """Events can be marked as processed."""
        from llmhive.app.payments.subscription_manager import WebhookIdempotencyStore
        
        store = WebhookIdempotencyStore()
        
        store.mark_processed("evt_123")
        
        assert store.is_processed("evt_123")
    
    def test_duplicate_detection(self):
        """Duplicate events are detected."""
        from llmhive.app.payments.subscription_manager import WebhookIdempotencyStore
        
        store = WebhookIdempotencyStore()
        
        store.mark_processed("evt_dupe")
        
        # Second check should detect duplicate
        assert store.is_processed("evt_dupe")
    
    def test_evicts_oldest_when_full(self):
        """Evicts oldest events when max is reached."""
        from llmhive.app.payments.subscription_manager import WebhookIdempotencyStore
        
        store = WebhookIdempotencyStore(max_events=3)
        
        store.mark_processed("evt_1")
        store.mark_processed("evt_2")
        store.mark_processed("evt_3")
        store.mark_processed("evt_4")
        
        # evt_1 should be evicted
        assert not store.is_processed("evt_1")
        assert store.is_processed("evt_4")


class TestSubscriptionStatusStateMachine:
    """Tests for subscription state machine."""
    
    def test_free_can_transition_to_trialing(self):
        """Free -> Trialing is valid."""
        from llmhive.app.payments.subscription_manager import SubscriptionStatus
        
        assert SubscriptionStatus.FREE.can_transition_to(SubscriptionStatus.TRIALING)
    
    def test_free_can_transition_to_active(self):
        """Free -> Active is valid (direct purchase)."""
        from llmhive.app.payments.subscription_manager import SubscriptionStatus
        
        assert SubscriptionStatus.FREE.can_transition_to(SubscriptionStatus.ACTIVE)
    
    def test_active_can_transition_to_past_due(self):
        """Active -> Past Due is valid (payment failed)."""
        from llmhive.app.payments.subscription_manager import SubscriptionStatus
        
        assert SubscriptionStatus.ACTIVE.can_transition_to(SubscriptionStatus.PAST_DUE)
    
    def test_active_cannot_transition_to_unpaid(self):
        """Active -> Unpaid is NOT valid (must go through Past Due)."""
        from llmhive.app.payments.subscription_manager import SubscriptionStatus
        
        assert not SubscriptionStatus.ACTIVE.can_transition_to(SubscriptionStatus.UNPAID)
    
    def test_past_due_can_recover_to_active(self):
        """Past Due -> Active is valid (payment retry success)."""
        from llmhive.app.payments.subscription_manager import SubscriptionStatus
        
        assert SubscriptionStatus.PAST_DUE.can_transition_to(SubscriptionStatus.ACTIVE)
    
    def test_unpaid_downgrades_to_free(self):
        """Unpaid -> Free is valid (downgrade after grace)."""
        from llmhive.app.payments.subscription_manager import SubscriptionStatus
        
        assert SubscriptionStatus.UNPAID.can_transition_to(SubscriptionStatus.FREE)


class TestUserSubscription:
    """Tests for UserSubscription data class."""
    
    def test_free_tier_is_always_active(self):
        """Free tier subscriptions are always active."""
        from llmhive.app.payments.subscription_manager import (
            UserSubscription, SubscriptionStatus
        )
        
        sub = UserSubscription(
            user_id="user_1",
            status=SubscriptionStatus.FREE,
        )
        
        assert sub.is_active
    
    def test_past_due_is_not_active(self):
        """Past due subscriptions are not active."""
        from llmhive.app.payments.subscription_manager import (
            UserSubscription, SubscriptionStatus
        )
        
        sub = UserSubscription(
            user_id="user_1",
            status=SubscriptionStatus.PAST_DUE,
        )
        
        assert not sub.is_active
        assert sub.is_past_due
    
    def test_grace_period_detection(self):
        """Grace period is correctly detected."""
        from llmhive.app.payments.subscription_manager import (
            UserSubscription, SubscriptionStatus
        )
        
        # In grace period
        sub_in_grace = UserSubscription(
            user_id="user_1",
            status=SubscriptionStatus.PAST_DUE,
            grace_period_end=datetime.now(timezone.utc) + timedelta(days=3),
        )
        assert sub_in_grace.in_grace_period
        
        # Expired grace period
        sub_expired = UserSubscription(
            user_id="user_2",
            status=SubscriptionStatus.PAST_DUE,
            grace_period_end=datetime.now(timezone.utc) - timedelta(days=1),
        )
        assert not sub_expired.in_grace_period


class TestStripeClientWebhookVerification:
    """Tests for Stripe webhook verification."""
    
    def test_rejects_missing_secret(self):
        """Rejects webhook when secret is not configured."""
        from llmhive.app.payments.subscription_manager import StripeClient
        
        client = StripeClient(api_key="sk_test_xxx")
        
        result = client.verify_webhook(
            payload=b"{}",
            signature="test_sig",
            webhook_secret="",  # Empty secret
        )
        
        assert result is None
    
    def test_rejects_missing_signature(self):
        """Rejects webhook when signature header is missing."""
        from llmhive.app.payments.subscription_manager import StripeClient
        
        client = StripeClient(api_key="sk_test_xxx")
        
        result = client.verify_webhook(
            payload=b"{}",
            signature="",  # Missing signature
            webhook_secret="whsec_xxx",
        )
        
        assert result is None


class TestSubscriptionManager:
    """Tests for SubscriptionManager."""
    
    def test_tier_validation(self):
        """Invalid tiers are rejected."""
        from llmhive.app.payments.subscription_manager import SubscriptionManager
        
        manager = SubscriptionManager()
        
        # Should fail for unknown tier
        import asyncio
        result = asyncio.run(manager.subscribe(
            user_id="user_1",
            tier="super_ultra_tier",
            email="test@example.com",
        ))
        
        assert not result["success"]
        assert "Unknown tier" in result["error"]
    
    def test_grace_period_message(self):
        """Grace period message includes end date."""
        from llmhive.app.payments.subscription_manager import (
            SubscriptionManager, UserSubscription, SubscriptionStatus
        )
        
        manager = SubscriptionManager()
        
        # Set up a past due subscription with grace period
        grace_end = datetime.now(timezone.utc) + timedelta(days=5)
        manager._subscriptions["user_1"] = UserSubscription(
            user_id="user_1",
            status=SubscriptionStatus.PAST_DUE,
            tier="pro",
            grace_period_end=grace_end,
        )
        
        guidance = manager.get_user_guidance("user_1")
        
        assert guidance is not None
        assert "⚠️" in guidance
        assert "payment" in guidance.lower()


class TestIdempotentWebhookHandling:
    """Tests for idempotent webhook handling."""
    
    @pytest.mark.asyncio
    async def test_duplicate_webhook_skipped(self):
        """Duplicate webhooks are skipped."""
        from llmhive.app.payments.subscription_manager import (
            SubscriptionManager, get_idempotency_store
        )
        
        # Reset singleton for test isolation
        import llmhive.app.payments.subscription_manager as sm
        sm._idempotency_store = None
        
        manager = SubscriptionManager()
        
        # Mock the webhook verification to return a valid event
        with patch.object(manager._stripe, 'verify_webhook') as mock_verify:
            mock_verify.return_value = {
                "id": "evt_test_123",
                "type": "invoice.paid",
                "data": {"customer": "cus_xxx", "amount_paid": 1000},
                "created": 1234567890,
            }
            
            # First call should process
            result1 = await manager.handle_webhook(
                payload=b"{}",
                signature="sig",
                webhook_secret="whsec_xxx",
            )
            
            # Second call should be skipped
            result2 = await manager.handle_webhook(
                payload=b"{}",
                signature="sig",
                webhook_secret="whsec_xxx",
            )
        
        assert result1.get("success")
        assert result2.get("success")
        assert result2.get("idempotent") == True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

