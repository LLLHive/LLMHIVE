# LLMHive Certified Benchmark Snapshot

Use this version for marketing materials derived from the latest completed paired certification runs:
- Free certification: `benchmark_reports/category_benchmarks_free_20260331.json`
- Elite certification: `benchmark_reports/category_benchmarks_elite_20260401.json`
- Leader references: `benchmark_configs/category_leaders_llmhive.json` (`version=2026-03-29`)

## Slide-Ready Table

| Category | Benchmark Test | Free | Elite | Industry #1 | Leading Model | Free Cost | Elite Cost | Leader Cost |
|----------|----------------|------|-------|-------------|---------------|-----------|------------|-------------|
| Reasoning | MMLU | 85.1% | 88.8% | 94.2% | OpenAI o3 | $0.000000 | $0.062315 | ~$0.030/query |
| Coding | HumanEval | 96.0% | 100.0% | 96.1% | DeepSeek R1 | $0.000000 | $0.003851 | ~$0.00055/query |
| Math | GSM8K | 100.0% | 97.9% | 99.2% | GPT-5.2 Pro | $0.000000 | $0.002147 | ~$0.004/query |
| Long Context | LongBench | 100.0% | 100.0% | 95.2% | Gemini 3 Pro | $0.000000 | $0.000000 | ~$0.00150/query |
| Tool Use | ToolBench | 100.0% | 100.0% | 89.3% | Claude Opus 4.5 | $0.000000 | $0.000000 | ~$0.018/query |
| RAG | MS MARCO (MRR@10) | 0.497 | 0.554 | 0.420 | GPT-5.2 | $0.000000 | $0.003723 | ~$0.004/query + retrieval |
| Multilingual | MMMLU | 87.0% | 88.4% | 92.4% | GPT-5.2 Pro | $0.000000 | $0.005438 | ~$0.004/query |
| Dialogue | MT-Bench | 7.5 / 10 | 7.2 / 10 | 9.31 / 10 | Claude Opus 4.5 | $0.000000 | $0.000000 | ~$0.018/query |

## Data Notes

- This table is sourced from the completed paired certification artifacts only, not from the older internal recovery snapshot.
- `RAG` is shown in its native `MRR@10` format, not converted to percentage accuracy.
- Elite `Reasoning` cost is `$0.062315` avg/sample in the certified artifact.
- Elite `Multilingual` cost is `$0.005438` avg/sample in the certified artifact.
- `Dialogue` score is certified, but MT-Bench cost telemetry is still underreported by the external evaluator, so the displayed `Dialogue` cost should not be treated as audited zero spend.

## Suggested Caption

LLMHive's latest certified benchmark pass shows `Elite` leading `Free` in reasoning, coding, RAG, and multilingual performance, while both tiers hit `100%` in long-context and tool-use evaluation. Results are drawn from completed paired certification runs using the same benchmark protocol and sample sizes for both tiers.

## Suggested Speaker Notes

- `Elite` outperformed `Free` in `4 of 8` categories and matched or exceeded category leaders in `coding`, `long context`, `tool use`, and `RAG`.
- `Free` maintained strong baseline performance with `100%` on `math`, `long context`, and `tool use`.
- `Elite` showed the clearest premium lift in `reasoning`, `RAG`, and `multilingual`, which are high-value enterprise workloads.
- `RAG` is shown as `MRR@10`, not percentage accuracy, to preserve metric integrity.
- `Dialogue` is shown on the benchmark's native `0-10` scale.

## Claim Guardrails

- Safe claim: "Certified paired benchmark runs using the same protocol for Free and Elite tiers."
- Safe claim: "Elite improved on Free in reasoning, coding, RAG, and multilingual benchmarks."
- Safe claim: "Both tiers achieved 100% in long-context and tool-use certification."
- Avoid claim: "Best model in the world" or "beats every frontier model overall."
- Avoid claim: "RAG accuracy" when referring to `MRR@10`; use `retrieval ranking quality` or `MRR@10`.

## Internal Notes

- Elite total measured benchmark cost: `$7.7690`
- Free total measured benchmark cost: `$0.0000`
- Leader references are public benchmark anchors, not measured in this paired run.
