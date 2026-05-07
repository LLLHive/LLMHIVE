# LLMHive Website Benchmark Version

## Headline

Certified performance across reasoning, coding, retrieval, multilingual tasks, and long-context workflows.

## Subheadline

LLMHive's latest paired certification run shows strong baseline performance in `Free` and meaningful premium lift in `Elite`, using the same benchmark protocol across both tiers.

## Website Table

| Category | Benchmark Test | Free | Elite | Industry Leader |
|----------|----------------|------|-------|-----------------|
| Reasoning | MMLU | 85.1% | 88.8% | 94.2% |
| Coding | HumanEval | 96.0% | 100.0% | 96.1% |
| Math | GSM8K | 100.0% | 97.9% | 99.2% |
| Long Context | LongBench | 100.0% | 100.0% | 95.2% |
| Tool Use | ToolBench | 100.0% | 100.0% | 89.3% |
| RAG | MS MARCO (MRR@10) | 0.497 | 0.554 | 0.420 |
| Multilingual | MMMLU | 87.0% | 88.4% | 92.4% |
| Dialogue | MT-Bench | 7.5 / 10 | 7.2 / 10 | 9.31 / 10 |

## Supporting Copy

`Elite` improves on `Free` in reasoning, coding, RAG, and multilingual evaluation, while both tiers reach `100%` in long-context and tool-use certification. This gives teams a clear upgrade path: strong zero-cost baseline performance, with premium gains for more demanding workloads.

## Small-Print Notes

- `RAG` is reported as `MRR@10`, the benchmark's native retrieval-ranking metric.
- `Dialogue` is reported on the benchmark's native `0-10` scale.
- Results come from completed paired certification runs using the same benchmark protocol for both tiers.
- `Reasoning` and `Multilingual` values in this page are sourced from the certified paired artifact, not the superseded internal recovery snapshot.

## Source Note

Certification artifacts:
- `benchmark_reports/category_benchmarks_free_20260331.json`
- `benchmark_reports/category_benchmarks_elite_20260401.json`
