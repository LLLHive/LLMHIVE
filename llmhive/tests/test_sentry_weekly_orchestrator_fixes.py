"""Regression tests for Sentry weekly orchestrator errors (Aug 2026)."""
from __future__ import annotations

from llmhive.app.intelligence.provider_equivalence import (
    ProviderFailureType,
    classify_provider_failure,
    is_failover_worthy,
)
from llmhive.app.anthropic_models import map_anthropic_model_id


def test_empty_provider_response_is_failover_worthy():
    failure = classify_provider_failure(ValueError("Invalid/empty provider response"))
    assert failure == ProviderFailureType.SERVER
    assert is_failover_worthy(failure)


def test_anthropic_model_mapping_strips_openrouter_prefix_and_retires_dated_ids():
    assert map_anthropic_model_id("anthropic/claude-opus-5") == "claude-opus-5"
    assert map_anthropic_model_id("claude-sonnet-4-20250514") == "claude-sonnet-4-6"
    assert map_anthropic_model_id("anthropic/claude-sonnet-4.6") == "claude-sonnet-4-6"
    assert map_anthropic_model_id("claude-opus-4-20250514") == "claude-opus-5"


def test_firestore_subscription_service_exposes_usage_helpers():
    from llmhive.app.firestore_db import FirestoreSubscriptionService

    assert hasattr(FirestoreSubscriptionService, "get_user_usage")
    assert hasattr(FirestoreSubscriptionService, "record_query_usage")

    service = FirestoreSubscriptionService()
    # No Firestore client in unit tests — should return empty counters, not raise.
    usage = service.get_user_usage("user_test")
    assert usage["elite_queries_used"] == 0
    assert usage["standard_queries_used"] == 0
    assert usage["budget_queries_used"] == 0
