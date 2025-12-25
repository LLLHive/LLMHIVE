#!/usr/bin/env python3
"""
LLMHive ModelDB Updater (OpenRouter-first + deterministic Epoch enrichment)

Goal
----
Produce a SINGLE-SHEET, Excel-friendly model database that your orchestrator and RAG can ingest.

Primary inputs
--------------
1) OpenRouter model catalog:
   - https://openrouter.ai/api/v1/models
2) OpenRouter rankings page (top lists by category, when available):
   - https://openrouter.ai/rankings
3) Epoch AI Models dataset (release dates, params, architecture, etc.):
   - https://epoch.ai/data/all_ai_models.csv   (preferred, if accessible)
   - https://epoch.ai/data/ai-models           (landing page)

This script is designed to:
- Preserve ALL columns from your previous master XLSX (no silent truncation)
- Add/update OpenRouter fields deterministically
- Enrich from Epoch by name+provider+date heuristics
- Resolve conflicts via "credibility_tier" and recency (with explicit logging)

Requirements
------------
pip install -r requirements.txt

Usage
-----
# First run (build from OpenRouter only; Epoch optional)
python llmhive_modeldb_update.py \
  --output ./LLMHive_ModelDB.xlsx \
  --cache-dir ./.cache/llmhive_modeldb

# Incremental run (preserves your prior columns)
python llmhive_modeldb_update.py \
  --previous ./LLMHive_ModelDB.xlsx \
  --output ./LLMHive_ModelDB.xlsx \
  --cache-dir ./.cache/llmhive_modeldb

# Disable Epoch enrichment (if rate-limited)
python llmhive_modeldb_update.py --no-epoch --previous ... --output ...

Notes
-----
- If your environment blocks Epoch downloads, the updater will keep epoch_* fields NULL and log to data_gaps.
- For maximum determinism, keep `id_map_models.csv` and `id_map_providers.csv` under version control.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import requests
from rapidfuzz import fuzz
from bs4 import BeautifulSoup


OPENROUTER_MODELS_URL = "https://openrouter.ai/api/v1/models"
OPENROUTER_RANKINGS_URL = "https://openrouter.ai/rankings"
EPOCH_MODELS_CSV_URL = "https://epoch.ai/data/all_ai_models.csv"
EPOCH_LANDING_URL = "https://epoch.ai/data/ai-models"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def safe_mkdir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def http_get(url: str, headers: Optional[Dict[str, str]] = None, timeout_s: int = 60) -> requests.Response:
    resp = requests.get(url, headers=headers or {}, timeout=timeout_s)
    resp.raise_for_status()
    return resp


def cache_write(path: str, content: bytes) -> None:
    safe_mkdir(os.path.dirname(path))
    with open(path, "wb") as f:
        f.write(content)


def cache_read(path: str) -> Optional[bytes]:
    if not os.path.exists(path):
        return None
    with open(path, "rb") as f:
        return f.read()


def normalize_name(s: str) -> str:
    s = (s or "").lower().strip()
    # remove provider prefix if present like "OpenAI: GPT-4o"
    s = re.sub(r"^[a-z0-9 ._-]+:\s*", "", s)
    # drop common suffixes
    s = re.sub(r"\b(instruct|instruction|chat|preview|beta|alpha|free|exacto)\b", " ", s)
    s = re.sub(r"[\(\)\[\]\{\}]", " ", s)
    s = re.sub(r"[^a-z0-9]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def normalize_provider(s: str) -> str:
    s = (s or "").lower().strip()
    s = re.sub(r"[^a-z0-9]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


@dataclass
class CandidateValue:
    value: Any
    source_name: str
    source_url: Optional[str]
    credibility_tier: int  # 1 best
    reference_date: Optional[str]  # ISO date or timestamp
    retrieved_at: Optional[str]
    confidence: str


def choose_best(candidates: List[CandidateValue]) -> Tuple[Any, Optional[CandidateValue], bool, Optional[str]]:
    """
    Returns: (chosen_value, chosen_candidate, conflict_flag, conflict_note)
    """
    # Filter NULL-ish
    c = [x for x in candidates if x.value is not None and (not (isinstance(x.value, float) and pd.isna(x.value)))]
    if not c:
        return None, None, False, None

    # conflict check: multiple distinct values
    distinct = set(str(x.value) for x in c)
    conflict = len(distinct) > 1

    # sort: credibility asc, then reference_date desc, then retrieved_at desc
    def sort_key(x: CandidateValue):
        ref = x.reference_date or ""
        ret = x.retrieved_at or ""
        return (x.credibility_tier, ref, ret)

    # We want most recent, so sort by tier asc, then dates desc. We'll invert dates by sorting ascending on tier and descending on date strings.
    # ISO strings sort lexicographically for recency.
    c_sorted = sorted(
        c,
        key=lambda x: (
            x.credibility_tier,
            "" if x.reference_date is None else "-" + x.reference_date,  # trick: prepend '-' to reverse
            "" if x.retrieved_at is None else "-" + x.retrieved_at,
        ),
    )
    chosen = c_sorted[0]
    note = None
    if conflict:
        note = json.dumps([cand.__dict__ for cand in c], ensure_ascii=False)
    return chosen.value, chosen, conflict, note


def load_id_map(map_path: str, key_col: str, id_col: str) -> Dict[str, int]:
    if not os.path.exists(map_path):
        return {}
    df = pd.read_csv(map_path, dtype={key_col: str, id_col: int})
    return dict(zip(df[key_col].astype(str), df[id_col].astype(int)))


def save_id_map(map_path: str, mapping: Dict[str, int], key_col: str, id_col: str) -> None:
    safe_mkdir(os.path.dirname(map_path))
    items = sorted(mapping.items(), key=lambda x: x[1])
    df = pd.DataFrame([{key_col: k, id_col: v} for k, v in items])
    df.to_csv(map_path, index=False)


def assign_ids(keys: List[str], existing: Dict[str, int]) -> Dict[str, int]:
    """
    Stable incremental integer IDs for new keys.
    """
    out = dict(existing)
    next_id = max(out.values()) + 1 if out else 1
    for k in keys:
        if k not in out:
            out[k] = next_id
            next_id += 1
    return out


def fetch_openrouter_models(cache_dir: str, api_key: Optional[str]) -> pd.DataFrame:
    headers = {}
    if api_key:
        # OpenRouter uses standard Authorization for some endpoints; models list usually works without key.
        headers["Authorization"] = f"Bearer {api_key}"
    ts = utc_now_iso()
    cache_path = os.path.join(cache_dir, f"openrouter_models_{ts}.json")
    resp = http_get(OPENROUTER_MODELS_URL, headers=headers)
    cache_write(cache_path, resp.content)

    payload = resp.json()
    data = payload.get("data", payload)  # tolerate either shape
    if not isinstance(data, list):
        raise RuntimeError("Unexpected OpenRouter /models response shape (expected list or {data:[...]})")

    rows = []
    for m in data:
        slug = m.get("id") or m.get("slug")
        name = m.get("name")
        ctx = m.get("context_length") or m.get("context") or m.get("contextWindow")
        pricing = m.get("pricing") or {}
        # API typically returns dollars per token; we normalize to $/1M tokens
        def per_million(v):
            try:
                return float(v) * 1_000_000
            except Exception:
                return None

        price_in = per_million(pricing.get("prompt"))
        price_out = per_million(pricing.get("completion"))

        arch = m.get("architecture") or {}
        # modality fields are inconsistent across providers; capture best-effort
        modalities = None
        for key in ["modality", "modalities", "input_modality"]:
            if key in arch and arch.get(key):
                modalities = arch.get(key)
        # Normalize modalities to pipe-delimited string if list
        if isinstance(modalities, list):
            modalities = "|".join(modalities)
        elif isinstance(modalities, str):
            modalities = modalities.replace(",", "|")

        rows.append(
            {
                "openrouter_slug": slug,
                "model_name": name,
                "max_context_tokens": ctx,
                "price_input_usd_per_1m": price_in,
                "price_output_usd_per_1m": price_out,
                "model_source_name": "OpenRouter Models API",
                "model_source_url": OPENROUTER_MODELS_URL,
                "model_retrieved_at": ts,
                "pricing_source_name": "OpenRouter Models API",
                "pricing_source_url": OPENROUTER_MODELS_URL,
                "pricing_retrieved_at": ts,
                "modalities": modalities,
            }
        )

    df = pd.DataFrame(rows)
    df = df[df["openrouter_slug"].notna()].drop_duplicates(subset=["openrouter_slug"])
    return df


def fetch_openrouter_rankings(cache_dir: str) -> pd.DataFrame:
    """
    Scrapes https://openrouter.ai/rankings. OpenRouter's DOM may change;
    this method is best-effort and should be treated as semi-structured.
    """
    ts = utc_now_iso()
    html_path = os.path.join(cache_dir, f"openrouter_rankings_{ts}.html")
    resp = http_get(OPENROUTER_RANKINGS_URL, headers={"User-Agent": "Mozilla/5.0"})
    cache_write(html_path, resp.content)
    soup = BeautifulSoup(resp.text, "lxml")

    # Best-effort: find ranking blocks by headings and model links
    blocks: List[Dict[str, Any]] = []
    for section in soup.find_all(["section", "div"]):
        h = section.find(["h1", "h2", "h3"])
        if not h:
            continue
        title = (h.get_text(" ", strip=True) or "").strip()
        # heuristic: require at least 3 model links
        links = [a for a in section.find_all("a", href=True) if "/models/" in a["href"]]
        if len(links) < 3:
            continue
        blocks.append({"title": title or "unknown_block", "section": section})

    out_rows = []
    for b in blocks:
        title = b["title"]
        section = b["section"]
        model_links = [a for a in section.find_all("a", href=True) if "/models/" in a["href"]]
        # dedupe preserve order
        seen = set()
        ordered = []
        for a in model_links:
            href = a["href"]
            # /models/<slug>
            m = re.search(r"/models/([^/?#]+)", href)
            if not m:
                continue
            slug = m.group(1)
            if slug in seen:
                continue
            seen.add(slug)
            ordered.append(slug)

        for i, slug in enumerate(ordered[:50], start=1):  # cap
            out_rows.append(
                {
                    "ranking_source": "OpenRouter",
                    "category": title,
                    "rank": i,
                    "openrouter_slug": slug,
                    "ranking_source_name": "OpenRouter Rankings Page",
                    "ranking_source_url": OPENROUTER_RANKINGS_URL,
                    "ranking_retrieved_at": ts,
                    "ranking_confidence": "medium",
                    "ranking_credibility_tier": 2,
                    "as_of_date": ts[:10],
                }
            )

    return pd.DataFrame(out_rows)


def fetch_epoch_models(cache_dir: str, epoch_url: str) -> pd.DataFrame:
    """
    Downloads Epoch models dataset CSV. If blocked, raise.
    """
    ts = utc_now_iso()
    csv_path = os.path.join(cache_dir, f"epoch_models_{ts}.csv")
    resp = http_get(epoch_url, headers={"User-Agent": "Mozilla/5.0"})
    cache_write(csv_path, resp.content)
    # Pandas can handle UTF-8 with BOM; fallback
    try:
        df = pd.read_csv(csv_path)
    except UnicodeDecodeError:
        df = pd.read_csv(csv_path, encoding="latin-1")
    df["_epoch_retrieved_at"] = ts
    df["_epoch_source_url"] = epoch_url
    return df


def guess_epoch_columns(df: pd.DataFrame) -> Dict[str, str]:
    """
    Map epoch dataframe columns to canonical names.
    """
    cols = list(df.columns)

    def find_col(keywords: List[str]) -> Optional[str]:
        # exact match first
        lowered = {c.lower().strip(): c for c in cols}
        for k in keywords:
            if k in lowered:
                return lowered[k]
        # contains match
        for c in cols:
            lc = c.lower()
            if any(k in lc for k in keywords):
                return c
        return None

    mapping = {
        "epoch_model_name": find_col(["model", "system", "name", "model name", "system name"]),
        "epoch_organization": find_col(["organization", "org", "developer", "lab", "company"]),
        "epoch_publication_date": find_col(["publication date", "release date", "date", "publication"]),
        "epoch_parameters": find_col(["parameters", "params", "parameter count"]),
        "epoch_architecture": find_col(["architecture", "arch"]),
    }
    return mapping


def parse_epoch_params(val: Any) -> Optional[float]:
    """
    Returns absolute parameter count as float (e.g., 70e9), if parseable.
    Accepts values like:
      - 70e9
      - "70B"
      - "70000000000"
    """
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    if isinstance(val, (int, float)):
        return float(val)
    s = str(val).strip()
    if not s:
        return None
    # remove commas
    s = s.replace(",", "")
    m = re.match(r"^(\d+(?:\.\d+)?)\s*([BbMmKk])?$", s)
    if m:
        num = float(m.group(1))
        unit = (m.group(2) or "").lower()
        if unit == "b":
            return num * 1e9
        if unit == "m":
            return num * 1e6
        if unit == "k":
            return num * 1e3
        return num
    return None


def build_epoch_index(epoch_df: pd.DataFrame, colmap: Dict[str, str]) -> pd.DataFrame:
    """
    Normalize epoch df for matching.
    """
    def get_col(key: str) -> Optional[str]:
        c = colmap.get(key)
        return c if c in epoch_df.columns else None

    out = pd.DataFrame()
    out["epoch_model_name_raw"] = epoch_df[get_col("epoch_model_name")] if get_col("epoch_model_name") else None
    out["epoch_org_raw"] = epoch_df[get_col("epoch_organization")] if get_col("epoch_organization") else None
    out["epoch_publication_date_raw"] = epoch_df[get_col("epoch_publication_date")] if get_col("epoch_publication_date") else None
    out["epoch_architecture_raw"] = epoch_df[get_col("epoch_architecture")] if get_col("epoch_architecture") else None
    out["epoch_parameters_raw"] = epoch_df[get_col("epoch_parameters")] if get_col("epoch_parameters") else None

    out["_epoch_retrieved_at"] = epoch_df["_epoch_retrieved_at"]
    out["_epoch_source_url"] = epoch_df["_epoch_source_url"]

    out["epoch_model_name_norm"] = out["epoch_model_name_raw"].astype(str).apply(normalize_name)
    out["epoch_org_norm"] = out["epoch_org_raw"].astype(str).apply(normalize_provider)
    out["epoch_parameters"] = out["epoch_parameters_raw"].apply(parse_epoch_params)

    # publication date normalize: keep ISO date string if parseable
    out["epoch_publication_date"] = pd.to_datetime(out["epoch_publication_date_raw"], errors="coerce").dt.strftime("%Y-%m-%d")
    return out


def match_epoch_row(openrouter_row: pd.Series, epoch_index: pd.DataFrame, org_map: Dict[str, str]) -> Tuple[Optional[pd.Series], Optional[float], str]:
    """
    Deterministic heuristic match.
    Returns: (best_epoch_row, score, status)
    """
    name_norm = normalize_name(str(openrouter_row.get("model_name") or ""))
    prov_norm = normalize_provider(str(openrouter_row.get("provider_name") or ""))

    # provider mapping
    prov_norm_mapped = normalize_provider(org_map.get(prov_norm, prov_norm))

    # restrict candidates by org when possible
    candidates = epoch_index
    if prov_norm_mapped:
        subset = epoch_index[epoch_index["epoch_org_norm"].str.contains(prov_norm_mapped, na=False)]
        if len(subset) >= 10:
            candidates = subset

    if candidates.empty:
        return None, None, "unmatched"

    # compute top match by name similarity
    best = None
    best_score = -1.0
    second_score = -1.0

    for _, erow in candidates.iterrows():
        s = fuzz.token_set_ratio(name_norm, str(erow["epoch_model_name_norm"]))
        # bonus if org matches strongly
        org_bonus = 0.0
        if prov_norm_mapped and prov_norm_mapped in str(erow["epoch_org_norm"]):
            org_bonus = 8.0
        score = float(s) + org_bonus
        if score > best_score:
            second_score = best_score
            best_score = score
            best = erow
        elif score > second_score:
            second_score = score

    if best_score < 85:
        return None, best_score, "unmatched"

    if (best_score - second_score) < 2.0:
        return best, best_score, "ambiguous"

    return best, best_score, "matched"


def ensure_columns(df: pd.DataFrame, required_cols: List[str]) -> pd.DataFrame:
    for c in required_cols:
        if c not in df.columns:
            df[c] = None
    return df


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--previous", type=str, default=None, help="Previous master XLSX (single sheet). Columns will be preserved.")
    ap.add_argument("--output", type=str, required=True, help="Output XLSX path (single sheet).")
    ap.add_argument("--sheet", type=str, default="LLMHive_ModelDB", help="Sheet name.")
    ap.add_argument("--cache-dir", type=str, default=".cache/llmhive_modeldb", help="Cache directory for raw downloads.")
    ap.add_argument("--openrouter-api-key", type=str, default=os.getenv("OPENROUTER_API_KEY"), help="Optional.")
    ap.add_argument("--epoch-url", type=str, default=EPOCH_MODELS_CSV_URL, help="Epoch CSV URL.")
    ap.add_argument("--no-epoch", action="store_true", help="Disable Epoch enrichment.")
    ap.add_argument("--no-rankings", action="store_true", help="Disable OpenRouter rankings scrape.")
    ap.add_argument("--id-map-models", type=str, default=None, help="CSV path to persist model IDs.")
    ap.add_argument("--id-map-providers", type=str, default=None, help="CSV path to persist provider IDs.")
    args = ap.parse_args()

    safe_mkdir(args.cache_dir)
    run_at = utc_now_iso()

    prev_df = None
    if args.previous and os.path.exists(args.previous):
        prev_df = pd.read_excel(args.previous, sheet_name=args.sheet)

    # === Pull OpenRouter models ===
    or_df = fetch_openrouter_models(args.cache_dir, args.openrouter_api_key)

    # derive provider_name from model_name prefix if absent
    if "provider_name" not in or_df.columns:
        or_df["provider_name"] = None
    def infer_provider(model_name: str, slug: str) -> str:
        if isinstance(model_name, str) and ":" in model_name:
            return model_name.split(":", 1)[0].strip()
        if isinstance(slug, str) and "/" in slug:
            return slug.split("/", 1)[0]
        return None
    or_df["provider_name"] = [infer_provider(n, s) for n, s in zip(or_df["model_name"], or_df["openrouter_slug"])]

    # === Stable IDs ===
    id_map_models_path = args.id_map_models or os.path.join(args.cache_dir, "id_map_models.csv")
    id_map_providers_path = args.id_map_providers or os.path.join(args.cache_dir, "id_map_providers.csv")

    model_map = assign_ids(or_df["openrouter_slug"].astype(str).tolist(), load_id_map(id_map_models_path, "openrouter_slug", "model_id"))
    provider_map = assign_ids(or_df["provider_name"].astype(str).tolist(), load_id_map(id_map_providers_path, "provider_name", "provider_id"))

    save_id_map(id_map_models_path, model_map, "openrouter_slug", "model_id")
    save_id_map(id_map_providers_path, provider_map, "provider_name", "provider_id")

    or_df["model_id"] = or_df["openrouter_slug"].astype(str).map(model_map).astype(int)
    or_df["provider_id"] = or_df["provider_name"].astype(str).map(provider_map).astype(int)
    or_df["in_openrouter"] = True
    or_df["record_type"] = "openrouter_model"

    # === Merge with previous (preserve all columns) ===
    if prev_df is not None:
        # preserve row-level data by openrouter_slug
        merged = prev_df.merge(or_df, on="openrouter_slug", how="outer", suffixes=("_prev", ""))
        # For any column that exists in prev but not in new, keep prev
        # For any OpenRouter-updatable columns, take the new value when present.
        openrouter_update_cols = [
            "model_name",
            "provider_name",
            "provider_id",
            "model_id",
            "max_context_tokens",
            "modalities",
            "price_input_usd_per_1m",
            "price_output_usd_per_1m",
            "model_source_name",
            "model_source_url",
            "model_retrieved_at",
            "pricing_source_name",
            "pricing_source_url",
            "pricing_retrieved_at",
            "in_openrouter",
            "record_type",
        ]
        # Start with prev columns
        out = merged[[c for c in merged.columns if c.endswith("_prev")]].copy()
        out.columns = [c[:-5] for c in out.columns]  # drop _prev

        # ensure openrouter_slug present
        out["openrouter_slug"] = merged["openrouter_slug"]

        # update known columns from new
        for c in openrouter_update_cols:
            if c in merged.columns:
                out[c] = merged[c].combine_first(out.get(c))

        df_out = out
    else:
        df_out = or_df.copy()

    # === OpenRouter rankings (optional) ===
    if not args.no_rankings:
        try:
            rnk = fetch_openrouter_rankings(args.cache_dir)
            # aggregate per slug
            rnk_grp = rnk.groupby("openrouter_slug").apply(lambda g: g.sort_values("rank")[["ranking_source","category","rank","as_of_date","ranking_source_url","ranking_retrieved_at"]].to_dict(orient="records"))
            df_out["openrouter_rankings_json"] = df_out["openrouter_slug"].map(lambda s: json.dumps(rnk_grp.get(s), ensure_ascii=False) if s in rnk_grp.index else None)
        except Exception as e:
            # keep NULL, log note
            df_out["openrouter_rankings_json"] = df_out.get("openrouter_rankings_json")

    # === Epoch enrichment (optional) ===
    df_out["epoch_source_name"] = "Epoch AI Models dataset"
    df_out["epoch_source_url"] = EPOCH_LANDING_URL
    df_out["epoch_retrieved_at"] = df_out.get("epoch_retrieved_at")
    df_out["epoch_join_status"] = df_out.get("epoch_join_status")
    df_out["epoch_match_score"] = df_out.get("epoch_match_score")
    df_out["epoch_matched_model_name"] = df_out.get("epoch_matched_model_name")
    df_out["epoch_matched_organization"] = df_out.get("epoch_matched_organization")
    df_out["epoch_publication_date"] = df_out.get("epoch_publication_date")
    df_out["epoch_parameters"] = df_out.get("epoch_parameters")
    df_out["epoch_architecture"] = df_out.get("epoch_architecture")

    # provider normalization mapping (customize as needed)
    org_map = {
        "meta ai": "meta",
        "meta": "meta",
        "openai": "openai",
        "anthropic": "anthropic",
        "google": "google",
        "deepmind": "google",
        "mistral": "mistral",
        "x ai": "xai",
        "xai": "xai",
    }

    if not args.no_epoch:
        try:
            epoch_df = fetch_epoch_models(args.cache_dir, args.epoch_url)
            colmap = guess_epoch_columns(epoch_df)
            epoch_index = build_epoch_index(epoch_df, colmap)
            epoch_retrieved_at = epoch_df["_epoch_retrieved_at"].iloc[0]
            epoch_source_url = epoch_df["_epoch_source_url"].iloc[0]

            # Match each row
            matched_params = []
            for idx, row in df_out.iterrows():
                best, score, status = match_epoch_row(row, epoch_index, org_map)
                df_out.at[idx, "epoch_retrieved_at"] = epoch_retrieved_at
                df_out.at[idx, "epoch_source_url"] = epoch_source_url
                df_out.at[idx, "epoch_match_score"] = score
                df_out.at[idx, "epoch_join_status"] = status
                if best is not None:
                    df_out.at[idx, "epoch_matched_model_name"] = best.get("epoch_model_name_raw")
                    df_out.at[idx, "epoch_matched_organization"] = best.get("epoch_org_raw")
                    df_out.at[idx, "epoch_publication_date"] = best.get("epoch_publication_date")
                    df_out.at[idx, "epoch_parameters"] = best.get("epoch_parameters")
                    df_out.at[idx, "epoch_architecture"] = best.get("epoch_architecture_raw")

            # Conflict resolution for parameter_count and release_date
            if "parameter_count" not in df_out.columns:
                df_out["parameter_count"] = None
            if "release_date" not in df_out.columns:
                df_out["release_date"] = None

            # choose parameter_count
            for idx, row in df_out.iterrows():
                candidates: List[CandidateValue] = []
                # existing parameter_count (from prior runs)
                if pd.notna(row.get("parameter_count")):
                    candidates.append(CandidateValue(
                        value=row.get("parameter_count"),
                        source_name="Existing DB value",
                        source_url=None,
                        credibility_tier=3,
                        reference_date=None,
                        retrieved_at=row.get("model_retrieved_at"),
                        confidence="medium"
                    ))
                # epoch
                if pd.notna(row.get("epoch_parameters")):
                    candidates.append(CandidateValue(
                        value=row.get("epoch_parameters"),
                        source_name="Epoch AI Models dataset",
                        source_url=row.get("epoch_source_url"),
                        credibility_tier=1,
                        reference_date=row.get("epoch_publication_date"),
                        retrieved_at=row.get("epoch_retrieved_at"),
                        confidence="high"
                    ))
                chosen, chosen_cand, conflict, note = choose_best(candidates)
                if chosen is not None:
                    df_out.at[idx, "parameter_count"] = chosen
                    df_out.at[idx, "parameter_count_source_name"] = chosen_cand.source_name if chosen_cand else None
                    df_out.at[idx, "parameter_count_source_url"] = chosen_cand.source_url if chosen_cand else None
                    df_out.at[idx, "parameter_count_retrieved_at"] = chosen_cand.retrieved_at if chosen_cand else None
                    df_out.at[idx, "parameter_count_confidence"] = chosen_cand.confidence if chosen_cand else None
                    df_out.at[idx, "parameter_count_conflict_flag"] = conflict
                    df_out.at[idx, "parameter_count_conflict_notes"] = note

            # choose release_date
            for idx, row in df_out.iterrows():
                candidates: List[CandidateValue] = []
                if pd.notna(row.get("release_date")):
                    candidates.append(CandidateValue(
                        value=row.get("release_date"),
                        source_name="Existing DB value",
                        source_url=None,
                        credibility_tier=3,
                        reference_date=row.get("release_date"),
                        retrieved_at=row.get("model_retrieved_at"),
                        confidence="medium"
                    ))
                if pd.notna(row.get("epoch_publication_date")):
                    candidates.append(CandidateValue(
                        value=row.get("epoch_publication_date"),
                        source_name="Epoch AI Models dataset",
                        source_url=row.get("epoch_source_url"),
                        credibility_tier=1,
                        reference_date=row.get("epoch_publication_date"),
                        retrieved_at=row.get("epoch_retrieved_at"),
                        confidence="high"
                    ))
                chosen, chosen_cand, conflict, note = choose_best(candidates)
                if chosen is not None:
                    df_out.at[idx, "release_date"] = chosen
                    df_out.at[idx, "release_date_source_name"] = chosen_cand.source_name if chosen_cand else None
                    df_out.at[idx, "release_date_source_url"] = chosen_cand.source_url if chosen_cand else None
                    df_out.at[idx, "release_date_retrieved_at"] = chosen_cand.retrieved_at if chosen_cand else None
                    df_out.at[idx, "release_date_confidence"] = chosen_cand.confidence if chosen_cand else None
                    df_out.at[idx, "release_date_conflict_flag"] = conflict
                    df_out.at[idx, "release_date_conflict_notes"] = note

        except Exception as e:
            # Keep epoch fields NULL but record an error note
            df_out["epoch_join_status"] = df_out["epoch_join_status"].fillna("epoch_download_failed")
            # Optionally, you can write a log file under cache_dir.
            err_path = os.path.join(args.cache_dir, f"epoch_error_{run_at}.txt")
            with open(err_path, "w", encoding="utf-8") as f:
                f.write(str(e))

    df_out["enrichment_run_at"] = run_at

    # === Output (single sheet XLSX) ===
    with pd.ExcelWriter(args.output, engine="openpyxl") as writer:
        df_out.to_excel(writer, sheet_name=args.sheet, index=False)

    print(f"[OK] wrote {args.output} rows={len(df_out)} cols={len(df_out.columns)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
