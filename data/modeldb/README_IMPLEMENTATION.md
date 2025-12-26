# LLMHive ModelDB Pipeline

Production-grade model database management with enrichment, Firestore, and Pinecone integration.

## Overview

This pipeline maintains the LLMHive model catalog:

1. **OpenRouter Update** → Fetch latest models from OpenRouter API
2. **Enrichment Layer** → Add rankings, benchmarks, language skills, telemetry
3. **Excel** → Single source of truth for model metadata
4. **Firestore** → Queryable document store for runtime lookups
5. **Pinecone** → Semantic embeddings for intelligent model routing

## How to Run & Example Usage

This section provides complete, verified instructions for running the ModelDB pipeline.

> **⚠️ Important**: Close Excel before running the pipeline to avoid "file locked" errors on macOS/Windows.

---

### 1. One-Time Environment Setup

#### macOS / Linux

```bash
# Navigate to repo root
cd /path/to/LLMHIVE

# Create virtual environment
python3 -m venv .venv

# Activate virtual environment
source .venv/bin/activate

# Upgrade pip
python -m pip install --upgrade pip

# Install dependencies
python -m pip install -r data/modeldb/requirements.txt

# Copy environment template
cp data/modeldb/.env.example data/modeldb/.env

# Edit .env with your API keys
nano data/modeldb/.env
# OR: code data/modeldb/.env
```

#### Windows PowerShell

```powershell
# Navigate to repo root
cd C:\path\to\LLMHIVE

# Create virtual environment
python -m venv .venv

# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Upgrade pip
python -m pip install --upgrade pip

# Install dependencies
python -m pip install -r data\modeldb\requirements.txt

# Copy environment template
Copy-Item data\modeldb\.env.example data\modeldb\.env

# Edit .env with your API keys
notepad data\modeldb\.env
```

---

### 2. Doctor Check (Verify Setup)

```bash
python data/modeldb/run_modeldb_refresh.py --doctor
```

**Expected output when healthy:**

```
======================================================================
LLMHive ModelDB Pipeline - Doctor Mode
======================================================================

🐍 Python Environment
   Executable: /path/to/.venv/bin/python3
   Virtual Env: ✅ Active

📦 Dependencies
   ✅ pandas: installed
   ✅ openpyxl: installed
   ✅ requests: installed
   ✅ tenacity: installed
   ✅ dotenv: installed
   ✅ google.cloud.firestore: installed
   ✅ pinecone: installed

📁 Files
   ✅ Canonical Excel: LLMHive_OpenRouter_SingleSheet_ModelDB_Enriched_2025-12-25.xlsx
      Rows: 353, Columns: 170
   ✅ Archive Dir: exists (1 Excel, 1 logs)
      Writable: ✅

🔐 Environment Configuration
   ✅ .env file: exists

   Environment Variables:
   ✅ GOOGLE_APPLICATION_CREDENTIALS: SET ✓ file exists
   ✅ PINECONE_API_KEY: SET
   ✅ OPENROUTER_API_KEY: SET
   ...

======================================================================
✅ ALL CHECKS PASSED - Ready to run!
```

If issues are found, the doctor will exit with code 2 and print actionable fixes.

---

### 3. Dry Run (Validate Without Changes)

```bash
python data/modeldb/run_modeldb_refresh.py --dry-run
```

**Guarantee**: Dry run does NOT modify:
- The canonical Excel file
- The archives folder
- Firestore
- Pinecone

**Verified behavior** (SHA256 hash unchanged):
```
[DRY RUN] Would archive ...
[DRY RUN] Would save to ...
[DRY RUN] Would validate updated file
[DRY RUN] Would write run log
✅ Refresh completed successfully!
```

---

### 4. Full Run (Standard Enrichment, No Evals/Telemetry)

For most use cases, skip expensive API calls:

```bash
python data/modeldb/run_modeldb_refresh.py --evals-enabled false --telemetry-enabled false
```

**Expected log sequence:**

```
======================================================================
ModelDB Refresh Runner
======================================================================
Excel: .../LLMHive_OpenRouter_SingleSheet_ModelDB_Enriched_2025-12-25.xlsx
Archive Dir: .../archives
Dry Run: False
Skip Update: False
Skip Enrichment: False
Skip Pipeline: False
Evals Enabled: False
Telemetry Enabled: False
======================================================================
Existing file has 353 rows, 170 columns
Archived: LLMHive_..._20251226T040000Z.xlsx
Running: llmhive_modeldb_update.py ...
Update step completed
Running: llmhive_modeldb_enrich.py ...
Enrichment step completed
✅ Validation passed: 353 rows, 175 columns
   Added 5 new columns
Running: llmhive_modeldb_pipeline.py ...
Pipeline step completed
======================================================================
✅ Refresh completed successfully!
======================================================================
```

---

### 5. Full Run with Evals & Telemetry (Costs API Credits)

```bash
# Limit to 10 models each to control costs
python data/modeldb/run_modeldb_refresh.py \
  --evals-enabled true --evals-max-models 10 \
  --telemetry-enabled true --telemetry-max-models 10 --telemetry-trials 3
```

---

### 6. Other Flags & Examples

| Flag | Description |
|------|-------------|
| `--dry-run` | Validate without writing anything |
| `--skip-update` | Skip OpenRouter catalog fetch |
| `--skip-enrichment` | Skip rankings/benchmarks/evals layer |
| `--skip-pipeline` | Skip Firestore/Pinecone sync |
| `--evals-enabled false` | Disable eval harness (saves cost) |
| `--telemetry-enabled false` | Disable telemetry probes (saves cost) |
| `--evals-max-models N` | Limit evals to N models |
| `--telemetry-max-models N` | Limit telemetry to N models |
| `--telemetry-trials N` | Number of probes per model (default: 3) |
| `--skip-expensive` | Skip expensive models in evals |
| `--allow-row-decrease` | Allow row count to decrease (safety override) |
| `-v, --verbose` | Enable debug logging |

**Combining flags:**

```bash
# Only update Excel from OpenRouter (no enrichment, no Firestore/Pinecone)
python data/modeldb/run_modeldb_refresh.py --skip-enrichment --skip-pipeline

# Only sync existing Excel to Firestore/Pinecone (no updates)
python data/modeldb/run_modeldb_refresh.py --skip-update --skip-enrichment

# Full run with limited eval cost
python data/modeldb/run_modeldb_refresh.py --evals-enabled true --evals-max-models 20 --skip-expensive
```

---

### 7. Post-Run Inspection: Verify the Excel

After a run, inspect the Excel to confirm enrichment worked:

**Key columns to look for:**
- `openrouter_slug` - Model identifier (should exist for all rows)
- `openrouter_rank_context_length` - Rank by context window
- `openrouter_rank_price_input` - Rank by input cost
- `rank_context_length_desc` - Derived rank (1 = largest context)
- `rank_cost_input_asc` - Derived rank (1 = cheapest)
- `openrouter_rankings_source_name` - Should say "OpenRouter API"
- `modalities` - text, vision, audio, etc.
- `derived_rank_formula_notes` - Explains derivation logic

---

### 8. Verify with Python Snippet

Run this to confirm the Excel is valid:

```python
import os
import hashlib
from pathlib import Path
import pandas as pd

excel_path = Path("data/modeldb/LLMHive_OpenRouter_SingleSheet_ModelDB_Enriched_2025-12-25.xlsx")

# Basic info
print(f"=== Excel Verification ===")
print(f"Path: {excel_path.resolve()}")
print(f"Size: {excel_path.stat().st_size:,} bytes")

# Compute SHA256
with open(excel_path, "rb") as f:
    sha256 = hashlib.sha256(f.read()).hexdigest()
print(f"SHA256: {sha256[:16]}...")

# Load and inspect
xl = pd.ExcelFile(excel_path)
print(f"\nSheets: {xl.sheet_names}")

df = pd.read_excel(excel_path)
print(f"Rows: {len(df)}")
print(f"Columns: {len(df.columns)}")

# Check key columns
key_cols = [
    "openrouter_slug", "model_name", "provider_name",
    "max_context_tokens", "price_input_usd_per_1m",
    "openrouter_rank_context_length", "rank_context_length_desc",
    "modalities", "derived_rank_formula_notes"
]
print(f"\nKey columns present:")
for col in key_cols:
    status = "✅" if col in df.columns else "❌"
    print(f"  {status} {col}")
```

Expected output:
```
=== Excel Verification ===
Path: /path/to/data/modeldb/LLMHive_OpenRouter_SingleSheet_ModelDB_Enriched_2025-12-25.xlsx
Size: 245,294 bytes
SHA256: 6fd695717bc04ac1...

Sheets: ['Sheet1']
Rows: 353
Columns: 170

Key columns present:
  ✅ openrouter_slug
  ✅ model_name
  ✅ provider_name
  ✅ max_context_tokens
  ✅ price_input_usd_per_1m
  ✅ openrouter_rank_context_length
  ✅ rank_context_length_desc
  ✅ modalities
  ✅ derived_rank_formula_notes
```

---

### 9. Schema Baseline

The file `schema_baseline_columns.json` defines the minimum required columns. This prevents accidental schema shrinkage.

**To regenerate baseline** (only when intentionally adding/removing columns):

```python
import pandas as pd
import json
from datetime import datetime, timezone

df = pd.read_excel("data/modeldb/LLMHive_OpenRouter_SingleSheet_ModelDB_Enriched_2025-12-25.xlsx")
baseline = {
    "version": "X.X.X",
    "created_at": datetime.now(timezone.utc).isoformat(),
    "columns": sorted(list(df.columns)),
    "min_row_count": len(df),
    "notes": "Your note here"
}
with open("data/modeldb/schema_baseline_columns.json", "w") as f:
    json.dump(baseline, f, indent=2)
```

**Warning**: Never regenerate baseline to a smaller column set than the canonical Excel. This would allow schema shrinkage and data loss.

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

---

## World-Class Run Modes

This section explains the recommended run modes for maintaining world-class coverage.

### Daily Free Run (No Evals/Telemetry)

Run this daily to keep the model catalog up-to-date with free data sources:

```bash
python data/modeldb/run_modeldb_refresh.py \
  --evals-enabled false \
  --telemetry-enabled false
```

**What it does:**
- ✅ Fetches latest models from OpenRouter API
- ✅ Updates OpenRouter rankings (free)
- ✅ Fetches LMSYS Arena Elo ratings (free, from HuggingFace)
- ✅ Fetches HuggingFace Open LLM Leaderboard scores (free)
- ✅ Applies derived rankings and provider docs
- ✅ Pushes to Firestore + Pinecone
- ✅ Generates coverage report
- ❌ No API costs (skips evals and telemetry)

**Expected runtime:** ~2-5 minutes

### Weekly World-Class Run (Limited Evals + Telemetry)

Run this weekly to add eval scores and telemetry for top models:

```bash
python data/modeldb/run_modeldb_refresh.py \
  --evals-enabled true --evals-max-models 50 \
  --telemetry-enabled true --telemetry-max-models 50 --telemetry-trials 3
```

**What it does:**
- Everything in the daily run, PLUS:
- ✅ Runs eval harness on top 50 models (programming, language, tool use)
- ✅ Probes top 50 models for latency/TPS telemetry
- ✅ Records per-model eval scores and telemetry

**Expected runtime:** ~30-60 minutes
**Expected cost:** ~$1-5 (depending on models selected)

### Full World-Class Run (Complete Coverage)

For comprehensive coverage of all models (not recommended for every run):

```bash
python data/modeldb/run_modeldb_refresh.py \
  --evals-enabled true \
  --telemetry-enabled true --telemetry-trials 5
```

**Expected runtime:** ~2-4 hours
**Expected cost:** ~$10-50 (full model coverage)

---

## Coverage Report

After each non-dry-run, a coverage report is automatically generated in `archives/`:

### Output Files

- `coverage_report_<timestamp>.json` - Machine-readable full report
- `coverage_report_<timestamp>.md` - Human-readable summary

### Coverage Groups Analyzed

| Source Group | Description | Key Columns |
|--------------|-------------|-------------|
| `openrouter_rankings` | OpenRouter API rankings | `openrouter_rank_context_length`, `openrouter_rank_price_input` |
| `lmsys_arena` | LMSYS Chatbot Arena | `arena_elo_overall`, `arena_rank_overall`, `arena_match_status` |
| `hf_leaderboard` | HuggingFace Open LLM Leaderboard | `hf_ollb_mmlu`, `hf_ollb_avg`, `hf_ollb_match_status` |
| `eval_harness` | Eval harness scores | `eval_programming_languages_score`, `eval_tool_use_score` |
| `telemetry` | Live telemetry | `telemetry_latency_p50_ms`, `telemetry_tps_p50` |
| `provider_docs` | Provider documentation | `modalities`, `supports_function_calling` |
| `derived_rankings` | Computed rankings | `rank_context_length_desc`, `rank_cost_input_asc` |

### Understanding Coverage Report

```
Source Group Coverage:
  ✅ openrouter_rankings: 95.2% (336/353)
  ✅ derived_rankings: 85.1% (300/353)
  ⚠️  lmsys_arena: 42.5% (150/353)
  ⚠️  hf_leaderboard: 35.7% (126/353)
  ❌ eval_harness: 0.0% (0/353)
  ❌ telemetry: 0.0% (0/353)
```

- **✅ Good coverage (>50%)**: Most models have data
- **⚠️  Partial coverage (10-50%)**: Only some models matched
- **❌ No coverage (0%)**: Enricher not run or no matches

### Top 20 Unmatched Lists

Each report includes the top 20 models that couldn't be matched for each source:

```
### lmsys_arena
**20 models unmatched:**
- `anthropic/claude-3.5-sonnet-20241022`: match_status=unmatched
- `google/gemini-2.0-flash-thinking-exp`: all columns null
...
```

Use these lists to improve matching logic or identify new models.

---

## Run Log Files

After each run, logs are saved to `archives/`:

| File Pattern | Description |
|--------------|-------------|
| `refresh_runlog_<timestamp>.json` | Full run summary with step statuses |
| `modeldb_runlog_<timestamp>.json` | Pipeline (Firestore/Pinecone) log |
| `enrich_runlog_<timestamp>.json` | Enrichment layer log |
| `coverage_report_<timestamp>.json` | Coverage statistics |
| `coverage_report_<timestamp>.md` | Human-readable coverage |

### Finding the Latest Log

```python
from pathlib import Path

archives = Path("data/modeldb/archives")
latest_log = sorted(archives.glob("refresh_runlog_*.json"), reverse=True)[0]
print(f"Latest run log: {latest_log}")
```

---

## Repository Safety

### ⚠️ Do NOT Use `git clean -xfd`

The command `git clean -xfd` will delete ALL untracked files, including:
- Service account keys in `data/modeldb/secrets/`
- Environment files (`.env`)
- Archives and run logs
- Virtual environments

**Instead, use the safe clean script:**

```bash
# Dry run (see what would be deleted)
./scripts/safe_clean.sh

# Actually clean (preserves secrets, .env, archives)
./scripts/safe_clean.sh --force
```

### CI Secret Scanning

The repository includes CI workflows that:
1. Scan for accidentally committed secrets
2. Block PRs that contain service account keys
3. Verify `data/modeldb/secrets/` is never tracked

If you see a CI failure about secrets, remove the file and rotate the credential immediately.

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
