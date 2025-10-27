"""
Main entry point for the LLMHIVE FastAPI application.
This module imports and exposes the FastAPI app instance for Gunicorn.
"""

# With PYTHONPATH=/app, we can import directly using absolute imports
from app.app import app

__all__ = ["app"]
