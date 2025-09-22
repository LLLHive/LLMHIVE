"""Redaction and incognito style helpers."""
from __future__ import annotations

import re

EMAIL_PATTERN = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_PATTERN = re.compile(r"\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b")
PROVIDER_PATTERN = re.compile(r"\[(?:OpenAI|Google|Anthropic|Azure)[^\]]*\]", re.IGNORECASE)


def redact_pii(text: str) -> str:
    """Replace obvious PII markers with neutral placeholders."""

    text = EMAIL_PATTERN.sub("[redacted-email]", text)
    text = PHONE_PATTERN.sub("[redacted-phone]", text)
    return text


def apply_incognito_style(text: str) -> str:
    """Normalize response style so provider identities are hidden."""

    text = PROVIDER_PATTERN.sub("[expert insight]", text)
    text = text.replace("Local reasoning synthesis", "Expert synthesis")
    if not text.endswith("."):
        text = text.strip() + "."
    return text
