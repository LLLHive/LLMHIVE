"""Tests for graceful fallback behaviour in :mod:`app.models.language_model`."""

from __future__ import annotations

import types

import pytest


class _FakeQuotaError(Exception):
    """Mimic the shape of the OpenAI insufficient quota error."""

    def __init__(self, message: str, status_code: int = 429) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.response = types.SimpleNamespace(status_code=status_code)


def test_language_model_falls_back_to_stub(monkeypatch):
    from app.models.language_model import LanguageModel

    lm = LanguageModel(api_key="test-key", model="gpt-4o")

    def _raise_quota_error(*args, **kwargs):
        raise _FakeQuotaError("You exceeded your current quota")

    monkeypatch.setattr(lm.client.chat.completions, "create", _raise_quota_error)

    result = lm.generate("What is the capital of Spain?")

    assert "Madrid" in result


def test_language_model_propagates_unhandled_errors(monkeypatch):
    from app.models.language_model import LanguageModel

    lm = LanguageModel(api_key="test-key", model="gpt-4o")

    class _UnexpectedError(Exception):
        pass

    def _raise_unexpected_error(*args, **kwargs):
        raise _UnexpectedError("boom")

    monkeypatch.setattr(lm.client.chat.completions, "create", _raise_unexpected_error)

    with pytest.raises(_UnexpectedError):
        lm.generate("Say hello")
