# Answer Quality Replay Benchmarks

The answer quality replay suite turns real user-facing failures into deterministic
regression tests. It complements the synthetic reasoning benchmarks by checking
whether final answers are product-grade: current, grounded in LLMHive wiring,
well formatted, and honest about confidence.

## Current Replay Suite

`benchmarks/suites/answer_quality_replay_v1.yaml`

Current cases:

- `aqr_free_llm_models_20260523` replays the failed free-LLM recommendation
  exchange where the answer drifted through legacy models, omitted exact IDs,
  ignored corrections, produced fake links, and showed misleading consensus.
- `aqr_kimi_moonshot_connection_20260523` verifies Kimi is described as
  working through LLMHive's Moonshot direct API path while preserving the
  distinction from public-free OpenRouter access.
- `aqr_provider_setup_links_20260523` catches fake or malformed setup links for
  DeepSeek, Qwen/Dashscope, Llama/Groq, and Kimi/Moonshot.
- `aqr_honest_consensus_explanation_20260523` checks that high consensus or
  confidence labels are explained as model/backend signals, not guaranteed
  factual correctness.
- `aqr_free_llm_models_ui_format_20260523` replays the exact public-free model
  prompt that exposed flattened numbering, `code Copy` leakage, malformed UI
  rendering, and unsupported consensus badges.
- `aqr_paid_llm_models_20260523` covers paid/frontier model recommendations so
  the app does not fall back to stale generic names like GPT-4 Turbo, Claude 3,
  Gemini 1 Pro, or invented Llama variants.

The scorer checks:

- Exact model IDs, not just family names.
- Legacy model mentions are framed as historical or not recommended.
- LLMHive-specific connection guidance is present.
- Links are syntactically valid and not fake/malformed `github. com` style URLs.
- Markdown is not broken.
- UI-copy artifacts such as `code Copy` and flattened `Documentation.2.` style
  numbering are rejected.
- User corrections across turns are preserved.
- Consensus/confidence claims are not overstated.

## Run Locally

Contract tests only:

```bash
python3 -m pytest llmhive/tests/test_answer_quality_replay_scoring.py
```

Run through the benchmark CLI:

```bash
python3 -m llmhive.app.benchmarks.cli \
  --suite benchmarks/suites/answer_quality_replay_v1.yaml \
  --systems llmhive \
  --mode local \
  --timeout 180
```

Production HTTP mode:

```bash
LLMHIVE_BENCHMARK_URL=https://llmhive-orchestrator-792354158895.us-east1.run.app \
LLMHIVE_API_KEY="$LLMHIVE_API_KEY" \
LLMHIVE_SCHEDULED_BENCHMARK_SECRET="$LLMHIVE_SCHEDULED_BENCHMARK_SECRET" \
python3 -m llmhive.app.benchmarks.cli \
  --suite benchmarks/suites/answer_quality_replay_v1.yaml \
  --systems llmhive \
  --mode http \
  --timeout 180
```

## CI Policy

`.github/workflows/quality-regression.yml` runs the replay checks as a
non-blocking job:

- Always runs deterministic scorer/fixture tests.
- Runs live production replay on schedule or manual dispatch when secrets are
  available.
- Uploads replay artifacts for review.

Promote to blocking only after at least 3-5 real replay cases are stable and
the failure threshold is trusted.

## Adding A Replay

Add a prompt under `benchmarks/suites/answer_quality_replay_v1.yaml` with:

- The final user prompt as `prompt`.
- Previous turns as `history`.
- `requirements.quality_replay` checks for required exact IDs, terms, links,
  formatting, and confidence behavior.
- `scoring.objective_weight: 1.0` and `rubric_weight: 0.0` for deterministic
  gating.

Then add or update a focused test in
`llmhive/tests/test_answer_quality_replay_scoring.py`.
