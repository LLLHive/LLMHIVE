from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.production_smoke_test import SmokeTestSuite
from scripts.run_prod_preflight import check_provider_health


class _FakeResponse:
    def __init__(self, status_code: int, payload=None):
        self.status_code = status_code
        self._payload = payload if payload is not None else {}

    def json(self):
        return self._payload


def _by_name(checks, name: str):
    return next(c for c in checks if c["name"] == name)


def test_preflight_accepts_current_tier_info_and_cost_tracking_shape(monkeypatch):
    monkeypatch.setenv("API_KEY", "test-key")
    monkeypatch.delenv("INTERNAL_ADMIN_OVERRIDE_KEY", raising=False)

    def fake_get(url, timeout=10, headers=None):
        if url.endswith("/health"):
            return _FakeResponse(200)
        if url.endswith("/build-info"):
            return _FakeResponse(200, {"commit": "abc123", "environment": "production"})
        if url.endswith("/internal/launch_kpis"):
            return _FakeResponse(403)
        raise AssertionError(f"Unexpected GET {url}")

    def fake_post(url, json=None, headers=None, timeout=60):
        if url.endswith("/v1/chat") and json["tier"] == "elite":
            return _FakeResponse(
                200,
                {
                    "extra": {
                        "tier_info": {"requested_tier": "elite", "effective_tier": "elite"},
                        "cost_tracking": {"cost_usd": 0.004525},
                    }
                },
            )
        if url.endswith("/v1/chat") and json["tier"] == "free":
            return _FakeResponse(
                200,
                {
                    "extra": {
                        "tier_info": {"requested_tier": "free", "effective_tier": "free"},
                        "cost_tracking": {"cost_usd": 0.0},
                    }
                },
            )
        raise AssertionError(f"Unexpected POST {url} {json}")

    with patch("requests.get", side_effect=fake_get), patch("requests.post", side_effect=fake_post):
        checks = check_provider_health("https://example.com")

    assert _by_name(checks, "spend_decision_in_elite_response")["passed"] is True
    assert _by_name(checks, "free_tier_spend_blocks_paid")["passed"] is True


def test_preflight_still_accepts_legacy_spend_decision_shape(monkeypatch):
    monkeypatch.setenv("API_KEY", "test-key")
    monkeypatch.delenv("INTERNAL_ADMIN_OVERRIDE_KEY", raising=False)

    def fake_get(url, timeout=10, headers=None):
        if url.endswith("/health"):
            return _FakeResponse(200)
        if url.endswith("/build-info"):
            return _FakeResponse(200, {"commit": "abc123", "environment": "production"})
        if url.endswith("/internal/launch_kpis"):
            return _FakeResponse(403)
        raise AssertionError(f"Unexpected GET {url}")

    def fake_post(url, json=None, headers=None, timeout=60):
        if url.endswith("/v1/chat") and json["tier"] == "elite":
            return _FakeResponse(
                200,
                {
                    "extra": {
                        "spend_decision": {"tier": "elite", "allowed_paid_escalation": True}
                    }
                },
            )
        if url.endswith("/v1/chat") and json["tier"] == "free":
            return _FakeResponse(
                200,
                {
                    "extra": {
                        "spend_decision": {"tier": "free", "allowed_paid_escalation": False}
                    }
                },
            )
        raise AssertionError(f"Unexpected POST {url} {json}")

    with patch("requests.get", side_effect=fake_get), patch("requests.post", side_effect=fake_post):
        checks = check_provider_health("https://example.com")

    assert _by_name(checks, "spend_decision_in_elite_response")["passed"] is True
    assert _by_name(checks, "free_tier_spend_blocks_paid")["passed"] is True


def test_smoke_support_endpoint_skips_mutation_by_default(monkeypatch):
    monkeypatch.delenv("SMOKE_TEST_ALLOW_MUTATIONS", raising=False)
    suite = SmokeTestSuite("https://example.com")

    def should_not_be_called(*args, **kwargs):
        raise AssertionError("Support mutation request should be skipped by default")

    suite._request = should_not_be_called
    suite.test_support_endpoint()

    result = suite.results[-1]
    assert result.name == "Support Tickets POST"
    assert result.passed is True
    assert "Skipped by default" in result.details["note"]


def test_smoke_support_endpoint_can_run_when_explicitly_enabled(monkeypatch):
    monkeypatch.setenv("SMOKE_TEST_ALLOW_MUTATIONS", "1")
    suite = SmokeTestSuite("https://example.com")

    def fake_request(method, endpoint, data=None, timeout=30, headers=None):
        assert method == "POST"
        assert endpoint == "/v1/support/tickets"
        return 201, {"ticketId": "smoke-123"}, 25.0

    suite._request = fake_request
    suite.test_support_endpoint()

    result = suite.results[-1]
    assert result.name == "Support Tickets POST"
    assert result.passed is True
    assert result.status_code == 201
    assert result.details["ticket_id"] == "smoke-123"
