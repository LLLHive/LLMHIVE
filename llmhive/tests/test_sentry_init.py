"""Tests for the optional backend Sentry initializer."""
from __future__ import annotations

import importlib

import pytest


def _reload() -> object:
    """Force a fresh import of the sentry_init module so module-level state resets."""
    from llmhive.app.monitoring import sentry_init
    importlib.reload(sentry_init)
    return sentry_init


def test_dormant_when_dsn_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SENTRY_DSN", raising=False)
    monkeypatch.delenv("LLMHIVE_SENTRY_DSN", raising=False)

    sentry_init = _reload()

    assert sentry_init.is_sentry_configured() is False
    assert sentry_init.init_sentry_if_configured() is False
    # capture_exception must be a no-op without init
    sentry_init.capture_exception(RuntimeError("boom"))


def test_placeholder_dsn_treated_as_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SENTRY_DSN", "https://foo@...ingest.sentry.io/123")
    sentry_init = _reload()
    assert sentry_init.is_sentry_configured() is False


def test_alt_env_var(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SENTRY_DSN", raising=False)
    monkeypatch.setenv(
        "LLMHIVE_SENTRY_DSN", "https://abc@o0.ingest.sentry.io/123"
    )
    sentry_init = _reload()
    assert sentry_init.is_sentry_configured() is True


def test_warns_when_sdk_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    """Init returns False (and warns) when DSN is set but sentry-sdk isn't installed."""
    import sys

    monkeypatch.setenv("SENTRY_DSN", "https://abc@o0.ingest.sentry.io/123")

    # Hide sentry_sdk from import so the helper exercises its fallback branch.
    real = sys.modules.pop("sentry_sdk", None)
    monkeypatch.setitem(sys.modules, "sentry_sdk", None)
    try:
        sentry_init = _reload()
        # Even if a sentry_sdk is installed elsewhere, our blocked module makes import fail.
        assert sentry_init.init_sentry_if_configured() is False
    finally:
        sys.modules.pop("sentry_sdk", None)
        if real is not None:
            sys.modules["sentry_sdk"] = real


def test_capture_exception_safe_when_uninitialized(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("SENTRY_DSN", raising=False)
    monkeypatch.delenv("LLMHIVE_SENTRY_DSN", raising=False)
    sentry_init = _reload()
    # Should not raise even with arbitrary scope kwargs.
    sentry_init.capture_exception(ValueError("ignored"), user="alice", op="checkout")
