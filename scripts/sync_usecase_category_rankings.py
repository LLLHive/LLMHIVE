#!/usr/bin/env python3
"""Generate frontend use-case rankings JSON from benchmark_rankings_jan2026.py."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "llmhive" / "src"))

from llmhive.app.knowledge.benchmark_rankings_jan2026 import (  # noqa: E402
    USECASE_TO_BENCHMARK,
    get_all_usecase_benchmark_rankings,
)

OUT = ROOT / "lib" / "marketing" / "usecase-category-rankings.generated.json"


def main() -> None:
    categories = get_all_usecase_benchmark_rankings(top_k=10)
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "benchmark_rankings_jan2026.py::RANKINGS_MAY_2026",
        "description": "Top 10 per UI category, sorted strictly by benchmark score (API-available models only).",
        "benchmark_mapping": {
            slug: bench.value for slug, bench in USECASE_TO_BENCHMARK.items()
        },
        "categories": categories,
    }
    OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUT} ({len(categories)} categories)")


if __name__ == "__main__":
    main()
