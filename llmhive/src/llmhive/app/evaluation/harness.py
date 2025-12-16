"""Lightweight evaluation harness for regression and parity checks."""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

from ..models.orchestration import ChatRequest, ChatMetadata
from ..services.orchestrator_adapter import run_orchestration

logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Data models
# -----------------------------------------------------------------------------

@dataclass
class BenchmarkCase:
    name: str
    prompt: str
    expected_answer: Optional[str] = None
    expect_contains: List[str] = field(default_factory=list)
    expect_json: bool = False
    tools_allowed: List[str] = field(default_factory=list)
    history: List[Dict[str, str]] = field(default_factory=list)


@dataclass
class BenchmarkOutcome:
    name: str
    passed: bool
    output: str
    latency_ms: float
    tokens: Any
    notes: List[str] = field(default_factory=list)
    baseline_regression: bool = False
    parity_mismatch: bool = False

    def summary(self) -> str:
        status = "PASS" if self.passed else "FAIL"
        flag = ""
        if self.baseline_regression:
            flag = " (REGRESSION)"
        elif self.parity_mismatch:
            flag = " (PARITY MISMATCH)"
        return f"[{status}] {self.name}{flag} – latency:{self.latency_ms:.1f}ms tokens:{self.tokens}"


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------

def _normalize(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s]", "", text)
    return " ".join(text.split())


def _contains_all(text: str, substrings: List[str]) -> bool:
    lowered = text.lower()
    return all(sub.lower() in lowered for sub in substrings)


def _is_json(text: str) -> bool:
    try:
        json.loads(text)
        return True
    except Exception:
        return False


def _load_cases(path: Path) -> List[BenchmarkCase]:
    data = yaml.safe_load(path.read_text())
    cases: List[BenchmarkCase] = []
    for item in data.get("cases", []):
        cases.append(
            BenchmarkCase(
                name=item["name"],
                prompt=item.get("prompt", ""),
                expected_answer=item.get("expected_answer"),
                expect_contains=item.get("expect_contains", []) or [],
                expect_json=item.get("expect_json", False),
                tools_allowed=item.get("tools_allowed", []) or [],
                history=item.get("history", []) or [],
            )
        )
    return cases


def _evaluate_expectations(output: str, case: BenchmarkCase) -> Tuple[bool, List[str]]:
    notes: List[str] = []
    passed = True

    if case.expected_answer:
        norm_out = _normalize(output)
        norm_exp = _normalize(case.expected_answer)
        if norm_exp not in norm_out:
            passed = False
            notes.append(f"expected_answer missing: '{case.expected_answer}'")

    if case.expect_contains:
        if not _contains_all(output, case.expect_contains):
            passed = False
            notes.append(f"missing substrings: {case.expect_contains}")

    if case.expect_json and not _is_json(output):
        passed = False
        notes.append("output not valid JSON")

    # Numeric exact compare if expected_answer is numeric
    if case.expected_answer and case.expected_answer.isdigit():
        digits = re.findall(r"\d+", output)
        if case.expected_answer not in digits and _normalize(output) != case.expected_answer:
            passed = False
            notes.append("numeric expected_answer mismatch")

    return passed, notes


def _compare_baseline(output: str, baseline: Optional[str]) -> bool:
    """Return True if regression detected."""
    if baseline is None:
        return False
    return _normalize(baseline) not in _normalize(output)


async def _run_single(case: BenchmarkCase, parity: bool = True) -> BenchmarkOutcome:
    """Execute a single case via orchestrator_adapter."""
    request = ChatRequest(
        prompt=case.prompt,
        history=case.history if case.history else None,
        metadata=ChatMetadata(),
    )

    start = time.perf_counter()
    resp = await run_orchestration(request)
    latency_ms = (time.perf_counter() - start) * 1000
    output = getattr(resp, "message", "") or ""

    passed, notes = _evaluate_expectations(output, case)

    parity_mismatch = False
    if parity:
        # For parity we simply re-run a second time to mimic a different surface (UI/API)
        # If outputs diverge meaningfully, flag it.
        resp2 = await run_orchestration(request)
        output2 = getattr(resp2, "message", "") or ""
        if _normalize(output2) not in _normalize(output) and _normalize(output) not in _normalize(output2):
            parity_mismatch = True
            passed = False
            notes.append("UI/API parity mismatch (outputs differ)")

    tokens_used = getattr(resp, "tokens_used", None)
    return BenchmarkOutcome(
        name=case.name,
        passed=passed,
        output=output,
        latency_ms=latency_ms,
        tokens=tokens_used,
        notes=notes,
        parity_mismatch=parity_mismatch,
    )


async def run_benchmarks(
    cases_path: str = str(Path(__file__).parent / "benchmarks.yaml"),
    baseline_path: str = str(Path(__file__).parent / "baseline_results.json"),
    parity_check: bool = True,
) -> List[BenchmarkOutcome]:
    """Run defined benchmarks and return outcomes."""
    cases = _load_cases(Path(cases_path))
    baseline = {}
    if Path(baseline_path).exists():
        try:
            baseline = json.loads(Path(baseline_path).read_text())
        except Exception:
            baseline = {}

    outcomes: List[BenchmarkOutcome] = []
    for case in cases:
        outcome = await _run_single(case, parity=parity_check)
        base_out = baseline.get(case.name)
        if base_out:
            outcome.baseline_regression = _compare_baseline(outcome.output, base_out.get("output"))
            if outcome.baseline_regression:
                outcome.passed = False
                outcome.notes.append("baseline regression detected")
        outcomes.append(outcome)

    return outcomes


def save_results(outcomes: List[BenchmarkOutcome], path: str) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(
            {
                o.name: {
                    "passed": o.passed,
                    "output": o.output,
                    "latency_ms": o.latency_ms,
                    "tokens": o.tokens,
                    "notes": o.notes,
                }
                for o in outcomes
            },
            f,
            indent=2,
        )
    logger.info("Saved benchmark results to %s", path)


async def run_and_print(parity_check: bool = True) -> int:
    """Run benchmarks and print summary. Returns exit code style int."""
    outcomes = await run_benchmarks(parity_check=parity_check)
    for o in outcomes:
        print(o.summary())
        if o.notes:
            for note in o.notes:
                print(f"  - {note}")
    failed = [o for o in outcomes if not o.passed]
    return 1 if failed else 0


if __name__ == "__main__":
    exit_code = asyncio.run(run_and_print(parity_check=os.getenv("PARITY_CHECK", "1") != "0"))
    raise SystemExit(exit_code)
