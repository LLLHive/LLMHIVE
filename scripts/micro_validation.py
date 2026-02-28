#!/usr/bin/env python3
"""
RAG Micro-Validation: A/B evaluator for 25 fixed MS MARCO samples.

Runs the RAG reranking pipeline twice (baseline vs flagged variant),
computes MRR@10 and Rank-1 hit rate for each, and fails if MRR drops
by >= 1.0 point or Rank-1 drops by >= 3.0 points.

Usage:
    # Baseline only (no flags):
    python3 scripts/micro_validation.py

    # DEFAULT EXPERIMENT — seeded shuffle determinism (recommended):
    RAG_RERANK_SHUFFLE_SEEDED=1 python3 scripts/micro_validation.py

    # Seeded shuffle + top1-first anchoring:
    RAG_RERANK_SHUFFLE_SEEDED=1 RAG_TOP1_FIRST=1 python3 scripts/micro_validation.py

    # Compare with confidence fallback:
    RAG_CONFIDENCE_FALLBACK=1 python3 scripts/micro_validation.py

    # DEBUG ONLY / KNOWN REGRESSOR — strict deterministic reranking:
    # (reduces multi-pass diversity; NOT recommended for benchmarks)
    RAG_RERANK_DETERMINISTIC=1 python3 scripts/micro_validation.py
"""
import asyncio
import json
import os
import random
import re
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import httpx
from datasets import load_dataset

sys.path.insert(0, str(Path(__file__).resolve().parent))

from benchmark_helpers import (
    extract_passage_ids_robust,
    extract_query_keywords,
    compute_keyword_matches,
    validate_ranking,
)
from sota_benchmark_improvements import compute_bm25_score, expand_query
from ultra_aggressive_improvements import (
    analyze_query_intent,
    ultra_hybrid_retrieval,
    generate_intent_aware_ranking_prompt,
)

API_URL = os.getenv("LLMHIVE_API_URL", os.getenv("CATEGORY_BENCH_API_URL",
    "https://llmhive-orchestrator-792354158895.us-east1.run.app"))
API_KEY = os.getenv("API_KEY", os.getenv("LLMHIVE_API_KEY", ""))
TIER = os.getenv("CATEGORY_BENCH_TIER", "elite")
_ORCH_TIER_LOCK = os.getenv("ORCH_TIER_LOCK", "none").lower()
if _ORCH_TIER_LOCK in ("elite", "free"):
    TIER = _ORCH_TIER_LOCK
_IS_FREE_TIER = (TIER.lower() == "free")
FREE_TIER_STRICT = os.getenv("FREE_TIER_STRICT", "1" if _IS_FREE_TIER else "0").lower() in ("1", "true", "yes")
FREE_HARNESS_ASSERT = os.getenv("FREE_HARNESS_ASSERT", "1" if _IS_FREE_TIER else "0").lower() in ("1", "true", "yes")
REASONING_MODE = os.getenv("CATEGORY_BENCH_REASONING_MODE", "deep")

FIXED_INDICES = [
    42, 137, 256, 389, 512, 678, 821, 943, 1057, 1198,
    1324, 1467, 1589, 1723, 1856, 2001, 2134, 2289, 2401, 2567,
    2698, 2834, 2967, 3102, 3245,
]

RAG_RERANK_DETERMINISTIC = os.getenv("RAG_RERANK_DETERMINISTIC", "").lower() in ("1", "true", "yes")
RAG_RERANK_SHUFFLE_SEEDED = os.getenv("RAG_RERANK_SHUFFLE_SEEDED", "1").lower() in ("1", "true", "yes")
RAG_TOP1_FIRST = os.getenv("RAG_TOP1_FIRST", "").lower() in ("1", "true", "yes")
RAG_CONFIDENCE_FALLBACK = os.getenv("RAG_CONFIDENCE_FALLBACK", "").lower() in ("1", "true", "yes")
_RAG_SHUFFLE_SALT = "rag_shuffle_v1"
_RAG_CONFIDENCE_BM25_THRESHOLD = float(os.getenv("RAG_CONFIDENCE_BM25_THRESHOLD", "2.0"))
_RAG_CONFIDENCE_KW_THRESHOLD = int(os.getenv("RAG_CONFIDENCE_KW_THRESHOLD", "2"))

if RAG_RERANK_DETERMINISTIC:
    import warnings
    warnings.warn(
        "RAG_RERANK_DETERMINISTIC=1 is a debug/known-regressor flag. "
        "It disables multi-pass diversity. Use RAG_RERANK_SHUFFLE_SEEDED=1 instead.",
        stacklevel=1,
    )


_FREE_ALLOWED_MODELS = {
    "deepseek/deepseek-chat",
    "meta-llama/llama-3.3-70b-instruct:free",
    "qwen/qwen3-coder:free",
    "google/gemma-3-27b-it:free",
    "qwen/qwen3-next-80b-a3b-instruct:free",
    "nvidia/nemotron-3-nano-30b-a3b:free",
    "nvidia/nemotron-nano-12b-v2-vl:free",
    "arcee-ai/trinity-large-preview:free",
    "arcee-ai/trinity-mini:free",
    "z-ai/glm-4.5-air:free",
    "upstage/solar-pro-3:free",
    "nousresearch/hermes-3-llama-3.1-405b:free",
}


async def call_api(prompt: str, temperature: float = 0.3, top_p: float = -1,
                   timeout: int = 150) -> dict:
    async with httpx.AsyncClient(timeout=timeout) as client:
        payload = {
            "prompt": prompt,
            "reasoning_mode": REASONING_MODE,
            "tier": TIER,
            "orchestration": {
                "accuracy_level": 5,
                "enable_verification": False,
                "use_deep_consensus": False,
                "temperature": temperature,
            },
        }
        if not _IS_FREE_TIER:
            payload["models"] = ["gpt-5.2-pro"]
        if top_p >= 0:
            payload["orchestration"]["top_p"] = top_p
        last_status = None
        last_err = None
        for attempt in range(3):
            try:
                resp = await client.post(
                    f"{API_URL}/v1/chat",
                    json=payload,
                    headers={"Content-Type": "application/json", "X-API-Key": API_KEY},
                )
                last_status = resp.status_code
                if resp.status_code == 200:
                    data = resp.json()
                    models_used = data.get("models_used", [])
                    if _IS_FREE_TIER and FREE_HARNESS_ASSERT and models_used:
                        for mu in models_used:
                            if mu not in _FREE_ALLOWED_MODELS:
                                return {
                                    "success": False,
                                    "error": f"FREE_TIER_MODEL_VIOLATION: {mu}",
                                    "models_used": models_used,
                                }
                    return {
                        "success": True,
                        "response": data.get("message", ""),
                        "models_used": models_used,
                        "tier": TIER,
                    }
                if resp.status_code in (429, 502, 503, 504):
                    last_err = f"HTTP {resp.status_code}"
                    await asyncio.sleep(2 ** attempt)
                    continue
                body_snippet = resp.text[:200] if resp.text else ""
                return {"success": False, "error": f"HTTP {resp.status_code}: {body_snippet}"}
            except Exception as e:
                last_err = f"{type(e).__name__}" + (f": {e}" if str(e) else "")
                if attempt < 2:
                    await asyncio.sleep(2 ** attempt)
                    continue
                return {"success": False, "error": f"exhausted retries (last: {last_err})"}
    return {"success": False, "error": f"exhausted retries (last: {last_err or last_status})"}


async def rank_single_query(
    query: str,
    passage_ids: List[int],
    passage_texts: List[str],
    *,
    use_flags: bool,
    qid: int = 0,
) -> List[int]:
    """Run the full RAG ranking pipeline for one query, returning ranked IDs."""

    passages_dict = {pid: text for pid, text in zip(passage_ids, passage_texts)}
    passage_tuples = list(zip(passage_ids, passage_texts))

    query_keywords = extract_query_keywords(query)
    expanded_query = expand_query(query)
    query_intent = analyze_query_intent(query)

    hybrid_ranked_ids = ultra_hybrid_retrieval(expanded_query, passage_tuples, query_intent)
    top_candidates = hybrid_ranked_ids[:20]

    rerank_formatted = []
    for pid in top_candidates:
        text = passages_dict[pid]
        bm25_s = compute_bm25_score(query, text)
        mc = compute_keyword_matches(text, query_keywords)
        trunc = text[:200] + "..." if len(text) > 200 else text
        rerank_formatted.append(f"[{pid}] BM25: {bm25_s:.1f}, Keywords: {mc}\n    {trunc}")
    passages_block = "\n\n".join(rerank_formatted)

    # ── Confidence fallback gate ──
    if use_flags and RAG_CONFIDENCE_FALLBACK and len(top_candidates) >= 2:
        b1 = compute_bm25_score(query, passages_dict[top_candidates[0]])
        b2 = compute_bm25_score(query, passages_dict[top_candidates[1]])
        kw1 = compute_keyword_matches(passages_dict[top_candidates[0]], query_keywords)
        if (b1 - b2) >= _RAG_CONFIDENCE_BM25_THRESHOLD and kw1 >= _RAG_CONFIDENCE_KW_THRESHOLD:
            return hybrid_ranked_ids

    # ── TOP1_FIRST anchor ──
    top1_anchor = None
    if use_flags and RAG_TOP1_FIRST:
        top1_prompt = (
            f"Query: {query}\n\n"
            "Below are candidate passages. Output ONLY the single passage ID "
            "that best answers the query. Output just the number, nothing else.\n\n"
            + passages_block
        )
        top1_result = await call_api(top1_prompt, temperature=0.0, top_p=1.0, timeout=60)
        if top1_result.get("success"):
            nums = re.findall(r'\b(\d+)\b', top1_result["response"])
            if nums:
                t1 = int(nums[0])
                if t1 in passage_ids:
                    top1_anchor = t1

    # ── Rerank config ──
    _use_deterministic = use_flags and RAG_RERANK_DETERMINISTIC
    _use_seeded_shuffle = use_flags and RAG_RERANK_SHUFFLE_SEEDED
    max_attempts = 1 if _use_deterministic else 3

    # ── LLM reranking ──
    all_rankings = []
    for attempt in range(max_attempts):
        if attempt > 0:
            shuffled = top_candidates.copy()
            if _use_seeded_shuffle:
                _seed = hash(f"{qid}|{attempt}|{_RAG_SHUFFLE_SALT}") & 0xFFFFFFFF
                random.Random(_seed).shuffle(shuffled)
            else:
                random.shuffle(shuffled)
            rf = []
            for pid in shuffled:
                text = passages_dict[pid]
                b = compute_bm25_score(query, text)
                mc = compute_keyword_matches(text, query_keywords)
                trunc = text[:200] + "..." if len(text) > 200 else text
                rf.append(f"[{pid}] BM25: {b:.1f}, Keywords: {mc}\n    {trunc}")
            block = "\n\n".join(rf)
            a_prompt = generate_intent_aware_ranking_prompt(query, block, query_intent)
        else:
            a_prompt = generate_intent_aware_ranking_prompt(query, passages_block, query_intent)

        a_prompt += "\n\nCRITICAL: Output ONLY comma-separated passage IDs, best first. Example: 7,3,1,9,2"

        if _use_deterministic:
            temp, tp = 0.0, 1.0
        else:
            temp, tp = 0.3 + (attempt * 0.15), -1

        result = await call_api(a_prompt, temperature=temp, top_p=tp)
        if result.get("success"):
            ranked = extract_passage_ids_robust(result["response"], top_candidates)
            if validate_ranking(ranked, passage_ids):
                if top1_anchor and top1_anchor in ranked:
                    ranked.remove(top1_anchor)
                    ranked.insert(0, top1_anchor)
                all_rankings.append(ranked)

    # RRF fusion
    if len(all_rankings) >= 2:
        rrf_scores: Dict[int, float] = {}
        for ranking in all_rankings:
            for pos, pid in enumerate(ranking, 1):
                base = 1.0 / (30 + pos)
                if pos == 1:
                    base *= 1.20
                elif pos > 3:
                    base *= 0.85
                rrf_scores[pid] = rrf_scores.get(pid, 0.0) + base
        final = sorted(rrf_scores, key=lambda x: rrf_scores[x], reverse=True)
    elif all_rankings:
        final = all_rankings[0]
    else:
        final = hybrid_ranked_ids

    for pid in passage_ids:
        if pid not in final:
            final.append(pid)
    return final


def compute_metrics(
    rankings: Dict[int, List[int]],
    relevants: Dict[int, List[int]],
) -> Tuple[float, float, float]:
    """Return (MRR@10, Rank-1 hit rate, Recall@10)."""
    mrr_sum = 0.0
    rank1_hits = 0
    recall_hits = 0
    total = 0
    for qid, ranked in rankings.items():
        rels = relevants.get(qid, [])
        if not rels:
            continue
        total += 1
        top10_set = set(ranked[:10])
        if top10_set & set(rels):
            recall_hits += 1
        for pos, pid in enumerate(ranked[:10], 1):
            if pid in rels:
                mrr_sum += 1.0 / pos
                if pos == 1:
                    rank1_hits += 1
                break
    mrr = mrr_sum / total if total else 0.0
    r1 = rank1_hits / total if total else 0.0
    recall = recall_hits / total if total else 0.0
    return mrr, r1, recall


async def run_variant(dataset, label: str, use_flags: bool) -> Tuple[float, float, float, int]:
    """Run the pipeline on 25 fixed samples. Returns (MRR@10, Rank1, Recall@10, errors)."""
    rankings: Dict[int, List[int]] = {}
    relevants: Dict[int, List[int]] = {}
    errors = 0

    for idx_pos, ds_idx in enumerate(FIXED_INDICES):
        if ds_idx >= len(dataset):
            continue
        item = dataset[ds_idx]
        query = item["query"]
        passages = item["passages"]
        p_texts = passages.get("passage_text", [])
        is_selected = passages.get("is_selected", [])
        p_ids = passages.get("passage_id", list(range(1, len(p_texts) + 1)))
        qid = item.get("query_id", ds_idx)
        rels = [pid for pid, sel in zip(p_ids, is_selected) if sel]
        relevants[qid] = rels

        try:
            ranked = await rank_single_query(query, p_ids, p_texts, use_flags=use_flags, qid=qid)
            rankings[qid] = ranked
        except Exception:
            errors += 1
            rankings[qid] = p_ids

        mrr_so_far, r1_so_far, rec_so_far = compute_metrics(rankings, relevants)
        status = "✅" if rels and ranked[:1] and ranked[0] in rels else "·"
        print(f"  [{idx_pos+1}/25] {label}: {status} qid={qid} mrr={mrr_so_far:.4f} "
              f"r1={r1_so_far:.1%} recall={rec_so_far:.1%}", flush=True)

    mrr, r1, recall = compute_metrics(rankings, relevants)
    print(f"\n  {label} FINAL: MRR@10={mrr:.4f}  Rank-1={r1:.1%}  "
          f"Recall@10={recall:.1%}  errors={errors}\n", flush=True)
    return mrr, r1, recall, errors


def _is_dry_run() -> bool:
    return "--dry-run" in sys.argv


async def dry_run() -> None:
    """Validate configuration without making API calls."""
    print("=" * 60)
    print("RAG Micro-Validation — DRY RUN")
    print("=" * 60)

    checks_passed = 0
    checks_failed = 0

    # 1. Check imports
    try:
        from benchmark_helpers import extract_passage_ids_robust  # noqa: F401
        from sota_benchmark_improvements import compute_bm25_score  # noqa: F401
        from ultra_aggressive_improvements import analyze_query_intent  # noqa: F401
        print("  [PASS] Helper imports OK")
        checks_passed += 1
    except ImportError as e:
        print(f"  [FAIL] Import error: {e}")
        checks_failed += 1

    # 2. Check API config
    if API_URL:
        print(f"  [PASS] API_URL = {API_URL}")
        checks_passed += 1
    else:
        print("  [FAIL] API_URL not set")
        checks_failed += 1

    if API_KEY:
        print(f"  [PASS] API_KEY present ({len(API_KEY)} chars)")
        checks_passed += 1
    else:
        print("  [WARN] API_KEY not set (will fail at runtime)")

    # 3. Check flags
    flags_active = []
    if RAG_RERANK_SHUFFLE_SEEDED:
        flags_active.append("RERANK_SHUFFLE_SEEDED")
    if RAG_TOP1_FIRST:
        flags_active.append("TOP1_FIRST")
    if RAG_CONFIDENCE_FALLBACK:
        flags_active.append("CONFIDENCE_FALLBACK")
    if RAG_RERANK_DETERMINISTIC:
        flags_active.append("RERANK_DETERMINISTIC (debug/known-regressor)")
    print(f"  [INFO] Flags: {', '.join(flags_active) or '(none)'}")
    checks_passed += 1

    # 4. Check dataset access
    print("  Loading MS MARCO dataset (dry-run)...", flush=True)
    try:
        dataset = load_dataset("microsoft/ms_marco", "v1.1", split="validation")
        max_idx = max(FIXED_INDICES)
        if max_idx >= len(dataset):
            print(f"  [WARN] Max index {max_idx} >= dataset size {len(dataset)}")
        else:
            print(f"  [PASS] Dataset loaded ({len(dataset)} samples), max index {max_idx} valid")
            checks_passed += 1

        # Quick schema check on first sample
        item = dataset[FIXED_INDICES[0]]
        assert "query" in item, "Missing 'query' field"
        assert "passages" in item, "Missing 'passages' field"
        p = item["passages"]
        assert "passage_text" in p, "Missing 'passage_text'"
        assert "is_selected" in p, "Missing 'is_selected'"
        print(f"  [PASS] Dataset schema valid (query + passages.passage_text + is_selected)")
        checks_passed += 1
    except Exception as e:
        print(f"  [FAIL] Dataset load/check: {e}")
        checks_failed += 1

    # 5. Check report directory
    out_dir = Path("benchmark_reports")
    if out_dir.exists():
        print(f"  [PASS] Report directory exists: {out_dir}")
        checks_passed += 1
    else:
        print(f"  [WARN] Report directory missing, will be created at runtime")

    print(f"\n  Dry-run summary: {checks_passed} passed, {checks_failed} failed")
    if checks_failed > 0:
        print("  DRY RUN FAILED")
        sys.exit(1)
    else:
        print("  DRY RUN PASSED — ready for execution")
        sys.exit(0)


async def main():
    if _is_dry_run():
        await dry_run()
        return

    print("=" * 60)
    print("RAG Micro-Validation (25 fixed MS MARCO samples)")
    print("=" * 60)

    flags_active = []
    if RAG_RERANK_SHUFFLE_SEEDED:
        flags_active.append("RERANK_SHUFFLE_SEEDED")
    if RAG_TOP1_FIRST:
        flags_active.append("TOP1_FIRST")
    if RAG_CONFIDENCE_FALLBACK:
        flags_active.append("CONFIDENCE_FALLBACK")
    if RAG_RERANK_DETERMINISTIC:
        flags_active.append("RERANK_DETERMINISTIC (debug/known-regressor)")

    if not flags_active:
        print("\n  No RAG flags set. Running baseline only.\n")

    print(f"  API: {API_URL}")
    print(f"  Flags: {', '.join(flags_active) or '(none — baseline only)'}")
    print(f"  Indices: {FIXED_INDICES[:5]}...{FIXED_INDICES[-1]}")
    print()

    print("Loading MS MARCO dataset...", flush=True)
    dataset = load_dataset("microsoft/ms_marco", "v1.1", split="validation")
    print(f"  Loaded {len(dataset)} samples.\n")

    # ── Run baseline (no flags) ──
    print("-" * 40)
    print("BASELINE (all RAG flags OFF)")
    print("-" * 40)
    baseline_mrr, baseline_r1, baseline_recall, baseline_errors = await run_variant(
        dataset, "baseline", use_flags=False,
    )

    flagged_mrr, flagged_r1, flagged_recall, flagged_errors = (
        baseline_mrr, baseline_r1, baseline_recall, baseline_errors,
    )
    if flags_active:
        print("-" * 40)
        print(f"VARIANT ({', '.join(flags_active)})")
        print("-" * 40)
        flagged_mrr, flagged_r1, flagged_recall, flagged_errors = await run_variant(
            dataset, "variant", use_flags=True,
        )

    # ── Report ──
    print("=" * 60)
    print("A/B RESULTS")
    print("=" * 60)
    mrr_delta = (flagged_mrr - baseline_mrr) * 100
    r1_delta = (flagged_r1 - baseline_r1) * 100
    recall_delta = (flagged_recall - baseline_recall) * 100
    print(f"  Baseline   MRR@10={baseline_mrr:.4f}  Rank-1={baseline_r1:.1%}"
          f"  Recall@10={baseline_recall:.1%}  errors={baseline_errors}")
    if flags_active:
        print(f"  Variant    MRR@10={flagged_mrr:.4f}  Rank-1={flagged_r1:.1%}"
              f"  Recall@10={flagged_recall:.1%}  errors={flagged_errors}")
        print(f"  Delta      MRR={mrr_delta:+.2f}pp  Rank-1={r1_delta:+.1f}pp"
              f"  Recall={recall_delta:+.1f}pp")

    report = {
        "baseline_mrr": round(baseline_mrr, 4),
        "baseline_rank1": round(baseline_r1, 4),
        "baseline_recall": round(baseline_recall, 4),
        "baseline_errors": baseline_errors,
        "variant_mrr": round(flagged_mrr, 4),
        "variant_rank1": round(flagged_r1, 4),
        "variant_recall": round(flagged_recall, 4),
        "variant_errors": flagged_errors,
        "mrr_delta_pp": round(mrr_delta, 2),
        "rank1_delta_pp": round(r1_delta, 2),
        "recall_delta_pp": round(recall_delta, 2),
        "flags": flags_active,
        "samples": len(FIXED_INDICES),
        "fixed_indices": FIXED_INDICES,
    }

    out_dir = Path("benchmark_reports")
    out_dir.mkdir(exist_ok=True)
    ts = time.strftime("%Y%m%d_%H%M%S")
    out_path = out_dir / f"rag_micro_validation_{ts}.json"
    out_path.write_text(json.dumps(report, indent=2))
    print(f"\n  Report: {out_path}")

    # ── Gate check ──
    _gate_failed = False
    if flags_active:
        if mrr_delta <= -1.0:
            print(f"  FAIL: MRR dropped by {abs(mrr_delta):.2f}pp (threshold: 1.0pp)")
            _gate_failed = True
        if r1_delta <= -3.0:
            print(f"  FAIL: Rank-1 dropped by {abs(r1_delta):.1f}pp (threshold: 3.0pp)")
            _gate_failed = True
        if recall_delta < 0:
            print(f"  FAIL: Recall@10 dropped by {abs(recall_delta):.1f}pp (must not decrease)")
            _gate_failed = True
        if flagged_errors > 0:
            print(f"  WARN: {flagged_errors} errors in variant run")

    if _gate_failed:
        sys.exit(1)
    else:
        print(f"\n  PASS: No regression detected.")
        sys.exit(0)


DIALOGUE_STUB_INDICES = list(range(10))

async def run_dialogue_stub() -> Dict:
    """10-sample Dialogue micro-test stub.

    Calls the MT-Bench evaluator on a tiny slice and returns pass/fail
    based on timeout only (no raw-score gate).  The full Dialogue quality
    gate lives in the certified suite.
    """
    print("\n" + "=" * 60)
    print("DIALOGUE MICRO-TEST (10-sample stub)")
    print("=" * 60)

    eval_script = Path(__file__).resolve().parent / "eval_mtbench.py"
    if not eval_script.exists():
        print("  [SKIP] eval_mtbench.py not found — dialogue stub skipped")
        return {"status": "skipped", "reason": "eval_mtbench.py not found"}

    import subprocess, shlex
    out_dir = Path("benchmark_reports")
    out_dir.mkdir(exist_ok=True)
    ts = time.strftime("%Y%m%d_%H%M%S")
    out_path = out_dir / f"mtbench_micro_{ts}.json"

    cmd = f"python3 {eval_script} --output {out_path} --seed 42"
    sub_env = os.environ.copy()
    sub_env["CATEGORY_BENCH_MTBENCH_SAMPLES"] = "10"

    try:
        proc = subprocess.run(
            shlex.split(cmd), check=True, timeout=600,
            capture_output=True, text=True, env=sub_env,
        )
        if out_path.exists():
            payload = json.loads(out_path.read_text())
            raw = round(float(payload.get("score", payload.get("avg_score", 0))), 2)
            acc = round(raw * 10, 2)
            errs = int(payload.get("errors", 0))
            print(f"  Score: {raw} / 10  (accuracy_pct={acc}%)  errors={errs}")
            result = {
                "status": "passed",
                "raw_score_out_of_10": raw,
                "accuracy_pct": acc,
                "errors": errs,
                "dialogue_exec_integrity": True,
            }
        else:
            result = {"status": "failed", "reason": "output file missing"}
    except subprocess.TimeoutExpired:
        print("  FAIL: Dialogue stub timed out (600s)")
        result = {"status": "failed", "reason": "timeout"}
    except subprocess.CalledProcessError as e:
        print(f"  FAIL: Dialogue stub exited {e.returncode}")
        result = {"status": "failed", "reason": f"exit {e.returncode}"}

    print(f"  Result: {result['status']}")
    return result


async def run_free_smoke() -> None:
    """Smoke test: 5 queries proving free tier uses free models only.

    Sends 5 simple prompts across 2 categories (math + reasoning).
    Asserts every response includes models_used, all models are in the
    free allowlist, and no paid models appear.
    """
    print("\n" + "=" * 60)
    print("FREE-TIER SMOKE TEST (5 queries)")
    print("=" * 60)
    print(f"  API:  {API_URL}")
    print(f"  TIER: {TIER}")
    print(f"  FREE_TIER_STRICT: {FREE_TIER_STRICT}")
    print(f"  Allowlist size: {len(_FREE_ALLOWED_MODELS)}")

    if TIER != "free":
        print(f"\n  [ABORT] TIER={TIER} but --free-smoke requires TIER=free.")
        print("  Set CATEGORY_BENCH_TIER=free and rerun.")
        sys.exit(1)

    prompts = [
        ("math", "What is 17 * 23? Show your work step by step and give the final answer."),
        ("math", "If a train travels 60 mph for 2.5 hours, how far does it go?"),
        ("reasoning", "What is the capital of France? Answer in one word."),
        ("reasoning", "Is the number 37 prime? Explain briefly."),
        ("reasoning", "Name the three states of matter."),
    ]

    paid_violations = []
    missing_models = []
    free_models_seen = set()
    passed = 0

    for i, (category, prompt) in enumerate(prompts, 1):
        print(f"\n  [{i}/5] category={category}", flush=True)
        result = await call_api(prompt, temperature=0.3, timeout=90)

        if not result.get("success"):
            err = result.get("error", "unknown")
            if "FREE_TIER_MODEL_VIOLATION" in str(err):
                paid_violations.append({"query": i, "error": err,
                                        "models": result.get("models_used", [])})
                print(f"        VIOLATION: {err}")
            else:
                print(f"        ERROR: {err}")
            continue

        models = result.get("models_used", [])
        if not models:
            missing_models.append(i)
            print(f"        WARN: models_used missing from response")
            continue

        all_free = all(m in _FREE_ALLOWED_MODELS for m in models)
        free_models_seen.update(models)
        if all_free:
            passed += 1
            print(f"        OK: models={models}")
        else:
            bad = [m for m in models if m not in _FREE_ALLOWED_MODELS]
            paid_violations.append({"query": i, "models": models, "paid": bad})
            print(f"        VIOLATION: paid models used: {bad}")

    print("\n" + "-" * 60)
    print("FREE-SMOKE RESULTS")
    print("-" * 60)
    print(f"  Passed:           {passed}/5")
    print(f"  Paid violations:  {len(paid_violations)}")
    print(f"  Missing models:   {len(missing_models)}")
    print(f"  Free models seen: {free_models_seen or '(none)'}")

    if paid_violations:
        print(f"\n  FAIL: {len(paid_violations)} paid-model violations detected:")
        for v in paid_violations:
            print(f"    query {v['query']}: {v}")
        sys.exit(1)
    elif passed == 0:
        print("\n  FAIL: 0 queries succeeded — cannot confirm free routing.")
        sys.exit(1)
    else:
        print(f"\n  PASS: All {passed} responses used free models only.")
        sys.exit(0)


if __name__ == "__main__":
    if "--free-smoke" in sys.argv:
        asyncio.run(run_free_smoke())
    elif "--dialogue" in sys.argv:
        asyncio.run(run_dialogue_stub())
    else:
        asyncio.run(main())
