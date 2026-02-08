#!/usr/bin/env python3
"""
Industry-Standard Benchmark Protocol for LLMHive
=================================================
Benchmarks:
- MMLU (General Reasoning)
- GSM8K (Math)
- HumanEval (Coding)
- MS MARCO (RAG/QA)
- ToolBench (Tool Use) [optional - requires local ToolBench data]

This script is designed for advertising-grade reporting:
- pinned datasets
- seeded sampling
- multi-run aggregation
"""

from __future__ import annotations

import asyncio
import json
import os
import random
import re
import statistics
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import httpx
from datasets import load_dataset

try:
    from human_eval.data import read_problems
    from human_eval.execution import check_correctness
except Exception:
    read_problems = None
    check_correctness = None

LLMHIVE_API_URL = os.getenv(
    "LLMHIVE_API_URL",
    "https://llmhive-orchestrator-792354158895.us-east1.run.app",
)
API_KEY = os.getenv("API_KEY") or os.getenv("LLMHIVE_API_KEY")

if not API_KEY:
    raise ValueError("API_KEY or LLMHIVE_API_KEY environment variable required")


def _get_env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if not value:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _get_env_str(name: str, default: str) -> str:
    value = os.getenv(name)
    return value if value else default


def _get_env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if not value:
        return default
    try:
        return float(value)
    except ValueError:
        return default


def _is_truthy(value: Optional[str]) -> bool:
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "yes", "on"}


NUM_RUNS = _get_env_int("INDUSTRY_BENCH_NUM_RUNS", 3)
BASE_SEED = _get_env_int("INDUSTRY_BENCH_SEED", 42)
REASONING_MODE = _get_env_str("INDUSTRY_BENCH_REASONING_MODE", "deep")
TIER = _get_env_str("INDUSTRY_BENCH_TIER", "elite")
TIMEOUT_SECS = _get_env_int("INDUSTRY_BENCH_TIMEOUT", 180)
PRINT_EVERY = max(1, _get_env_int("INDUSTRY_BENCH_PRINT_EVERY", 5))
BASELINE_JSON_PATH = _get_env_str("INDUSTRY_BENCH_BASELINE_JSON", "")
REGRESSION_TOLERANCE = _get_env_float("INDUSTRY_BENCH_REGRESSION_TOLERANCE", 0.0)
TEMPERATURE = _get_env_float("INDUSTRY_BENCH_TEMPERATURE", -1.0)
TOP_P = _get_env_float("INDUSTRY_BENCH_TOP_P", -1.0)
STRICT_MODE = _is_truthy(os.getenv("INDUSTRY_BENCH_STRICT"))
MSMARCO_EVAL_CMD = _get_env_str("MSMARCO_EVAL_CMD", "")
CHECKPOINT_PATH = _get_env_str(
    "INDUSTRY_BENCH_CHECKPOINT_PATH",
    "benchmark_reports/industry_benchmarks_checkpoint.json",
)
FORCE_RESUME = _is_truthy(os.getenv("INDUSTRY_BENCH_FORCE_RESUME"))
START_AT = _get_env_str("INDUSTRY_BENCH_START_AT", "")
SKIP_CATEGORIES_RAW = _get_env_str("INDUSTRY_BENCH_SKIP_CATEGORIES", "")

SAMPLE_SIZES = {
    "mmlu": _get_env_int("INDUSTRY_BENCH_MMLU_SAMPLES", 100),
    "gsm8k": _get_env_int("INDUSTRY_BENCH_GSM8K_SAMPLES", 100),
    "humaneval": _get_env_int("INDUSTRY_BENCH_HUMANEVAL_SAMPLES", 50),
    "msmarco": _get_env_int("INDUSTRY_BENCH_MSMARCO_SAMPLES", 100),
    "toolbench": _get_env_int("INDUSTRY_BENCH_TOOLBENCH_SAMPLES", 50),
}

TOOLBENCH_DATA_DIR = os.getenv("TOOLBENCH_DATA_DIR")


@dataclass
class RunResult:
    category: str
    dataset: str
    sample_size: int
    correct: int
    attempted: int
    errors: int
    accuracy: float
    avg_latency_ms: int
    avg_cost: float
    total_cost: float
    extra: Dict[str, Any]


def _normalize_text(text: str) -> str:
    text = text.lower()
    text = re.sub(r"\b(a|an|the)\b", " ", text)
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _exact_match(pred: str, answers: List[str]) -> bool:
    pred_norm = _normalize_text(pred)
    return any(pred_norm == _normalize_text(a) for a in answers if a)


def _f1_score(pred: str, answers: List[str]) -> float:
    pred_tokens = _normalize_text(pred).split()
    if not pred_tokens:
        return 0.0
    best = 0.0
    for ans in answers:
        ans_tokens = _normalize_text(ans).split()
        if not ans_tokens:
            continue
        common = set(pred_tokens) & set(ans_tokens)
        if not common:
            continue
        precision = len(common) / len(pred_tokens)
        recall = len(common) / len(ans_tokens)
        score = (2 * precision * recall) / (precision + recall)
        best = max(best, score)
    return best


def _strip_code_fences(text: str) -> str:
    match = re.search(r"```(?:python)?\n(.*?)```", text, re.DOTALL | re.IGNORECASE)
    return match.group(1).strip() if match else text.strip()


def _strip_non_code_trailers(text: str) -> str:
    lines = text.splitlines()
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines:
        line = lines[-1]
        if not line.strip():
            lines.pop()
            continue
        if line.startswith(("def ", "class ", "@", "#")):
            break
        if not line.startswith((" ", "\t")):
            lines.pop()
            continue
        break
    return "\n".join(lines)


def _completion_from_response(problem: Dict[str, Any], response: str) -> str:
    """Extract and format code completion for HumanEval"""
    text = _strip_code_fences(response)
    
    # If response contains the full function, return it
    entry_point = problem.get("entry_point", "")
    if entry_point:
        pattern = re.compile(rf"def\s+{re.escape(entry_point)}\s*\([^)]*\):", re.MULTILINE)
        match = pattern.search(text)
        if match:
            # Found full function definition - use it as-is
            return text.strip() + "\n"
    
    # Otherwise, try to extract just the body
    prompt = problem.get("prompt", "")
    if prompt and prompt in text:
        text = text.split(prompt, 1)[1]

    text = _strip_non_code_trailers(text)
    if not text.strip():
        # Return original prompt + empty implementation as fallback
        return prompt.strip() + "\n    pass\n"

    # Ensure proper indentation for function body
    lines = text.splitlines()
    for line in lines:
        if line.strip():
            if not line.startswith((" ", "\t")):
                lines = [f"    {ln}" if ln.strip() else ln for ln in lines]
            break
    
    # Combine prompt with implementation
    return prompt.strip() + "\n" + "\n".join(lines).rstrip() + "\n"


async def call_llmhive_api(
    prompt: str,
    reasoning_mode: str = REASONING_MODE,
    tier: str = TIER,
    timeout: int = TIMEOUT_SECS,
    orchestration_config: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    async with httpx.AsyncClient(timeout=timeout) as client:
        max_retries = 3
        for attempt in range(max_retries):
            try:
                start_time = time.time()
                payload = {
                    "prompt": prompt,
                    "reasoning_mode": reasoning_mode,
                    "orchestration": orchestration_config or {
                        "accuracy_level": 5,  # Maximum quality
                        "use_deep_consensus": True,
                        "enable_verification": True,
                    },
                }
                if tier:
                    payload["tier"] = tier
                if TEMPERATURE >= 0:
                    payload["temperature"] = TEMPERATURE
                if TOP_P >= 0:
                    payload["top_p"] = TOP_P
                response = await client.post(
                    f"{LLMHIVE_API_URL}/v1/chat",
                    json=payload,
                    headers={
                        "Content-Type": "application/json",
                        "X-API-Key": API_KEY,
                    },
                )
                latency = int((time.time() - start_time) * 1000)
                if response.status_code == 200:
                    data = response.json()
                    return {
                        "success": True,
                        "response": data.get("message", "") or data.get("response", ""),
                        "latency": latency,
                        "cost": data.get("extra", {})
                        .get("cost_tracking", {})
                        .get("total_cost", 0.0),
                    }
                if response.status_code == 429 or response.status_code >= 500:
                    await asyncio.sleep(min(2 ** attempt, 10))
                    continue
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}: {response.text[:200]}",
                    "latency": latency,
                    "cost": 0.0,
                }
            except Exception as e:
                if attempt < max_retries - 1:
                    await asyncio.sleep(min(2 ** attempt, 10))
                    continue
                return {"success": False, "error": str(e), "latency": 0, "cost": 0.0}
    return {"success": False, "error": "Max retries exceeded", "latency": 0, "cost": 0.0}


def _extract_multiple_choice(text: str) -> Optional[str]:
    match = re.search(r"\b([ABCD])\b", text.strip().upper())
    return match.group(1) if match else None


async def evaluate_mmlu(
    seed: int,
    progress: Optional[Dict[str, Any]] = None,
    on_progress: Optional[Callable[[Dict[str, Any]], None]] = None,
) -> RunResult:
    dataset = load_dataset("lighteval/mmlu", "all", split="test")
    selected_indices: Optional[List[int]] = None
    if STRICT_MODE:
        sample_size = len(dataset)
        samples = dataset
    else:
        if progress and progress.get("selected_indices"):
            selected_indices = progress["selected_indices"]
        else:
            sample_size = min(SAMPLE_SIZES["mmlu"], len(dataset))
            # Stratified sampling by subject
            subject_map: Dict[str, List[int]] = {}
            for idx, row in enumerate(dataset):
                subject_map.setdefault(row["subject"], []).append(idx)

            rng = random.Random(seed)
            subjects = list(subject_map.keys())
            rng.shuffle(subjects)
            per_subject = max(1, sample_size // len(subjects))

            selected_indices = []
            for subject in subjects:
                indices = subject_map[subject][:]
                rng.shuffle(indices)
                selected_indices.extend(indices[:per_subject])
                if len(selected_indices) >= sample_size:
                    break
            selected_indices = selected_indices[:sample_size]
        sample_size = min(SAMPLE_SIZES["mmlu"], len(selected_indices))
        selected_indices = selected_indices[:sample_size]
        samples = dataset.select(selected_indices)

    correct = int(progress.get("correct", 0)) if progress else 0
    errors = int(progress.get("errors", 0)) if progress else 0
    total_latency = int(progress.get("total_latency", 0)) if progress else 0
    total_cost = float(progress.get("total_cost", 0.0)) if progress else 0.0
    error_samples: List[str] = list(progress.get("error_samples", [])) if progress else []
    start_index = int(progress.get("index", 0)) if progress else 0

    print(f"→ MMLU: {sample_size} samples (seed={seed})", flush=True)
    for i, item in enumerate(samples, start=1):
        if i <= start_index:
            continue
        question = item["question"]
        choices = item["choices"]
        correct_answer = item["answer"]
        correct_letter = (
            correct_answer
            if isinstance(correct_answer, str)
            else ["A", "B", "C", "D"][correct_answer]
        )

        prompt = (
            "Answer this multiple-choice question. Provide ONLY the letter (A, B, C, or D).\n\n"
            f"Question: {question}\n\n"
            f"A) {choices[0]}\n"
            f"B) {choices[1]}\n"
            f"C) {choices[2]}\n"
            f"D) {choices[3]}\n\n"
            "Answer:"
        )
        if i == 1 or i % PRINT_EVERY == 0:
            print(f"  MMLU progress: {i}/{sample_size}", flush=True)
        result = await call_llmhive_api(prompt)
        if result["success"]:
            predicted = _extract_multiple_choice(result["response"])
            if predicted == correct_letter:
                correct += 1
            total_latency += result["latency"]
            total_cost += result["cost"]
        else:
            errors += 1
            if len(error_samples) < 3:
                error_samples.append(result.get("error", "unknown error")[:200])

        if on_progress:
            on_progress(
                {
                    "index": i,
                    "correct": correct,
                    "errors": errors,
                    "total_latency": total_latency,
                    "total_cost": total_cost,
                    "error_samples": error_samples,
                    "selected_indices": selected_indices
                    if not STRICT_MODE
                    else None,
                }
            )

    attempted = sample_size - errors
    accuracy = (correct / attempted * 100) if attempted > 0 else 0
    return RunResult(
        category="General Reasoning",
        dataset="MMLU (lighteval/mmlu)",
        sample_size=sample_size,
        correct=correct,
        attempted=attempted,
        errors=errors,
        accuracy=round(accuracy, 2),
        avg_latency_ms=int(total_latency / attempted) if attempted else 0,
        avg_cost=round(total_cost / attempted, 6) if attempted else 0.0,
        total_cost=round(total_cost, 4),
        extra={"seed": seed, "error_samples": error_samples},
    )


def _extract_gsm8k_answer(answer_text: str) -> Optional[float]:
    match = re.search(r"####\s*(-?[\d,]+\.?\d*)", answer_text)
    if match:
        value = match.group(1).replace(",", "").strip()
        if value and value not in {"-", ".", "-."}:
            return float(value)
    numbers = re.findall(r"-?[\d,]+\.?\d*", answer_text)
    if numbers:
        for raw in reversed(numbers):
            value = raw.replace(",", "").strip()
            if not value or value in {"-", ".", "-."}:
                continue
            try:
                return float(value)
            except ValueError:
                continue
    return None


def _extract_ranked_ids(response: str, valid_ids: List[int]) -> List[int]:
    found = []
    for match in re.findall(r"\b\d+\b", response):
        try:
            value = int(match)
        except ValueError:
            continue
        if value in valid_ids and value not in found:
            found.append(value)
    return found


async def evaluate_gsm8k(
    seed: int,
    progress: Optional[Dict[str, Any]] = None,
    on_progress: Optional[Callable[[Dict[str, Any]], None]] = None,
) -> RunResult:
    dataset = load_dataset("openai/gsm8k", "main", split="test")
    selected_indices: Optional[List[int]] = None
    if STRICT_MODE:
        sample_size = len(dataset)
        samples = dataset
    else:
        if progress and progress.get("selected_indices"):
            selected_indices = progress["selected_indices"]
        else:
            sample_size = min(SAMPLE_SIZES["gsm8k"], len(dataset))
            indices = list(range(len(dataset)))
            random.Random(seed).shuffle(indices)
            selected_indices = indices[:sample_size]
        sample_size = min(SAMPLE_SIZES["gsm8k"], len(selected_indices))
        selected_indices = selected_indices[:sample_size]
        samples = dataset.select(selected_indices)

    correct = int(progress.get("correct", 0)) if progress else 0
    errors = int(progress.get("errors", 0)) if progress else 0
    total_latency = int(progress.get("total_latency", 0)) if progress else 0
    total_cost = float(progress.get("total_cost", 0.0)) if progress else 0.0
    error_samples: List[str] = list(progress.get("error_samples", [])) if progress else []
    start_index = int(progress.get("index", 0)) if progress else 0

    print(f"→ GSM8K: {sample_size} samples (seed={seed})", flush=True)
    for i, item in enumerate(samples, start=1):
        if i <= start_index:
            continue
        question = item["question"]
        answer_text = item["answer"]
        correct_answer = _extract_gsm8k_answer(answer_text)

        prompt = (
            "Solve this math problem. Show your work and provide the final answer after ####.\n\n"
            f"{question}\n\nSolution:"
        )
        if i == 1 or i % PRINT_EVERY == 0:
            print(f"  GSM8K progress: {i}/{sample_size}", flush=True)
        result = await call_llmhive_api(prompt)
        if result["success"]:
            predicted = _extract_gsm8k_answer(result["response"] or "")
            if predicted is not None and correct_answer is not None:
                if abs(predicted - correct_answer) < 0.01:
                    correct += 1
            total_latency += result["latency"]
            total_cost += result["cost"]
        else:
            errors += 1
            if len(error_samples) < 3:
                error_samples.append(result.get("error", "unknown error")[:200])

        if on_progress:
            on_progress(
                {
                    "index": i,
                    "correct": correct,
                    "errors": errors,
                    "total_latency": total_latency,
                    "total_cost": total_cost,
                    "error_samples": error_samples,
                    "selected_indices": selected_indices
                    if not STRICT_MODE
                    else None,
                }
            )

    attempted = sample_size - errors
    accuracy = (correct / attempted * 100) if attempted > 0 else 0
    return RunResult(
        category="Math",
        dataset="GSM8K (openai/gsm8k)",
        sample_size=sample_size,
        correct=correct,
        attempted=attempted,
        errors=errors,
        accuracy=round(accuracy, 2),
        avg_latency_ms=int(total_latency / attempted) if attempted else 0,
        avg_cost=round(total_cost / attempted, 6) if attempted else 0.0,
        total_cost=round(total_cost, 4),
        extra={"seed": seed, "error_samples": error_samples},
    )


async def evaluate_humaneval(
    seed: int,
    progress: Optional[Dict[str, Any]] = None,
    on_progress: Optional[Callable[[Dict[str, Any]], None]] = None,
) -> RunResult:
    if not read_problems or not check_correctness:
        return RunResult(
            category="Coding",
            dataset="HumanEval (openai/human_eval)",
            sample_size=0,
            correct=0,
            attempted=0,
            errors=1,
            accuracy=0.0,
            avg_latency_ms=0,
            avg_cost=0.0,
            total_cost=0.0,
            extra={"error": "human-eval not installed"},
        )

    problems = read_problems()
    problem_ids = list(problems.keys())
    rng = random.Random(seed)
    rng.shuffle(problem_ids)
    if progress and progress.get("sample_ids"):
        sample_ids = progress["sample_ids"]
    elif STRICT_MODE:
        sample_ids = problem_ids
    else:
        sample_ids = problem_ids[: min(SAMPLE_SIZES["humaneval"], len(problem_ids))]

    correct = int(progress.get("correct", 0)) if progress else 0
    errors = int(progress.get("errors", 0)) if progress else 0
    total_latency = int(progress.get("total_latency", 0)) if progress else 0
    total_cost = float(progress.get("total_cost", 0.0)) if progress else 0.0
    error_samples: List[str] = list(progress.get("error_samples", [])) if progress else []
    start_index = int(progress.get("index", 0)) if progress else 0

    print(f"→ HumanEval: {len(sample_ids)} samples (seed={seed})", flush=True)
    for i, task_id in enumerate(sample_ids, start=1):
        if i <= start_index:
            continue
        problem = problems[task_id]
        prompt = (
            "Complete this Python function. Return ONLY the code implementation, no explanations or markdown.\n\n"
            f"{problem['prompt']}\n\nImplementation:"
        )
        if i == 1 or i % PRINT_EVERY == 0:
            print(f"  HumanEval progress: {i}/{len(sample_ids)}", flush=True)
        result = await call_llmhive_api(prompt, timeout=TIMEOUT_SECS)
        if result["success"]:
            completion = _completion_from_response(problem, result["response"])

            try:
                check_result = check_correctness(
                    problem,
                    completion,
                    timeout=5.0,
                    completion_id=i,
                )
                is_correct = (
                    check_result.get("passed", False)
                    if isinstance(check_result, dict)
                    else False
                )
                if is_correct:
                    correct += 1
                total_latency += result["latency"]
                total_cost += result["cost"]
            except Exception:
                errors += 1
                if len(error_samples) < 3:
                    error_samples.append("human-eval execution error")
        else:
            errors += 1
            if len(error_samples) < 3:
                error_samples.append(result.get("error", "unknown error")[:200])

        if on_progress:
            on_progress(
                {
                    "index": i,
                    "correct": correct,
                    "errors": errors,
                    "total_latency": total_latency,
                    "total_cost": total_cost,
                    "error_samples": error_samples,
                    "sample_ids": sample_ids,
                }
            )

    attempted = len(sample_ids) - errors
    accuracy = (correct / attempted * 100) if attempted > 0 else 0
    return RunResult(
        category="Coding",
        dataset="HumanEval (openai/human_eval)",
        sample_size=len(sample_ids),
        correct=correct,
        attempted=attempted,
        errors=errors,
        accuracy=round(accuracy, 2),
        avg_latency_ms=int(total_latency / attempted) if attempted else 0,
        avg_cost=round(total_cost / attempted, 6) if attempted else 0.0,
        total_cost=round(total_cost, 4),
        extra={"seed": seed, "error_samples": error_samples},
    )


async def evaluate_msmarco(
    seed: int,
    progress: Optional[Dict[str, Any]] = None,
    on_progress: Optional[Callable[[Dict[str, Any]], None]] = None,
) -> RunResult:
    dataset = load_dataset("microsoft/ms_marco", "v1.1", split="validation")
    selected_indices: Optional[List[int]] = None
    if STRICT_MODE:
        sample_size = len(dataset)
        samples = dataset
    else:
        if progress and progress.get("selected_indices"):
            selected_indices = progress["selected_indices"]
        else:
            sample_size = min(SAMPLE_SIZES["msmarco"], len(dataset))
            indices = list(range(len(dataset)))
            random.Random(seed).shuffle(indices)
            selected_indices = indices[:sample_size]
        sample_size = min(SAMPLE_SIZES["msmarco"], len(selected_indices))
        selected_indices = selected_indices[:sample_size]
        samples = dataset.select(selected_indices)

    correct = int(progress.get("correct", 0)) if progress else 0
    errors = int(progress.get("errors", 0)) if progress else 0
    total_latency = int(progress.get("total_latency", 0)) if progress else 0
    total_cost = float(progress.get("total_cost", 0.0)) if progress else 0.0
    em_scores = list(progress.get("em_scores", [])) if progress else []
    f1_scores = list(progress.get("f1_scores", [])) if progress else []
    error_samples: List[str] = list(progress.get("error_samples", [])) if progress else []
    start_index = int(progress.get("index", 0)) if progress else 0

    ref_lines: List[str] = list(progress.get("ref_lines", [])) if progress else []
    cand_lines: List[str] = list(progress.get("cand_lines", [])) if progress else []

    print(f"→ MS MARCO: {sample_size} samples (seed={seed})", flush=True)
    for i, item in enumerate(samples, start=1):
        if i <= start_index:
            continue
        query = item["query"]
        passages = item["passages"]
        answers = item.get("answers", []) or item.get("wellFormedAnswers", [])
        passage_texts = passages.get("passage_text", [])
        is_selected = passages.get("is_selected", [])
        passage_ids = passages.get("passage_id", [])

        if not passage_ids:
            passage_ids = list(range(1, len(passage_texts) + 1))

        if STRICT_MODE:
            qid = item.get("query_id", i)
            relevant_ids = [
                pid for pid, sel in zip(passage_ids, is_selected) if sel
            ]
            for pid in relevant_ids:
                ref_lines.append(f"{qid}\t0\t{pid}")

            passages_block = "\n".join(
                f"[{pid}] {text}" for pid, text in zip(passage_ids, passage_texts)
            )
            prompt = (
                "Rank the passage IDs by relevance to the query. "
                "Return ONLY a comma-separated list of passage IDs ordered best to worst.\n\n"
                f"Query: {query}\n\nPassages:\n{passages_block}\n\nRanked IDs:"
            )
        else:
            selected_passages = [
                p for p, sel in zip(passage_texts, is_selected) if sel
            ] or passage_texts[:3]
            context = "\n\n".join(selected_passages[:3])
            prompt = (
                "Answer the question using ONLY the provided passages.\n\n"
                f"Passages:\n{context}\n\nQuestion: {query}\n\nAnswer:"
            )

        if i == 1 or i % PRINT_EVERY == 0:
            print(f"  MS MARCO progress: {i}/{sample_size}", flush=True)
        result = await call_llmhive_api(prompt)
        if result["success"]:
            response = result["response"]
            if STRICT_MODE:
                ranked = _extract_ranked_ids(response, passage_ids)
                if not ranked:
                    ranked = passage_ids[:10]
                for rank, pid in enumerate(ranked[:10], start=1):
                    cand_lines.append(f"{qid}\t{pid}\t{rank}")
            else:
                is_em = _exact_match(response, answers)
                em_scores.append(1.0 if is_em else 0.0)
                f1_scores.append(_f1_score(response, answers))
                if is_em:
                    correct += 1
            total_latency += result["latency"]
            total_cost += result["cost"]
        else:
            errors += 1
            if len(error_samples) < 3:
                error_samples.append(result.get("error", "unknown error")[:200])

        if on_progress:
            on_progress(
                {
                    "index": i,
                    "correct": correct,
                    "errors": errors,
                    "total_latency": total_latency,
                    "total_cost": total_cost,
                    "error_samples": error_samples,
                    "em_scores": em_scores,
                    "f1_scores": f1_scores,
                    "ref_lines": ref_lines,
                    "cand_lines": cand_lines,
                    "selected_indices": selected_indices
                    if not STRICT_MODE
                    else None,
                }
            )

    attempted = sample_size - errors
    accuracy = (correct / attempted * 100) if attempted > 0 else 0
    avg_f1 = statistics.mean(f1_scores) * 100 if f1_scores else 0.0
    external_eval_used = False
    mrr_at_10 = 0.0

    if STRICT_MODE:
        import shlex
        import subprocess
        import tempfile

        with tempfile.TemporaryDirectory() as temp_dir:
            reference_path = Path(temp_dir) / "msmarco_reference.tsv"
            candidate_path = Path(temp_dir) / "msmarco_candidate.tsv"
            output_path = Path(temp_dir) / "msmarco_eval_output.txt"

            reference_path.write_text("\n".join(ref_lines), encoding="utf-8")
            candidate_path.write_text("\n".join(cand_lines), encoding="utf-8")

            if not MSMARCO_EVAL_CMD:
                # Use built-in MRR@10 calculation
                relevant_by_query = {}
                for line in ref_lines:
                    parts = line.split('\t')
                    if len(parts) >= 3:
                        qid, _, pid = parts[0], parts[1], parts[2]
                        if qid not in relevant_by_query:
                            relevant_by_query[qid] = []
                        relevant_by_query[qid].append(int(pid))
                
                mrr_sum = 0.0
                for line in cand_lines:
                    parts = line.split('\t')
                    if len(parts) >= 3:
                        qid, pid, rank = parts[0], int(parts[1]), int(parts[2])
                        if qid in relevant_by_query and pid in relevant_by_query[qid]:
                            if rank <= 10:
                                mrr_sum += 1.0 / rank
                                break
                
                mrr_at_10 = (mrr_sum / len(relevant_by_query)) if relevant_by_query else 0.0
                accuracy = mrr_at_10 * 100
                return RunResult(
                    category="RAG",
                    dataset="MS MARCO (microsoft/ms_marco v1.1)",
                    sample_size=sample_size,
                    correct=int(mrr_sum),
                    attempted=attempted,
                    errors=errors,
                    accuracy=round(accuracy, 2),
                    avg_latency_ms=int(total_latency / attempted) if attempted > 0 else 0,
                    avg_cost=round(total_cost / attempted, 6) if attempted > 0 else 0.0,
                    total_cost=round(total_cost, 4),
                    extra={
                        "seed": seed,
                        "avg_f1": 0.0,
                        "mrr_at_10": round(mrr_at_10, 4),
                        "error_samples": error_samples,
                        "msmarco_eval": "builtin"
                    },
                )

            command = MSMARCO_EVAL_CMD.format(
                reference_path=str(reference_path),
                candidate_path=str(candidate_path),
                output_path=str(output_path),
                seed=seed,
            )
            try:
                completed = subprocess.run(
                    shlex.split(command),
                    check=True,
                    timeout=TIMEOUT_SECS * 10,
                    capture_output=True,
                    text=True,
                )
                output_text = completed.stdout.strip()
                if output_path.exists():
                    output_text = output_path.read_text().strip()
                match = re.search(r"MRR @10\s*:\s*([0-9.]+)", output_text)
                if not match:
                    raise ValueError("MS MARCO eval output missing MRR @10")
                mrr_at_10 = float(match.group(1))
                accuracy = mrr_at_10 * 100
                external_eval_used = True
            except Exception as exc:
                return RunResult(
                    category="RAG",
                    dataset="MS MARCO (microsoft/ms_marco v1.1) - ERROR",
                    sample_size=sample_size,
                    correct=0,
                    attempted=0,
                    errors=1,
                    accuracy=0.0,
                    avg_latency_ms=0,
                    avg_cost=0.0,
                    total_cost=0.0,
                    extra={"error": f"MS MARCO eval failed: {exc}"},
                )

    return RunResult(
        category="RAG",
        dataset="MS MARCO (microsoft/ms_marco v1.1)",
        sample_size=sample_size,
        correct=correct,
        attempted=attempted,
        errors=errors,
        accuracy=round(accuracy, 2),
        avg_latency_ms=int(total_latency / attempted) if attempted else 0,
        avg_cost=round(total_cost / attempted, 6) if attempted else 0.0,
        total_cost=round(total_cost, 4),
        extra={
            "seed": seed,
            "avg_f1": round(avg_f1, 2),
            "mrr_at_10": round(mrr_at_10, 4),
            "error_samples": error_samples,
            "msmarco_eval": "external" if external_eval_used else "proxy",
        },
    )


async def evaluate_toolbench(
    seed: int,
    progress: Optional[Dict[str, Any]] = None,
    on_progress: Optional[Callable[[Dict[str, Any]], None]] = None,
) -> RunResult:
    if not TOOLBENCH_DATA_DIR:
        return RunResult(
            category="Tool Use",
            dataset="ToolBench (OpenBMB) - SKIPPED",
            sample_size=0,
            correct=0,
            attempted=0,
            errors=1,
            accuracy=0.0,
            avg_latency_ms=0,
            avg_cost=0.0,
            total_cost=0.0,
            extra={"error": "TOOLBENCH_DATA_DIR not set"},
        )

    toolbench_cmd = os.getenv("TOOLBENCH_EVAL_CMD")
    if toolbench_cmd:
        import shlex
        import subprocess
        import tempfile

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "toolbench_eval.json"
            command = toolbench_cmd.format(
                data_dir=TOOLBENCH_DATA_DIR,
                output_path=str(output_path),
                seed=seed,
            )
            try:
                subprocess.run(
                    shlex.split(command),
                    check=True,
                    timeout=TIMEOUT_SECS * 5,
                )
                if output_path.exists():
                    payload = json.loads(output_path.read_text())
                    accuracy = payload.get("accuracy") or payload.get("success_rate")
                    if accuracy is None:
                        raise ValueError("ToolEval output missing accuracy/success_rate")
                    avg_latency = int(payload.get("avg_latency_ms", 0))
                    avg_cost = float(payload.get("avg_cost", 0.0))
                    attempted = int(payload.get("attempted", 0))
                    correct = int(payload.get("correct", 0))
                    errors = int(payload.get("errors", 0))
                    sample_size = attempted if attempted > 0 else SAMPLE_SIZES["toolbench"]
                    return RunResult(
                        category="Tool Use",
                        dataset="ToolBench (OpenBMB)",
                        sample_size=sample_size,
                        correct=correct,
                        attempted=attempted,
                        errors=errors,
                        accuracy=round(float(accuracy), 2),
                        avg_latency_ms=avg_latency,
                        avg_cost=round(avg_cost, 6),
                        total_cost=round(avg_cost * attempted, 4),
                        extra={"seed": seed, "toolbench_eval": "external"},
                    )
            except Exception as exc:
                return RunResult(
                    category="Tool Use",
                    dataset="ToolBench (OpenBMB) - ERROR",
                    sample_size=0,
                    correct=0,
                    attempted=0,
                    errors=1,
                    accuracy=0.0,
                    avg_latency_ms=0,
                    avg_cost=0.0,
                    total_cost=0.0,
                    extra={"error": f"ToolEval failed: {exc}"},
                )

    # Placeholder: ToolBench official evaluation requires ToolEval and tool environment.
    # We mark as skipped unless user provides full ToolBench setup or TOOLBENCH_EVAL_CMD.
    return RunResult(
        category="Tool Use",
        dataset="ToolBench (OpenBMB) - REQUIRES ToolEval",
        sample_size=0,
        correct=0,
        attempted=0,
        errors=1,
        accuracy=0.0,
        avg_latency_ms=0,
        avg_cost=0.0,
        total_cost=0.0,
        extra={"error": "ToolEval not implemented in this script"},
    )


def _aggregate_runs(results: List[RunResult]) -> Dict[str, Any]:
    accuracies = [r.accuracy for r in results]
    avg_accuracy = statistics.mean(accuracies) if accuracies else 0.0
    std_accuracy = statistics.pstdev(accuracies) if len(accuracies) > 1 else 0.0
    total_cost = sum(r.total_cost for r in results)
    total_attempted = sum(r.attempted for r in results)
    avg_cost = total_cost / total_attempted if total_attempted > 0 else 0.0
    return {
        "avg_accuracy": round(avg_accuracy, 2),
        "std_accuracy": round(std_accuracy, 2),
        "runs": [r.__dict__ for r in results],
        "total_cost": round(total_cost, 4),
        "avg_cost": round(avg_cost, 6),
    }


def _checkpoint_config() -> Dict[str, Any]:
    return {
        "num_runs": NUM_RUNS,
        "base_seed": BASE_SEED,
        "sample_sizes": SAMPLE_SIZES,
        "temperature": TEMPERATURE if TEMPERATURE >= 0 else None,
        "top_p": TOP_P if TOP_P >= 0 else None,
        "tier": TIER,
        "reasoning_mode": REASONING_MODE,
        "strict_mode": STRICT_MODE,
        "toolbench_eval_cmd_set": bool(os.getenv("TOOLBENCH_EVAL_CMD")),
        "msmarco_eval_cmd_set": bool(MSMARCO_EVAL_CMD),
        "start_at": START_AT,
        "skip_categories": SKIP_CATEGORIES_RAW,
    }


def _load_checkpoint() -> Optional[Dict[str, Any]]:
    path = Path(CHECKPOINT_PATH)
    if not path.exists():
        return None
    payload = json.loads(path.read_text())
    if not FORCE_RESUME:
        current = _checkpoint_config()
        saved = payload.get("config", {})
        if saved and saved != current:
            raise RuntimeError(
                "Checkpoint config mismatch. "
                "Delete checkpoint or set INDUSTRY_BENCH_FORCE_RESUME=1."
            )
    return payload


def _save_checkpoint(payload: Dict[str, Any]) -> None:
    path = Path(CHECKPOINT_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2))


def _normalize_skip_list() -> List[str]:
    if not SKIP_CATEGORIES_RAW:
        return []
    tokens = [t.strip().lower() for t in SKIP_CATEGORIES_RAW.split(",") if t.strip()]
    mapping = {
        "mmlu": "general_reasoning",
        "gsm8k": "math",
        "humaneval": "coding",
        "msmarco": "rag",
        "toolbench": "tool_use",
    }
    normalized = []
    for token in tokens:
        normalized.append(mapping.get(token, token))
    return normalized


def _categories_to_run() -> List[str]:
    order = ["general_reasoning", "math", "coding", "rag", "tool_use"]
    skip = set(_normalize_skip_list())
    start_at = START_AT.strip().lower()
    if start_at:
        mapping = {
            "mmlu": "general_reasoning",
            "gsm8k": "math",
            "humaneval": "coding",
            "msmarco": "rag",
            "toolbench": "tool_use",
        }
        start_key = mapping.get(start_at, start_at)
        if start_key in order:
            start_index = order.index(start_key)
            skip.update(order[:start_index])
    return [key for key in order if key not in skip]


async def run_all() -> Dict[str, Any]:
    all_results: Dict[str, List[RunResult]] = {
        "general_reasoning": [],
        "math": [],
        "coding": [],
        "rag": [],
        "tool_use": [],
    }

    checkpoint = _load_checkpoint()
    checkpoint_runs = checkpoint.get("runs", []) if checkpoint else []
    if checkpoint is None:
        checkpoint = {"config": _checkpoint_config(), "runs": []}

    for run_idx in range(NUM_RUNS):
        seed = BASE_SEED + run_idx
        print(f"\n=== Run {run_idx + 1}/{NUM_RUNS} (seed={seed}) ===", flush=True)

        run_snapshot = (
            checkpoint_runs[run_idx] if run_idx < len(checkpoint_runs) else {}
        )
        if run_idx >= len(checkpoint_runs):
            checkpoint_runs.append({"seed": seed, "results": {}})
            run_snapshot = checkpoint_runs[run_idx]

        categories_to_run = _categories_to_run()
        for key, evaluator in [
            ("general_reasoning", evaluate_mmlu),
            ("math", evaluate_gsm8k),
            ("coding", evaluate_humaneval),
            ("rag", evaluate_msmarco),
            ("tool_use", evaluate_toolbench),
        ]:
            cached = run_snapshot.get("results", {}).get(key)
            if key not in categories_to_run:
                if cached:
                    all_results[key].append(RunResult(**cached))
                continue
            if cached:
                all_results[key].append(RunResult(**cached))
                continue
            progress = run_snapshot.get("progress", {}).get(key)
            def _on_progress(data: Dict[str, Any], k: str = key) -> None:
                run_snapshot.setdefault("progress", {})[k] = data
                checkpoint["runs"] = checkpoint_runs
                _save_checkpoint(checkpoint)

            result = await evaluator(
                seed,
                progress=progress,
                on_progress=_on_progress,
            )
            all_results[key].append(result)
            run_snapshot.setdefault("results", {})[key] = result.__dict__
            checkpoint["runs"] = checkpoint_runs
            _save_checkpoint(checkpoint)

    aggregated = {
        "general_reasoning": _aggregate_runs(all_results["general_reasoning"]),
        "math": _aggregate_runs(all_results["math"]),
        "coding": _aggregate_runs(all_results["coding"]),
        "rag": _aggregate_runs(all_results["rag"]),
        "tool_use": _aggregate_runs(all_results["tool_use"]),
    }

    return {
        "timestamp": datetime.now().isoformat(),
        "tier": TIER,
        "reasoning_mode": REASONING_MODE,
        "config": {
            "num_runs": NUM_RUNS,
            "base_seed": BASE_SEED,
            "sample_sizes": SAMPLE_SIZES,
            "temperature": TEMPERATURE if TEMPERATURE >= 0 else None,
            "top_p": TOP_P if TOP_P >= 0 else None,
            "strict_mode": STRICT_MODE,
            "msmarco_eval_cmd_set": bool(MSMARCO_EVAL_CMD),
        },
        "results": aggregated,
    }


def generate_report(payload: Dict[str, Any]) -> str:
    results = payload["results"]
    lines = [
        "# LLMHive Industry Benchmark Report",
        f"**Timestamp:** {payload['timestamp']}",
        f"**Tier:** {payload['tier']}",
        f"**Reasoning Mode:** {payload['reasoning_mode']}",
        f"**Strict Mode:** {'ON' if payload['config'].get('strict_mode') else 'OFF'}",
        "",
        "## Category Summary",
        "| Category | Avg Accuracy | Std Dev | Avg Cost/Attempt | Dataset |",
        "|----------|--------------|---------|------------------|---------|",
    ]

    def add_row(key: str, label: str, dataset: str):
        r = results[key]
        lines.append(
            f"| {label} | {r['avg_accuracy']:.2f}% | {r['std_accuracy']:.2f}% | "
            f"${r['avg_cost']:.6f} | {dataset} |"
        )

    add_row("general_reasoning", "General Reasoning", "MMLU")
    add_row("math", "Math", "GSM8K")
    add_row("coding", "Coding", "HumanEval")
    add_row("rag", "RAG", "MS MARCO")
    add_row("tool_use", "Tool Use", "ToolBench")

    lines.append("\n## Detailed Runs")
    for key, label in [
        ("general_reasoning", "General Reasoning"),
        ("math", "Math"),
        ("coding", "Coding"),
        ("rag", "RAG"),
        ("tool_use", "Tool Use"),
    ]:
        lines.append(f"### {label}")
        runs = results[key]["runs"]
        lines.append("| Run | Accuracy | Attempted | Errors | Avg Latency | Total Cost |")
        lines.append("|-----|----------|-----------|--------|-------------|------------|")
        for idx, run in enumerate(runs, start=1):
            lines.append(
                f"| {idx} | {run['accuracy']:.2f}% | {run['attempted']} | "
                f"{run['errors']} | {run['avg_latency_ms']}ms | ${run['total_cost']:.4f} |"
            )
        if key == "rag":
            f1s = [r.get("extra", {}).get("avg_f1", 0) for r in runs if r.get("extra")]
            mrrs = [
                r.get("extra", {}).get("mrr_at_10", 0)
                for r in runs
                if r.get("extra")
            ]
            if f1s:
                lines.append(f"- Avg F1 across runs: {statistics.mean(f1s):.2f}%")
            if mrrs:
                lines.append(f"- Avg MRR@10 across runs: {statistics.mean(mrrs):.4f}")
        if key == "tool_use":
            errors = [r.get("extra", {}).get("error") for r in runs if r.get("extra")]
            for err in set([e for e in errors if e]):
                lines.append(f"- ToolBench note: {err}")

        lines.append("")

    return "\n".join(lines)


def _assert_no_regressions(payload: Dict[str, Any]) -> None:
    if not BASELINE_JSON_PATH:
        return
    baseline_path = Path(BASELINE_JSON_PATH)
    if not baseline_path.exists():
        raise FileNotFoundError(f"Baseline JSON not found: {baseline_path}")

    baseline = json.loads(baseline_path.read_text())
    baseline_results = baseline.get("results", {})
    current_results = payload.get("results", {})

    regressions = []
    invalid_runs = []
    skip_set = set(_normalize_skip_list())
    for key, current in current_results.items():
        if key in skip_set:
            continue
        baseline_entry = baseline_results.get(key, {})
        baseline_acc = baseline_entry.get("avg_accuracy")
        current_acc = current.get("avg_accuracy")
        attempted = sum(r.get("attempted", 0) for r in current.get("runs", []))
        errors = sum(r.get("errors", 0) for r in current.get("runs", []))
        if attempted == 0:
            error_samples = []
            for run in current.get("runs", []):
                samples = run.get("extra", {}).get("error_samples") or []
                error_samples.extend(samples)
            sample_text = f" Examples: {error_samples[:3]}" if error_samples else ""
            if key == "tool_use":
                # ToolBench may be intentionally skipped when ToolEval isn't configured.
                continue
            invalid_runs.append(
                f"{key}: no successful attempts (errors={errors}).{sample_text}"
            )
            continue
        if baseline_acc is None or current_acc is None:
            continue
        if current_acc + REGRESSION_TOLERANCE < baseline_acc:
            regressions.append(
                f"{key}: {current_acc:.2f}% < {baseline_acc:.2f}%"
            )

        if key == "rag":
            baseline_runs = baseline_entry.get("runs", [])
            current_runs = current.get("runs", [])
            baseline_f1 = statistics.mean(
                [r.get("extra", {}).get("avg_f1", 0) for r in baseline_runs]
            ) if baseline_runs else None
            current_f1 = statistics.mean(
                [r.get("extra", {}).get("avg_f1", 0) for r in current_runs]
            ) if current_runs else None
            if baseline_f1 is not None and current_f1 is not None:
                if current_f1 + REGRESSION_TOLERANCE < baseline_f1:
                    regressions.append(
                        f"rag_f1: {current_f1:.2f}% < {baseline_f1:.2f}%"
                    )

    if regressions:
        raise RuntimeError(
            "Regression guard failed:\n- " + "\n- ".join(regressions)
        )
    if invalid_runs:
        raise RuntimeError(
            "Regression guard blocked due to invalid runs:\n- "
            + "\n- ".join(invalid_runs)
        )


def _preflight_checks() -> None:
    if not STRICT_MODE:
        return
    missing = []
    if TEMPERATURE != 0.0 or TOP_P != 1.0:
        missing.append(
            "deterministic decoding required: set INDUSTRY_BENCH_TEMPERATURE=0 "
            "and INDUSTRY_BENCH_TOP_P=1.0"
        )
    if not TOOLBENCH_DATA_DIR:
        missing.append("TOOLBENCH_DATA_DIR is required")
    if not os.getenv("TOOLBENCH_EVAL_CMD"):
        missing.append("TOOLBENCH_EVAL_CMD is required")
    if not MSMARCO_EVAL_CMD:
        missing.append("MSMARCO_EVAL_CMD is required")
    if MSMARCO_EVAL_CMD and (
        "{reference_path}" not in MSMARCO_EVAL_CMD
        or "{candidate_path}" not in MSMARCO_EVAL_CMD
    ):
        missing.append(
            "MSMARCO_EVAL_CMD must include {reference_path} and {candidate_path}"
        )
    if not read_problems or not check_correctness:
        missing.append("human-eval package is required")
    if missing:
        raise RuntimeError(
            "Strict mode preflight failed:\n- " + "\n- ".join(missing)
        )


async def main():
    _preflight_checks()
    payload = await run_all()
    _assert_no_regressions(payload)
    report = generate_report(payload)

    out_dir = Path("benchmark_reports")
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    md_path = out_dir / f"industry_benchmarks_{payload['tier']}_{ts}.md"
    json_path = out_dir / f"industry_benchmarks_{payload['tier']}_{ts}.json"

    md_path.write_text(report)
    json_path.write_text(json.dumps(payload, indent=2))

    print(f"✅ Report saved: {md_path}")
    print(f"✅ JSON saved: {json_path}")


if __name__ == "__main__":
    asyncio.run(main())
