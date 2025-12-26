# LLMHive ModelDB Pipeline

Production-grade model database management with Firestore + Pinecone integration.

## Overview

This pipeline maintains the LLMHive model catalog:

1. **Excel** → Single source of truth for model metadata
2. **Firestore** → Queryable document store for runtime lookups
3. **Pinecone** → Semantic embeddings for intelligent model routing

## Quick Start

### Prerequisites

1. Python 3.10+
2. Google Cloud credentials (Firestore access)
3. Pinecone API key
4. (Optional) OpenRouter API key for model enrichment

### Setup

```bash
# Navigate to modeldb directory
cd data/modeldb

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys
```

### Run the Pipeline

**One command does it all:**

```bash
python run_modeldb_refresh.py
```

This will:
1. ✅ Archive the current Excel (timestamped backup)
2. ✅ Fetch latest models from OpenRouter
3. ✅ Validate no data loss (rows/columns preserved)
4. ✅ Upsert to Firestore (`model_catalog` collection)
5. ✅ Upsert to Pinecone (semantic embeddings)
6. ✅ Write run log to `archives/`

**Options:**

```bash
# Dry run (validate without writing)
python run_modeldb_refresh.py --dry-run

# Skip OpenRouter update (only run Firestore/Pinecone import)
python run_modeldb_refresh.py --skip-update

# Skip Firestore/Pinecone (only update Excel)
python run_modeldb_refresh.py --skip-pipeline

# Custom Excel path
python run_modeldb_refresh.py --excel /path/to/models.xlsx

# Verbose logging
python run_modeldb_refresh.py -v
```

## Individual Scripts

### 1. Update Script (`llmhive_modeldb_update.py`)

Enriches Excel with OpenRouter data:

```bash
# Update existing Excel
python llmhive_modeldb_update.py --previous models.xlsx --output models_updated.xlsx

# Create new from OpenRouter
python llmhive_modeldb_update.py --from-openrouter --output models_new.xlsx
```

### 2. Pipeline Script (`llmhive_modeldb_pipeline.py`)

Imports Excel to Firestore + Pinecone:

```bash
# Full import
python llmhive_modeldb_pipeline.py --excel models.xlsx

# Firestore only (skip Pinecone)
python llmhive_modeldb_pipeline.py --excel models.xlsx --firestore-only

# Dry run
python llmhive_modeldb_pipeline.py --excel models.xlsx --dry-run
```

### 3. Import Script (`llmhive_modeldb_import.py`)

Alias for pipeline script (backwards compatibility):

```bash
python llmhive_modeldb_import.py --excel models.xlsx
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GOOGLE_APPLICATION_CREDENTIALS` | Yes* | Path to service account JSON |
| `GOOGLE_CLOUD_PROJECT` | No | GCP project ID (default: `llmhive-orchestrator`) |
| `PINECONE_API_KEY` | Yes | Pinecone API key |
| `PINECONE_INDEX_NAME` | No | Index name (default: `modeldb-embeddings`) |
| `OPENROUTER_API_KEY` | No | For model enrichment |
| `MODELDB_EMBEDDINGS_ENABLED` | No | Set to `false` to skip embeddings |

\* Not required if running in Cloud Run with default service account

## Data Guarantees

### NO DATA LOSS

- ✅ All rows preserved across updates
- ✅ All columns preserved across updates
- ✅ New columns added with provenance tracking
- ✅ Values never overwritten with nulls
- ✅ Duplicate slugs detected and rejected
- ✅ Row count decrease = hard failure + rollback

### Provenance Tracking

Enriched fields include:
- `*_source_name` - Where the data came from
- `*_source_url` - API endpoint or URL
- `*_retrieved_at` - ISO timestamp
- `*_confidence` - Confidence score (if applicable)

### Idempotent Operations

- Safe to run repeatedly
- Uses deterministic document IDs
- Upsert semantics (merge, not replace)

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
  
  "payload": { /* full Excel row data */ },
  "payload_overflow": false,
  
  "last_ingested_at": "2025-12-25T00:00:00Z",
  "source_excel_path": "data/modeldb/models.xlsx",
  "schema_version": "1.0.0"
}
```

**Collection: `model_catalog_payloads`** (overflow)

If payload exceeds Firestore document limit (~1MB), the full payload is stored separately:

```json
{
  "model_id": "abc123...",
  "payload": { /* full data */ },
  "payload_sha256": "abc123...",
  "stored_at": "2025-12-25T00:00:00Z"
}
```

## Pinecone Schema

**Index: `modeldb-embeddings`**

- Uses integrated embeddings (`llama-text-embed-v2`)
- Namespace: `model_catalog`

**Record format:**
```json
{
  "_id": "abc123...",
  "content": "Model: gpt-4o\nProvider: openai\n...",
  "model_id": "abc123...",
  "openrouter_slug": "openai/gpt-4o",
  "provider_name": "openai",
  "max_context_tokens": 128000,
  "price_input_usd_per_1m": 2.5,
  "price_output_usd_per_1m": 10.0
}
```

## Rollback

If the pipeline fails:
1. Errors are logged
2. Archive copy is automatically restored
3. Run log captures failure details

Manual rollback:
```bash
# List archives
ls -la archives/

# Restore specific archive
cp archives/models_20251225T120000Z.xlsx LLMHive_OpenRouter_SingleSheet_ModelDB_Enriched_2025-12-25.xlsx
```

## Scheduled Execution

The pipeline integrates with the weekly improvement workflow:

**GitHub Actions:** `.github/workflows/modeldb_refresh.yml`

Runs daily at 02:15 UTC to:
1. Update model catalog from OpenRouter
2. Sync to Firestore + Pinecone
3. Commit changes (if any)

## Troubleshooting

### "Firestore not available"
- Check `GOOGLE_APPLICATION_CREDENTIALS` is set
- Verify service account has Firestore access

### "Pinecone index not found"
- The pipeline auto-creates the index
- Check `PINECONE_API_KEY` is valid

### "Row count decreased"
- This is a safety check to prevent data loss
- Use `--allow-row-decrease` to override (not recommended)

### "Duplicate slugs detected"
- Excel has duplicate `openrouter_slug` values
- Clean up duplicates before running

## File Structure

```
data/modeldb/
├── LLMHive_OpenRouter_SingleSheet_ModelDB_Enriched_2025-12-25.xlsx  # Master file
├── llmhive_modeldb_pipeline.py   # Firestore + Pinecone import
├── llmhive_modeldb_update.py     # OpenRouter enrichment
├── llmhive_modeldb_import.py     # Import alias
├── run_modeldb_refresh.py        # One-command runner
├── requirements.txt              # Python dependencies
├── .env.example                  # Environment template
├── .env                          # Your config (gitignored)
├── README_IMPLEMENTATION.md      # This file
└── archives/                     # Backups and run logs
    ├── models_20251225T120000Z.xlsx
    ├── modeldb_runlog_2025-12-25T120000Z.json
    └── refresh_runlog_2025-12-25T120000Z.json
```

