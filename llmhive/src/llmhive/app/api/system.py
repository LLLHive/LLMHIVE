"""System endpoints such as health checks."""
from __future__ import annotations

import os
from typing import Any

from fastapi import APIRouter

from ..config import settings
from ..orchestrator import Orchestrator

router = APIRouter()


def _deployment_metadata() -> dict[str, Any]:
    """Capture build and runtime metadata for deployment verification."""

    metadata: dict[str, Any] = {}

    commit = os.getenv("GIT_COMMIT") or os.getenv("COMMIT_SHA")
    if commit:
        metadata["git_commit"] = commit

    repository = os.getenv("GITHUB_REPOSITORY") or os.getenv("CLOUD_SOURCE_REPO")
    if repository:
        metadata["repository"] = repository

    cloud_run_keys = {
        "service": os.getenv("K_SERVICE"),
        "revision": os.getenv("K_REVISION"),
        "configuration": os.getenv("K_CONFIGURATION"),
        "project": os.getenv("GOOGLE_CLOUD_PROJECT"),
        "region": os.getenv("GOOGLE_CLOUD_REGION"),
    }
    cloud_run = {key: value for key, value in cloud_run_keys.items() if value}
    if cloud_run:
        metadata["cloud_run"] = cloud_run

    return metadata


def _health_payload() -> dict[str, object]:
    orchestrator = Orchestrator()
    return {
        "status": "ok",
        "providers": orchestrator.provider_status(),
        "default_models": settings.default_models,
        "deployment": _deployment_metadata(),
    }


@router.get("/healthz", summary="Health check")
async def health_check() -> dict[str, object]:
    """Return a simple health payload for readiness probes."""

    return _health_payload()


@router.get("/api/v1/healthz", summary="Health check (api v1)")
async def health_check_v1() -> dict[str, object]:
    return _health_payload()
