from fastapi import FastAPI
from orchestration.router import router as orchestration_router
from config import settings
from google.cloud import secretmanager
from pythonjsonlogger import jsonlogger
import logging
import os

# 1. CONFIGURE STRUCTURED LOGGING
# This must happen first to ensure all subsequent logs are structured.
logger = logging.getLogger("llmhive")
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))
logHandler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter(
    '%(asctime)s %(name)s %(levelname)s %(message)s'
)
logHandler.setFormatter(formatter)
# Clear existing handlers to avoid duplicate logs
if logger.hasHandlers():
    logger.handlers.clear()
logger.addHandler(logHandler)


# 2. DEFINE THE SECRET FETCHER FUNCTION
def get_secret(project_id: str, secret_id: str, version_id: str = "latest") -> str:
    """Retrieves a secret from Google Cloud Secret Manager."""
    try:
        client = secretmanager.SecretManagerServiceClient()
        name = f"projects/{project_id}/secrets/{secret_id}/versions/{version_id}"
        response = client.access_secret_version(request={"name": name})
        logger.info("Successfully fetched secret from Secret Manager")
        return response.payload.data.decode("UTF-8")
    except Exception as e:
        # Log error type without exposing sensitive details
        error_type = type(e).__name__
        logger.error(f"Failed to fetch secret from Secret Manager: {error_type}")
        # Return empty string to allow app to start with fallback behavior
        # Note: Calling code should check for empty string and handle accordingly
        return ""


# 3. INITIALIZE AND CONFIGURE THE FASTAPI APP
app = FastAPI(
    title="LLMHive Orchestrator",
    description="API for orchestrating LLM agent interactions.",
    version="1.0.0"
)

@app.on_event("startup")
async def startup_event():
    """
    On application startup, load secrets into the settings object.
    """
    logger.info("Application startup sequence initiated.")
    if not settings.TAVILY_API_KEY:
        api_key = get_secret(settings.PROJECT_ID, "TAVILY_API_KEY")
        if not api_key:
            logger.critical("TAVILY_API_KEY secret could not be loaded. The application might not function correctly.")
        settings.TAVILY_API_KEY = api_key
    logger.info("Application startup complete.")


# 4. ADD THE HEALTH CHECK ENDPOINT
@app.get("/healthz", tags=["Health Check"])
async def health_check():
    """Health check endpoint for Cloud Run readiness and liveness probes."""
    return {"status": "ok"}


# 5. INCLUDE THE EXISTING API ROUTER (CRITICAL)
# This preserves our main API functionality.
app.include_router(orchestration_router, prefix="/api")