"""
LMSYS Chatbot Arena Enricher

Fetches Elo ratings and rankings from the LMSYS Chatbot Arena leaderboard.
Uses HuggingFace datasets with local caching for reliability.

Primary dataset: mathewhe/chatbot-arena-elo (reliable HF mirror)
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import requests
from tenacity import retry, stop_after_attempt, wait_exponential

from .base import BaseEnricher, EnricherResult

logger = logging.getLogger(__name__)

# HuggingFace dataset for Arena data (reliable mirror with Elo scores)
ARENA_HF_DATASET_PRIMARY = "mathewhe/chatbot-arena-elo"
ARENA_HF_DATASET_FALLBACK = "lmsys/chatbot_arena_leaderboard"

# Fallback CSV endpoint
ARENA_CSV_FALLBACK = "https://huggingface.co/datasets/mathewhe/chatbot-arena-elo/resolve/main/arena_elo_data.csv"

# Cache settings
DEFAULT_CACHE_DIR = Path(".cache/llmhive_modeldb/arena")
CACHE_TTL_HOURS = 24

# Matching thresholds - higher threshold to reduce false positives
MATCH_THRESHOLD_EXACT = 0.95
MATCH_THRESHOLD_HEURISTIC = 0.82  # Stricter threshold


class LMSYSArenaEnricher(BaseEnricher):
    """
    Enricher that fetches LMSYS Chatbot Arena Elo ratings.
    
    Adds columns:
    - arena_rank (int)
    - arena_score (float, Elo score)
    - arena_votes (int)
    - arena_95ci (str)
    - arena_organization (str)
    - arena_license (str)
    - arena_match_status ("matched" | "unmatched")
    - arena_match_score (float 0-1)
    - arena_matched_name (str, original Arena model name)
    - arena_asof_date (str)
    - arena_source_name (str)
    - arena_source_url (str)
    - arena_retrieved_at (ISO timestamp)
    """
    
    name = "lmsys_arena"
    source_name = "LMSYS Chatbot Arena (via HuggingFace)"
    source_url = "https://lmarena.ai"
    
    def __init__(
        self,
        dry_run: bool = False,
        cache_dir: Optional[str] = None,
    ):
        super().__init__(dry_run=dry_run, cache_dir=cache_dir)
        self._cache_dir = Path(cache_dir) if cache_dir else DEFAULT_CACHE_DIR
        self._arena_data: Optional[pd.DataFrame] = None
        self._fuzzy_available = False
        
        # Try to import rapidfuzz for better matching
        try:
            from rapidfuzz import fuzz
            self._fuzzy_available = True
        except ImportError:
            logger.info("rapidfuzz not available, using difflib for matching")
    
    def _get_cache_path(self) -> Path:
        """Get the path for cached arena data."""
        return self._cache_dir / "arena_leaderboard.parquet"
    
    def _get_cache_metadata_path(self) -> Path:
        """Get the path for cache metadata."""
        return self._cache_dir / "arena_cache_metadata.json"
    
    def _is_cache_valid(self) -> bool:
        """Check if cache exists and is still valid."""
        cache_path = self._get_cache_path()
        meta_path = self._get_cache_metadata_path()
        
        if not cache_path.exists() or not meta_path.exists():
            return False
        
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
            
            cached_at = datetime.fromisoformat(meta.get("cached_at", ""))
            now = datetime.now(timezone.utc)
            age_hours = (now - cached_at).total_seconds() / 3600
            
            if age_hours > CACHE_TTL_HOURS:
                self.logger.info("Cache expired (%.1f hours old)", age_hours)
                return False
            
            self.logger.info("Using cached Arena data (%.1f hours old)", age_hours)
            return True
            
        except Exception as e:
            self.logger.warning("Cache metadata invalid: %s", e)
            return False
    
    def _load_from_cache(self) -> Optional[pd.DataFrame]:
        """Load arena data from cache."""
        try:
            cache_path = self._get_cache_path()
            return pd.read_parquet(cache_path)
        except Exception as e:
            self.logger.warning("Failed to load cache: %s", e)
            return None
    
    def _save_to_cache(self, df: pd.DataFrame, source_label: str) -> None:
        """Save arena data to cache."""
        try:
            self._cache_dir.mkdir(parents=True, exist_ok=True)
            
            # Save data
            cache_path = self._get_cache_path()
            df.to_parquet(cache_path, index=False)
            
            # Save metadata
            meta_path = self._get_cache_metadata_path()
            meta = {
                "cached_at": datetime.now(timezone.utc).isoformat(),
                "source": source_label,
                "row_count": len(df),
                "columns": list(df.columns),
            }
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(meta, f, indent=2)
            
            self.logger.info("Cached Arena data: %d rows from %s", len(df), source_label)
            
        except Exception as e:
            self.logger.warning("Failed to cache Arena data: %s", e)
    
    def _fetch_from_hf_datasets(self, dataset_name: str) -> Optional[pd.DataFrame]:
        """Try to fetch arena data using HuggingFace datasets library."""
        try:
            from datasets import load_dataset
            
            self.logger.info("Loading Arena data from HuggingFace: %s", dataset_name)
            ds = load_dataset(dataset_name, split="train")
            df = ds.to_pandas()
            self.logger.info("Loaded %d models from Arena via HF datasets", len(df))
            return df
            
        except ImportError:
            self.logger.warning("datasets library not available")
            return None
        except Exception as e:
            self.logger.warning("HuggingFace datasets %s failed: %s", dataset_name, e)
            return None
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
    )
    def _fetch_from_csv(self) -> Optional[pd.DataFrame]:
        """Fallback: fetch arena data from CSV endpoint."""
        try:
            import io
            
            self.logger.info("Fetching Arena data from CSV fallback...")
            response = requests.get(ARENA_CSV_FALLBACK, timeout=60)
            response.raise_for_status()
            
            df = pd.read_csv(io.StringIO(response.text))
            self.logger.info("Loaded %d models from Arena CSV", len(df))
            return df
            
        except Exception as e:
            self.logger.warning("CSV fetch failed: %s", e)
            return None
    
    def _fetch_arena_data(self) -> Tuple[pd.DataFrame, str]:
        """
        Fetch Arena leaderboard data with caching.
        
        Returns (dataframe, source_label) tuple.
        """
        # Check cache first
        if self._is_cache_valid():
            cached = self._load_from_cache()
            if cached is not None:
                return cached, "cache"
        
        # Try primary HF dataset
        df = self._fetch_from_hf_datasets(ARENA_HF_DATASET_PRIMARY)
        source = f"HuggingFace: {ARENA_HF_DATASET_PRIMARY}"
        
        # Try fallback HF dataset
        if df is None:
            df = self._fetch_from_hf_datasets(ARENA_HF_DATASET_FALLBACK)
            source = f"HuggingFace: {ARENA_HF_DATASET_FALLBACK}"
        
        # Try CSV fallback
        if df is None:
            df = self._fetch_from_csv()
            source = "CSV fallback"
        
        if df is None:
            raise RuntimeError("Failed to fetch Arena data from all sources")
        
        # Cache the result
        self._save_to_cache(df, source)
        
        return df, source
    
    def _normalize_arena_name(self, name: str) -> str:
        """
        Normalize an Arena model name for matching.
        
        Handles patterns like:
        - "ChatGPT-4o-latest (2025-03-26)" → "chatgpt-4o-latest"
        - "Claude Opus 4 (thinking-16k)" → "claude-opus-4"
        - "Gemini-2.5-Pro" → "gemini-2.5-pro"
        """
        if not name:
            return ""
        
        name = str(name).lower().strip()
        
        # Remove parenthetical suffixes (dates, thinking-XYk, etc.)
        name = re.sub(r'\s*\([^)]+\)$', '', name)
        name = re.sub(r'\s*\([^)]+\)$', '', name)  # Apply twice for nested
        
        # Normalize spaces to hyphens
        name = re.sub(r'\s+', '-', name)
        
        # Remove underscores → hyphens
        name = name.replace("_", "-")
        
        # Remove punctuation except hyphens and dots (keep version numbers)
        name = re.sub(r"[^\w\-.]", "", name)
        
        # Normalize multiple hyphens
        name = re.sub(r"-+", "-", name).strip("-")
        
        return name
    
    def _normalize_slug(self, slug: str) -> Tuple[str, str]:
        """
        Normalize an OpenRouter slug for matching.
        
        Returns (full_normalized, model_part_normalized) tuple.
        """
        if not slug:
            return "", ""
        
        slug = str(slug).lower().strip()
        
        # Split into provider/model
        parts = slug.split("/", 1)
        if len(parts) == 2:
            provider, model = parts
        else:
            provider, model = "", slug
        
        # Remove common suffixes for matching
        model_clean = model
        for suffix in [":free", ":extended", ":exacto", ":thinking"]:
            if model_clean.endswith(suffix):
                model_clean = model_clean[:-len(suffix)]
        
        # Normalize
        model_clean = model_clean.replace("_", "-").replace(" ", "-")
        model_clean = re.sub(r"-+", "-", model_clean).strip("-")
        
        full = f"{provider}-{model_clean}" if provider else model_clean
        full = re.sub(r"-+", "-", full).strip("-")
        
        return full, model_clean
    
    def _fuzzy_score(self, s1: str, s2: str) -> float:
        """
        Compute fuzzy matching score between two strings.
        
        Uses rapidfuzz if available, else difflib.
        Returns score 0.0 to 1.0.
        """
        if not s1 or not s2:
            return 0.0
        
        if self._fuzzy_available:
            try:
                from rapidfuzz import fuzz
                # Use token_set_ratio for better matching of reordered words
                ratio1 = fuzz.ratio(s1, s2) / 100.0
                ratio2 = fuzz.token_set_ratio(s1, s2) / 100.0
                return max(ratio1, ratio2)
            except Exception:
                pass
        
        # Fallback to difflib
        import difflib
        return difflib.SequenceMatcher(None, s1, s2).ratio()
    
    def _build_candidate_strings(
        self, row: pd.Series, slug: str
    ) -> List[str]:
        """
        Build multiple candidate strings from an OpenRouter row for matching.
        """
        candidates = []
        
        # From slug
        full_norm, model_part = self._normalize_slug(slug)
        if full_norm:
            candidates.append(full_norm)
        if model_part:
            candidates.append(model_part)
        
        # From model_name if available
        model_name = row.get("model_name")
        if pd.notna(model_name) and model_name:
            norm_name = self._normalize_arena_name(str(model_name))
            if norm_name and norm_name not in candidates:
                candidates.append(norm_name)
        
        # From display_name if available
        display_name = row.get("display_name")
        if pd.notna(display_name) and display_name:
            norm_display = self._normalize_arena_name(str(display_name))
            if norm_display and norm_display not in candidates:
                candidates.append(norm_display)
        
        return candidates
    
    def _extract_version_markers(self, text: str) -> set:
        """Extract version-like markers for conflict detection."""
        markers = set()
        text_lower = text.lower()
        
        # Version numbers like 2.5, 3, 4, v3
        for match in re.findall(r'(?:^|[^0-9])([0-9]+(?:\.[0-9]+)?)', text_lower):
            markers.add(f"v{match}")
        
        # Size markers
        size_patterns = [
            (r'\b(nano|micro|mini|small|medium|large|huge|xl|xxl)\b', lambda m: m.group(1)),
            (r'\b(\d+)b\b', lambda m: f"size-{m.group(1)}b"),
            (r'\b(\d+)k\b', lambda m: f"ctx-{m.group(1)}k"),
        ]
        for pattern, extractor in size_patterns:
            for match in re.finditer(pattern, text_lower):
                markers.add(extractor(match))
        
        # Model-type markers
        for marker in ["lite", "premier", "pro", "ultra", "flash", "opus", "sonnet", "haiku"]:
            if marker in text_lower:
                markers.add(marker)
        
        return markers
    
    def _has_conflict(self, candidate: str, arena_key: str) -> bool:
        """Check if there's a conflicting version/size marker."""
        cand_markers = self._extract_version_markers(candidate)
        arena_markers = self._extract_version_markers(arena_key)
        
        # Check for conflicting size markers
        size_markers = {"nano", "micro", "mini", "small", "medium", "large", "huge", "xl", "xxl",
                        "lite", "premier", "pro", "ultra"}
        cand_sizes = cand_markers & size_markers
        arena_sizes = arena_markers & size_markers
        
        if cand_sizes and arena_sizes and cand_sizes != arena_sizes:
            return True
        
        # Check for conflicting major versions (e.g., v2 vs v3)
        cand_versions = {m for m in cand_markers if m.startswith("v") and "." not in m}
        arena_versions = {m for m in arena_markers if m.startswith("v") and "." not in m}
        
        if cand_versions and arena_versions and cand_versions != arena_versions:
            return True
        
        # Check for opus vs sonnet vs haiku conflict
        model_types = {"opus", "sonnet", "haiku"}
        cand_types = cand_markers & model_types
        arena_types = arena_markers & model_types
        
        if cand_types and arena_types and cand_types != arena_types:
            return True
        
        return False
    
    def _match_model(
        self,
        row: pd.Series,
        slug: str,
        arena_lookup: Dict[str, Dict[str, Any]],
    ) -> Tuple[str, float, Optional[Dict[str, Any]]]:
        """
        Match an OpenRouter model to Arena data.
        
        Returns:
            (match_status, match_score, arena_info_or_none)
        """
        if not slug:
            return "unmatched", 0.0, None
        
        # Build candidate strings
        candidates = self._build_candidate_strings(row, slug)
        if not candidates:
            return "unmatched", 0.0, None
        
        # Try exact match first
        for candidate in candidates:
            if candidate in arena_lookup:
                return "matched", 1.0, arena_lookup[candidate]
        
        # Fuzzy matching with conflict detection
        best_score = 0.0
        best_arena_key = None
        
        for arena_key, arena_info in arena_lookup.items():
            for candidate in candidates:
                # Skip if there's a version/size conflict
                if self._has_conflict(candidate, arena_key):
                    continue
                
                score = self._fuzzy_score(candidate, arena_key)
                
                # Also try contains matching with length penalty
                if len(candidate) >= 5 and len(arena_key) >= 5:
                    if candidate in arena_key or arena_key in candidate:
                        contain_score = min(len(candidate), len(arena_key)) / max(len(candidate), len(arena_key))
                        score = max(score, contain_score * 0.90)
                
                if score > best_score:
                    best_score = score
                    best_arena_key = arena_key
        
        if best_score >= MATCH_THRESHOLD_HEURISTIC and best_arena_key:
            return "matched", round(best_score, 3), arena_lookup[best_arena_key]
        
        return "unmatched", round(best_score, 3), None
    
    def _identify_columns(self, arena_df: pd.DataFrame) -> Dict[str, Optional[str]]:
        """Identify key columns in the Arena DataFrame."""
        columns = {
            "model_name": None,
            "arena_score": None,
            "rank": None,
            "votes": None,
            "ci_95": None,
            "organization": None,
            "license": None,
        }
        
        col_lower_map = {c.lower(): c for c in arena_df.columns}
        
        # Model name column
        for pattern in ["model", "model_name", "name"]:
            if pattern in col_lower_map:
                columns["model_name"] = col_lower_map[pattern]
                break
        
        # Arena score column
        for pattern in ["arena score", "arena_score", "elo", "rating", "score"]:
            if pattern.replace(" ", "") in col_lower_map.get(pattern.replace(" ", ""), "") or \
               pattern in [c.lower() for c in arena_df.columns]:
                for col in arena_df.columns:
                    if pattern.replace(" ", "") in col.lower().replace(" ", ""):
                        columns["arena_score"] = col
                        break
            if columns["arena_score"]:
                break
        
        # More specific matching
        for col in arena_df.columns:
            col_lower = col.lower()
            if "arena" in col_lower and "score" in col_lower:
                columns["arena_score"] = col
            if col_lower == "votes":
                columns["votes"] = col
            if "95" in col_lower and "ci" in col_lower:
                columns["ci_95"] = col
            if col_lower == "organization":
                columns["organization"] = col
            if col_lower == "license":
                columns["license"] = col
            if "rank" in col_lower and "ub" in col_lower:
                columns["rank"] = col
        
        # Fallback for rank
        if columns["rank"] is None:
            for col in arena_df.columns:
                if "rank" in col.lower():
                    columns["rank"] = col
                    break
        
        return columns
    
    def _do_enrich(self, df: pd.DataFrame, result: EnricherResult) -> pd.DataFrame:
        """Fetch Arena data and enrich the catalog."""
        
        if self.dry_run:
            self.logger.info("[DRY RUN] Would fetch LMSYS Arena data")
            result.warnings.append("Dry run - no API calls made")
            return df
        
        try:
            arena_df, source_label = self._fetch_arena_data()
        except Exception as e:
            result.warnings.append(f"Failed to fetch Arena data: {e}")
            self.logger.warning("Arena fetch failed: %s", e)
            return df
        
        now_iso = datetime.now(timezone.utc).isoformat()
        today = now_iso[:10]
        
        # Initialize new columns
        new_columns = [
            "arena_rank",
            "arena_score",
            "arena_votes",
            "arena_95ci",
            "arena_organization",
            "arena_license",
            "arena_match_status",
            "arena_match_score",
            "arena_matched_name",
            "arena_asof_date",
            "arena_source_name",
            "arena_source_url",
            "arena_retrieved_at",
        ]
        
        for col in new_columns:
            if col not in df.columns:
                df[col] = None
        
        # Identify Arena columns
        arena_cols = self._identify_columns(arena_df)
        name_col = arena_cols["model_name"]
        score_col = arena_cols["arena_score"]
        rank_col = arena_cols["rank"]
        votes_col = arena_cols["votes"]
        ci_col = arena_cols["ci_95"]
        org_col = arena_cols["organization"]
        lic_col = arena_cols["license"]
        
        self.logger.info(
            "Arena columns identified: name=%s, score=%s, rank=%s, votes=%s",
            name_col, score_col, rank_col, votes_col
        )
        
        # Build Arena lookup by normalized name
        arena_lookup: Dict[str, Dict[str, Any]] = {}
        
        for idx, row in arena_df.iterrows():
            original_name = str(row.get(name_col, "")) if name_col else ""
            if not original_name or original_name == "nan":
                continue
            
            normalized = self._normalize_arena_name(original_name)
            if not normalized:
                continue
            
            entry = {
                "original_name": original_name,
                "score": row.get(score_col) if score_col else None,
                "rank": row.get(rank_col) if rank_col else idx + 1,
                "votes": row.get(votes_col) if votes_col else None,
                "ci_95": row.get(ci_col) if ci_col else None,
                "organization": row.get(org_col) if org_col else None,
                "license": row.get(lic_col) if lic_col else None,
            }
            
            arena_lookup[normalized] = entry
        
        self.logger.info("Built Arena lookup with %d unique models", len(arena_lookup))
        
        # Match and enrich
        matched_count = 0
        unmatched_count = 0
        unmatched_details: List[Dict[str, Any]] = []
        
        for idx, row in df.iterrows():
            slug = row.get("openrouter_slug")
            if pd.isna(slug) or not slug:
                continue
            
            slug = str(slug).strip()
            
            # Match to Arena
            match_status, match_score, arena_info = self._match_model(
                row, slug, arena_lookup
            )
            
            # Always set match status and score
            df.at[idx, "arena_match_status"] = match_status
            df.at[idx, "arena_match_score"] = match_score if match_score > 0 else None
            
            if match_status == "matched" and arena_info:
                # Write metrics
                if pd.notna(arena_info.get("score")):
                    df.at[idx, "arena_score"] = arena_info["score"]
                if pd.notna(arena_info.get("rank")):
                    df.at[idx, "arena_rank"] = arena_info["rank"]
                if pd.notna(arena_info.get("votes")):
                    df.at[idx, "arena_votes"] = arena_info["votes"]
                if arena_info.get("ci_95"):
                    df.at[idx, "arena_95ci"] = str(arena_info["ci_95"])
                if arena_info.get("organization"):
                    df.at[idx, "arena_organization"] = arena_info["organization"]
                if arena_info.get("license"):
                    df.at[idx, "arena_license"] = arena_info["license"]
                
                df.at[idx, "arena_matched_name"] = arena_info.get("original_name")
                df.at[idx, "arena_source_name"] = source_label
                df.at[idx, "arena_source_url"] = self.source_url
                df.at[idx, "arena_retrieved_at"] = now_iso
                df.at[idx, "arena_asof_date"] = today
                
                matched_count += 1
            else:
                unmatched_count += 1
                unmatched_details.append({
                    "slug": slug,
                    "best_score": match_score,
                })
                result.data_gaps.append({
                    "slug": slug,
                    "source": "lmsys_arena",
                    "field": "arena_score",
                    "reason": "unmatched",
                    "best_score": match_score,
                    "retrieved_at": now_iso,
                })
        
        result.rows_enriched = matched_count
        result.rows_with_gaps = unmatched_count
        
        # Log summary
        self.logger.info(
            "Arena enrichment complete: matched %d (%.1f%%), unmatched %d",
            matched_count,
            100.0 * matched_count / (matched_count + unmatched_count) if (matched_count + unmatched_count) > 0 else 0,
            unmatched_count,
        )
        
        # Log top 10 unmatched with closest scores for debugging
        if unmatched_details:
            unmatched_sorted = sorted(
                unmatched_details, key=lambda x: x["best_score"], reverse=True
            )
            self.logger.info("Top unmatched models (by closest match score):")
            for item in unmatched_sorted[:10]:
                self.logger.info("  %.2f: %s", item["best_score"], item["slug"])
        
        return df
