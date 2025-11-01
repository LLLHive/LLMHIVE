"""Application entrypoint that gracefully supports both runtime layouts.

Historically the project exposed ``app.app:app`` as the FastAPI instance,
while the refactored architecture ships the application code from the
``llmhive/src`` directory.  Local development environments (and some
deployment setups) still import :mod:`main` directly, so this module adds the
``llmhive/src`` directory to :data:`sys.path` when present and then imports
the FastAPI application from the modern location.  If the refactored package
is unavailable we fall back to the legacy import so older deployments keep
working.
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
LLMHIVE_SRC = PROJECT_ROOT / "llmhive" / "src"

if LLMHIVE_SRC.exists():
    path_value = str(LLMHIVE_SRC)
    if path_value not in sys.path:
        sys.path.insert(0, path_value)

try:
    # Preferred import path for the refactored service layout.
    from llmhive.app.main import app
except ModuleNotFoundError:
    # Fall back to the legacy package so older environments remain functional.
    from app.app import app  # type: ignore[assignment]

__all__ = ["app"]
