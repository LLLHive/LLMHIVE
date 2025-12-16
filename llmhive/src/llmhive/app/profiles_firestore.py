"""
Firestore-backed user profile store for defaults:
- default_format_style
- default_tone_style
- default_language
- show_confidence

Requires Google Cloud credentials with access to Firestore.
Configure collection via PROFILE_COLLECTION (default: "profiles").
"""
from __future__ import annotations

import os
from dataclasses import dataclass, asdict
from typing import Optional

from google.cloud import firestore  # type: ignore

PROFILE_COLLECTION = os.getenv("PROFILE_COLLECTION", "profiles")


@dataclass
class UserProfile:
    user_id: str
    default_format_style: Optional[str] = None
    default_tone_style: Optional[str] = None
    default_language: Optional[str] = None
    show_confidence: Optional[bool] = None


def _client() -> firestore.Client:
    return firestore.Client()


def get_profile(user_id: Optional[str]) -> Optional[UserProfile]:
    if not user_id:
        return None
    doc_ref = _client().collection(PROFILE_COLLECTION).document(user_id)
    doc = doc_ref.get()
    if not doc.exists:
        return None
    data = doc.to_dict() or {}
    data["user_id"] = user_id
    return UserProfile(**data)


def upsert_profile(profile: UserProfile) -> None:
    doc_ref = _client().collection(PROFILE_COLLECTION).document(profile.user_id)
    doc_ref.set({k: v for k, v in asdict(profile).items() if k != "user_id"})
