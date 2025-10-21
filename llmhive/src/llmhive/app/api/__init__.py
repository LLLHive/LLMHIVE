"""API routers for LLMHive."""
from fastapi import APIRouter

from .orchestration import router as orchestration_router
from .providers import router as providers_router
from .system import router as system_router

api_router = APIRouter()
api_router.include_router(system_router, tags=["system"])
api_router.include_router(orchestration_router, prefix="/orchestration", tags=["orchestration"])
api_router.include_router(providers_router)

__all__ = ["api_router"]
