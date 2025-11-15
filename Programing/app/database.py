"""Database utilities and configuration for LLMHIVE."""

from functools import lru_cache
from typing import Generator

from pydantic import BaseSettings, Field
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


class Settings(BaseSettings):
    """Application settings derived from environment variables."""

    database_url: str = Field(
        "sqlite:///./llmhive.db",
        env=["DATABASE_URL", "LLMHIVE_DATABASE_URL"],
        description="Database connection string",
    )

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached settings instance."""

    return Settings()


def create_session_factory() -> sessionmaker:
    """Create a synchronous SQLAlchemy session factory."""

    settings = get_settings()
    engine = create_engine(settings.database_url, pool_pre_ping=True, future=True)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


SessionLocal = create_session_factory()


def get_db() -> Generator:
    """Provide a database session dependency."""

    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
