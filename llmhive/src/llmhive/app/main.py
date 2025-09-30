"""FastAPI application entry point."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from .api import api_router
from .config import settings
from .database import engine
from .models import Base

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.database_url.startswith("sqlite"):
        Base.metadata.create_all(bind=engine)
        logger.info("Ensured SQLite schema is created for local development.")
    yield


app = FastAPI(
    title=settings.app_name,
    version="3.0.0",
    description="LLMHive orchestrates multiple LLMs through debate and synthesis.",
    lifespan=lifespan,
)

app.include_router(api_router, prefix="/api/v1")
