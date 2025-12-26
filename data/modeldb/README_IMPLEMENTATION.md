# LLMHive ModelDB Pipeline

Production-grade model database management with Firestore + Pinecone integration.

## Overview

This pipeline maintains the LLMHive model catalog:

1. **Excel** → Single source of truth for model metadata
2. **Firestore** → Queryable document store for runtime lookups
3. **Pinecone** → Semantic embeddings for intelligent model routing

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
# Optional: OPENROUTER_API_KEY
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
python data/modeldb/run_modeldb_refresh.py
```

## Commands Reference

| Command | Description |
|---------|-------------|
| `python data/modeldb/run_modeldb_refresh.py --doctor` | Check environment and dependencies |
| `python data/modeldb/run_modeldb_refresh.py --dry-run` | Validate without making changes |
| `python data/modeldb/run_modeldb_refresh.py` | Full refresh: OpenRouter → Excel → Firestore + Pinecone |
| `python data/modeldb/run_modeldb_refresh.py --skip-update` | Skip OpenRouter fetch, only sync to Firestore/Pinecone |
| `python data/modeldb/run_modeldb_refresh.py --skip-pipeline` | Only update Excel, skip Firestore/Pinecone |
| `python data/modeldb/run_modeldb_refresh.py -v` | Verbose logging |

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GOOGLE_APPLICATION_CREDENTIALS` | Yes* | Path to service account JSON |
| `GOOGLE_CLOUD_PROJECT` | No | GCP project ID (default: `llmhive-orchestrator`) |
| `PINECONE_API_KEY` | Yes | Pinecone API key |
| `PINECONE_INDEX_NAME` | No | Index name (default: `modeldb-embeddings`) |
| `OPENROUTER_API_KEY` | No | For model enrichment |
| `MODELDB_EMBEDDINGS_ENABLED` | No | Set to `false` to skip embeddings |

\* Not required in Cloud Run with default service account

## NO DATA LOSS Guarantees

The pipeline enforces strict data integrity:

| Guarantee | Enforcement |
|-----------|-------------|
| ✅ All rows preserved | Row count cannot decrease (hard fail + rollback) |
| ✅ All columns preserved | Column count cannot decrease (hard fail + rollback) |
| ✅ No null overwrites | Existing non-null values never replaced with null |
| ✅ Duplicate detection | Duplicate slugs cause hard failure |
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

## Scheduled Execution

**GitHub Actions:** `.github/workflows/modeldb_refresh.yml`

- Runs daily at 02:15 UTC
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

### "Duplicate slugs detected"

The Excel has duplicate `openrouter_slug` values. Clean them up manually before running.

## File Structure

```
data/modeldb/
├── LLMHive_OpenRouter_SingleSheet_ModelDB_Enriched_2025-12-25.xlsx  # Master file
├── run_modeldb_refresh.py        # One-command runner with doctor mode
├── llmhive_modeldb_pipeline.py   # Firestore + Pinecone import
├── llmhive_modeldb_update.py     # OpenRouter enrichment
├── llmhive_modeldb_import.py     # Import alias
├── requirements.txt              # Python dependencies
├── .env.example                  # Environment template (committed)
├── .env                          # Your config (gitignored)
├── README_IMPLEMENTATION.md      # This file
└── archives/                     # Backups and run logs
    ├── LLMHive_*_20251225T120000Z.xlsx
    ├── modeldb_runlog_2025-12-25T120000Z.json
    └── refresh_runlog_2025-12-25T120000Z.json
```
