"""Unit tests for TierSpendGovernor and internal auth."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "llmhive", "src"))

from llmhive.app.orchestration.tier_spend_governor import (
    TierSpendGovernor,
    _SpendLedger,
    SpendDecision,
)
from llmhive.app.orchestration.internal_auth import (
    is_internal_request,
    sanitize_internal_flags,
)


class TestFreeTierGovernor(unittest.TestCase):
    """Free tier is mathematically unable to incur paid LLM spend."""

    def setUp(self):
        self.ledger = _SpendLedger()
        self.gov = TierSpendGovernor(self.ledger)

    def test_free_blocks_paid_escalation(self):
        d = self.gov.evaluate("free", "user1", predicted_cost_usd=0.01)
        self.assertFalse(d.allowed_paid_escalation)
        self.assertIn("free_tier", d.reason_blocked)

    def test_free_blocks_zero_cost(self):
        d = self.gov.evaluate("free", "user1", predicted_cost_usd=0.0)
        self.assertFalse(d.allowed_paid_escalation)

    def test_free_always_returns_zero_spend_remaining(self):
        d = self.gov.evaluate("free", "user1", predicted_cost_usd=0.0)
        self.assertEqual(d.spend_remaining_day, 0.0)
        self.assertEqual(d.spend_remaining_month, 0.0)

    def test_free_tool_cap_per_request(self):
        d = self.gov.evaluate("free", "user1", predicted_cost_usd=0.0, tool_calls_requested=100)
        self.assertIn("tool_cap", d.reason_blocked)

    def test_free_tool_cap_daily(self):
        for _ in range(110):
            self.ledger.record_tool_calls("user1", 1)
        d = self.gov.evaluate("free", "user1", predicted_cost_usd=0.0, tool_calls_requested=1)
        self.assertIn("daily_tool_cap", d.reason_blocked)

    def test_free_decision_is_auditable(self):
        d = self.gov.evaluate("free", "user1", predicted_cost_usd=0.0)
        obj = d.to_dict()
        self.assertIn("tier", obj)
        self.assertIn("allowed_paid_escalation", obj)
        self.assertIn("reason_blocked", obj)
        self.assertEqual(obj["tier"], "free")


class TestElitePlusGovernor(unittest.TestCase):
    """Elite+ cannot exceed request, account, or global spend budgets."""

    def setUp(self):
        self.ledger = _SpendLedger()
        self.gov = TierSpendGovernor(self.ledger)

    def test_elite_plus_allows_within_budget(self):
        d = self.gov.evaluate("elite+", "user1", predicted_cost_usd=0.01)
        self.assertTrue(d.allowed_paid_escalation)

    def test_elite_plus_blocks_over_request_ceiling(self):
        d = self.gov.evaluate("elite+", "user1", predicted_cost_usd=0.05)
        self.assertFalse(d.allowed_paid_escalation)
        self.assertIn("request_ceiling", d.reason_blocked)

    def test_elite_plus_daily_budget(self):
        for _ in range(100):
            self.ledger.record_spend("user1", 0.025)
        d = self.gov.evaluate("elite+", "user1", predicted_cost_usd=0.01)
        self.assertFalse(d.allowed_paid_escalation)
        self.assertIn("daily_budget", d.reason_blocked)

    def test_elite_plus_monthly_budget(self):
        for _ in range(1100):
            self.ledger.record_spend("user1", 0.025)
        d = self.gov.evaluate("elite+", "user1", predicted_cost_usd=0.01)
        self.assertFalse(d.allowed_paid_escalation)
        self.assertIn("monthly_budget", d.reason_blocked)

    def test_elite_plus_decision_has_remaining(self):
        d = self.gov.evaluate("elite+", "user1", predicted_cost_usd=0.01)
        self.assertGreater(d.spend_remaining_day, 0)
        self.assertGreater(d.spend_remaining_month, 0)

    def test_concurrency_cap(self):
        from llmhive.app.orchestration.tier_spend_governor import ELITE_PLUS_ACCOUNT_CONCURRENCY_CAP
        for _ in range(ELITE_PLUS_ACCOUNT_CONCURRENCY_CAP):
            self.assertTrue(self.gov.acquire_concurrency("user1"))
        self.assertFalse(self.gov.acquire_concurrency("user1"))
        self.gov.release_concurrency("user1")
        self.assertTrue(self.gov.acquire_concurrency("user1"))


class TestGlobalBreaker(unittest.TestCase):
    """Global breaker shuts down all paid escalation when threshold exceeded."""

    def setUp(self):
        self.ledger = _SpendLedger()
        self.gov = TierSpendGovernor(self.ledger)

    def test_global_breaker_triggers(self):
        for _ in range(2500):
            self.ledger.record_spend("any", 0.025)
        d = self.gov.evaluate("elite+", "new_user", predicted_cost_usd=0.01)
        self.assertTrue(d.global_breaker_active)
        self.assertFalse(d.allowed_paid_escalation)

    def test_internal_bypasses_global_breaker(self):
        for _ in range(2500):
            self.ledger.record_spend("any", 0.025)
        d = self.gov.evaluate("elite+", "admin", predicted_cost_usd=0.01, is_internal=True)
        self.assertTrue(d.allowed_paid_escalation)
        self.assertTrue(d.is_internal_override)


class TestInternalAuth(unittest.TestCase):
    """Internal bench headers cannot be abused by external requests."""

    def test_empty_key_rejected(self):
        self.assertFalse(is_internal_request({"X-LLMHive-Internal-Key": ""}))

    def test_no_header_rejected(self):
        self.assertFalse(is_internal_request({}))

    def test_wrong_key_rejected(self):
        self.assertFalse(is_internal_request({"X-LLMHive-Internal-Key": "wrong_key_12345"}))

    def test_convenience_header_ignored(self):
        self.assertFalse(is_internal_request({"X-LLMHIVE-INTERNAL-BENCH": "1"}))

    def test_sanitize_returns_false_for_external(self):
        flags = sanitize_internal_flags({"X-LLMHive-Internal-Key": "wrong"})
        self.assertFalse(flags["is_internal"])
        self.assertFalse(flags["allow_bench_output"])
        self.assertFalse(flags["allow_extra_paid_calls"])
        self.assertIsNone(flags["max_paid_calls_override"])

    def test_sanitize_without_env_flag(self):
        flags = sanitize_internal_flags({})
        self.assertFalse(flags["is_internal"])


class TestSpendLedger(unittest.TestCase):
    """Spend ledger operations are correct."""

    def test_record_and_retrieve(self):
        ledger = _SpendLedger()
        ledger.record_spend("u1", 1.5)
        self.assertAlmostEqual(ledger.get_daily_spend("u1"), 1.5)
        self.assertAlmostEqual(ledger.get_monthly_spend("u1"), 1.5)

    def test_global_window(self):
        ledger = _SpendLedger()
        ledger.record_spend("u1", 10.0)
        self.assertAlmostEqual(ledger.global_spend_last_n_minutes(10), 10.0)

    def test_tool_calls_tracked(self):
        ledger = _SpendLedger()
        ledger.record_tool_calls("u1", 5)
        self.assertEqual(ledger.get_daily_tool_calls("u1"), 5)

    def test_status_output(self):
        ledger = _SpendLedger()
        ledger.record_spend("u1", 1.0)
        status = ledger.get_status()
        self.assertIn("active_accounts_daily", status)
        self.assertEqual(status["active_accounts_daily"], 1)


if __name__ == "__main__":
    unittest.main()
