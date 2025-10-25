"""
Main entry point for the LLMHive application.

This file initializes a FastAPI application, sets up the necessary API endpoints,
and defines the root endpoint for health checks. The application structure is
designed to be modular, with different functionalities handled by their
respective components.
"""

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from .api.endpoints import router as api_router
from .config import settings

# Initialize the FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="LLMHive: A Multi-Agent LLM Orchestration Platform"
)

# Add CORS Middleware
# This allows our Vercel-hosted frontend to make requests to this backend.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, you should restrict this to your frontend's domain.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", summary="Health Check", description="Root endpoint to check if the application is running.")
async def root():
    """
    Health check endpoint.
    Returns a welcome message indicating the service is operational.
    """
    return {"message": f"Welcome to {settings.APP_NAME} v{settings.APP_VERSION}"}

# Include the API router
# All endpoints defined in `api/endpoints.py` will be prefixed with `/api`
app.include_router(api_router, prefix="/api")

# In a real application, you would also have startup and shutdown events
# to handle things like database connections, model loading, etc.
#
# @app.on_event("startup")
# async def startup_event():
#     print("Starting up LLMHive...")
#     # Initialize database connections, load models, etc.
#
# @app.on_event("shutdown")
# async def shutdown_event():
#     print("Shutting down LLMHive...")
#     # Close database connections, clean up resources, etc.
