#!/usr/bin/env python3
"""Generate frontend use-case rankings JSON from benchmark_rankings_jan2026.py."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "llmhive" / "src"))

from llmhive.app.knowledge.usecase_category_rankings import (  # noqa: E402
    build_category_rankings_json,
)

OUT = ROOT / "lib" / "marketing" / "usecase-category-rankings.generated.json"


def main() -> None:
    OUT.write_text(build_category_rankings_json(), encoding="utf-8")
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
