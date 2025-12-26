# LLMHive ModelDB Pipeline

Production-grade model database management with enrichment, Firestore, and Pinecone integration.

## Overview

This pipeline maintains the LLMHive model catalog:

1. **OpenRouter Update** → Fetch latest models from OpenRouter API
2. **Enrichment Layer** → Add rankings, benchmarks, language skills, telemetry
3. **Excel** → Single source of truth for model metadata
4. **Firestore** → Queryable document store for runtime lookups
5. **Pinecone** → Semantic embeddings for intelligent model routing

## Quick Start (Local Development)

### Step 1: Set Up Python Environment

```bash
# From the repo root
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r data/modeldb/requirements.txt
```

### Step 2: Configure Environment

```bash
# Copy the example config
cp data/modeldb/.env.example data/modeldb/.env

# Edit with your API keys
# Required: GOOGLE_APPLICATION_CREDENTIALS, PINECONE_API_KEY
# Optional but recommended: OPENROUTER_API_KEY
nano data/modeldb/.env  # or use your editor
```

### Step 3: Run Doctor to Verify Setup

```bash
python data/modeldb/run_modeldb_refresh.py --doctor
```

Expected output when healthy:
```
✅ ALL CHECKS PASSED - Ready to run!
```

### Step 4: Dry Run (Validate Without Changes)

```bash
python data/modeldb/run_modeldb_refresh.py --dry-run
```

### Step 5: Full Run

```bash
# Full run with all enrichments
python data/modeldb/run_modeldb_refresh.py

# Skip expensive evals and telemetry (faster, no API costs)
python data/modeldb/run_modeldb_refresh.py --evals-enabled false --telemetry-enabled false
```

## Commands Reference

| Command | Description |
|---------|-------------|
| `python data/modeldb/run_modeldb_refresh.py --doctor` | Check environment and dependencies |
| `python data/modeldb/run_modeldb_refresh.py --dry-run` | Validate without making changes |
| `python data/modeldb/run_modeldb_refresh.py` | Full refresh with all enrichments |
| `python data/modeldb/run_modeldb_refresh.py --skip-update` | Skip OpenRouter fetch |
| `python data/modeldb/run_modeldb_refresh.py --skip-enrichment` | Skip rankings/benchmarks/evals |
| `python data/modeldb/run_modeldb_refresh.py --skip-pipeline` | Only update Excel, skip Firestore/Pinecone |
| `python data/modeldb/run_modeldb_refresh.py --evals-enabled false` | Skip eval harness (saves API cost) |
| `python data/modeldb/run_modeldb_refresh.py --telemetry-enabled false` | Skip telemetry probes (saves API cost) |
| `python data/modeldb/run_modeldb_refresh.py --evals-max-models 10` | Limit evals to 10 models |
| `python data/modeldb/run_modeldb_refresh.py --telemetry-max-models 10` | Limit telemetry to 10 models |
| `python data/modeldb/run_modeldb_refresh.py -v` | Verbose logging |

## Enrichment Layer

The enrichment layer adds data from multiple sources:

### 1. OpenRouter Rankings
- `openrouter_rank_context_length` - Rank by context window size
- `openrouter_rank_price_input` - Rank by input token cost
- `openrouter_rank_price_output` - Rank by output token cost
- `openrouter_rankings_json_full` - Full ranking data as JSON

### 2. LMSYS Chatbot Arena
- `arena_elo_overall` - Overall Elo rating
- `arena_rank_overall` - Overall rank
- `arena_match_status` - Match quality (exact/heuristic/unmatched)

### 3. HuggingFace Open LLM Leaderboard
- `hf_ollb_mmlu` - MMLU benchmark score
- `hf_ollb_arc_challenge` - ARC Challenge score
- `hf_ollb_hellaswag` - HellaSwag score
- `hf_ollb_truthfulqa` - TruthfulQA score
- `hf_ollb_avg` - Average score

### 4. Provider Documentation
- Fills missing values for `max_context_tokens`, `modalities`, `supports_function_calling`

### 5. Derived Rankings (computed from existing data)
- `rank_context_length_desc` - Rank by context (1 = largest)
- `rank_cost_input_asc` - Rank by cost (1 = cheapest)
- `rank_tool_support` - Rank by tool capabilities
- `rank_multimodal_support` - Rank by modality support

### 6. Eval Harness (optional, costs API credits)
- `eval_programming_languages_score` - Programming language skill score
- `eval_languages_score` - Natural language skill score
- `eval_tool_use_score` - Tool use capability score

### 7. Telemetry Probe (optional, costs API credits)
- `telemetry_latency_p50_ms` - Median latency
- `telemetry_latency_p95_ms` - 95th percentile latency
- `telemetry_tps_p50` - Tokens per second
- `telemetry_error_rate` - Error rate across trials

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GOOGLE_APPLICATION_CREDENTIALS` | Yes* | Path to service account JSON |
| `GOOGLE_CLOUD_PROJECT` | No | GCP project ID (default: `llmhive-orchestrator`) |
| `PINECONE_API_KEY` | Yes | Pinecone API key |
| `PINECONE_INDEX_NAME` | No | Index name (default: `modeldb-embeddings`) |
| `OPENROUTER_API_KEY` | Yes** | For enrichment and eval harness |
| `MODELDB_EMBEDDINGS_ENABLED` | No | Set to `false` to skip embeddings |

\* Not required in Cloud Run with default service account
\** Required for evals and telemetry; optional for basic enrichment

## NO DATA LOSS Guarantees

The pipeline enforces strict data integrity:

| Guarantee | Enforcement |
|-----------|-------------|
| ✅ All rows preserved | Row count cannot decrease (hard fail + rollback) |
| ✅ All columns preserved | Column NAME superset enforced (hard fail + rollback) |
| ✅ No null overwrites | Existing non-null values never replaced with null |
| ✅ Duplicate detection | Duplicate slugs cause hard failure |
| ✅ Schema baseline | `schema_baseline_columns.json` defines minimum columns |
| ✅ Automatic rollback | On any failure, archived Excel is restored |

### Provenance Tracking

Enriched fields include provenance metadata:
- `*_source_name` - Where the data came from
- `*_source_url` - API endpoint or URL
- `*_retrieved_at` - ISO timestamp of retrieval
- `*_confidence` - Confidence score (if applicable)

## How Rollback Works

1. **Before any modification**: The Excel file is archived with timestamp
   - Example: `archives/LLMHive_..._20251225T120000Z.xlsx`

2. **On failure**: The pipeline automatically restores the archived version
   - You'll see: `Rollback successful`

3. **Manual rollback**:
   ```bash
   # List archives
   ls -la data/modeldb/archives/*.xlsx
   
   # Restore specific archive
   cp data/modeldb/archives/LLMHive_*_YYYYMMDDTHHMMSSZ.xlsx \
      data/modeldb/LLMHive_OpenRouter_SingleSheet_ModelDB_Enriched_2025-12-25.xlsx
   ```

## Expected Runtime and Cost

| Enricher | Runtime | API Cost |
|----------|---------|----------|
| OpenRouter Rankings | ~10s | Free (public API) |
| LMSYS Arena | ~5s | Free (HuggingFace datasets) |
| HF Leaderboard | ~5s | Free (HuggingFace datasets) |
| Provider Docs | ~1s | Free (local reference) |
| Derived Rankings | ~1s | Free (computed) |
| Eval Harness | ~10-30min | $0.50-$5 (depends on model count) |
| Telemetry Probe | ~5-15min | $0.10-$1 (depends on trials) |
| **Full Run (no evals)** | ~30s | ~Free |
| **Full Run (with evals)** | ~30-45min | ~$1-$6 |

## Verifying Results

### Check Firestore

```python
from google.cloud import firestore
db = firestore.Client(project="llmhive-orchestrator")
docs = db.collection("model_catalog").limit(5).stream()
for doc in docs:
    print(f"{doc.id}: {doc.to_dict().get('openrouter_slug')}")
```

### Check Pinecone

```python
from pinecone import Pinecone
pc = Pinecone(api_key="YOUR_KEY")
index = pc.Index("modeldb-embeddings")
stats = index.describe_index_stats()
print(f"Total vectors: {stats.total_vector_count}")
```

## Firestore Schema

**Collection: `model_catalog`**

```json
{
  "model_id": "abc123...",
  "openrouter_slug": "openai/gpt-4o",
  "model_name": "gpt-4o",
  "provider_name": "openai",
  "model_family": "GPT-4",
  "max_context_tokens": 128000,
  "price_input_usd_per_1m": 2.50,
  "price_output_usd_per_1m": 10.00,
  "modalities": "text,image",
  "orchestration_roles": "reasoning,coding,creative",
  
  "arena_elo_overall": 1280,
  "openrouter_rank_context_length": 15,
  "hf_ollb_mmlu": 88.5,
  "eval_programming_languages_score": 0.92,
  "telemetry_latency_p50_ms": 450,
  
  "payload": { /* full Excel row data */ },
  "payload_overflow": false,
  
  "last_ingested_at": "2025-12-25T00:00:00Z",
  "source_excel_path": "data/modeldb/models.xlsx",
  "schema_version": "1.0.0"
}
```

**Collection: `model_catalog_payloads`** (overflow for large docs)

## Pinecone Schema

**Index: `modeldb-embeddings`**

- Uses integrated embeddings (`llama-text-embed-v2`)
- Namespace: `model_catalog`
- Metadata filters: `model_id`, `openrouter_slug`, `provider_name`, `max_context_tokens`, `price_*`, `arena_*`, `eval_*`

## Scheduled Execution

**GitHub Actions:** `.github/workflows/modeldb_refresh.yml`

- Runs daily at 02:15 UTC
- OpenRouter + rankings enrichment: daily
- Eval harness + telemetry: weekly (to control costs)
- Auto-commits updated Excel on success
- Uploads run logs as artifacts

## Troubleshooting

### "Missing data/modeldb/.env"

```bash
cp data/modeldb/.env.example data/modeldb/.env
# Then edit and fill in your API keys
```

### "GOOGLE_APPLICATION_CREDENTIALS: FILE NOT FOUND"

The path in your `.env` points to a non-existent file. Get a service account key from GCP Console.

### "Firestore not available"

1. Check `GOOGLE_APPLICATION_CREDENTIALS` is set to valid file
2. Verify service account has Firestore read/write permissions

### "Row count decreased"

This safety check prevents data loss. If intentional:
```bash
python data/modeldb/run_modeldb_refresh.py --allow-row-decrease
```

### "Missing columns"

The pipeline enforces column NAME superset. The `schema_baseline_columns.json` file defines the minimum required columns. If you intentionally want to remove columns:
1. Update the baseline file
2. Run again

### "Duplicate slugs detected"

The Excel has duplicate `openrouter_slug` values. Clean them up manually before running.

## File Structure

```
data/modeldb/
├── LLMHive_OpenRouter_SingleSheet_ModelDB_Enriched_2025-12-25.xlsx  # Master file
├── run_modeldb_refresh.py        # One-command runner with doctor mode
├── llmhive_modeldb_enrich.py     # Enrichment orchestrator
├── llmhive_modeldb_pipeline.py   # Firestore + Pinecone import
├── llmhive_modeldb_update.py     # OpenRouter catalog update
├── schema_baseline_columns.json  # Column name baseline (committed)
├── requirements.txt              # Python dependencies
├── .env.example                  # Environment template (committed)
├── .env                          # Your config (gitignored)
├── README_IMPLEMENTATION.md      # This file
├── enrichers/                    # Enricher modules
│   ├── __init__.py
│   ├── base.py
│   ├── openrouter_rankings.py
│   ├── lmsys_arena.py
│   ├── hf_open_llm_leaderboard.py
│   ├── provider_docs_extract.py
│   ├── derived_rankings.py
│   ├── eval_harness.py
│   └── telemetry_probe.py
├── evals/                        # Eval prompt sets
│   ├── languages/
│   ├── programming_languages/
│   └── tool_use/
└── archives/                     # Backups and run logs
    ├── LLMHive_*_20251225T120000Z.xlsx
    ├── enrich_runlog_*.json
    └── refresh_runlog_*.json
```
