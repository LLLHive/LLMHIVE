"""Database session and engine configuration."""
from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from .config import settings


def _create_engine(url: str) -> Engine:
    if url.startswith("sqlite"):
        connect_args = {"check_same_thread": False}
        if ":memory:" in url:
            return create_engine(
                url,
                future=True,
                connect_args=connect_args,
                poolclass=StaticPool,
            )
        return create_engine(url, future=True, connect_args=connect_args)
    return create_engine(url, future=True, pool_pre_ping=True)


engine = _create_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)


@contextmanager
def session_scope() -> Iterator[Session]:
    """Provide a transactional scope for database operations."""

    session: Session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_db() -> Iterator[Session]:
    """FastAPI dependency that yields a database session."""

    with session_scope() as session:
        yield session
