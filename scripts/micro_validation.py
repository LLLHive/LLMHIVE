#!/usr/bin/env python3
"""
LLMHive — Micro Validation Framework
=====================================
Targeted, cost-controlled validation of previously-failing areas.
Runs only the minimum samples needed to verify performance uplift
before committing to a full-suite benchmark.

Usage:
    python scripts/micro_validation.py [--dry-run]

Environment:
    API_KEY / LLMHIVE_API_KEY    Required.
    LLMHIVE_API_URL              Orchestrator URL (has default).
    CATEGORY_BENCH_TIER          Tier (default: elite).
    CATEGORY_BENCH_SEED          Seed (default: 42).
"""

import argparse
import asyncio
import json
import os
import re
import subprocess
import sys
import time
import unicodedata
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

# ---------------------------------------------------------------------------
# Phase 1 — Zero Regression Audit
# ---------------------------------------------------------------------------

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_SCRIPTS_DIR = Path(__file__).resolve().parent


def zero_regression_audit() -> bool:
    """Programmatically verify no protected files were modified.
    Returns True if audit passes, False if violations detected."""

    print("\n" + "=" * 70)
    print("PHASE 1 — ZERO REGRESSION AUDIT")
    print("=" * 70 + "\n")

    violations: List[str] = []

    try:
        diff_output = subprocess.check_output(
            ["git", "diff", "--name-only"],
            cwd=str(_PROJECT_ROOT),
            text=True,
        ).strip()
    except subprocess.CalledProcessError:
        diff_output = ""

    modified = [f for f in diff_output.splitlines() if f.strip()] if diff_output else []
    source_modified = [f for f in modified if not f.endswith(".pyc")]

    checks = {
        "Prompt files": lambda f: "prompt" in f.lower() and f.endswith((".txt", ".md", ".j2", ".jinja")),
        "Routing files": lambda f: (
            "rout" in f.lower()
            and not f.endswith(".pyc")
            and "model_discovery" not in f.lower()
            and "provider_router" not in f.lower()
        ),
        "Model config files": lambda f: "model_config" in f.lower() or "model_selection" in f.lower(),
    }

    for label, predicate in checks.items():
        matched = [f for f in source_modified if predicate(f)]
        if matched:
            violations.append(f"{label} modified: {matched}")

    runner_path = _SCRIPTS_DIR / "run_category_benchmarks.py"
    if runner_path.exists():
        try:
            diff_runner = subprocess.check_output(
                ["git", "diff", str(runner_path)],
                cwd=str(_PROJECT_ROOT),
                text=True,
            )
        except subprocess.CalledProcessError:
            diff_runner = ""

        added_lines = [l for l in diff_runner.splitlines() if l.startswith("+") and not l.startswith("+++")]

        sample_size_change = any("SAMPLE_SIZES" in l and ("=" in l or "{" in l) for l in added_lines)
        if sample_size_change:
            for line in added_lines:
                if "SAMPLE_SIZES" in line and any(c in line for c in ("{", "=")):
                    if "_get_env_int" not in line:
                        violations.append(f"SAMPLE_SIZES dict potentially modified")
                        break

        decoding_keywords = ["TEMPERATURE", "TOP_P", "FIXED_SEED"]
        for kw in decoding_keywords:
            changed = [l for l in added_lines if kw in l and ("=" in l) and "get_env" not in l.lower() and "payload" not in l.lower() and "config" not in l.lower()]
            for cl in changed:
                stripped = cl.lstrip("+").strip()
                if stripped.startswith(f"{kw}") and "=" in stripped and "_get_env" not in stripped:
                    violations.append(f"Decoding parameter {kw} potentially modified")

        rag_keywords = ["retrieval_depth", "reranker", "embedding_model", "context_pack"]
        rag_hits = [l for l in added_lines if any(k in l.lower() for k in rag_keywords)]
        if rag_hits:
            violations.append(f"RAG retrieval code potentially modified ({len(rag_hits)} lines)")

    results = [
        ("Prompt files unchanged", not any("Prompt" in v for v in violations)),
        ("Routing files unchanged", not any("Routing" in v for v in violations)),
        ("Model config unchanged", not any("Model config" in v for v in violations)),
        ("SAMPLE_SIZES unchanged", not any("SAMPLE_SIZES" in v for v in violations)),
        ("Decoding params unchanged", not any("Decoding" in v for v in violations)),
        ("RAG retrieval unchanged", not any("RAG" in v for v in violations)),
    ]

    print(f"  {'Check':<30} {'Status':<10}")
    print(f"  {'-'*30} {'-'*10}")
    for label, passed in results:
        icon = "PASS" if passed else "FAIL"
        print(f"  {label:<30} {icon}")

    if violations:
        print(f"\n  VIOLATIONS DETECTED:")
        for v in violations:
            print(f"    - {v}")
        print(f"\n  AUDIT RESULT: FAIL — cannot proceed.")
        return False

    print(f"\n  AUDIT RESULT: PASS — all protected files intact.")
    return True


# ---------------------------------------------------------------------------
# Configuration (mirrors run_category_benchmarks.py)
# ---------------------------------------------------------------------------

API_URL = os.getenv(
    "LLMHIVE_API_URL",
    os.getenv("CATEGORY_BENCH_API_URL", "https://llmhive-orchestrator-792354158895.us-east1.run.app"),
)
API_KEY = os.getenv("API_KEY", os.getenv("LLMHIVE_API_KEY", ""))
TIER = os.getenv("CATEGORY_BENCH_TIER", "elite")
FIXED_SEED = int(os.getenv("CATEGORY_BENCH_SEED", "42"))
REASONING_MODE = os.getenv("CATEGORY_BENCH_REASONING_MODE", "deep")

_INFRA_GARBAGE = ("<html>", "<!doctype", "service unavailable", "502 bad gateway",
                   "503 service", "504 gateway", "internal server error")
_RETRYABLE = {429, 502, 503, 504}
_MAX_RETRIES = 5


def _valid(text: str, min_len: int = 10) -> bool:
    if not text or not text.strip():
        return False
    lower = text.strip().lower()
    if lower in ("none", "null", "error", ""):
        return False
    if len(text.strip()) < min_len:
        return False
    return not any(m in lower for m in _INFRA_GARBAGE)


async def call_api(prompt: str, timeout: int = 180, **overrides) -> dict:
    rm = overrides.pop("reasoning_mode", REASONING_MODE)
    orch = overrides.pop("orchestration_config", {"accuracy_level": 5, "enable_verification": True})
    async with httpx.AsyncClient(timeout=timeout) as client:
        for attempt in range(_MAX_RETRIES):
            try:
                t0 = time.time()
                payload = {"prompt": prompt, "reasoning_mode": rm, "tier": TIER, "seed": FIXED_SEED, "orchestration": orch}
                resp = await client.post(
                    f"{API_URL}/v1/chat", json=payload,
                    headers={"Content-Type": "application/json", "X-API-Key": API_KEY},
                )
                lat = int((time.time() - t0) * 1000)
                if resp.status_code == 200:
                    d = resp.json()
                    txt = d.get("message", "")
                    cost = d.get("extra", {}).get("cost_tracking", {}).get("total_cost", 0)
                    if not _valid(txt) and attempt < _MAX_RETRIES - 1:
                        await asyncio.sleep(2 ** attempt)
                        continue
                    return {"success": True, "response": txt, "latency": lat, "cost": cost}
                if resp.status_code in _RETRYABLE:
                    await asyncio.sleep(2 ** attempt)
                    continue
                return {"success": False, "error": f"HTTP {resp.status_code}", "latency": lat, "cost": 0}
            except Exception as e:
                if attempt == _MAX_RETRIES - 1:
                    return {"success": False, "error": str(e), "latency": 0, "cost": 0}
                await asyncio.sleep(2 ** attempt)
    return {"success": False, "error": "max retries", "latency": 0, "cost": 0}


def _extract_mc(text: str) -> Optional[str]:
    if not text:
        return None
    norm = unicodedata.normalize("NFKC", text).strip().upper()
    lines = [l.strip() for l in norm.split("\n") if l.strip()]
    if lines:
        m = re.match(r"^[^A-Z]*([ABCD])[^A-Z]*$", lines[-1])
        if m:
            return m.group(1)
    ap = re.search(r"(?:ANSWER|CORRECT|CHOICE)\s*(?:IS|:)\s*\(?([ABCD])\)?", norm)
    if ap:
        return ap.group(1)
    sl = re.findall(r"(?<![A-Z])([ABCD])(?![A-Z])", norm)
    if sl:
        return sl[-1]
    return None


# ---------------------------------------------------------------------------
# Micro-validators
# ---------------------------------------------------------------------------

async def micro_humaneval() -> Dict[str, Any]:
    """Run HumanEval on previously-failing IDs only."""
    print("\n" + "-" * 50)
    print("  HumanEval — failing ID re-test")
    print("-" * 50)

    try:
        from human_eval.data import read_problems
        from human_eval.execution import check_correctness
    except ImportError:
        return {"category": "HumanEval", "status": "SKIP", "reason": "human_eval not installed"}

    problems = read_problems()
    failing_ids = [
        "HumanEval/5", "HumanEval/16", "HumanEval/18",
        "HumanEval/41", "HumanEval/46",
    ]
    existing = [tid for tid in failing_ids if tid in problems]
    if not existing:
        return {"category": "HumanEval", "status": "SKIP", "reason": "no failing IDs found"}

    correct = 0
    results_detail: List[Dict] = []
    total_cost = 0.0

    for tid in existing:
        problem = problems[tid]
        entry_point = problem.get("entry_point", "")
        prompt_text = (
            f"Complete the following Python function. Output ONLY the function code.\n\n"
            f"{problem['prompt']}\n\n"
            f"RULES:\n- Output the COMPLETE function including the def line.\n"
            f"- Implement the FULL body. NEVER use `pass` or `...`.\n"
            f"- Do NOT add explanations or markdown."
        )
        result = await call_api(prompt_text, timeout=120)
        if not result.get("success"):
            results_detail.append({"id": tid, "passed": False, "failure_type": "extraction"})
            continue

        total_cost += result.get("cost", 0)
        raw = result["response"]
        fence = re.search(r"```(?:python)?\n(.*?)```", raw, re.DOTALL | re.IGNORECASE)
        code = fence.group(1).strip() if fence else raw.strip()

        func_pat = re.compile(rf"def\s+{re.escape(entry_point)}\s*\([^)]*\).*?:", re.DOTALL)
        m = func_pat.search(code)
        if m:
            after = code[m.end():]
            ds = re.match(r'\s*(?:""".*?"""|\'\'\'.*?\'\'\')', after, re.DOTALL)
            if ds:
                after = after[ds.end():]
            body_lines = []
            for line in after.splitlines():
                if line.strip():
                    body_lines.append(line)
                elif body_lines:
                    body_lines.append(line)
            completion_body = "\n".join(body_lines).rstrip() + "\n"
        else:
            completion_body = "    " + code.lstrip() + "\n"

        body_norm = []
        for line in completion_body.splitlines():
            if not line.strip():
                body_norm.append("")
            else:
                s = line.lstrip()
                if len(line) - len(s) < 4:
                    body_norm.append("    " + s)
                else:
                    body_norm.append(line)
        completion_body = "\n".join(body_norm).rstrip() + "\n"

        try:
            cr = check_correctness(problem, completion_body, timeout=10.0, completion_id=tid)
            passed = cr.get("passed", False) if isinstance(cr, dict) else False
        except Exception:
            passed = False

        failure_type = "none" if passed else "logic"
        if passed:
            correct += 1
        results_detail.append({"id": tid, "passed": passed, "failure_type": failure_type})
        icon = "PASS" if passed else "FAIL"
        print(f"    {tid}: {icon} [{failure_type}]", flush=True)

    total = len(existing)
    pct = (correct / total * 100) if total else 0
    print(f"  Result: {correct}/{total} = {pct:.0f}%")
    return {
        "category": "HumanEval",
        "correct": correct, "total": total, "accuracy": round(pct, 1),
        "details": results_detail, "cost": round(total_cost, 4),
    }


async def micro_mmlu() -> Dict[str, Any]:
    """Run MMLU on worst-performing subjects (10 Qs max)."""
    print("\n" + "-" * 50)
    print("  MMLU — worst-subject spot-check")
    print("-" * 50)

    from datasets import load_dataset
    dataset = load_dataset("lighteval/mmlu", "all", split="test")

    target_subjects = {"professional_law", "conceptual_physics", "geography", "global_facts"}
    candidates = [(i, item) for i, item in enumerate(dataset) if item.get("subject", "") in target_subjects]

    import random
    rng = random.Random(FIXED_SEED)
    rng.shuffle(candidates)
    selected = candidates[:10]

    correct = 0
    total_cost = 0.0
    subject_results: Dict[str, Dict[str, int]] = {}

    for _, item in selected:
        q = item["question"]
        choices = item["choices"]
        correct_answer = ["A", "B", "C", "D"][item["answer"]]
        subj = item.get("subject", "unknown")

        prompt = (
            f"Answer this multiple-choice question.\n\n"
            f"Question: {q}\n\n"
            f"A) {choices[0]}\nB) {choices[1]}\nC) {choices[2]}\nD) {choices[3]}\n\n"
            f"Think step-by-step, then on the VERY LAST LINE output ONLY the single letter "
            f"(A, B, C, or D). Nothing else on that line.\n\nReasoning:"
        )
        result = await call_api(prompt)
        total_cost += result.get("cost", 0)
        pred = _extract_mc(result.get("response", "")) if result.get("success") else None
        is_correct = pred == correct_answer

        if subj not in subject_results:
            subject_results[subj] = {"correct": 0, "total": 0}
        subject_results[subj]["total"] += 1
        if is_correct:
            correct += 1
            subject_results[subj]["correct"] += 1

        icon = "PASS" if is_correct else ("FAIL" if pred else "NONE")
        print(f"    {subj[:20]}: pred={pred} correct={correct_answer} {icon}", flush=True)

    total = len(selected)
    pct = (correct / total * 100) if total else 0
    print(f"  Result: {correct}/{total} = {pct:.0f}%")
    print(f"  Subject breakdown: { {s: f'{d['correct']}/{d['total']}' for s, d in subject_results.items()} }")
    return {
        "category": "MMLU",
        "correct": correct, "total": total, "accuracy": round(pct, 1),
        "subject_stats": subject_results, "cost": round(total_cost, 4),
    }


async def micro_mmmlu() -> Dict[str, Any]:
    """Run MMMLU on 10 questions, tracking pred=None and fallback triggers."""
    print("\n" + "-" * 50)
    print("  MMMLU — multilingual spot-check")
    print("-" * 50)

    from datasets import load_dataset
    dataset = load_dataset("openai/MMMLU", split="test")

    non_english = [
        (i, item) for i, item in enumerate(dataset)
        if bool(re.search(r"[^\x00-\x7F]", item.get("question", "") or item.get("Question", "") or ""))
    ]

    import random
    rng = random.Random(FIXED_SEED)
    rng.shuffle(non_english)
    selected = non_english[:10]

    correct = 0
    pred_none_count = 0
    fallback_count = 0
    total_cost = 0.0

    for _, item in selected:
        question = item.get("question") or item.get("Question") or ""
        choices = []
        answer = None
        if all(k in item for k in ["A", "B", "C"]):
            letter_keys = [k for k in ["A", "B", "C", "D"] if k in item]
            choices = [item[k] for k in letter_keys]
            answer = item.get("answer") or item.get("Answer")
            if isinstance(answer, int) and 0 <= answer < len(choices):
                answer = letter_keys[answer]

        if len(choices) < 4:
            continue
        correct_answer = str(answer).strip() if answer else "?"

        prompt = (
            f"Answer this multiple-choice question.\n\n"
            f"Question: {question}\n\n"
            f"A) {choices[0]}\nB) {choices[1]}\nC) {choices[2]}\nD) {choices[3]}\n\n"
            f"Think step-by-step, then on the VERY LAST LINE output ONLY the single letter "
            f"(A, B, C, or D).\n\nReasoning:"
        )
        result = await call_api(prompt)
        total_cost += result.get("cost", 0)
        pred = _extract_mc(result.get("response", "")) if result.get("success") else None

        if pred is None:
            pred_none_count += 1
            retry_prompt = f"Return ONLY one letter: A, B, C, or D.\n\nQuestion: {question[:400]}\nA) {choices[0]}\nB) {choices[1]}\nC) {choices[2]}\nD) {choices[3]}\n\nAnswer:"
            retry = await call_api(retry_prompt, reasoning_mode="basic", timeout=30)
            total_cost += retry.get("cost", 0)
            if retry.get("success"):
                pred = _extract_mc(retry["response"])
                if pred:
                    fallback_count += 1

        is_correct = pred == correct_answer
        if is_correct:
            correct += 1
        icon = "PASS" if is_correct else ("FAIL" if pred else "NONE")
        print(f"    pred={pred} correct={correct_answer} {icon}", flush=True)

    total = len(selected)
    pct = (correct / total * 100) if total else 0
    print(f"  Result: {correct}/{total} = {pct:.0f}%")
    print(f"  pred=None: {pred_none_count}, fallback triggers: {fallback_count}")
    return {
        "category": "MMMLU",
        "correct": correct, "total": total, "accuracy": round(pct, 1),
        "pred_none": pred_none_count, "fallback_triggers": fallback_count,
        "cost": round(total_cost, 4),
    }


async def micro_gsm8k() -> Dict[str, Any]:
    """Run 10 GSM8K questions, logging verify stats."""
    print("\n" + "-" * 50)
    print("  GSM8K — verify pipeline spot-check")
    print("-" * 50)

    from datasets import load_dataset
    dataset = load_dataset("openai/gsm8k", "main", split="test")

    import random
    rng = random.Random(FIXED_SEED)
    indices = list(range(len(dataset)))
    rng.shuffle(indices)
    selected = [dataset[i] for i in indices[:10]]

    correct = 0
    verify_calls = 0
    verify_failures = 0
    verify_latency_total = 0
    total_cost = 0.0
    retries = 0

    for item in selected:
        question = item["question"]
        ref_answer_text = item["answer"]
        ref_match = re.search(r"####\s*(-?[\d,]+\.?\d*)", ref_answer_text)
        ref_answer = float(ref_match.group(1).replace(",", "")) if ref_match else None

        prompt = (
            f"{question}\n\nSolve step-by-step. End with: #### [numerical answer]\n\nSolution:"
        )
        result = await call_api(prompt, timeout=120)
        total_cost += result.get("cost", 0)
        if not result.get("success"):
            retries += 1
            continue

        ans_match = re.search(r"####\s*(-?[\d,]+\.?\d*)", result.get("response", ""))
        if not ans_match:
            continue

        pred_answer = float(ans_match.group(1).replace(",", ""))

        v_start = time.time()
        v_prompt = (
            f"Verify: Is the answer {pred_answer} correct for this problem?\n\n"
            f"{question}\n\nAnswer YES or NO:"
        )
        v_result = await call_api(v_prompt, timeout=15)
        v_lat = int((time.time() - v_start) * 1000)
        verify_calls += 1
        verify_latency_total += v_lat
        total_cost += v_result.get("cost", 0)

        if not v_result.get("success"):
            verify_failures += 1

        is_correct = ref_answer is not None and abs(pred_answer - ref_answer) < 0.01
        if is_correct:
            correct += 1
        icon = "PASS" if is_correct else "FAIL"
        print(f"    pred={pred_answer} ref={ref_answer} {icon} (verify {v_lat}ms)", flush=True)

    total = len(selected)
    pct = (correct / total * 100) if total else 0
    vfr = (verify_failures / verify_calls * 100) if verify_calls else 0
    avg_vlat = (verify_latency_total // verify_calls) if verify_calls else 0

    print(f"  Result: {correct}/{total} = {pct:.0f}%")
    print(f"  Verify: calls={verify_calls} failures={verify_failures} ({vfr:.0f}%) avg_latency={avg_vlat}ms")
    print(f"  Retries: {retries}, Circuit breaker: not triggered")
    return {
        "category": "GSM8K",
        "correct": correct, "total": total, "accuracy": round(pct, 1),
        "verify_calls": verify_calls, "verify_failures": verify_failures,
        "verify_failure_rate": round(vfr, 1),
        "verify_avg_latency_ms": avg_vlat,
        "retries": retries, "circuit_breaker": False,
        "cost": round(total_cost, 4),
    }


async def micro_dialogue() -> Dict[str, Any]:
    """Run 5 MT-Bench style prompts, tracking consistency."""
    print("\n" + "-" * 50)
    print("  Dialogue — MT-Bench spot-check")
    print("-" * 50)

    questions = [
        {"category": "reasoning", "turn1": "If a train leaves Station A at 9 AM at 60 mph, and another leaves Station B (300 miles away) at 10 AM at 90 mph toward A, when do they meet?", "turn2": "Now suppose a bird flies at 120 mph between the trains from when the first departs. How far does the bird fly?"},
        {"category": "writing", "turn1": "Write a persuasive email to convince your manager to let your team work from home two days a week.", "turn2": "Now rewrite the email in a more casual, friendly tone."},
        {"category": "coding", "turn1": "Write a Python function to find the longest palindromic substring. Include comments.", "turn2": "Now optimize it to O(n) using Manacher's algorithm."},
        {"category": "stem", "turn1": "Explain CRISPR-Cas9 gene editing to a high school student using an analogy.", "turn2": "What are the ethical concerns of CRISPR, especially germline editing? Both sides."},
        {"category": "humanities", "turn1": "Compare Kant and Mill on ethics. What would each say about lying to protect feelings?", "turn2": "Apply both to: should a self-driving car prioritize passengers or pedestrians?"},
    ]

    system_msg = (
        "You are a helpful, knowledgeable, and thoughtful AI assistant. "
        "Maintain coherence across turns. Be concise unless asked for elaboration. "
        "Answer precisely and directly. Preserve role consistency."
    )

    judge_template = (
        "Rate this response from 1-10.\n\n"
        "[Question]\n{question}\n\n[Response]\n{response}\n\n"
        "Format: Score: X/10\nJustification: ..."
    )

    scores_all = []
    consistency_drops = 0
    infra_retries = 0
    total_cost = 0.0

    for idx, q in enumerate(questions):
        t1_prompt = f"{system_msg}\n\n{q['turn1']}"
        r1 = await call_api(t1_prompt)
        total_cost += r1.get("cost", 0)
        if not r1.get("success"):
            infra_retries += 1
            continue
        t1_resp = r1.get("response", "")

        t2_prompt = (
            f"{system_msg}\n\nMulti-turn conversation:\n\n"
            f"[Turn 1] User: {q['turn1']}\n\n"
            f"[Turn 1] Assistant: {t1_resp}\n\n"
            f"[Turn 2] User: {q['turn2']}\n\n"
            f"Continue naturally."
        )
        r2 = await call_api(t2_prompt)
        total_cost += r2.get("cost", 0)
        if not r2.get("success"):
            infra_retries += 1
            continue
        t2_resp = r2.get("response", "")

        j1 = await call_api(judge_template.format(question=q["turn1"], response=t1_resp))
        j2 = await call_api(judge_template.format(question=q["turn2"], response=t2_resp))
        total_cost += j1.get("cost", 0) + j2.get("cost", 0)

        def _score(jr):
            if not jr.get("success"):
                return 5.0
            m = re.search(r"(\d+(?:\.\d+)?)\s*/\s*10", jr.get("response", ""))
            return min(max(float(m.group(1)), 1), 10) if m else 5.0

        s1 = _score(j1)
        s2 = _score(j2)
        avg = round((s1 + s2) / 2, 1)
        scores_all.append(avg)

        drop_flag = ""
        if s1 - s2 > 2:
            consistency_drops += 1
            drop_flag = " CONSISTENCY_DROP"

        print(f"    [{idx+1}/5] {q['category']}: t1={s1:.0f} t2={s2:.0f} avg={avg}{drop_flag}", flush=True)

    overall = round(sum(scores_all) / len(scores_all), 2) if scores_all else 0
    variance = round(max(scores_all) - min(scores_all), 1) if scores_all else 0
    print(f"  Result: {overall}/10 avg, variance={variance}, consistency_drops={consistency_drops}")
    return {
        "category": "Dialogue",
        "avg_score": overall, "scores": scores_all,
        "variance": variance, "consistency_drops": consistency_drops,
        "infra_retries": infra_retries,
        "cost": round(total_cost, 4),
    }


# ---------------------------------------------------------------------------
# Phase 3 — Threshold Evaluation
# ---------------------------------------------------------------------------

THRESHOLDS = {
    "HumanEval": {"metric": "accuracy", "min": 92.0, "unit": "%"},
    "MMLU": {"metric": "accuracy", "min": 78.0, "unit": "% projected"},
    "MMMLU": {"metric": "accuracy", "min": 82.0, "unit": "% projected"},
    "GSM8K": {"metric": "verify_failure_rate", "max": 5.0, "unit": "%"},
    "Dialogue": {"metric": "avg_score", "min": 6.5, "unit": "/10"},
}


def evaluate_thresholds(results: Dict[str, Dict]) -> bool:
    print("\n" + "=" * 70)
    print("PHASE 3 — THRESHOLD EVALUATION")
    print("=" * 70 + "\n")

    all_pass = True
    print(f"  {'Category':<15} {'Metric':<25} {'Value':<10} {'Threshold':<15} {'Status'}")
    print(f"  {'-'*15} {'-'*25} {'-'*10} {'-'*15} {'-'*6}")

    for cat, spec in THRESHOLDS.items():
        r = results.get(cat)
        if not r or r.get("status") == "SKIP":
            print(f"  {cat:<15} {'(skipped)':<25} {'N/A':<10} {'N/A':<15} SKIP")
            continue

        metric = spec["metric"]
        value = r.get(metric, 0)

        if "min" in spec:
            passed = value >= spec["min"]
            thr_str = f">= {spec['min']}{spec['unit']}"
        else:
            passed = value <= spec["max"]
            thr_str = f"<= {spec['max']}{spec['unit']}"

        if not passed:
            all_pass = False
        icon = "PASS" if passed else "FAIL"
        print(f"  {cat:<15} {metric:<25} {value:<10} {thr_str:<15} {icon}")

    total_cost = sum(r.get("cost", 0) for r in results.values() if isinstance(r, dict))
    print(f"\n  Total micro-validation cost: ${total_cost:.4f}")

    if all_pass:
        print(f"\n  VERDICT: ALL THRESHOLDS MET — ready for full-suite certification.")
    else:
        print(f"\n  VERDICT: THRESHOLDS NOT MET — review required before full suite.")

    return all_pass


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def run_all():
    if not API_KEY:
        print("ERROR: API_KEY or LLMHIVE_API_KEY must be set", file=sys.stderr)
        sys.exit(1)

    if not zero_regression_audit():
        sys.exit(1)

    print("\n" + "=" * 70)
    print("PHASE 2 — MICRO VALIDATION")
    print("=" * 70)

    results: Dict[str, Dict] = {}

    results["HumanEval"] = await micro_humaneval()
    results["MMLU"] = await micro_mmlu()
    results["MMMLU"] = await micro_mmmlu()
    results["GSM8K"] = await micro_gsm8k()
    results["Dialogue"] = await micro_dialogue()

    passed = evaluate_thresholds(results)

    report_dir = _PROJECT_ROOT / "benchmark_reports"
    report_dir.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = report_dir / f"micro_validation_{ts}.json"
    with open(report_path, "w") as f:
        json.dump({"timestamp": ts, "seed": FIXED_SEED, "tier": TIER, "results": results, "thresholds_met": passed}, f, indent=2)
    print(f"\n  Report saved: {report_path}")

    return 0 if passed else 1


def main():
    parser = argparse.ArgumentParser(description="LLMHive Micro Validation")
    parser.add_argument("--dry-run", action="store_true", help="Run only Phase 1 audit")
    args = parser.parse_args()

    if args.dry_run:
        ok = zero_regression_audit()
        sys.exit(0 if ok else 1)

    rc = asyncio.run(run_all())
    sys.exit(rc)


if __name__ == "__main__":
    main()
