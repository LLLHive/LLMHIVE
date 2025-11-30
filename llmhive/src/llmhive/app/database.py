"""Database configuration and session management for LLMHive.

This module provides database connectivity for billing, subscriptions,
and other persistent data. Falls back to in-memory storage when
a database is not configured.
"""
from __future__ import annotations

import logging
import os
from contextlib import contextmanager
from typing import Generator, Optional

logger = logging.getLogger(__name__)

# Try to import SQLAlchemy
try:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker, Session
    from sqlalchemy.pool import StaticPool
    SQLALCHEMY_AVAILABLE = True
except ImportError:
    SQLALCHEMY_AVAILABLE = False
    Session = None  # type: ignore
    logger.warning("SQLAlchemy not available, database features disabled")

# Database configuration
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    os.getenv("SQLALCHEMY_DATABASE_URI", "")
)

# Global engine and session factory
_engine = None
_SessionLocal = None


def _init_database() -> bool:
    """Initialize database connection if configured."""
    global _engine, _SessionLocal
    
    if not SQLALCHEMY_AVAILABLE:
        logger.warning("SQLAlchemy not installed, skipping database initialization")
        return False
    
    if not DATABASE_URL:
        logger.info("No DATABASE_URL configured, using in-memory SQLite")
        # Use in-memory SQLite for development/testing
        _engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
    else:
        try:
            _engine = create_engine(DATABASE_URL)
            logger.info("Database engine created for: %s", DATABASE_URL.split("@")[-1] if "@" in DATABASE_URL else "configured database")
        except Exception as e:
            logger.error("Failed to create database engine: %s", e)
            return False
    
    _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)
    return True


# Initialize on module load
_db_initialized = _init_database()


def get_db() -> Generator[Optional[Session], None, None]:
    """Get a database session.
    
    Yields:
        SQLAlchemy Session if database is available, None otherwise.
        
    Usage:
        with get_db() as db:
            if db:
                # Use database
                result = db.query(Model).all()
            else:
                # Handle no database case
                pass
    
    Or as FastAPI dependency:
        @router.get("/")
        def endpoint(db: Session = Depends(get_db)):
            ...
    """
    if not _db_initialized or _SessionLocal is None:
        logger.debug("Database not available, yielding None")
        yield None
        return
    
    db = _SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_context() -> Generator[Optional[Session], None, None]:
    """Context manager for database sessions.
    
    Usage:
        with get_db_context() as db:
            if db:
                result = db.query(Model).all()
    """
    if not _db_initialized or _SessionLocal is None:
        yield None
        return
    
    db = _SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def get_engine():
    """Get the database engine."""
    return _engine


def is_database_available() -> bool:
    """Check if database is available."""
    return _db_initialized and _engine is not None


# Create tables function (called from main.py)
def create_tables(base) -> bool:
    """Create all tables from a SQLAlchemy Base.
    
    Args:
        base: SQLAlchemy declarative base with model definitions
        
    Returns:
        True if tables were created, False otherwise
    """
    if not is_database_available():
        logger.warning("Cannot create tables: database not available")
        return False
    
    try:
        base.metadata.create_all(bind=_engine)
        logger.info("Database tables created successfully")
        return True
    except Exception as e:
        logger.error("Failed to create tables: %s", e)
        return False

