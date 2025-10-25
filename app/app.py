from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from api.endpoints import router as api_router
from config import settings

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="LLMHive: A Multi-Agent LLM Orchestration Platform"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", summary="Health Check")
async def root():
    return {"message": f"Welcome to {settings.APP_NAME} v{settings.APP_VERSION}"}

@app.get("/health", status_code=200, summary="Lightweight Health Check")
def health():
    """
    Simple health check endpoint for Cloud Run probes.
    """
    return {"status": "ok"}

@app.get("/healthz", summary="Cloud Run Health Check")
async def health_check():
    """Health check endpoint required by Cloud Run."""
    return {"status": "ok"}

app.include_router(api_router, prefix="/api")