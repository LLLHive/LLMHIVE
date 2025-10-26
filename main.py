"""
Main entry point for the LLMHIVE FastAPI application.
This module imports and exposes the FastAPI app instance for Gunicorn.
"""
import sys
import os

# Add the app directory to the Python path so relative imports in app/app.py work correctly
# This allows app/app.py to use relative imports like "from orchestration.router import..."
app_dir = os.path.join(os.path.dirname(__file__), "app")
sys.path.insert(0, app_dir)

# Import the FastAPI app instance from app/app.py
from app import app

__all__ = ["app"]
