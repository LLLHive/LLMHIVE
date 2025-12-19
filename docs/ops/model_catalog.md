# Model Catalog - Schema & Operations

## Overview

The model catalog is the central repository for all model metadata ingested from OpenRouter. It powers:
- Dynamic model selection in orchestration
- UI model explorer and rankings
- Cost estimation and budget controls
- Capability-aware routing

## Database Schema

### Table: `openrouter_models`

| Column | Type | Description |
|--------|------|-------------|
| id | VARCHAR(255) PK | OpenRouter model ID (e.g., `openai/gpt-4o`) |
| name | VARCHAR(255) | Display name |
| description | TEXT | Model description |
| context_length | INTEGER | Maximum context window |
| author | VARCHAR(100) | Provider/author (derived from ID) |
| family | VARCHAR(100) | Model family (gpt-5.2, claude-4.5, etc.) |
| created_at | TIMESTAMP | Model creation date from OpenRouter |
| updated_at | TIMESTAMP | Last sync timestamp |
| is_active | BOOLEAN | Whether model is currently available |

### Pricing Columns

| Column | Type | Description |
|--------|------|-------------|
| price_per_1m_prompt | DECIMAL(10,6) | USD per 1M input tokens |
| price_per_1m_completion | DECIMAL(10,6) | USD per 1M output tokens |
| price_per_request | DECIMAL(10,6) | Per-request cost (if applicable) |
| price_per_image | DECIMAL(10,6) | Image generation cost |
| price_web_search | DECIMAL(10,6) | Web search cost |
| price_reasoning | DECIMAL(10,6) | Reasoning token cost |
| price_cache_read | DECIMAL(10,6) | Cache read cost |
| price_cache_write | DECIMAL(10,6) | Cache write cost |

### Capability Columns

| Column | Type | Description |
|--------|------|-------------|
| supports_tools | BOOLEAN | Function/tool calling |
| supports_structured | BOOLEAN | Structured output (JSON mode) |
| supports_reasoning | BOOLEAN | Extended thinking/reasoning |
| multimodal_input | BOOLEAN | Image/file input |
| multimodal_output | BOOLEAN | Image/audio output |
| supports_streaming | BOOLEAN | Streaming responses |
| max_completion_tokens | INTEGER | Max output tokens |
| is_moderated | BOOLEAN | Has content moderation |

### Architecture Columns

| Column | Type | Description |
|--------|------|-------------|
| modality | VARCHAR(50) | Primary modality (text, image, etc.) |
| input_modalities | JSONB | Array of input types |
| output_modalities | JSONB | Array of output types |
| tokenizer | VARCHAR(100) | Tokenizer type |
| instruct_type | VARCHAR(100) | Instruction format |

### Metadata Columns

| Column | Type | Description |
|--------|------|-------------|
| supported_parameters | JSONB | Array of supported API params |
| top_provider | JSONB | Top provider info object |
| per_request_limits | JSONB | Rate limits if any |
| raw_data | JSONB | Full API response for reference |
| logo_url | VARCHAR(500) | Resolved logo URL |

## Family Detection

Models are assigned to families using pattern matching:

```python
FAMILY_PATTERNS = {
    "gpt-5.2": r"openai/gpt-5\.2",
    "gpt-4o": r"openai/gpt-4o",
    "o3-pro": r"openai/o3-pro",
    "claude-4.5": r"anthropic/claude-.*-4\.5",
    "claude-4": r"anthropic/claude-.*-4[^.]",
    "gemini-3": r"google/gemini-3",
    "gemini-2.5": r"google/gemini-2\.5",
    "grok-4": r"x-ai/grok-4",
    "llama-4": r"meta-llama/llama-4",
    "deepseek-v3": r"deepseek/deepseek-v3",
}
```

## Logo Resolution

Logos are resolved in order:
1. If OpenRouter provides a logo URL, use it
2. Fall back to author-based mapping:

```python
AUTHOR_LOGOS = {
    "openai": "https://cdn.openrouter.ai/logos/openai.svg",
    "anthropic": "https://cdn.openrouter.ai/logos/anthropic.svg",
    "google": "https://cdn.openrouter.ai/logos/google.svg",
    "x-ai": "https://cdn.openrouter.ai/logos/xai.svg",
    "meta-llama": "https://cdn.openrouter.ai/logos/meta.svg",
    "deepseek": "https://cdn.openrouter.ai/logos/deepseek.svg",
    "mistralai": "https://cdn.openrouter.ai/logos/mistral.svg",
}
```

## Derived Capabilities

Capabilities are derived from `supported_parameters` array:

| Parameter | Capability |
|-----------|------------|
| `tools` | supports_tools |
| `reasoning` | supports_reasoning |
| `structured_outputs` | supports_structured |
| `temperature` | (baseline) |
| `top_p` | (baseline) |

And from `architecture.input_modalities`:

| Modality | Capability |
|----------|------------|
| `image` | multimodal_input |
| `file` | supports_pdf |
| `audio` | supports_audio |

## Sync Operations

### 6-Hour Sync (Existing)
- Triggered by Cloud Scheduler
- Updates model availability and pricing
- Quick incremental update

### Weekly Research Sync (New)
- Full model catalog refresh
- Category rankings update
- New model detection with alerts
- Capability matrix refresh

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/models` | GET | List all models with filters |
| `/api/models/:id` | GET | Get model details |
| `/api/models/top` | GET | Top models per category |
| `/api/models/families` | GET | List model families |
| `/api/openrouter/sync` | POST | Trigger sync |
| `/api/openrouter/sync/status` | GET | Sync status |

