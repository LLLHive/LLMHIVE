"""Test session defaults for the LLMHive backend.

We turn the strict paid-access backend guard OFF for the test session because
most existing tests use synthetic payloads without a real Firestore-backed
subscription. Tests that need to exercise the guard (see
``test_access_guard.py``) re-enable it via ``monkeypatch``.
"""
from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _disable_paid_access_guard_by_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Default OFF in tests; specific tests opt in via ``monkeypatch.setenv``."""
    monkeypatch.setenv("LLMHIVE_REQUIRE_PAID_BACKEND", "0")
