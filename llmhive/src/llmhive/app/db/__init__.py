"""Database session helper for CLI and background sync jobs.

FastAPI routes should continue to use ``database.get_db`` / ``get_db_context``.
``openrouter.scheduler`` and ``weekly_improvement`` import ``get_db_session`` from
``llmhive.app.db`` (this package).
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from ..database import _SessionLocal, _db_initialized


def get_db_session() -> Session:
    """Return a new SQLAlchemy session. Caller **must** ``close()`` when done.

    Raises:
        RuntimeError: if SQLAlchemy is unavailable or the engine could not be created.
    """
    if not _db_initialized or _SessionLocal is None:
        raise RuntimeError(
            "Database not configured: install SQLAlchemy and set DATABASE_URL or "
            "SQLALCHEMY_DATABASE_URI before running OpenRouter sync or the weekly "
            "improvement cycle."
        )
    return _SessionLocal()
