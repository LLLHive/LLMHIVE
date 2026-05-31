"""Load generated frontier roster artifacts (from scripts/sync_frontier_surfaces.py)."""
from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).resolve().parent
_PAID_CATALOG_PATH = _DATA_DIR / "frontier_paid_catalog.generated.json"
_REGISTRY_PATH = _DATA_DIR / "frontier_registry.generated.json"
_REPO_ROSTER_PATH = Path(__file__).resolve().parents[5] / "data" / "generated" / "frontier_roster.json"


@lru_cache(maxsize=1)
def load_paid_model_catalog() -> List[Dict[str, Any]]:
    if not _PAID_CATALOG_PATH.is_file():
        logger.warning("Missing generated paid catalog: %s", _PAID_CATALOG_PATH)
        return []
    try:
        payload = json.loads(_PAID_CATALOG_PATH.read_text(encoding="utf-8"))
        catalog = payload.get("paid_catalog") or []
        return sorted(catalog, key=lambda x: int(x.get("rank", 999)))
    except Exception as exc:
        logger.warning("Could not load paid catalog: %s", exc)
        return []


@lru_cache(maxsize=1)
def load_registry_additions() -> List[Dict[str, Any]]:
    if not _REGISTRY_PATH.is_file():
        logger.warning("Missing generated registry additions: %s", _REGISTRY_PATH)
        return []
    try:
        payload = json.loads(_REGISTRY_PATH.read_text(encoding="utf-8"))
        return list(payload.get("registry_additions") or [])
    except Exception as exc:
        logger.warning("Could not load registry additions: %s", exc)
        return []


@lru_cache(maxsize=1)
def load_frontier_roster_source() -> Dict[str, Any]:
    if not _REPO_ROSTER_PATH.is_file():
        return {}
    try:
        return json.loads(_REPO_ROSTER_PATH.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning("Could not load frontier roster source: %s", exc)
        return {}
