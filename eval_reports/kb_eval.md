# LLMHive KB Orchestrator Evaluation Report

**Date**: 2025-12-27 18:33:44 UTC

## Summary

- **Total Tests**: 10
- **Passed**: 10
- **Failed**: 0
- **Pass Rate**: 100.0%

## Results by Category

### Math
- Tests: 2
- Pipeline Match Rate: 100%
- Avg Latency: 130ms

### Tool_Use
- Tests: 1
- Pipeline Match Rate: 100%
- Avg Latency: 2ms

### Factual
- Tests: 2
- Pipeline Match Rate: 100%
- Avg Latency: 2ms

### Writing
- Tests: 2
- Pipeline Match Rate: 100%
- Avg Latency: 1ms

### Coding
- Tests: 1
- Pipeline Match Rate: 100%
- Avg Latency: 1ms

### Medical
- Tests: 1
- Pipeline Match Rate: 100%
- Avg Latency: 1ms

### Logic
- Tests: 1
- Pipeline Match Rate: 100%
- Avg Latency: 2ms

## Detailed Results

| Test | Category | Pipeline | Expected | Match | CoT Safe |
|------|----------|----------|----------|-------|----------|
| math_arithmetic | math | PIPELINE_MATH_REASONING | PIPELINE_MATH_REASONING | ✅ | ✅ |
| math_word_problem | math | PIPELINE_MATH_REASONING | PIPELINE_MATH_REASONING | ✅ | ✅ |
| tool_search | tool_use | PIPELINE_TOOL_USE_REACT | PIPELINE_TOOL_USE_REACT | ✅ | ✅ |
| factual_with_search | factual | PIPELINE_TOOL_USE_REACT | PIPELINE_TOOL_USE_REACT | ✅ | ✅ |
| factual_with_citations | factual | PIPELINE_RAG | PIPELINE_RAG | ✅ | ✅ |
| writing_simple | writing | PIPELINE_BASELINE_SINGLECALL | PIPELINE_BASELINE_SINGLECALL | ✅ | ✅ |
| writing_detailed | writing | PIPELINE_BASELINE_SINGLECALL | PIPELINE_BASELINE_SINGLECALL | ✅ | ✅ |
| coding_function | coding | PIPELINE_CODING_AGENT | PIPELINE_CODING_AGENT | ✅ | ✅ |
| medical_question | medical | PIPELINE_BASELINE_SINGLECALL | PIPELINE_BASELINE_SINGLECALL | ✅ | ✅ |
| logic_reasoning | logic | PIPELINE_MATH_REASONING | PIPELINE_MATH_REASONING | ✅ | ✅ |

## Notes

- **Pipeline Match**: Whether the selected pipeline matches expected
- **CoT Safe**: No chain-of-thought exposed in final answer
- This is an internal evaluation harness, not external benchmark claims