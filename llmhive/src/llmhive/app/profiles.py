"""
Lightweight user profile store (file-backed JSON) for defaults:
- default_format_style
- default_tone_style
- default_language
- show_confidence

This is a minimal, non-intrusive implementation to apply per-user defaults
without requiring DB migrations. Production deployments can replace this with
their own persistent profile service; keep the interface compatible.
"""
from __future__ import annotations

import json
import os
import threading
from dataclasses import dataclass, asdict
from typing import Optional

PROFILE_PATH = os.getenv("PROFILE_STORE_PATH", ".profiles.json")
_lock = threading.Lock()


@dataclass
class UserProfile:
    user_id: str
    default_format_style: Optional[str] = None
    default_tone_style: Optional[str] = None
    default_language: Optional[str] = None
    show_confidence: Optional[bool] = None


def _load_all() -> dict:
    if not os.path.isfile(PROFILE_PATH):
        return {}
    try:
        with open(PROFILE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_all(data: dict) -> None:
    tmp_path = PROFILE_PATH + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f)
    os.replace(tmp_path, PROFILE_PATH)


def get_profile(user_id: Optional[str]) -> Optional[UserProfile]:
    if not user_id:
        return None
    with _lock:
        data = _load_all()
        raw = data.get(user_id)
        if not raw:
            return None
        return UserProfile(**raw)


def upsert_profile(profile: UserProfile) -> None:
    with _lock:
        data = _load_all()
        data[profile.user_id] = asdict(profile)
        _save_all(data)
