"""FastAPI application entry point for LLMHive."""
from __future__ import annotations

import logging
import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import api_router
from .config import settings
from .database import engine
from .models import Base

# Configure comprehensive logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# Initialize FastAPI application
app = FastAPI(
    title=settings.app_name,
    description="LLM orchestration service",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(api_router, prefix="/api/v1")


@app.on_event("startup")
async def startup_event():
    """Initialize database tables on startup."""
    logger.info("Starting up LLMHive application")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Database URL: {settings.database_url}")
    
    # Create database tables
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Failed to create database tables: {e}")
        # Don't fail startup if database creation fails
        # This allows the app to start for debugging purposes


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on shutdown."""
    logger.info("Shutting down LLMHive application")


@app.get("/", tags=["root"])
async def root():
    """Root endpoint for basic verification."""
    return {
        "service": "LLMHive Orchestrator API",
        "status": "online",
        "version": "1.0.0"
    }


@app.get("/healthz", tags=["health"])
async def health_check_root():
    """Health check endpoint at root level for Cloud Run."""
    return {"status": "ok"}


@app.get("/health", tags=["health"])
async def health_check_alt():
    """Alternative health check endpoint."""
    return {"status": "ok"}
