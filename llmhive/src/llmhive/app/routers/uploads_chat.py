"""Secure chat document uploads to Google Cloud Storage (optional).

When ``LLMHIVE_CHAT_UPLOAD_BUCKET`` is set and ``google-cloud-storage`` is
available, authenticated clients can POST a PDF (or other binary) here; the
object is stored under ``chat-uploads/{user_id}/…`` and metadata is returned
for inclusion in the chat prompt. The orchestrator does not automatically
fetch the object yet — the Next.js client merges ``gs_uri`` (and optional
short-lived signed URL) into the outbound prompt so the user and model know
where the bytes live.

Environment:
- ``LLMHIVE_CHAT_UPLOAD_BUCKET`` — target bucket name (required for uploads).
- ``GCP_PROJECT_ID`` — optional; inferred from default credentials if omitted.
"""
from __future__ import annotations

import logging
import os
import re
import uuid
from datetime import timedelta
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from ..auth import verify_api_key
from ..billing.access_guard import require_app_access

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["uploads"])

# Hard cap per upload (bytes) — keeps Cloud Run memory predictable.
_MAX_UPLOAD_BYTES = 25 * 1024 * 1024


def _safe_user_segment(user_id: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_-]", "_", user_id.strip())[:200]
    return cleaned or "unknown"


@router.post("/uploads/chat-document")
async def upload_chat_document(
    user_id: str = Form(..., min_length=3, max_length=256),
    file: UploadFile = File(...),
    _auth: str = Depends(verify_api_key),
) -> Dict[str, Any]:
    """Upload one file for chat context; returns GCS location when configured."""
    require_app_access(user_id.strip())

    bucket_name = (os.environ.get("LLMHIVE_CHAT_UPLOAD_BUCKET") or "").strip()
    if not bucket_name:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": "upload_not_configured",
                "message": "Set LLMHIVE_CHAT_UPLOAD_BUCKET on the orchestrator to enable uploads.",
            },
        )

    try:
        from google.cloud import storage  # type: ignore
    except ImportError as exc:  # pragma: no cover - optional dependency path
        logger.error("google-cloud-storage not installed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": "upload_dependency_missing",
                "message": "Install google-cloud-storage on the orchestrator image.",
            },
        ) from exc

    raw = await file.read()
    if len(raw) > _MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail={"error": "file_too_large", "max_bytes": _MAX_UPLOAD_BYTES},
        )
    if len(raw) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "empty_file"},
        )

    orig = (file.filename or "document").strip() or "document"
    ext = os.path.splitext(orig)[1][:32] or ".bin"
    if len(ext) > 32:
        ext = ext[:32]
    object_name = f"chat-uploads/{_safe_user_segment(user_id)}/{uuid.uuid4().hex}{ext}"
    content_type = file.content_type or "application/octet-stream"

    try:
        project = os.environ.get("GCP_PROJECT_ID")
        client = storage.Client(project=project) if project else storage.Client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(object_name)
        blob.upload_from_string(raw, content_type=content_type)
    except Exception as exc:
        logger.exception("GCS upload failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"error": "upload_failed", "message": str(exc)},
        ) from exc

    gs_uri = f"gs://{bucket_name}/{object_name}"
    signed_url: Optional[str] = None
    try:
        signed_url = blob.generate_signed_url(
            version="v4",
            expiration=timedelta(minutes=15),
            method="GET",
        )
    except Exception as exc:
        logger.info("Signed URL not generated (IAM may lack signBlob): %s", exc)

    return {
        "gs_uri": gs_uri,
        "object_path": object_name,
        "bucket": bucket_name,
        "size": len(raw),
        "content_type": content_type,
        "original_filename": orig,
        "signed_read_url": signed_url,
    }
