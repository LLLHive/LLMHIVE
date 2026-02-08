#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import random
import subprocess
from pathlib import Path
from typing import Dict, List

TEST_SETS = ["G1_instruction", "G1_category", "G1_tool", "G2_instruction", "G2_category", "G3_instruction"]


def load_queries(data_dir: Path, set_name: str) -> List[Dict]:
    group = set_name.split("_")[0]
    query_path = data_dir / "instruction" / f"{group}_query.json"
    with query_path.open("r") as f:
        return json.load(f)


def load_test_ids(data_dir: Path, set_name: str) -> List[int]:
    test_ids_path = data_dir / "test_query_ids" / f"{set_name}.json"
    with test_ids_path.open("r") as f:
        payload = json.load(f)
    return [int(k) for k in payload.keys()]


def write_subset(data_dir: Path, set_name: str, sample_size: int, seed: int) -> Path:
    queries = load_queries(data_dir, set_name)
    id_set = set(load_test_ids(data_dir, set_name))
    filtered = [q for q in queries if int(q.get("query_id", -1)) in id_set]

    rng = random.Random(seed)
    rng.shuffle(filtered)
    subset = filtered[: min(sample_size, len(filtered))]

    out_dir = data_dir / "llmhive_toolbench_subset"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{set_name}.json"
    with out_path.open("w") as f:
        json.dump(subset, f)
    return out_path


def run_pipeline(data_dir: Path, set_name: str, query_path: Path, api_key: str, method: str) -> Path:
    answer_dir = data_dir / "llmhive_toolbench_answers" / set_name
    answer_dir.mkdir(parents=True, exist_ok=True)
    tool_root = data_dir / "toolenv" / "tools"
    toolbench_root = "/Users/camilodiaz/Downloads/ToolBench"
    cmd = [
        "python3",
        "/Users/camilodiaz/Downloads/ToolBench/toolbench/inference/qa_pipeline.py",
        "--backbone_model",
        "llmhive",
        "--openai_key",
        api_key,
        "--tool_root_dir",
        str(tool_root),
        "--input_query_file",
        str(query_path),
        "--output_answer_file",
        str(answer_dir),
        "--method",
        method,
    ]
    env = os.environ.copy()
    env["PYTHONPATH"] = f"{toolbench_root}:{env.get('PYTHONPATH', '')}"
    subprocess.run(cmd, check=True, env=env)
    return answer_dir


def convert_answers(data_dir: Path, set_name: str, answer_dir: Path, method: str) -> Path:
    converted_root = data_dir / "model_predictions_converted" / "llmhive"
    converted_root.mkdir(parents=True, exist_ok=True)
    output_file = converted_root / f"{set_name}.json"
    cmd = [
        "python3",
        "/Users/camilodiaz/Downloads/ToolBench/toolbench/tooleval/convert_to_answer_format.py",
        "--answer_dir",
        str(answer_dir),
        "--method",
        method,
        "--output",
        str(output_file),
    ]
    subprocess.run(cmd, check=True)
    return output_file


def ensure_openai_pool(data_dir: Path, openai_key: str) -> Path:
    pool_path = data_dir / "openai_pool.json"
    if pool_path.exists():
        return pool_path
    pool = [
        {
            "username": "llmhive",
            "passwd": "generated",
            "api_key": openai_key,
            "organization": "",
        }
    ]
    with pool_path.open("w") as f:
        json.dump(pool, f, indent=2)
    return pool_path


def run_eval(data_dir: Path, openai_key: str) -> float:
    save_path = data_dir / "toolbench_pass_rate"
    save_path.mkdir(parents=True, exist_ok=True)
    pool_path = ensure_openai_pool(data_dir, openai_key)
    cmd = [
        "python3",
        "/Users/camilodiaz/Downloads/ToolBench/toolbench/tooleval/eval_pass_rate.py",
        "--converted_answer_path",
        str(data_dir / "model_predictions_converted"),
        "--save_path",
        str(save_path),
        "--reference_model",
        "llmhive",
        "--test_ids",
        str(data_dir / "test_query_ids"),
        "--max_eval_threads",
        "20",
        "--evaluate_times",
        "4",
        "--evaluator",
        "tooleval_gpt-3.5-turbo_default",
    ]
    subprocess.run(cmd, check=True)

    # Aggregate pass rate from saved JSONs
    total = 0
    passed = 0
    for set_name in TEST_SETS:
        json_path = save_path / f"{set_name}_llmhive.json"
        if not json_path.exists():
            continue
        label_cnt = json.load(json_path.open("r"))
        for qid, entry in label_cnt.items():
            total += 1
            if entry["failed"] <= entry["passed"]:
                passed += 1
    return (passed / total) if total else 0.0


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data_dir", required=True)
    parser.add_argument("--api_key", required=False)
    parser.add_argument("--openai_key", required=False)
    env_sample = os.getenv("INDUSTRY_BENCH_TOOLBENCH_SAMPLES")
    default_sample = int(env_sample) if env_sample and env_sample.isdigit() else 10
    parser.add_argument("--sample_size", type=int, default=default_sample)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--method", default="DFS_woFilter_w2")
    parser.add_argument("--output_path", required=True)
    args = parser.parse_args()

    api_key = args.api_key or os.getenv("API_KEY") or os.getenv("LLMHIVE_API_KEY")
    openai_key = args.openai_key or os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise SystemExit("API_KEY or LLMHIVE_API_KEY is required for ToolBench generation.")
    if not openai_key:
        raise SystemExit("OPENAI_API_KEY is required for ToolEval.")

    data_dir = Path(args.data_dir)
    for set_name in TEST_SETS:
        query_path = write_subset(data_dir, set_name, args.sample_size, args.seed)
        answer_dir = run_pipeline(data_dir, set_name, query_path, api_key, args.method)
        convert_answers(data_dir, set_name, answer_dir, args.method)

    pass_rate = run_eval(data_dir, openai_key)
    payload = {
        "accuracy": round(pass_rate * 100, 4),
        "success_rate": round(pass_rate, 6),
        "attempted": "subset",
        "method": args.method,
    }
    Path(args.output_path).write_text(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
