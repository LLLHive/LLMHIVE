"""
HuggingFace Open LLM Leaderboard Enricher

Fetches benchmark results from the HuggingFace Open LLM Leaderboard v2.
Uses HuggingFace datasets with local caching for reliability.

Key Features:
- Eligibility tracking: Only open-weight models with HF repos are expected to match
- Explicit hugging_face_id matching with robust normalization
- Fuzzy matching fallback with conflict detection and size mismatch prevention
- Clear classification of why models don't match (closed_model, missing_hf_id, etc.)

Coverage Semantics:
- Attempt Coverage: All rows where enrichment was attempted
- Eligible Coverage: Models expected to be on HF OLLB (open-weight with HF repos)
- Metric Coverage (Eligible): % of eligible models that matched with benchmark data
"""
from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import pandas as pd
import requests
from tenacity import retry, stop_after_attempt, wait_exponential

from .base import BaseEnricher, EnricherResult

logger = logging.getLogger(__name__)

# HuggingFace Open LLM Leaderboard data sources
# v2 is the current active leaderboard
HF_LEADERBOARD_DATASET_V2 = "open-llm-leaderboard/contents"
HF_LEADERBOARD_URL = "https://huggingface.co/spaces/open-llm-leaderboard/open_llm_leaderboard"

# Cache settings
DEFAULT_CACHE_DIR = Path(".cache/llmhive_modeldb/hf_ollb")
CACHE_TTL_HOURS = 24

# Matching thresholds
MATCH_THRESHOLD_EXACT = 1.0
MATCH_THRESHOLD_FUZZY = 0.90  # Higher threshold to avoid false positives like qwen-plus -> qwenmplus
MATCH_THRESHOLD_CONFLICT = 0.02  # If top-2 are within this, mark as conflict

# Known closed model providers (not expected to be on HF OLLB)
CLOSED_MODEL_PROVIDERS = {
    "openai", "anthropic", "google", "cohere", "ai21",
    "inflection", "perplexity", "x-ai", "amazon",
}

# Known closed model name patterns
CLOSED_MODEL_PATTERNS = [
    r"^gpt-",           # OpenAI GPT models
    r"^o1-",            # OpenAI o1 reasoning models
    r"^claude-",        # Anthropic Claude
    r"^gemini-",        # Google Gemini
    r"^palm-",          # Google PaLM
    r"^bard",           # Google Bard
    r"^command-",       # Cohere Command
    r"^jurassic-",      # AI21 Jurassic
    r"^grok-",          # xAI Grok (closed API)
    r"^nova-",          # Amazon Nova
]

# Ineligibility reasons
INELIGIBLE_CLOSED_MODEL = "closed_model"
INELIGIBLE_MISSING_HF_ID = "missing_hf_id"
INELIGIBLE_NON_HF_PROVIDER = "non_hf_provider"
INELIGIBLE_UNKNOWN = "unknown"


class HFLeaderboardEnricher(BaseEnricher):
    """
    Enricher that fetches HuggingFace Open LLM Leaderboard metrics.
    
    Columns added:
    
    Eligibility (new):
    - hf_ollb_eligible (boolean: True if model expected on HF OLLB)
    - hf_ollb_ineligible_reason (closed_model/missing_hf_id/non_hf_provider/unknown)
    - hf_ollb_candidate_hf_id (the repo ID we attempted to match)
    
    Benchmark Scores:
    - hf_ollb_mmlu_pro (MMLU-PRO score from v2)
    - hf_ollb_ifeval (IFEval score)
    - hf_ollb_bbh (BBH score)
    - hf_ollb_math (MATH Lvl 5 score)
    - hf_ollb_gpqa (GPQA score)
    - hf_ollb_musr (MUSR score)
    - hf_ollb_avg (Average score)
    
    Matching Metadata:
    - hf_ollb_match_status (matched/unmatched/conflict/low_confidence)
    - hf_ollb_match_method (hf_id_exact/slug_exact/fuzzy/none)
    - hf_ollb_match_score (0.0-1.0)
    - hf_ollb_matched_name (original HF repo name)
    - hf_ollb_repo_id (canonical HF repo ID)
    
    Provenance:
    - hf_ollb_source_dataset
    - hf_ollb_asof_date
    - hf_ollb_retrieved_at
    """
    
    name = "hf_open_llm_leaderboard"
    source_name = "HuggingFace Open LLM Leaderboard v2"
    source_url = HF_LEADERBOARD_URL
    
    # V2 benchmark column mappings (dataset column -> our column)
    BENCHMARK_COLUMNS_V2 = {
        "MMLU-PRO": "hf_ollb_mmlu_pro",
        "MMLU-PRO Raw": "hf_ollb_mmlu_pro_raw",
        "IFEval": "hf_ollb_ifeval",
        "IFEval Raw": "hf_ollb_ifeval_raw",
        "BBH": "hf_ollb_bbh",
        "BBH Raw": "hf_ollb_bbh_raw",
        "MATH Lvl 5": "hf_ollb_math",
        "MATH Lvl 5 Raw": "hf_ollb_math_raw",
        "GPQA": "hf_ollb_gpqa",
        "GPQA Raw": "hf_ollb_gpqa_raw",
        "MUSR": "hf_ollb_musr",
        "MUSR Raw": "hf_ollb_musr_raw",
        "Average ⬆️": "hf_ollb_avg",
    }
    
    # Metadata columns from v2
    METADATA_COLUMNS_V2 = {
        "#Params (B)": "hf_ollb_params_b",
        "Architecture": "hf_ollb_architecture",
        "Type": "hf_ollb_type",
        "Hub License": "hf_ollb_license",
    }
    
    def __init__(
        self,
        dry_run: bool = False,
        cache_dir: Optional[str] = None,
    ):
        super().__init__(dry_run=dry_run, cache_dir=cache_dir)
        self._cache_dir = Path(cache_dir) if cache_dir else DEFAULT_CACHE_DIR
        self._leaderboard_data: Optional[pd.DataFrame] = None
        self._fuzzy_available = False
        
        # Try to import rapidfuzz
        try:
            from rapidfuzz import fuzz
            self._fuzzy_available = True
        except ImportError:
            logger.info("rapidfuzz not available, using difflib for matching")
    
    def _get_cache_path(self) -> Path:
        return self._cache_dir / "hf_leaderboard_v2.parquet"
    
    def _get_cache_metadata_path(self) -> Path:
        return self._cache_dir / "hf_cache_metadata.json"
    
    def _is_cache_valid(self) -> bool:
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
            
            self.logger.info("Using cached HF leaderboard data (%.1f hours old)", age_hours)
            return True
            
        except Exception as e:
            self.logger.warning("Cache metadata invalid: %s", e)
            return False
    
    def _load_from_cache(self) -> Optional[pd.DataFrame]:
        try:
            return pd.read_parquet(self._get_cache_path())
        except Exception as e:
            self.logger.warning("Failed to load cache: %s", e)
            return None
    
    def _save_to_cache(self, df: pd.DataFrame, source: str) -> None:
        try:
            self._cache_dir.mkdir(parents=True, exist_ok=True)
            df.to_parquet(self._get_cache_path(), index=False)
            
            meta = {
                "cached_at": datetime.now(timezone.utc).isoformat(),
                "source": source,
                "row_count": len(df),
                "columns": list(df.columns),
            }
            with open(self._get_cache_metadata_path(), "w", encoding="utf-8") as f:
                json.dump(meta, f, indent=2)
            
            self.logger.info("Cached HF leaderboard data: %d rows", len(df))
        except Exception as e:
            self.logger.warning("Failed to cache: %s", e)
    
    def _fetch_leaderboard_v2(self) -> Optional[pd.DataFrame]:
        """Fetch v2 leaderboard from HuggingFace datasets."""
        try:
            from datasets import load_dataset
            
            self.logger.info("Loading HF Leaderboard v2 from datasets...")
            ds = load_dataset(HF_LEADERBOARD_DATASET_V2, split="train")
            df = ds.to_pandas()
            self.logger.info("Loaded %d models from HF Leaderboard v2", len(df))
            return df
        except ImportError:
            self.logger.warning("datasets library not installed")
            return None
        except Exception as e:
            self.logger.warning("HF v2 fetch failed: %s", e)
            return None
    
    def _fetch_leaderboard_data(self) -> Tuple[pd.DataFrame, str]:
        """Fetch leaderboard data with caching."""
        if self._is_cache_valid():
            cached = self._load_from_cache()
            if cached is not None:
                return cached, "cache"
        
        df = self._fetch_leaderboard_v2()
        source = HF_LEADERBOARD_DATASET_V2
        
        if df is None or len(df) == 0:
            raise RuntimeError("Failed to fetch HF Leaderboard data")
        
        self._save_to_cache(df, source)
        return df, source
    
    def _normalize_repo_id(self, repo_id: str) -> str:
        """
        Normalize a HuggingFace repo ID for matching.
        
        Handles:
        - Case normalization
        - :free and other OpenRouter suffixes
        - Whitespace/punctuation
        """
        if not repo_id:
            return ""
        
        repo_id = str(repo_id).lower().strip()
        
        # Remove OpenRouter suffixes like :free, :extended
        if ":" in repo_id:
            repo_id = repo_id.split(":")[0]
        
        # Remove leading/trailing whitespace and quotes
        repo_id = repo_id.strip().strip('"').strip("'")
        
        # Normalize separators (keep / for org/model format)
        repo_id = repo_id.replace(" ", "-").replace("_", "-")
        
        # Collapse multiple hyphens
        repo_id = re.sub(r"-+", "-", repo_id).strip("-")
        
        return repo_id
    
    def _normalize_for_fuzzy(self, name: str) -> str:
        """
        Normalize a name for fuzzy matching (more aggressive).
        """
        if not name:
            return ""
        
        name = self._normalize_repo_id(name)
        
        # Remove org prefix for fuzzy matching
        if "/" in name:
            name = name.split("/", 1)[1]
        
        # Remove common suffixes that differ between sources
        suffixes = [
            r"-instruct$", r"-chat$", r"-it$", r"-base$",
            r"-hf$", r"-gguf$", r"-gptq$", r"-awq$",
            r"-fp16$", r"-bf16$", r"-4bit$", r"-8bit$",
        ]
        for suffix in suffixes:
            name = re.sub(suffix, "", name, flags=re.IGNORECASE)
        
        return name
    
    def _extract_size_markers(self, text: str) -> Set[str]:
        """Extract model size markers for conflict detection."""
        markers = set()
        text_lower = text.lower()
        
        # Size patterns like 7b, 70b, 1.5b
        for match in re.findall(r'(\d+(?:\.\d+)?)[bB]', text_lower):
            markers.add(f"size-{match}b")
        
        # Version patterns like v1, v2, v0.1
        for match in re.findall(r'v(\d+(?:\.\d+)?)', text_lower):
            markers.add(f"ver-{match}")
        
        return markers
    
    def _has_size_conflict(self, s1: str, s2: str) -> bool:
        """Check if two strings have conflicting size markers."""
        m1 = self._extract_size_markers(s1)
        m2 = self._extract_size_markers(s2)
        
        # Get size markers only
        sizes1 = {m for m in m1 if m.startswith("size-")}
        sizes2 = {m for m in m2 if m.startswith("size-")}
        
        # If both have size markers and they differ, conflict
        if sizes1 and sizes2 and sizes1 != sizes2:
            return True
        
        return False
    
    def _is_closed_model(self, row: pd.Series) -> bool:
        """
        Determine if a model is from a closed provider (not expected on HF OLLB).
        
        Conservative: Only returns True if we're confident it's closed.
        """
        slug = row.get("openrouter_slug")
        model_name = row.get("model_name", "")
        
        if pd.isna(slug) or not slug:
            return False
        
        slug = str(slug).lower().strip()
        model_name = str(model_name).lower() if pd.notna(model_name) else ""
        
        # Check provider prefix in slug (e.g., "openai/gpt-4o")
        if "/" in slug:
            provider = slug.split("/")[0]
            if provider in CLOSED_MODEL_PROVIDERS:
                return True
        
        # Check known closed model name patterns
        for pattern in CLOSED_MODEL_PATTERNS:
            if re.match(pattern, slug.split("/")[-1] if "/" in slug else slug):
                return True
            if model_name and re.match(pattern, model_name):
                return True
        
        return False
    
    def _looks_like_hf_repo_id(self, value: str) -> bool:
        """Check if a string looks like a HuggingFace org/model repo ID."""
        if not value:
            return False
        
        value = str(value).strip()
        
        # Must contain exactly one slash
        if value.count("/") != 1:
            return False
        
        parts = value.split("/")
        # Both parts must be non-empty and look like valid identifiers
        if not parts[0] or not parts[1]:
            return False
        
        # Basic sanity: org and model should have reasonable lengths
        if len(parts[0]) < 2 or len(parts[1]) < 2:
            return False
        
        # Should not contain obvious non-HF patterns
        if any(p in value.lower() for p in [":free", ":extended", "http", ".com"]):
            return False
        
        return True
    
    def _determine_eligibility(
        self, 
        row: pd.Series,
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Determine if a model is eligible for HF OLLB matching.
        
        Returns: (eligible, ineligible_reason, candidate_hf_id)
        
        Eligibility criteria:
        1. Has explicit hugging_face_id that looks like org/name -> eligible
        2. Slug looks like org/name and model appears open-weight -> eligible
        3. Model is from known closed provider -> ineligible (closed_model)
        4. No HF ID and slug doesn't look like repo -> ineligible (missing_hf_id)
        """
        hf_id = row.get("hugging_face_id")
        slug = row.get("openrouter_slug")
        
        # Priority 1: Explicit HF ID
        if pd.notna(hf_id) and hf_id:
            hf_id_str = str(hf_id).strip()
            if self._looks_like_hf_repo_id(hf_id_str):
                normalized = self._normalize_repo_id(hf_id_str)
                return True, None, normalized
        
        # Check if closed model
        if self._is_closed_model(row):
            # Still record what we would have tried
            candidate = None
            if pd.notna(slug) and slug:
                candidate = self._normalize_repo_id(str(slug))
            return False, INELIGIBLE_CLOSED_MODEL, candidate
        
        # Priority 2: Slug looks like HF repo ID
        if pd.notna(slug) and slug:
            slug_str = str(slug).strip()
            normalized = self._normalize_repo_id(slug_str)
            
            if self._looks_like_hf_repo_id(normalized):
                return True, None, normalized
            
            # Slug doesn't look like a HF repo
            return False, INELIGIBLE_MISSING_HF_ID, normalized
        
        # No slug at all
        return False, INELIGIBLE_UNKNOWN, None
    
    def _fuzzy_score(self, s1: str, s2: str) -> float:
        """Compute fuzzy matching score."""
        if not s1 or not s2:
            return 0.0
        
        if self._fuzzy_available:
            try:
                from rapidfuzz import fuzz
                ratio = fuzz.ratio(s1, s2) / 100.0
                token_ratio = fuzz.token_set_ratio(s1, s2) / 100.0
                return max(ratio, token_ratio)
            except Exception:
                pass
        
        import difflib
        return difflib.SequenceMatcher(None, s1, s2).ratio()
    
    def _build_hf_index(self, hf_df: pd.DataFrame) -> Dict[str, Dict[str, Any]]:
        """
        Build index from HF leaderboard data.
        
        Key: normalized repo_id (fullname column)
        Value: dict with benchmarks and metadata
        """
        index: Dict[str, Dict[str, Any]] = {}
        
        # Identify the fullname column
        fullname_col = None
        for candidate in ["fullname", "Model", "model", "model_id", "repo_id"]:
            if candidate in hf_df.columns:
                fullname_col = candidate
                break
        
        if fullname_col is None:
            self.logger.warning("Could not identify model name column in HF data")
            return index
        
        self.logger.info("Using '%s' as model identifier column", fullname_col)
        
        for idx, row in hf_df.iterrows():
            # Get and clean the fullname
            fullname = row.get(fullname_col)
            if pd.isna(fullname) or not fullname:
                continue
            
            fullname = str(fullname).strip()
            
            # Handle HTML links in Model column
            if "<a " in fullname:
                # Extract the repo ID from the link
                match = re.search(r'huggingface\.co/([^">\s]+)', fullname)
                if match:
                    fullname = match.group(1)
            
            normalized = self._normalize_repo_id(fullname)
            if not normalized:
                continue
            
            entry = {
                "original_name": fullname,
                "normalized": normalized,
            }
            
            # Extract benchmark scores
            for hf_col, our_col in self.BENCHMARK_COLUMNS_V2.items():
                val = row.get(hf_col)
                if pd.notna(val):
                    try:
                        entry[our_col] = float(val)
                    except (ValueError, TypeError):
                        pass
            
            # Extract metadata
            for hf_col, our_col in self.METADATA_COLUMNS_V2.items():
                val = row.get(hf_col)
                if pd.notna(val):
                    entry[our_col] = val
            
            # Store in index (prefer first occurrence if duplicates)
            if normalized not in index:
                index[normalized] = entry
        
        return index
    
    def _match_model(
        self,
        row: pd.Series,
        hf_index: Dict[str, Dict[str, Any]],
    ) -> Tuple[str, str, float, Optional[Dict[str, Any]]]:
        """
        Match a model to HF leaderboard.
        
        Returns: (match_status, match_method, match_score, hf_info)
        """
        # Priority 1: Use explicit hugging_face_id if available
        hf_id = row.get("hugging_face_id")
        if pd.notna(hf_id) and hf_id:
            hf_id_norm = self._normalize_repo_id(str(hf_id))
            if hf_id_norm in hf_index:
                return "matched", "hf_id_exact", 1.0, hf_index[hf_id_norm]
        
        # Priority 2: Try OpenRouter slug as repo ID
        slug = row.get("openrouter_slug")
        if pd.notna(slug) and slug:
            slug = str(slug).strip()
            
            # Remove provider prefix if present (e.g., "meta-llama/llama-3" -> "meta-llama/llama-3")
            # But keep the format since HF uses org/model
            slug_norm = self._normalize_repo_id(slug)
            
            if slug_norm in hf_index:
                return "matched", "slug_exact", 1.0, hf_index[slug_norm]
            
            # Try without the provider prefix (e.g., "openai/gpt-4" -> check just "gpt-4")
            if "/" in slug:
                # For OpenRouter, first part is provider, not org
                # Try the model part against all HF repos
                model_part = slug.split("/", 1)[1]
                model_part_norm = self._normalize_repo_id(model_part)
                
                # Check if model_part matches the model portion of any HF repo
                for hf_key, hf_info in hf_index.items():
                    if "/" in hf_key:
                        hf_model_part = hf_key.split("/", 1)[1]
                        if model_part_norm == hf_model_part:
                            return "matched", "model_part_exact", 0.95, hf_info
        
        # Priority 3: Fuzzy matching as fallback
        model_name = row.get("model_name")
        candidates = []
        
        if pd.notna(hf_id) and hf_id:
            candidates.append(self._normalize_for_fuzzy(str(hf_id)))
        if pd.notna(slug) and slug:
            candidates.append(self._normalize_for_fuzzy(str(slug)))
        if pd.notna(model_name) and model_name:
            candidates.append(self._normalize_for_fuzzy(str(model_name)))
        
        if not candidates:
            return "unmatched", "none", 0.0, None
        
        best_matches: List[Tuple[float, str, Dict[str, Any]]] = []
        
        for hf_key, hf_info in hf_index.items():
            hf_fuzzy = self._normalize_for_fuzzy(hf_key)
            
            for candidate in candidates:
                # Check for size conflicts
                if self._has_size_conflict(candidate, hf_key):
                    continue
                
                score = self._fuzzy_score(candidate, hf_fuzzy)
                
                if score >= MATCH_THRESHOLD_FUZZY:
                    best_matches.append((score, hf_key, hf_info))
        
        if not best_matches:
            return "unmatched", "fuzzy", 0.0, None
        
        # Sort by score descending
        best_matches.sort(key=lambda x: x[0], reverse=True)
        
        # Check for conflict (top-2 too close)
        if len(best_matches) >= 2:
            if best_matches[0][0] - best_matches[1][0] < MATCH_THRESHOLD_CONFLICT:
                return "conflict", "fuzzy", best_matches[0][0], None
        
        top_match = best_matches[0]
        if top_match[0] < MATCH_THRESHOLD_FUZZY:
            return "low_confidence", "fuzzy", top_match[0], None
        
        return "matched", "fuzzy", round(top_match[0], 3), top_match[2]
    
    def _do_enrich(self, df: pd.DataFrame, result: EnricherResult) -> pd.DataFrame:
        """Fetch HF Leaderboard data and enrich the catalog."""
        
        if self.dry_run:
            self.logger.info("[DRY RUN] Would fetch HF Leaderboard data")
            result.warnings.append("Dry run - no API calls made")
            return df
        
        try:
            hf_df, source = self._fetch_leaderboard_data()
        except Exception as e:
            result.warnings.append(f"Failed to fetch HF Leaderboard data: {e}")
            self.logger.warning("HF Leaderboard fetch failed: %s", e)
            return df
        
        now_iso = datetime.now(timezone.utc).isoformat()
        today = now_iso[:10]
        
        # Initialize new columns with appropriate dtypes
        # Numeric columns (benchmarks)
        numeric_columns = [
            "hf_ollb_mmlu_pro",
            "hf_ollb_ifeval",
            "hf_ollb_bbh",
            "hf_ollb_math",
            "hf_ollb_gpqa",
            "hf_ollb_musr",
            "hf_ollb_avg",
            "hf_ollb_match_score",
        ]
        
        # Boolean columns (eligibility)
        boolean_columns = [
            "hf_ollb_eligible",
        ]
        
        # String columns (metadata, provenance, eligibility)
        string_columns = [
            "hf_ollb_match_status",
            "hf_ollb_match_method",
            "hf_ollb_matched_name",
            "hf_ollb_repo_id",
            "hf_ollb_source_dataset",
            "hf_ollb_asof_date",
            "hf_ollb_source_name",
            "hf_ollb_source_url",
            "hf_ollb_retrieved_at",
            # New eligibility columns
            "hf_ollb_ineligible_reason",
            "hf_ollb_candidate_hf_id",
        ]
        
        for col in numeric_columns:
            if col not in df.columns:
                df[col] = pd.NA
        
        for col in boolean_columns:
            if col not in df.columns:
                df[col] = None
        
        for col in string_columns:
            if col not in df.columns:
                df[col] = None
            # Ensure object dtype for string columns
            if df[col].dtype != object:
                df[col] = df[col].astype(object)
        
        # Build HF index
        hf_index = self._build_hf_index(hf_df)
        self.logger.info("Built HF index with %d models", len(hf_index))
        
        # Match and enrich with eligibility tracking
        matched_count = 0
        unmatched_count = 0
        eligible_count = 0
        eligible_matched_count = 0
        ineligible_count = 0
        match_methods: Dict[str, int] = {}
        ineligible_reasons: Dict[str, int] = {}
        unmatched_eligible_details: List[Dict[str, Any]] = []
        
        for idx, row in df.iterrows():
            slug = row.get("openrouter_slug")
            if pd.isna(slug) or not slug:
                continue
            
            # Step 1: Determine eligibility
            eligible, ineligible_reason, candidate_hf_id = self._determine_eligibility(row)
            
            # Record eligibility info
            df.at[idx, "hf_ollb_eligible"] = eligible
            df.at[idx, "hf_ollb_ineligible_reason"] = ineligible_reason
            df.at[idx, "hf_ollb_candidate_hf_id"] = candidate_hf_id
            
            if eligible:
                eligible_count += 1
            else:
                ineligible_count += 1
                ineligible_reasons[ineligible_reason or "unknown"] = ineligible_reasons.get(ineligible_reason or "unknown", 0) + 1
            
            # Step 2: Perform matching (for all models, but expected success varies by eligibility)
            match_status, match_method, match_score, hf_info = self._match_model(
                row, hf_index
            )
            
            # Always record match status (for attempt coverage)
            df.at[idx, "hf_ollb_match_status"] = match_status
            df.at[idx, "hf_ollb_match_method"] = match_method
            df.at[idx, "hf_ollb_match_score"] = match_score if match_score > 0 else None
            
            if match_status == "matched" and hf_info:
                # Copy benchmark scores
                for our_col in self.BENCHMARK_COLUMNS_V2.values():
                    if our_col in hf_info:
                        if our_col not in df.columns:
                            df[our_col] = None
                        df.at[idx, our_col] = hf_info[our_col]
                
                # Copy metadata
                for our_col in self.METADATA_COLUMNS_V2.values():
                    if our_col in hf_info:
                        if our_col not in df.columns:
                            df[our_col] = None
                        df.at[idx, our_col] = hf_info[our_col]
                
                df.at[idx, "hf_ollb_matched_name"] = hf_info.get("original_name")
                df.at[idx, "hf_ollb_repo_id"] = hf_info.get("normalized")
                df.at[idx, "hf_ollb_source_dataset"] = source
                df.at[idx, "hf_ollb_source_name"] = self.source_name
                df.at[idx, "hf_ollb_source_url"] = self.source_url
                df.at[idx, "hf_ollb_retrieved_at"] = now_iso
                df.at[idx, "hf_ollb_asof_date"] = today
                
                matched_count += 1
                match_methods[match_method] = match_methods.get(match_method, 0) + 1
                
                if eligible:
                    eligible_matched_count += 1
            else:
                unmatched_count += 1
                
                # Only track unmatched ELIGIBLE models for debugging
                if eligible:
                    unmatched_eligible_details.append({
                        "slug": str(slug),
                        "hf_id": str(row.get("hugging_face_id", "")),
                        "candidate_hf_id": candidate_hf_id or "",
                        "status": match_status,
                        "score": match_score,
                    })
                    result.data_gaps.append({
                        "slug": str(slug),
                        "source": "hf_open_llm_leaderboard",
                        "field": "hf_ollb_avg",
                        "reason": match_status,
                        "hf_id": str(row.get("hugging_face_id", "")),
                        "candidate_hf_id": candidate_hf_id or "",
                        "best_score": match_score,
                        "eligible": True,
                        "retrieved_at": now_iso,
                    })
        
        result.rows_enriched = matched_count
        result.rows_with_gaps = unmatched_count
        
        # Log comprehensive summary
        total_attempted = eligible_count + ineligible_count
        self.logger.info("=" * 60)
        self.logger.info("HF Leaderboard Enrichment Summary:")
        self.logger.info("  Total models attempted: %d", total_attempted)
        self.logger.info("  Eligible models: %d (%.1f%%)", 
                        eligible_count, 
                        100.0 * eligible_count / total_attempted if total_attempted > 0 else 0)
        self.logger.info("  Ineligible models: %d (%.1f%%)", 
                        ineligible_count,
                        100.0 * ineligible_count / total_attempted if total_attempted > 0 else 0)
        self.logger.info("  Ineligibility breakdown: %s", ineligible_reasons)
        self.logger.info("")
        self.logger.info("  Matched (all): %d (%.1f%%)", 
                        matched_count,
                        100.0 * matched_count / total_attempted if total_attempted > 0 else 0)
        self.logger.info("  Matched (eligible only): %d / %d (%.1f%%)", 
                        eligible_matched_count, eligible_count,
                        100.0 * eligible_matched_count / eligible_count if eligible_count > 0 else 0)
        self.logger.info("  Match methods: %s", match_methods)
        self.logger.info("=" * 60)
        
        # Log top unmatched ELIGIBLE models (these are the ones that matter)
        if unmatched_eligible_details:
            self.logger.info("Top unmatched ELIGIBLE models (should investigate):")
            for item in unmatched_eligible_details[:15]:
                self.logger.info("  %s | candidate=%s | status=%s | score=%.2f", 
                               item["slug"], item["candidate_hf_id"], 
                               item["status"], item["score"] or 0)
        
        return df
