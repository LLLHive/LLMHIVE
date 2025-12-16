"""OpenRouter Database Migrations.

Creates and manages OpenRouter tables.

Usage:
    from llmhive.app.openrouter.migrations import init_openrouter_tables
    
    # Call during app startup
    init_openrouter_tables()
"""
from __future__ import annotations

import logging
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import Session

from .models import Base, OpenRouterModel, OpenRouterEndpoint, OpenRouterUsageTelemetry, PromptTemplate, SavedRun

logger = logging.getLogger(__name__)


def init_openrouter_tables(engine=None, db_url: str = None) -> bool:
    """Initialize OpenRouter database tables.
    
    Creates all tables defined in openrouter.models if they don't exist.
    Safe to call multiple times (idempotent).
    
    Args:
        engine: SQLAlchemy engine (optional, created from db_url if not provided)
        db_url: Database URL (optional, uses environment if not provided)
        
    Returns:
        True if tables were created successfully, False otherwise
    """
    try:
        if engine is None:
            import os
            db_url = db_url or os.getenv("DATABASE_URL", "sqlite:///./llmhive.db")
            engine = create_engine(db_url)
        
        # Check which tables exist
        inspector = inspect(engine)
        existing_tables = set(inspector.get_table_names())
        
        target_tables = [
            "openrouter_models",
            "openrouter_endpoints",
            "openrouter_usage_telemetry",
            "openrouter_prompt_templates",
            "openrouter_saved_runs",
        ]
        
        missing_tables = [t for t in target_tables if t not in existing_tables]
        
        if not missing_tables:
            logger.info("All OpenRouter tables already exist")
            return True
        
        logger.info("Creating OpenRouter tables: %s", missing_tables)
        
        # Create all tables defined in Base
        Base.metadata.create_all(bind=engine)
        
        # Verify creation
        inspector = inspect(engine)
        created_tables = set(inspector.get_table_names())
        
        for table in target_tables:
            if table in created_tables:
                logger.info("✓ Table '%s' created/exists", table)
            else:
                logger.warning("✗ Table '%s' was NOT created", table)
        
        return all(t in created_tables for t in target_tables)
        
    except Exception as e:
        logger.error("Failed to create OpenRouter tables: %s", e, exc_info=True)
        return False


def drop_openrouter_tables(engine=None, db_url: str = None, confirm: bool = False) -> bool:
    """Drop all OpenRouter tables.
    
    WARNING: This deletes all OpenRouter data!
    
    Args:
        engine: SQLAlchemy engine
        db_url: Database URL
        confirm: Must be True to actually drop tables
        
    Returns:
        True if tables were dropped, False otherwise
    """
    if not confirm:
        logger.warning("drop_openrouter_tables called without confirm=True, aborting")
        return False
    
    try:
        if engine is None:
            import os
            db_url = db_url or os.getenv("DATABASE_URL", "sqlite:///./llmhive.db")
            engine = create_engine(db_url)
        
        Base.metadata.drop_all(bind=engine)
        logger.info("OpenRouter tables dropped")
        return True
        
    except Exception as e:
        logger.error("Failed to drop OpenRouter tables: %s", e)
        return False


def get_table_stats(session: Session) -> dict:
    """Get row counts for OpenRouter tables.
    
    Args:
        session: SQLAlchemy session
        
    Returns:
        Dictionary with table names and row counts
    """
    stats = {}
    
    try:
        stats["openrouter_models"] = session.query(OpenRouterModel).count()
        stats["openrouter_models_active"] = session.query(OpenRouterModel).filter(
            OpenRouterModel.is_active == True
        ).count()
    except Exception:
        stats["openrouter_models"] = "error"
    
    try:
        stats["openrouter_endpoints"] = session.query(OpenRouterEndpoint).count()
    except Exception:
        stats["openrouter_endpoints"] = "error"
    
    try:
        stats["openrouter_usage_telemetry"] = session.query(OpenRouterUsageTelemetry).count()
    except Exception:
        stats["openrouter_usage_telemetry"] = "error"
    
    try:
        stats["openrouter_prompt_templates"] = session.query(PromptTemplate).count()
    except Exception:
        stats["openrouter_prompt_templates"] = "error"
    
    try:
        stats["openrouter_saved_runs"] = session.query(SavedRun).count()
    except Exception:
        stats["openrouter_saved_runs"] = "error"
    
    return stats


# CLI for manual migrations
if __name__ == "__main__":
    import argparse
    import os
    import sys
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    
    parser = argparse.ArgumentParser(description="OpenRouter Database Migrations")
    parser.add_argument("action", choices=["create", "drop", "stats"], help="Action to perform")
    parser.add_argument("--db-url", help="Database URL (default: DATABASE_URL env or sqlite)")
    parser.add_argument("--confirm", action="store_true", help="Confirm destructive actions")
    
    args = parser.parse_args()
    
    db_url = args.db_url or os.getenv("DATABASE_URL", "sqlite:///./llmhive.db")
    
    if args.action == "create":
        success = init_openrouter_tables(db_url=db_url)
        sys.exit(0 if success else 1)
        
    elif args.action == "drop":
        if not args.confirm:
            print("ERROR: Must pass --confirm to drop tables")
            sys.exit(1)
        success = drop_openrouter_tables(db_url=db_url, confirm=True)
        sys.exit(0 if success else 1)
        
    elif args.action == "stats":
        from sqlalchemy.orm import sessionmaker
        engine = create_engine(db_url)
        Session = sessionmaker(bind=engine)
        with Session() as session:
            stats = get_table_stats(session)
            print("\nOpenRouter Table Stats:")
            for table, count in stats.items():
                print(f"  {table}: {count}")

