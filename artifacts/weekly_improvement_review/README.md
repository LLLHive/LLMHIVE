# Improvement reports — human review queue

Dated folders (`YYYY-MM-DD/`) are created by the **review-only** monthly workflow **`.github/workflows/monthly-improvement-reports.yml`** (*Monthly improvement reports*). Each folder contains:

- `README.md` — how to proceed
- `report.md` / `report.json` — cycle summary
- `plan.json` — proposed upgrades (not applied in review mode)

Canonical outputs also remain under `llmhive/src/llmhive/app/weekly/reports/` and `.../plans/`.

Retention: each run **uploads a workflow artifact** (180 days in this workflow) and opens a **pull request to `main`** with only the new dated folder (branch name `chore/monthly-improvement-pack-<date>-<run_id>`). Merge the PR when the pack looks correct so the snapshot lives in git history on `main`.

## No auto-apply in CI

GitHub Actions does **not** run live OpenRouter sync or auto-apply upgrades. For a **local** legacy apply path only when you explicitly intend it, use the Python CLI with **`--allow-apply`** (never enabled in the monthly workflow).
