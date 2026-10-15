#!/usr/bin/env bash
# Copy weekly reports and plans into separate directories for a review-only pack.
# Does not sync catalogs, apply upgrades, or rewrite existing dated packs.
set -euo pipefail

DATE="${DATE:-$(date -u +%Y-%m-%d)}"
ROOT="${ROOT:-artifacts/weekly_improvement_review}"
REPORT_SRC="${REPORT_SRC:-llmhive/src/llmhive/app/weekly/reports}"
PLAN_SRC="${PLAN_SRC:-llmhive/src/llmhive/app/weekly/plans}"
DEST="${ROOT}/${DATE}"

write_output() {
  local key="$1"
  local value="$2"
  if [ -n "${GITHUB_OUTPUT:-}" ]; then
    echo "${key}=${value}" >> "$GITHUB_OUTPUT"
  fi
  echo "${key}=${value}"
}

is_date_name() {
  case "$1" in
    [0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]) return 0 ;;
    *) return 1 ;;
  esac
}

if ! is_date_name "$DATE"; then
  echo "refusing pack: DATE must be YYYY-MM-DD" >&2
  exit 1
fi
if [ -z "$ROOT" ] || [ "$DEST" = "/" ] || [ "$DEST" = "$ROOT" ]; then
  echo "refusing pack: unsafe destination" >&2
  exit 1
fi

shopt -s nullglob

LATEST=""
if [ -d "$ROOT" ]; then
  for dir in "$ROOT"/*/; do
    [ -d "$dir" ] || continue
    name=$(basename "$dir")
    if [ "$name" = "$DATE" ]; then
      continue
    fi
    if is_date_name "$name"; then
      if [ -z "$LATEST" ] || [[ "$name" > "$LATEST" ]]; then
        LATEST=$name
      fi
    fi
  done
fi

rm -rf "$DEST"
mkdir -p "$DEST/reports" "$DEST/plans"

copied_reports=0
for f in "$REPORT_SRC"/*.md "$REPORT_SRC"/*.json; do
  cp "$f" "$DEST/reports/"
  copied_reports=$((copied_reports + 1))
done

if [ "$copied_reports" -eq 0 ]; then
  rm -rf "$DEST"
  write_output date "$DATE"
  write_output skip_pr true
  echo "No weekly reports found; skipping PR."
  exit 0
fi

reject_pack() {
  echo "$1" >&2
  rm -rf "$DEST"
  exit 1
}

json_count=0
for f in "$DEST/reports"/*.json; do
  json_count=$((json_count + 1))
  python3 -c 'import json, sys
path = sys.argv[1]
try:
    data = json.load(open(path))
except Exception as exc:
    raise SystemExit(f"refusing pack: {path} is not valid JSON ({exc})")
if not isinstance(data, dict) or not isinstance(data.get("report_date"), str) or not data["report_date"].strip():
    raise SystemExit(f"refusing pack: {path} is not a weekly report (missing report_date)")' "$f" \
    || reject_pack "refusing pack: invalid report JSON $(basename "$f")"
done

if [ "$json_count" -eq 0 ]; then
  reject_pack "refusing pack: markdown reports have no JSON counterpart"
fi

for f in "$DEST/reports"/*.md; do
  base=$(basename "$f" .md)
  if [ ! -f "$DEST/reports/${base}.json" ]; then
    reject_pack "refusing pack: missing report JSON for ${base}.md"
  fi
done

for f in "$PLAN_SRC"/*.json; do
  cp "$f" "$DEST/plans/"
done

python3 -c 'import json, sys
from pathlib import Path
dest = Path(sys.argv[1])
for report in (dest / "reports").glob("*.json"):
    data = json.loads(report.read_text())
    if not isinstance(data, dict) or "report_date" not in data:
        raise SystemExit(f"refusing pack: {report} lost report_date")
' "$DEST" || reject_pack "refusing pack: report JSON lost report_date after plan copy"

skip_pr=false
if [ -n "$LATEST" ] \
  && [ -d "${ROOT}/${LATEST}/reports" ] \
  && [ -d "${ROOT}/${LATEST}/plans" ]; then
  if diff -rq "${ROOT}/${LATEST}/reports" "$DEST/reports" >/dev/null \
    && diff -rq "${ROOT}/${LATEST}/plans" "$DEST/plans" >/dev/null; then
    skip_pr=true
    echo "Report set matches ${LATEST}; skipping PR."
  fi
fi

if [ "$skip_pr" = false ]; then
  cat > "$DEST/README.md" << EOF
# Improvement report pack (${DATE})

Produced by \`monthly-improvement-reports.yml\` (review-only).

- Reports: \`reports/\` (markdown and report JSON)
- Plans: \`plans/\` (upgrade plans; an empty array means no planned upgrades)
- Report JSON and plan JSON stay in separate directories.
- No catalog sync and no auto-apply in this workflow.

## Human review

1. Inspect \`reports/\` and \`plans/\`.
2. Apply gated upgrades manually if appropriate.
EOF
fi

write_output date "$DATE"
write_output skip_pr "$skip_pr"
echo "Pack at ${DEST} skip_pr=${skip_pr} latest=${LATEST:-none}"
