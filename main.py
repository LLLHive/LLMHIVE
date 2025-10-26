"""
Main entry point for the LLMHIVE FastAPI application.
This module imports and exposes the FastAPI app instance for Gunicorn.
"""
import sys
import os

# Add the app directory to the Python path so relative imports work
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "app"))

from app import app

__all__ = ["app"]
