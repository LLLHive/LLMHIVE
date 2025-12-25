# LLMHive ModelDB — Implementation Guide (Cursor / Opus 4.5)

This folder contains the scripts to **update** and **import** the single-sheet Excel model database.

## 1) One-time setup

### A) Create a Python environment
```bash
python -m venv .venv
source .venv/bin/activate   # macOS/Linux
# or: .venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

### B) Put your current master Excel in the repo
Recommended location:
```
data/modeldb/LLMHive_ModelDB.xlsx
```

> IMPORTANT: The updater is designed to **preserve columns** from the previous file. Use `--previous` on every run.

## 2) Update / enrich the ModelDB

### Minimal (OpenRouter only)
```bash
python llmhive_modeldb_update.py \
  --previous data/modeldb/LLMHive_ModelDB.xlsx \
  --output   data/modeldb/LLMHive_ModelDB.xlsx \
  --cache-dir .cache/llmhive_modeldb \
  --no-epoch
```

### Full (OpenRouter + Epoch)
```bash
python llmhive_modeldb_update.py \
  --previous data/modeldb/LLMHive_ModelDB.xlsx \
  --output   data/modeldb/LLMHive_ModelDB.xlsx \
  --cache-dir .cache/llmhive_modeldb
```

Outputs:
- Updated `data/modeldb/LLMHive_ModelDB.xlsx`
- Cached raw source payloads under `.cache/llmhive_modeldb/`

## 3) Import into your orchestrator DB

### Option A: SQLite (fastest to start)
```bash
python llmhive_modeldb_import.py \
  --excel data/modeldb/LLMHive_ModelDB.xlsx \
  --db sqlite:///data/modeldb/llmhive_modeldb.sqlite \
  --table ai_models
```

### Option B: Postgres
```bash
export DATABASE_URL="postgresql+psycopg2://user:pass@host:5432/dbname"
python llmhive_modeldb_import.py \
  --excel data/modeldb/LLMHive_ModelDB.xlsx \
  --db "$DATABASE_URL" \
  --table ai_models
```

## 4) Automation (periodic updates)

### Cron example (daily 02:15 UTC)
```cron
15 2 * * * cd /path/to/repo && . .venv/bin/activate && \
python llmhive_modeldb_update.py --previous data/modeldb/LLMHive_ModelDB.xlsx --output data/modeldb/LLMHive_ModelDB.xlsx --cache-dir .cache/llmhive_modeldb && \
python llmhive_modeldb_import.py --excel data/modeldb/LLMHive_ModelDB.xlsx --db "$DATABASE_URL" --table ai_models
```

### Recommended guardrails
- Commit `id_map_models.csv` + `id_map_providers.csv` so IDs stay stable across runs.
- Add a CI check that row count does not drop unexpectedly.
- Keep a dated snapshot archive: `LLMHive_ModelDB_YYYY-MM-DD.xlsx`.

## 5) Where to extend (other sources)
The updater is intentionally modular:
- Add new benchmark scrapers under a new function, and merge into:
  - `benchmark_results_json_merged`
  - or new `*_json` fields.

Start with:
- LMSYS Chatbot Arena leaderboards (overall, coding, etc.)
- Provider docs/pricing pages for confirmation of parameter counts & release dates
- PapersWithCode leaderboards for static benchmark tables
