"""Main entrypoint for the LLMHIVE FastAPI application."""

from fastapi import FastAPI

from .api.routes import router
from .config import settings

app = FastAPI(title=settings.api_title)


@app.get("/healthz", tags=["health"])
def healthcheck() -> dict[str, str]:
    """Return a basic health status payload."""

    return {"status": "ok"}


app.include_router(router, prefix="/api")
