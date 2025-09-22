"""Offline evaluation harness for experimentation."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, List

from ..orchestration.orchestrator import OrchestrationOptions, Orchestrator


async def evaluate_file(path: str, orchestrator: Orchestrator | None = None) -> List[dict[str, str]]:
    """Run orchestration over prompts defined in a JSON or CSV file."""

    orchestrator = orchestrator or Orchestrator()
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(path)

    prompts = _load_prompts(file_path)
    results: List[dict[str, str]] = []
    for prompt in prompts:
        options = OrchestrationOptions(
            accuracy=float(prompt.get("accuracy", 0.8)),
            speed=float(prompt.get("speed", 0.4)),
            creativity=float(prompt.get("creativity", 0.3)),
            cost=float(prompt.get("cost", 0.5)),
            max_tokens=int(prompt.get("max_tokens", 600)),
            json_mode=bool(prompt.get("json_mode", False)),
        )
        result = await orchestrator.run(prompt["query"], options)
        results.append(
            {
                "query": prompt["query"],
                "final_answer": result.final_answer,
                "confidence": f"{result.confidence:.2f}",
            }
        )
    return results


def _load_prompts(path: Path) -> List[dict[str, Any]]:
    if path.suffix.lower() == ".json":
        return json.loads(path.read_text())
    if path.suffix.lower() == ".csv":
        import csv

        with path.open() as handle:
            reader = csv.DictReader(handle)
            return [row for row in reader]
    raise ValueError(f"Unsupported file type: {path.suffix}")
