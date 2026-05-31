"""Tests for real-product answer quality replay benchmark checks."""
from __future__ import annotations

from pathlib import Path

import yaml

from llmhive.app.benchmarks.runner_base import BenchmarkCase
from llmhive.app.benchmarks.scoring import ObjectiveScorer


ROOT = Path(__file__).resolve().parents[2]
SUITE = ROOT / "benchmarks" / "suites" / "answer_quality_replay_v1.yaml"


def _load_cases() -> list[BenchmarkCase]:
    data = yaml.safe_load(SUITE.read_text())
    return [BenchmarkCase.from_yaml(case) for case in data["prompts"]]


def _load_case(case_id: str = "aqr_free_llm_models_20260523") -> BenchmarkCase:
    cases = {case.id: case for case in _load_cases()}
    return cases[case_id]


def test_answer_quality_replay_suite_loads_history():
    cases = _load_cases()
    case = _load_case()

    assert len(cases) == 6
    assert case.id == "aqr_free_llm_models_20260523"
    assert case.category == "answer_quality_replay"
    assert len(case.history) >= 5
    assert case.requirements["quality_replay"]["require_clean_markdown"] is True


def test_answer_quality_replay_good_answer_passes():
    case = _load_case()
    answer = """
For LLMHive, use these current candidates and be explicit about public-free versus direct-provider access:

- **DeepSeek Chat** — exact model ID `deepseek/deepseek-chat`; best for fast reasoning and coding. In LLMHive, select the slug in the model picker or let Automatic routing use the DeepSeek direct API. Docs: https://api-docs.deepseek.com/
- **Qwen3 Next 80B** — exact model ID `qwen/qwen3-next-80b-a3b-instruct:free`; best for multilingual, math, and long-context tasks. In LLMHive, route with preferred_api Dashscope/native_model_id `qwen3-next-80b-a3b-instruct` or use the OpenRouter free slug when available. Docs: https://help.aliyun.com/zh/model-studio/
- **Llama 3.3 70B Instruct** — exact model ID `meta-llama/llama-3.3-70b-instruct:free`; best as a broad general fallback. In LLMHive, use the slug or Groq direct routing where configured. Docs: https://ai.meta.com/llama/
- **Kimi K2.6** — exact direct model `kimi-k2.6` through Moonshot. This is connected in LLMHive via the Moonshot direct API, not claimed as a public-free OpenRouter model unless the free slug is live-verified. Docs: https://platform.moonshot.ai/docs

Legacy models such as GPT-Neo, GPT-J, BLOOM, OPT, Alpaca, and MMLU are historical baselines or benchmarks, not top 2026 recommendations.
No independent consensus percentage is claimed here; model agreement is not factual verification.
"""

    score = ObjectiveScorer().score(answer, case.expected, case.requirements)

    assert score.passed, score.details
    assert score.score == 1.0


def test_answer_quality_replay_bad_answer_fails_core_regressions():
    case = _load_case()
    answer = """
As of today, the best free LLMs are GPT** — Neo**, BLOOM, MMLU, Kimi, Deepseek, Llama, and Qwen.
Kimi is available at https://github. com/KimiModelRepo and the answer is 100% accurate.
All can be connected with APIs.
"""

    score = ObjectiveScorer().score(answer, case.expected, case.requirements)

    assert not score.passed
    assert score.checks["exact_model_ids"] is False
    assert score.checks["legacy_hallucinations_framed"] is False
    assert score.checks["grounded_connection_instructions"] is False
    assert score.checks["clean_markdown"] is False
    assert score.checks["honest_consensus_confidence"] is False


def test_kimi_moonshot_connection_replay_passes_with_direct_api_framing():
    case = _load_case("aqr_kimi_moonshot_connection_20260523")
    answer = """
Kimi is working for LLMHive through the Moonshot direct API. The backend uses
`Kimi_K26_Api_Key`, base URL https://api.moonshot.ai/v1, and the tested model
`kimi-k2.6`. Describe this as direct API access in LLMHive, not as a public free
OpenRouter model unless a public free slug is separately verified.
"""

    score = ObjectiveScorer().score(answer, case.expected, case.requirements)

    assert score.passed, score.details


def test_provider_setup_links_replay_rejects_malformed_urls():
    case = _load_case("aqr_provider_setup_links_20260523")
    bad_answer = """
Use DeepSeek, Qwen, and Kimi. Setup links:
https://github. com/KimiModelRepo
https://deepseek. tech/docs
Then add APIs in LLMHive.
"""

    score = ObjectiveScorer().score(bad_answer, case.expected, case.requirements)

    assert not score.passed
    assert score.checks["valid_links_only"] is False


def test_legacy_opt_requires_word_boundary():
    case = _load_case()
    answer = """
For LLMHive, use optimized current models:
- **DeepSeek Chat** — exact model ID `deepseek/deepseek-chat`; LLMHive slug with direct API and DeepSeek docs: https://api-docs.deepseek.com/
- **Qwen3 Next 80B** — exact model ID `qwen/qwen3-next-80b-a3b-instruct:free`; LLMHive slug via Dashscope docs: https://help.aliyun.com/zh/model-studio/
- **Llama 3.3 70B Instruct** — exact model ID `meta-llama/llama-3.3-70b-instruct:free`; LLMHive model picker via Groq docs: https://ai.meta.com/llama/
- **Kimi K2.6** — exact model `kimi-k2.6`; Moonshot direct API in LLMHive via `Kimi_K26_Api_Key`, base URL https://api.moonshot.ai/v1, docs https://platform.moonshot.ai/docs. It is not public free.
Consensus is model agreement, not factual verification.
"""

    score = ObjectiveScorer().score(answer, case.expected, case.requirements)

    assert score.checks["legacy_hallucinations_framed"] is True


def test_markdown_label_lists_are_not_broken_markdown():
    case = _load_case("aqr_provider_setup_links_20260523")
    answer = """
LLMHive setup links:
- **DeepSeek**
- **Exact model slug** — `deepseek/deepseek-chat`
- **Qwen/Dashscope**
- **Primary exact model slug** — `qwen/qwen3-next-80b-a3b-instruct:free`
- **Kimi/Moonshot**
- **Exact model** — `kimi-k2.6`
Docs: https://api-docs.deepseek.com/ https://help.aliyun.com/zh/model-studio/ https://ai.meta.com/llama/ https://platform.moonshot.ai/docs
Use the slug in LLMHive, direct API for Moonshot, Dashscope, Groq, and DeepSeek.
"""

    score = ObjectiveScorer().score(answer, case.expected, case.requirements)

    assert score.checks["clean_markdown"] is True


def test_replay_markdown_rejects_code_copy_and_flattened_numbering():
    case = _load_case()
    answer = """
LLMHive recommendations:
1. Llama code Copy meta-llama/llama-3.3-70b-instruct:free.2. Qwen code Copy qwen/qwen3-next-80b-a3b-instruct:free.
DeepSeek `deepseek/deepseek-chat`; Kimi `kimi-k2.6`; Moonshot direct API https://api.moonshot.ai/v1; docs https://platform.moonshot.ai/docs.
"""

    score = ObjectiveScorer().score(answer, case.expected, case.requirements)

    assert score.checks["clean_markdown"] is False


def test_honest_consensus_replay_rejects_uncaveated_percent_claims():
    case = _load_case("aqr_honest_consensus_explanation_20260523")
    bad_answer = "The app showed 88% consensus and 100% confidence because the answer was definitely current and accurate."

    score = ObjectiveScorer().score(bad_answer, case.expected, case.requirements)

    assert not score.passed
    assert score.checks["honest_consensus_confidence"] is False


def test_honest_consensus_replay_accepts_nearby_caveat():
    case = _load_case("aqr_honest_consensus_explanation_20260523")
    answer = (
        "When the app reports 88% consensus, it means agreement among different models. "
        "It is model agreement, not factual verification, confidence, or quality."
    )

    score = ObjectiveScorer().score(answer, case.expected, case.requirements)

    assert score.checks["honest_consensus_confidence"] is True


def test_paid_model_replay_passes_with_frontier_catalog():
    case = _load_case("aqr_paid_llm_models_20260523")
    answer = """
For LLMHive paid/frontier routing, use these exact model slugs in the model picker or let Automatic routing choose them:

- **Claude Opus 4.8** — exact model slug `anthropic/claude-opus-4.8`; best for deep reasoning and writing quality. Connect with `preferred_api=anthropic` and `native_model_id=claude-opus-4.8`. Docs: https://docs.anthropic.com/
- **GPT-5.5 Pro** — exact model slug `openai/gpt-5.5-pro`; best for broad agent tasks and tool use. Connect with `preferred_api=openai` and `native_model_id=gpt-5.5-pro`. Docs: https://platform.openai.com/docs
- **Gemini 3.1 Pro Preview** — exact model slug `google/gemini-3.1-pro-preview`; best for long context and multimodal work. Connect with `preferred_api=google`. Docs: https://ai.google.dev/gemini-api/docs
- **Kimi K2.6** — exact model slug `moonshotai/kimi-k2.6`; LLMHive direct API uses `kimi-k2.6`, `Kimi_K26_Api_Key`, and https://api.moonshot.ai/v1. Docs: https://platform.moonshot.ai/docs

This is paid/provider access, not a public-free recommendation.
"""

    score = ObjectiveScorer().score(answer, case.expected, case.requirements)

    assert score.passed, score.details


def test_paid_model_replay_rejects_stale_generic_models():
    case = _load_case("aqr_paid_llm_models_20260523")
    answer = "Use GPT-4 Turbo, Claude 3, Gemini 1 Pro, Cohere Command R, and LLaMA 4 X via their APIs."

    score = ObjectiveScorer().score(answer, case.expected, case.requirements)

    assert not score.passed
    assert score.checks["exact_model_ids"] is False
    assert score.checks["legacy_hallucinations_framed"] is False
