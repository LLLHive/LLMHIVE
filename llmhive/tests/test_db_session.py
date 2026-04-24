"""Tests for ``llmhive.app.db.get_db_session``."""
from __future__ import annotations

import pytest


def test_get_db_session_returns_usable_session():
    from llmhive.app.db import get_db_session

    session = get_db_session()
    try:
        assert session is not None
    finally:
        session.close()


def test_get_db_session_raises_when_uninitialized(monkeypatch):
    import llmhive.app.db as db_mod

    monkeypatch.setattr(db_mod, "_db_initialized", False)
    monkeypatch.setattr(db_mod, "_SessionLocal", None)

    with pytest.raises(RuntimeError, match="Database not configured"):
        db_mod.get_db_session()
