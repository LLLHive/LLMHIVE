"""Security and safety helpers for outward facing responses."""
from __future__ import annotations

import re

from ..utils.redact import apply_incognito_style, redact_pii

INTERNAL_MARKER_PATTERN = re.compile(r"<<internal:[^>]+>>", re.IGNORECASE)


def sanitize_output(text: str) -> str:
    """Strip internal markers and apply incognito styling.

    The incognito mode ensures consumers cannot infer which model produced the
    response. Any PII snippets detected by the heuristic redactor are removed.
    """

    cleaned = INTERNAL_MARKER_PATTERN.sub("", text)
    cleaned = redact_pii(cleaned)
    cleaned = apply_incognito_style(cleaned)
    return cleaned.strip()
