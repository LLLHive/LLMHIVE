# LLMHive Techniques Knowledge Base v1.0

> **as_of_date**: 2025-12-26

This Knowledge Base contains a curated collection of AI reasoning techniques, architectures, benchmarks, and evaluation rubrics used by the LLMHive orchestrator to select optimal reasoning strategies for different query types.

## Contents

| Table | Description | Count |
|-------|-------------|-------|
| `techniques` | Reasoning techniques (CoT, ToT, ReAct, etc.) | 12 |
| `architectures` | Architecture patterns (Single-Agent, Multi-Agent, etc.) | 7 |
| `benchmarks` | Evaluation benchmarks (GSM8K, MMLU, etc.) | 10 |
| `benchmark_results` | Published results for techniques | 8 |
| `evaluation_rubric` | Quality criteria (DQ, HHH) | 2 |
| `rankings` | Model performance rankings | 10 |
| `sources` | Academic sources and references | 12 |
| `technique_source_map` | Technique-to-source mappings | 12 |

## Techniques Overview

| ID | Name | Architecture | Reasoning Type |
|----|------|--------------|----------------|
| TECH_0001 | Chain-of-Thought Prompting | Single-Agent LLM | Stepwise-deductive |
| TECH_0002 | Self-Consistency Decoding | Single-Agent LLM | Multi-path voting |
| TECH_0003 | Tree-of-Thought (ToT) | Single-Agent LLM | Search-based reasoning |
| TECH_0004 | ReAct (Reason+Act) | Single-Agent with Tools | Tool-augmented |
| TECH_0005 | Self-Refine Prompting | Single-Agent LLM | Self-critique |
| TECH_0006 | Retrieval-Augmented Generation (RAG) | Single-Agent with Tools | Knowledge-augmented |
| TECH_0007 | Multi-Agent Debate (MAD) | Multi-Agent Peer | Dialectical |
| TECH_0008 | Expert Panel (Ensemble) | Multi-Agent Parallel | Ensemble reasoning |
| TECH_0009 | Challenge & Refine Loop | Multi-Agent Iterative | Adversarial refinement |
| TECH_0010 | ChatDev Multi-Stage | Multi-Agent Sequential | Workflow reasoning |
| TECH_0011 | MacNet DAG Orchestration | Multi-Agent Hierarchical | Distributed reasoning |
| TECH_0012 | HuggingGPT Orchestrator | Multi-Model Hierarchical | Plan-and-execute |

## Architecture Patterns

| ID | Pattern | Description |
|----|---------|-------------|
| ARCH_0001 | Single-Agent Monolithic | Single LLM handles query end-to-end |
| ARCH_0002 | Single-Agent + Tools | Single LLM with tool use (APIs, search) |
| ARCH_0003 | Multi-Agent Parallel | Multiple agents work independently, outputs combined |
| ARCH_0004 | Multi-Agent Sequential | Pipeline of agents passing context |
| ARCH_0005 | Multi-Agent Hierarchical | Orchestrator coordinates subordinate agents |
| ARCH_0006 | Multi-Agent Adversarial | Debate/critique format for refinement |
| ARCH_0007 | Iterative Self-Improvement | Multi-round self-critique and update |

## Files

- `LLMHive_Techniques_KB_v1.json` - Machine-readable KB (required)
- `LLMHive_Techniques_KB_v1.xlsx` - Excel version for human review
- `seed/LLMHive_Techniques_KB_v1_seed.txt` - Source data in CSV format

## Usage

The KB is loaded at runtime by `llmhive.kb.technique_kb.TechniqueKB`:

```python
from llmhive.kb import get_technique_kb

kb = get_technique_kb()

# Lookup technique
tech = kb.get_technique("TECH_0001")
print(tech.name)  # "Chain-of-Thought Prompting"

# Search techniques
results = kb.search_techniques("tool use")

# Get recommendations
recs = kb.recommend_techniques(
    query="Solve this math problem step by step",
    reasoning_type="mathematical_reasoning"
)
```

## Ingestion

To regenerate the KB from the seed file:

```bash
python scripts/import_llmhive_kb.py
```

This parses `seed/LLMHive_Techniques_KB_v1_seed.txt` and outputs:
- `LLMHive_Techniques_KB_v1.json`
- `LLMHive_Techniques_KB_v1.xlsx` (optional)

## Sources

All techniques are backed by peer-reviewed research or reputable preprints. See the `sources` table in the KB for full citations (SRC_0001 through SRC_0012).

## Extending the KB

To add a new technique:

1. Add a new row to `techniques` in the seed file with unique `TECH_####` ID
2. Add corresponding source to `sources` table
3. Add mapping to `technique_source_map`
4. Re-run ingestion script
5. Update pipeline selector if the technique requires a new pipeline
