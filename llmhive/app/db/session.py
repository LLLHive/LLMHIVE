"""Database session factory using SQLAlchemy async engine."""
from __future__ import annotations

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from ..core.settings import settings
from .models import Base


def _create_engine():
    return create_async_engine(settings.db_url, echo=False, future=True)


def _create_session_factory(engine):
    return sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


engine = _create_engine()
SessionLocal = _create_session_factory(engine)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
