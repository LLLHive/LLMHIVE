# Advanced Reasoning Methods Implementation

## Overview

This document describes the implementation of advanced reasoning methods for the LLMHive orchestrator, based on the latest model capabilities and rankings as of November 2025.

## Implementation Summary

### Files Created/Modified

**Backend (FastAPI):**

1. **`llmhive/src/llmhive/app/services/model_router.py`** (NEW)
   - Model routing system that maps reasoning methods to optimal models
   - Includes fallback logic for model availability
   - Maps simple reasoning modes (fast/standard/deep) to advanced methods

2. **`llmhive/src/llmhive/app/services/reasoning_prompts.py`** (NEW)
   - Prompt templates for each reasoning method
   - Domain-specific prompt enhancements
   - Specialized prompts for Reflexion and Tree-of-Thought

3. **`llmhive/src/llmhive/app/models/orchestration.py`** (MODIFIED)
   - Added `ReasoningMethod` enum with 6 advanced methods
   - Added `reasoning_method` field to `ChatRequest` (optional)
   - Added `reasoning_method` field to `ChatResponse`

4. **`llmhive/src/llmhive/app/services/orchestrator_adapter.py`** (MODIFIED)
   - Integrated model routing based on reasoning method
   - Enhanced prompts with reasoning method templates
   - Model selection with fallback logic

**Frontend (Next.js):**

1. **`lib/types.ts`** (MODIFIED)
   - Added `ReasoningMethod` type
   - Added `reasoningMethod` field to `OrchestratorSettings`

2. **`app/api/chat/route.ts`** (MODIFIED)
   - Passes `reasoning_method` to backend API

3. **`components/advanced-settings-drawer.tsx`** (MODIFIED)
   - Added reasoning method selector dropdown
   - Shows current method selection

4. **`components/chat-interface.tsx`** (MODIFIED)
   - Updated default settings to include reasoning method

## Supported Reasoning Methods

All methods are based on research: "Implementing Advanced Reasoning Methods with Optimal LLMs (2025)"

### Original Methods

### 1. Chain-of-Thought (CoT)
- **Best Model:** GPT-5.1 (with fallbacks: Claude 4.5, Gemini 3 Pro, Grok 4)
- **Description:** Step-by-step reasoning with explicit intermediate steps
- **Use Case:** Complex problems requiring logical sequences
- **Auto-mapped from:** `reasoning_mode: "fast"` or `"standard"`

### 2. Tree-of-Thought
- **Best Model:** Claude Opus 4.5 (with fallbacks: GPT-5.1, Gemini 3 Pro, Grok 4 Heavy)
- **Description:** Explores multiple reasoning paths, branching and backtracking
- **Use Case:** Problems with multiple valid approaches
- **Auto-mapped from:** `reasoning_mode: "deep"`

### 3. ReAct (Reason + Act)
- **Best Model:** Claude Opus 4.5 (with fallbacks: GPT-5.1, Gemini 3 Pro)
- **Description:** Interleaves reasoning with tool/action execution
- **Use Case:** Tasks requiring external tools, searches, or API calls
- **Auto-mapped from:** None (must be explicitly selected)

### 4. Plan-and-Solve (PAL)
- **Best Model:** GPT-5.1 (with fallbacks: Claude 4.5, Gemini 3 Pro)
- **Description:** First creates a plan/pseudocode, then executes it
- **Use Case:** Complex coding or math problems
- **Auto-mapped from:** None (must be explicitly selected)

### 5. Self-Consistency
- **Best Model:** GPT-5.1 (with fallbacks: Claude 4.5, Gemini 3 Pro, Grok 4 Heavy)
- **Description:** Generates multiple independent reasoning paths and aggregates results
- **Use Case:** High-stakes problems requiring maximum accuracy
- **Auto-mapped from:** None (must be explicitly selected)

### 6. Reflexion
- **Best Model:** Claude Opus 4.5 (with fallbacks: GPT-5.1, Gemini 3 Pro)
- **Description:** Iteratively refines solution through self-critique
- **Use Case:** Problems where initial attempts may have errors
- **Auto-mapped from:** None (must be explicitly selected)

### Research Methods from "Implementing Advanced Reasoning Methods with Optimal LLMs (2025)"

### 7. Hierarchical Task Decomposition (HRM-style)
- **Best Model:** GPT-5.1/GPT-4.1 (with fallbacks: Claude 4.5, Gemini 3 Pro, Grok 4)
- **Description:** Breaks complex problems into a hierarchy of sub-tasks. High-level planner outlines steps, low-level executors solve smaller chunks sequentially
- **Use Case:** Very complex problems that benefit from decomposition into manageable sub-problems
- **Research Ranking:** GPT-4.1 > Claude 2/3 > Gemini Pro/Ultra > PaLM 2 > LLaMA-2 70B
- **Auto-mapped from:** None (must be explicitly selected)

### 8. Iterative Refinement (Diffusion-Inspired)
- **Best Model:** GPT-5.1/GPT-4.1 (with fallbacks: Gemini 3 Pro, Claude 4.5, Grok 4)
- **Description:** Generates initial "draft" solution, then iteratively refines it by correcting errors, filling gaps, and polishing wording (like denoising in diffusion models)
- **Use Case:** Problems where a quick first pass followed by refinement improves quality
- **Research Ranking:** GPT-4.1 > Gemini 2.5 Pro/Ultra > Claude 2 > GPT-3.5 Turbo > Open-source
- **Auto-mapped from:** None (must be explicitly selected)

### 9. Confidence-Based Filtering (DeepConf)
- **Best Model:** GPT-5.1/GPT-4 (with fallbacks: Gemini 3 Pro, Claude 4.5, Grok 4)
- **Description:** Generates multiple candidate answers, filters out low-confidence or self-contradictory ones, then aggregates remaining high-confidence answers
- **Use Case:** Critical problems where accuracy is paramount and we want to filter out uncertain answers
- **Research Ranking:** GPT-4 > Gemini > Claude 2 > GPT-3.5 > Open-source with logits
- **Auto-mapped from:** None (must be explicitly selected)

### 10. Dynamic Planning (Test-Time Decision-Making)
- **Best Model:** GPT-5.1/GPT-4 (with fallbacks: Gemini 3 Pro, Claude 4.5, Grok 4)
- **Description:** Makes on-the-fly decisions about which action or model to invoke next, adapting based on intermediate results (agentic meta-reasoning)
- **Use Case:** Complex, evolving problems where the solution path needs to adapt dynamically
- **Research Ranking:** GPT-4 > Gemini > Claude 2 > GPT-3.5 > Rule-based
- **Auto-mapped from:** None (must be explicitly selected)

## Model Routing Logic

The system uses intelligent routing:

1. **Primary Selection:** Chooses the best model for the reasoning method
2. **Fallback Chain:** If primary unavailable, tries fallbacks in order
3. **Current Model Mapping:** Maps future models (GPT-5.1, Claude 4.5, etc.) to currently available models (GPT-4o, Claude 3.5, etc.)
4. **Stub Fallback:** If no models available, uses stub provider

## Usage

### Backend API

```python
# Request with explicit reasoning method
{
  "prompt": "Solve this complex problem...",
  "reasoning_method": "tree-of-thought",  # Optional
  "reasoning_mode": "deep",  # Will be used if reasoning_method not provided
  "domain_pack": "coding",
  "agent_mode": "team",
  ...
}

# Response includes reasoning method used
{
  "message": "The solution is...",
  "reasoning_method": "tree-of-thought",
  "reasoning_mode": "deep",
  ...
}
```

### Frontend UI

1. **Automatic Selection:** If no reasoning method is selected, it's inferred from `reasoning_mode`:
   - `fast` → `chain-of-thought`
   - `standard` → `chain-of-thought`
   - `deep` → `tree-of-thought`

2. **Manual Selection:** Users can select a specific reasoning method in the Advanced Settings drawer:
   - Opens the advanced settings panel
   - Select "Advanced Reasoning Method"
   - Choose from dropdown (Auto, Chain-of-Thought, Tree-of-Thought, ReAct, Plan-and-Solve, Self-Consistency, Reflexion)

## Prompt Templates

Each reasoning method has a specialized prompt template that:
- Includes domain-specific prefixes (medical, legal, marketing, coding)
- Provides clear instructions for the reasoning approach
- Ensures the model follows the method correctly

### Example: Chain-of-Thought Template

```
Let's work this out step by step.

[User's prompt]

Please think through this problem step by step, showing your reasoning at each stage. After working through the problem, provide your final answer clearly marked.
```

## Model Availability

The system currently maps to available models:

- **GPT-5.1** → `gpt-4o-mini` or `gpt-4o` (fallback)
- **Claude Opus 4.5** → `claude-3-haiku` or `claude-3-5-sonnet` (fallback)
- **Gemini 3 Pro** → `gemini-2.5-pro` (fallback)
- **Grok 4** → `grok-beta` (fallback)

When GPT-5.1, Claude 4.5, Gemini 3 Pro, and Grok 4 become available, update the model router to use them directly.

## Future Enhancements

1. **Implement full ReAct tool integration** - Currently prompts for ReAct format, but tool execution needs to be wired
2. **Add Reflexion iteration loop** - Currently uses single-pass, should implement multi-iteration refinement
3. **Tree-of-Thought branch management** - Add logic to manage and evaluate multiple branches
4. **Self-Consistency sampling** - Implement parallel sampling and voting mechanism
5. **Plan-and-Solve code execution** - Add sandbox for executing generated code

## Testing

To test different reasoning methods:

1. **Via UI:** Select reasoning method in Advanced Settings → send a message
2. **Via API:** Include `reasoning_method` field in ChatRequest
3. **Check logs:** Backend logs show which method and models were used

## Notes

- Reasoning methods are backward compatible - if not specified, inferred from `reasoning_mode`
- All methods work with current model providers (OpenAI, Anthropic, Google, xAI)
- Prompt templates are designed to work with any model, though results vary by model capability
- The system gracefully falls back if preferred models aren't available

