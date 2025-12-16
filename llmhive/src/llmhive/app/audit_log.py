"""Simple audit logging to Firestore."""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

try:
    from google.cloud import firestore  # type: ignore
except Exception:  # pragma: no cover
    firestore = None  # type: ignore

logger = logging.getLogger(__name__)

AUDIT_COLLECTION = "audit_logs"


def _client():
    if firestore is None:
        return None
    try:
        return firestore.Client()
    except Exception as e:  # pragma: no cover
        logger.debug("Audit log client init failed: %s", e)
        return None


def log_audit_event(
    *,
    org_id: Optional[str],
    user_id: Optional[str],
    action: str,
    details: Optional[Dict[str, Any]] = None,
) -> None:
    """Write a lightweight audit event to Firestore."""
    client = _client()
    if client is None:
        return
    try:
        doc = {
            "org_id": org_id,
            "user_id": user_id,
            "action": action,
            "details": details or {},
            "timestamp": firestore.SERVER_TIMESTAMP,  # type: ignore[attr-defined]
        }
        client.collection(AUDIT_COLLECTION).add(doc)
    except Exception as e:  # pragma: no cover
        logger.debug("Failed to log audit event: %s", e)
