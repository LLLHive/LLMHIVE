"""
HuggingFace Open LLM Leaderboard Enricher

Fetches benchmark results from the HuggingFace Open LLM Leaderboard v2.
Uses HuggingFace datasets with local caching for reliability.

Key Features:
- Eligibility tracking: Only open-weight models with HF repos are expected to match
- Multi-tier matching: exact -> prefix_unique -> fuzzy (with conflict detection)
- HF ID inference from provider docs and metadata columns
- Base model resolution via de-quantization transforms and optional HF Hub lookup
- "Not listed on leaderboard" semantics for models absent from dataset
- Clear debug semantics: attempted_methods, match_outcome, conflict_candidates

Coverage Semantics:
- Attempt Coverage: All rows where enrichment was attempted
- Eligible Coverage: Models expected to be on HF OLLB (open-weight with HF repos)
- Metric Coverage (Eligible): % of eligible models that matched with benchmark data
- Not-Listed Count: Eligible models where candidate(s) don't exist in leaderboard

Matching Tiers (priority order):
1. hf_id_exact: Exact match on hugging_face_id (or inferred)
2. hf_id_prefix_unique: Unique prefix match on hugging_face_id
3. slug_exact: Exact match on openrouter_slug
4. slug_prefix_unique: Unique prefix match on slug
5. base_model variants: De-quantized/wrapper-stripped candidates
6. fuzzy: Fuzzy matching with conservative threshold (>= 0.90)

Environment Variables:
- HF_OLLB_RESOLVE_BASE_MODEL: true/false (default false) - Enable HF Hub base_model lookup
"""
from __future__ import annotations

import json
import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import pandas as pd
import requests
from tenacity import retry, stop_after_attempt, wait_exponential

from .base import BaseEnricher, EnricherResult

# Environment toggle for HF Hub base model resolution
HF_OLLB_RESOLVE_BASE_MODEL = os.environ.get("HF_OLLB_RESOLVE_BASE_MODEL", "false").lower() == "true"

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

# Prefix matching separators (for unique prefix matching)
PREFIX_SEPARATORS = ["-", ".", "_"]

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

# Match outcome reasons (for non-matched eligible rows)
OUTCOME_HF_ID_NOT_FOUND = "hf_id_not_found"
OUTCOME_NO_UNIQUE_PREFIX = "no_unique_prefix"
OUTCOME_FUZZY_BELOW_THRESHOLD = "fuzzy_below_threshold"
OUTCOME_CONFLICT = "conflict"
OUTCOME_SIZE_MISMATCH = "size_mismatch"
OUTCOME_NOT_LISTED = "not_listed_on_leaderboard"
OUTCOME_NO_CANDIDATES = "no_candidates"
OUTCOME_LISTED_BUT_MISSING_METRICS = "listed_but_missing_metrics"

# De-quantization / wrapper suffixes to strip when deriving base model candidates
DEQUANT_SUFFIXES = [
    "-gguf", "-gptq", "-awq", "-exl2", "-bnb-4bit", "-bnb-8bit",
    "-4bit", "-8bit", "-int4", "-int8",
    "-fp16", "-bf16", "-fp8",
    "-hf",  # Sometimes added by wrappers
]

# HF model info cache directory
HF_MODEL_INFO_CACHE_DIR = Path(".cache/llmhive_modeldb/hf_model_info")


class HFLeaderboardEnricher(BaseEnricher):
    """
    Enricher that fetches HuggingFace Open LLM Leaderboard metrics.
    
    Columns added:
    
    Eligibility:
    - hf_ollb_eligible (boolean: True if model expected on HF OLLB)
    - hf_ollb_ineligible_reason (closed_model/missing_hf_id/non_hf_provider/unknown)
    - hf_ollb_candidate_hf_id (the candidate that produced match, or last tried)
    
    HF ID Inference:
    - hf_ollb_inferred_hf_id (string: inferred HF repo ID from metadata/docs)
    - hf_ollb_inferred_hf_id_source (string: which column/source produced the inference)
    - hf_ollb_base_model_hf_id (string: base model derived via transforms or HF Hub)
    - hf_ollb_candidate_set (string: brief list of candidates tried, deduped)
    
    Not-Listed Semantics:
    - hf_ollb_not_listed_on_leaderboard (boolean: True if candidates not in dataset)
    - hf_ollb_not_listed_reason (string: why not listed - candidate_repo_absent, etc.)
    
    Benchmark Scores (v2):
    - hf_ollb_mmlu_pro (MMLU-PRO score from v2)
    - hf_ollb_ifeval (IFEval score)
    - hf_ollb_bbh (BBH score)
    - hf_ollb_math (MATH Lvl 5 score)
    - hf_ollb_gpqa (GPQA score)
    - hf_ollb_musr (MUSR score)
    - hf_ollb_avg (Average score)
    
    Matching Metadata:
    - hf_ollb_match_status (matched/unmatched/conflict)
    - hf_ollb_match_method (ONLY set when matched)
    - hf_ollb_match_score (0.0-1.0)
    - hf_ollb_matched_name (original HF repo name)
    - hf_ollb_repo_id (canonical HF repo ID)
    
    Debug/Audit:
    - hf_ollb_attempted_methods (ordered methods tried)
    - hf_ollb_match_outcome (reason for non-match)
    - hf_ollb_conflict_candidates (top-2 candidates when conflict)
    
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
    
    def _normalize_hf_repo_id(self, repo_id: str) -> str:
        """
        Normalize a HuggingFace repo ID for matching.
        
        Handles:
        - URLs like "https://huggingface.co/org/name"
        - Trailing slashes
        - Case normalization
        - :free and other OpenRouter suffixes
        - Whitespace/quotes
        
        Returns canonical lowercase "org/name" format.
        """
        if not repo_id:
            return ""
        
        repo_id = str(repo_id).strip()
        
        # Remove leading/trailing whitespace and quotes
        repo_id = repo_id.strip('"').strip("'").strip()
        
        # Handle HuggingFace URLs
        # e.g., "https://huggingface.co/org/name" -> "org/name"
        url_patterns = [
            r"https?://huggingface\.co/([^/\s]+/[^/\s]+)/?",
            r"huggingface\.co/([^/\s]+/[^/\s]+)/?",
        ]
        for pattern in url_patterns:
            match = re.search(pattern, repo_id, re.IGNORECASE)
            if match:
                repo_id = match.group(1)
                break
        
        # Lowercase
        repo_id = repo_id.lower()
        
        # Remove trailing slashes
        repo_id = repo_id.rstrip("/")
        
        # Remove OpenRouter suffixes like :free, :extended
        if ":" in repo_id:
            repo_id = repo_id.split(":")[0]
        
        return repo_id
    
    def _normalize_repo_id(self, repo_id: str) -> str:
        """
        Legacy normalization for fuzzy matching compatibility.
        
        More aggressive: also normalizes separators and collapses hyphens.
        """
        if not repo_id:
            return ""
        
        # First apply HF-specific normalization
        repo_id = self._normalize_hf_repo_id(repo_id)
        
        # Additional normalization for fuzzy matching
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
    
    def _extract_hf_repo_ids_from_text(self, text: str) -> List[str]:
        """
        Extract HuggingFace repo IDs from text.
        
        Finds patterns like:
        - https://huggingface.co/org/name
        - huggingface.co/org/name
        - org/name (only with HF context nearby)
        
        Returns unique list in stable order.
        """
        if not text or not isinstance(text, str):
            return []
        
        found: List[str] = []
        seen: Set[str] = set()
        
        # Pattern 1: Full HF URLs
        url_pattern = r"(?:https?://)?huggingface\.co/([a-zA-Z0-9_-]+/[a-zA-Z0-9._-]+)"
        for match in re.finditer(url_pattern, text, re.IGNORECASE):
            repo_id = self._normalize_hf_repo_id(match.group(1))
            if repo_id and repo_id not in seen and self._looks_like_hf_repo_id(repo_id):
                found.append(repo_id)
                seen.add(repo_id)
        
        # Pattern 2: org/name near "hugging" or "hf" context
        # Only if we find context words within 100 chars
        context_pattern = r"\b(hugging\s*face|hf\s+model|hf\s+repo)\b"
        if re.search(context_pattern, text, re.IGNORECASE):
            # Look for org/name patterns
            repo_pattern = r"\b([a-zA-Z0-9_-]+/[a-zA-Z0-9._-]+)\b"
            for match in re.finditer(repo_pattern, text):
                candidate = match.group(1)
                # Skip obvious non-HF patterns
                if any(x in candidate.lower() for x in ["http", ".com", ".org", "github"]):
                    continue
                repo_id = self._normalize_hf_repo_id(candidate)
                if repo_id and repo_id not in seen and self._looks_like_hf_repo_id(repo_id):
                    found.append(repo_id)
                    seen.add(repo_id)
        
        return found
    
    def _derive_base_model_candidates(self, repo_id: str) -> List[str]:
        """
        Derive base model candidates by stripping quantization/wrapper suffixes.
        
        E.g., "TheBloke/llama-2-7b-chat-GGUF" -> ["thebloke/llama-2-7b-chat"]
        
        Returns additional candidates (does NOT replace original).
        """
        if not repo_id:
            return []
        
        candidates: List[str] = []
        seen: Set[str] = set()
        
        repo_lower = repo_id.lower()
        
        for suffix in DEQUANT_SUFFIXES:
            if repo_lower.endswith(suffix):
                base = repo_lower[:-len(suffix)]
                if base and base not in seen and self._looks_like_hf_repo_id(base):
                    candidates.append(base)
                    seen.add(base)
        
        # Also try removing trailing version/quantization patterns
        # e.g., "-q4_k_m", "-q5_0"
        quant_pattern = r"-q\d+[a-z_]*$"
        stripped = re.sub(quant_pattern, "", repo_lower)
        if stripped != repo_lower and stripped not in seen and self._looks_like_hf_repo_id(stripped):
            candidates.append(stripped)
            seen.add(stripped)
        
        return candidates
    
    def _get_hf_hub_base_model(self, repo_id: str) -> Optional[str]:
        """
        Fetch base_model from HF Hub model info (cached).
        
        Only called if HF_OLLB_RESOLVE_BASE_MODEL=true.
        Returns normalized base model repo ID or None.
        """
        if not HF_OLLB_RESOLVE_BASE_MODEL:
            return None
        
        if not repo_id:
            return None
        
        # Check cache first
        cache_key = repo_id.replace("/", "__")
        cache_path = HF_MODEL_INFO_CACHE_DIR / f"{cache_key}.json"
        
        if cache_path.exists():
            try:
                with open(cache_path, "r", encoding="utf-8") as f:
                    cached = json.load(f)
                if "base_model" in cached:
                    return cached.get("base_model")
                return None
            except Exception:
                pass
        
        # Fetch from HF Hub
        try:
            from huggingface_hub import model_info
            
            info = model_info(repo_id)
            base_model = None
            
            # Check cardData for base_model
            if hasattr(info, "cardData") and info.cardData:
                card = info.cardData
                base = card.get("base_model") or card.get("base_models")
                if base:
                    if isinstance(base, list):
                        base = base[0] if base else None
                    if base:
                        base_model = self._normalize_hf_repo_id(str(base))
            
            # Cache the result
            HF_MODEL_INFO_CACHE_DIR.mkdir(parents=True, exist_ok=True)
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump({"base_model": base_model, "fetched_at": datetime.now(timezone.utc).isoformat()}, f)
            
            return base_model
            
        except Exception as e:
            self.logger.debug("HF Hub lookup failed for %s: %s", repo_id, e)
            # Cache the failure to avoid repeated attempts
            try:
                HF_MODEL_INFO_CACHE_DIR.mkdir(parents=True, exist_ok=True)
                with open(cache_path, "w", encoding="utf-8") as f:
                    json.dump({"base_model": None, "error": str(e), "fetched_at": datetime.now(timezone.utc).isoformat()}, f)
            except Exception:
                pass
            return None
    
    def _infer_hf_id_from_row(self, row: pd.Series) -> Tuple[Optional[str], Optional[str]]:
        """
        Infer HF repo ID from metadata columns for rows missing hugging_face_id.
        
        Returns: (inferred_hf_id, source_column)
        """
        # Columns to scan for HF repo IDs (in priority order)
        candidate_columns = [
            "provider_docs_source_url",
            "model_source_url",
            "benchmark_source_url",
            "description",
            "training_notes",
            "notes",
        ]
        
        for col in candidate_columns:
            if col not in row.index:
                continue
            val = row.get(col)
            if pd.isna(val) or not val:
                continue
            
            repo_ids = self._extract_hf_repo_ids_from_text(str(val))
            if repo_ids:
                return repo_ids[0], col
        
        return None, None
    
    def _generate_hf_candidates(
        self, 
        row: pd.Series,
        inferred_hf_id: Optional[str] = None,
    ) -> Tuple[List[str], Optional[str]]:
        """
        Generate all HF repo ID candidates for a row, in priority order.
        
        Returns: (candidates_list, base_model_hf_id if derived)
        
        Candidates include:
        1. hugging_face_id (if present)
        2. inferred_hf_id (if provided)
        3. openrouter_slug (if looks like org/name)
        4. De-quantization variants of above
        5. HF Hub base_model (if enabled and available)
        """
        candidates: List[str] = []
        seen: Set[str] = set()
        base_model_hf_id: Optional[str] = None
        
        def add_candidate(c: str) -> None:
            if c and c not in seen:
                candidates.append(c)
                seen.add(c)
        
        # Priority 1: Explicit hugging_face_id
        hf_id = row.get("hugging_face_id")
        if pd.notna(hf_id) and hf_id:
            norm = self._normalize_hf_repo_id(str(hf_id))
            if norm and self._looks_like_hf_repo_id(norm):
                add_candidate(norm)
        
        # Priority 2: Inferred HF ID
        if inferred_hf_id:
            add_candidate(inferred_hf_id)
        
        # Priority 3: OpenRouter slug (if looks like org/name)
        slug = row.get("openrouter_slug")
        if pd.notna(slug) and slug:
            norm = self._normalize_hf_repo_id(str(slug))
            if norm and self._looks_like_hf_repo_id(norm):
                add_candidate(norm)
        
        # Now add de-quantization variants for each candidate so far
        current_candidates = list(candidates)  # Copy to avoid mutation during iteration
        for cand in current_candidates:
            for derived in self._derive_base_model_candidates(cand):
                if derived not in seen:
                    add_candidate(derived)
                    if not base_model_hf_id:
                        base_model_hf_id = derived
        
        # Priority 4: HF Hub base_model lookup (if enabled)
        # Only for the primary candidate
        if HF_OLLB_RESOLVE_BASE_MODEL and candidates:
            hub_base = self._get_hf_hub_base_model(candidates[0])
            if hub_base and hub_base not in seen:
                add_candidate(hub_base)
                base_model_hf_id = hub_base
        
        return candidates, base_model_hf_id
    
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
    
    def _find_prefix_matches(
        self,
        candidate: str,
        hf_index: Dict[str, Dict[str, Any]],
    ) -> List[Tuple[str, Dict[str, Any]]]:
        """
        Find HF repos that start with candidate + separator.
        
        Returns list of (hf_key, hf_info) tuples.
        """
        matches = []
        if not candidate:
            return matches
        
        candidate_lower = candidate.lower()
        
        for hf_key, hf_info in hf_index.items():
            for sep in PREFIX_SEPARATORS:
                if hf_key.startswith(candidate_lower + sep):
                    matches.append((hf_key, hf_info))
                    break  # Don't add same key multiple times
        
        return matches
    
    def _check_candidate_in_index(
        self,
        candidate: str,
        hf_index: Dict[str, Dict[str, Any]],
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Check if a candidate (exact) exists in the index.
        
        Returns: (found, hf_info_if_found)
        """
        if not candidate:
            return False, None
        
        if candidate in hf_index:
            return True, hf_index[candidate]
        
        return False, None
    
    def _match_model_with_candidates(
        self,
        candidates: List[str],
        hf_index: Dict[str, Dict[str, Any]],
        model_name: Optional[str] = None,
    ) -> Tuple[str, Optional[str], float, Optional[Dict[str, Any]], str, Optional[str], Optional[str], Optional[str], bool, bool]:
        """
        Match a model to HF leaderboard using provided candidates.
        
        Returns: (match_status, match_method, match_score, hf_info, 
                  attempted_methods, match_outcome, conflict_candidates,
                  matched_candidate, all_candidates_absent, listed_in_dataset)
        
        all_candidates_absent: True if NONE of the candidates exist in the dataset (exact match check)
        listed_in_dataset: True if at least one candidate has an exact match in dataset
        
        Match tiers (priority order) applied to each candidate:
        1. exact: Exact match
        2. prefix_unique: Unique prefix match
        After all candidates, try fuzzy.
        """
        attempted_methods: List[str] = []
        match_outcome: Optional[str] = None
        conflict_candidates: Optional[str] = None
        listed_in_dataset = False  # True ONLY if exact match found for a candidate
        found_hf_info: Optional[Dict[str, Any]] = None  # HF info if listed but not matched (missing metrics)
        found_candidate: Optional[str] = None
        
        if not candidates:
            return (
                "unmatched", None, 0.0, None,
                "no_candidates", OUTCOME_NO_CANDIDATES, None, None, True, False
            )
        
        # ============================================
        # TIER 1-4: Try each candidate with exact + prefix_unique
        # ============================================
        for cand in candidates:
            if not cand:
                continue
            
            # Exact match - this confirms candidate is IN the dataset
            attempted_methods.append("exact")
            if cand in hf_index:
                listed_in_dataset = True
                found_hf_info = hf_index[cand]
                found_candidate = cand
                return (
                    "matched", "candidate_exact", 1.0, hf_index[cand],
                    ">".join(attempted_methods), None, None, cand, False, True
                )
            
            # Prefix unique match - candidate is a prefix of something in dataset
            # This does NOT mean the exact candidate is listed
            attempted_methods.append("prefix_unique")
            prefix_matches = self._find_prefix_matches(cand, hf_index)
            
            if len(prefix_matches) == 1:
                # Single prefix match - use it as a match
                # But note: the candidate itself is NOT in the dataset
                hf_key, hf_info = prefix_matches[0]
                return (
                    "matched", "candidate_prefix_unique", 1.0, hf_info,
                    ">".join(attempted_methods), None, None, cand, False, False
                )
            elif len(prefix_matches) > 1:
                # Multiple prefix matches - conflict
                if not conflict_candidates:
                    conflict_candidates = "; ".join([f"{k} (1.0)" for k, _ in prefix_matches[:2]])
        
        # ============================================
        # TIER 5: Fuzzy matching across all candidates
        # ============================================
        attempted_methods.append("fuzzy")
        
        fuzzy_candidates = [self._normalize_for_fuzzy(c) for c in candidates if c]
        if model_name:
            fuzzy_candidates.append(self._normalize_for_fuzzy(str(model_name)))
        
        if not fuzzy_candidates:
            return (
                "unmatched", None, 0.0, None,
                ">".join(attempted_methods), OUTCOME_HF_ID_NOT_FOUND, None, None, True, listed_in_dataset
            )
        
        best_matches: List[Tuple[float, str, Dict[str, Any]]] = []
        
        for hf_key, hf_info in hf_index.items():
            hf_fuzzy = self._normalize_for_fuzzy(hf_key)
            
            for candidate in fuzzy_candidates:
                # Check for size conflicts
                if self._has_size_conflict(candidate, hf_key):
                    continue
                
                score = self._fuzzy_score(candidate, hf_fuzzy)
                
                if score >= MATCH_THRESHOLD_FUZZY:
                    best_matches.append((score, hf_key, hf_info))
        
        if not best_matches:
            # No fuzzy matches above threshold
            # all_candidates_absent is True if we never found an exact match
            all_candidates_absent = not listed_in_dataset
            outcome = OUTCOME_NOT_LISTED if all_candidates_absent else OUTCOME_FUZZY_BELOW_THRESHOLD
            return (
                "unmatched", None, 0.0, None,
                ">".join(attempted_methods), outcome, conflict_candidates, None, all_candidates_absent, listed_in_dataset
            )
        
        # Sort by score descending
        best_matches.sort(key=lambda x: x[0], reverse=True)
        
        # Check for conflict (top-2 too close)
        if len(best_matches) >= 2:
            if best_matches[0][0] - best_matches[1][0] < MATCH_THRESHOLD_CONFLICT:
                conflict_candidates = f"{best_matches[0][1]} ({best_matches[0][0]:.3f}); {best_matches[1][1]} ({best_matches[1][0]:.3f})"
                return (
                    "conflict", None, best_matches[0][0], None,
                    ">".join(attempted_methods), OUTCOME_CONFLICT, conflict_candidates, None, False, listed_in_dataset
                )
        
        top_match = best_matches[0]
        return (
            "matched", "fuzzy", round(top_match[0], 3), top_match[2],
            ">".join(attempted_methods), None, None, candidates[0] if candidates else None, False, listed_in_dataset
        )
    
    def _match_model(
        self,
        row: pd.Series,
        hf_index: Dict[str, Dict[str, Any]],
        candidates: Optional[List[str]] = None,
    ) -> Tuple[str, Optional[str], float, Optional[Dict[str, Any]], str, Optional[str], Optional[str]]:
        """
        Match a model to HF leaderboard using multi-tier matching.
        
        Legacy wrapper that generates candidates if not provided.
        
        Returns: (match_status, match_method, match_score, hf_info, 
                  attempted_methods, match_outcome, conflict_candidates)
        """
        # Generate candidates if not provided
        if candidates is None:
            candidates, _ = self._generate_hf_candidates(row)
        
        model_name = row.get("model_name") if pd.notna(row.get("model_name")) else None
        
        result = self._match_model_with_candidates(candidates, hf_index, model_name)
        # Return without the extra fields (matched_candidate, all_candidates_absent)
        return result[:7]
    
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
            "hf_ollb_not_listed_on_leaderboard",
            "hf_ollb_listed_in_dataset",
            "hf_ollb_listed_but_missing_metrics",
        ]
        
        # String columns (metadata, provenance, eligibility, debug)
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
            # Eligibility columns
            "hf_ollb_ineligible_reason",
            "hf_ollb_candidate_hf_id",
            # HF ID inference columns (new)
            "hf_ollb_inferred_hf_id",
            "hf_ollb_inferred_hf_id_source",
            "hf_ollb_base_model_hf_id",
            "hf_ollb_candidate_set",
            # Not-listed columns (new)
            "hf_ollb_not_listed_reason",
            # Debug/audit columns
            "hf_ollb_attempted_methods",
            "hf_ollb_match_outcome",
            "hf_ollb_conflict_candidates",
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
        conflict_count = 0
        not_listed_count = 0
        eligible_count = 0
        eligible_matched_count = 0
        eligible_conflict_count = 0
        eligible_not_listed_count = 0
        ineligible_count = 0
        inferred_hf_id_count = 0
        match_methods: Dict[str, int] = {}
        match_outcomes: Dict[str, int] = {}
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
            
            if eligible:
                eligible_count += 1
            else:
                ineligible_count += 1
                ineligible_reasons[ineligible_reason or "unknown"] = ineligible_reasons.get(ineligible_reason or "unknown", 0) + 1
            
            # Step 2: Infer HF ID if missing
            inferred_hf_id = None
            inferred_source = None
            hf_id = row.get("hugging_face_id")
            
            if eligible and (pd.isna(hf_id) or not hf_id):
                inferred_hf_id, inferred_source = self._infer_hf_id_from_row(row)
                if inferred_hf_id:
                    df.at[idx, "hf_ollb_inferred_hf_id"] = inferred_hf_id
                    df.at[idx, "hf_ollb_inferred_hf_id_source"] = inferred_source
                    inferred_hf_id_count += 1
            
            # Step 3: Generate all candidates
            candidates, base_model_hf_id = self._generate_hf_candidates(row, inferred_hf_id)
            
            # Record candidate set (first 5, truncated)
            if candidates:
                candidate_set_str = "; ".join(candidates[:5])
                if len(candidates) > 5:
                    candidate_set_str += f"; (+{len(candidates) - 5} more)"
                df.at[idx, "hf_ollb_candidate_set"] = candidate_set_str
                df.at[idx, "hf_ollb_candidate_hf_id"] = candidates[0]  # Primary candidate
            else:
                df.at[idx, "hf_ollb_candidate_hf_id"] = candidate_hf_id  # Fallback
            
            if base_model_hf_id:
                df.at[idx, "hf_ollb_base_model_hf_id"] = base_model_hf_id
            
            # Step 4: Perform matching with candidate set
            model_name = row.get("model_name") if pd.notna(row.get("model_name")) else None
            (match_status, match_method, match_score, hf_info,
             attempted_methods, match_outcome, conflict_candidates,
             matched_candidate, all_candidates_absent, listed_in_dataset) = self._match_model_with_candidates(
                candidates, hf_index, model_name
            )
            
            # Record match status
            df.at[idx, "hf_ollb_match_status"] = match_status
            df.at[idx, "hf_ollb_match_score"] = match_score if match_score > 0 else None
            df.at[idx, "hf_ollb_attempted_methods"] = attempted_methods
            df.at[idx, "hf_ollb_listed_in_dataset"] = listed_in_dataset
            
            # match_method ONLY set when matched (semantic clarity)
            if match_status == "matched":
                df.at[idx, "hf_ollb_match_method"] = match_method
                df.at[idx, "hf_ollb_match_outcome"] = None  # No outcome for matched
                df.at[idx, "hf_ollb_listed_but_missing_metrics"] = False
                if matched_candidate:
                    df.at[idx, "hf_ollb_candidate_hf_id"] = matched_candidate
            else:
                df.at[idx, "hf_ollb_match_method"] = None  # Clear method for non-matched
                df.at[idx, "hf_ollb_match_outcome"] = match_outcome
                df.at[idx, "hf_ollb_listed_but_missing_metrics"] = False
            
            # Conflict candidates for conflict or prefix ambiguity
            df.at[idx, "hf_ollb_conflict_candidates"] = conflict_candidates
            
            # Step 5: Not-listed semantics
            # A model is "not listed" if NONE of its candidates exist in the dataset index (exact match)
            # all_candidates_absent is True when no exact matches were found
            if eligible and match_status != "matched" and match_status != "conflict":
                if all_candidates_absent and candidates:
                    # No candidates found in dataset - model is NOT on the leaderboard
                    df.at[idx, "hf_ollb_not_listed_on_leaderboard"] = True
                    df.at[idx, "hf_ollb_not_listed_reason"] = "candidate_repo_absent"
                    df.at[idx, "hf_ollb_match_outcome"] = OUTCOME_NOT_LISTED
                    not_listed_count += 1
                    eligible_not_listed_count += 1
                elif not candidates:
                    df.at[idx, "hf_ollb_not_listed_on_leaderboard"] = True
                    df.at[idx, "hf_ollb_not_listed_reason"] = "no_candidates"
                    df.at[idx, "hf_ollb_match_outcome"] = OUTCOME_NO_CANDIDATES
                    not_listed_count += 1
                    eligible_not_listed_count += 1
                else:
                    # Candidates exist but didn't match - this should NOT happen after our fix
                    # All remaining unmatched should be conflict or not-listed
                    df.at[idx, "hf_ollb_not_listed_on_leaderboard"] = True
                    df.at[idx, "hf_ollb_not_listed_reason"] = "candidate_repo_absent"
                    df.at[idx, "hf_ollb_match_outcome"] = OUTCOME_NOT_LISTED
                    not_listed_count += 1
                    eligible_not_listed_count += 1
            else:
                df.at[idx, "hf_ollb_not_listed_on_leaderboard"] = False
            
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
            elif match_status == "conflict":
                conflict_count += 1
                if match_outcome:
                    match_outcomes[match_outcome] = match_outcomes.get(match_outcome, 0) + 1
                if eligible:
                    eligible_conflict_count += 1
                    unmatched_eligible_details.append({
                        "slug": str(slug),
                        "hf_id": str(row.get("hugging_face_id", "")),
                        "candidate_hf_id": candidate_hf_id or "",
                        "status": match_status,
                        "score": match_score,
                        "outcome": match_outcome,
                        "conflict_candidates": conflict_candidates,
                    })
            else:
                unmatched_count += 1
                if match_outcome:
                    match_outcomes[match_outcome] = match_outcomes.get(match_outcome, 0) + 1
                
                # Only track unmatched ELIGIBLE models for debugging
                if eligible:
                    unmatched_eligible_details.append({
                        "slug": str(slug),
                        "hf_id": str(row.get("hugging_face_id", "")),
                        "candidate_hf_id": candidate_hf_id or "",
                        "status": match_status,
                        "score": match_score,
                        "outcome": match_outcome,
                        "conflict_candidates": conflict_candidates,
                    })
                    result.data_gaps.append({
                        "slug": str(slug),
                        "source": "hf_open_llm_leaderboard",
                        "field": "hf_ollb_avg",
                        "reason": match_outcome or match_status,
                        "hf_id": str(row.get("hugging_face_id", "")),
                        "candidate_hf_id": candidate_hf_id or "",
                        "best_score": match_score,
                        "eligible": True,
                        "retrieved_at": now_iso,
                    })
        
        result.rows_enriched = matched_count
        result.rows_with_gaps = unmatched_count + conflict_count
        
        # Compute true gaps (eligible - matched - conflict - not_listed)
        true_gaps = eligible_count - eligible_matched_count - eligible_conflict_count - eligible_not_listed_count
        
        # Log comprehensive summary
        total_attempted = eligible_count + ineligible_count
        eligible_metric_pct = 100.0 * eligible_matched_count / eligible_count if eligible_count > 0 else 0
        
        self.logger.info("=" * 60)
        self.logger.info("HF Leaderboard Enrichment Summary:")
        self.logger.info("=" * 60)
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
        self.logger.info("  Matched (eligible only): %d / %d (%.1f%%) <- Metric(Eligible)", 
                        eligible_matched_count, eligible_count, eligible_metric_pct)
        self.logger.info("  Conflicts (eligible): %d", eligible_conflict_count)
        self.logger.info("  Not-listed (eligible): %d", eligible_not_listed_count)
        self.logger.info("  True gaps (eligible): %d", true_gaps)
        self.logger.info("")
        self.logger.info("  Inferred HF IDs: %d", inferred_hf_id_count)
        self.logger.info("  HF Hub base_model resolution: %s", "enabled" if HF_OLLB_RESOLVE_BASE_MODEL else "disabled")
        self.logger.info("")
        self.logger.info("  Match methods (matched rows only): %s", match_methods)
        self.logger.info("  Match outcomes (non-matched): %s", match_outcomes)
        self.logger.info("=" * 60)
        
        # Print summary to stdout for visibility
        print("")
        print("=" * 60)
        print("HF LEADERBOARD ENRICHMENT SUMMARY")
        print("=" * 60)
        print(f"  Eligible count:        {eligible_count}")
        print(f"  Matched count:         {matched_count}")
        print(f"  Metric(Eligible):      {eligible_matched_count}/{eligible_count} ({eligible_metric_pct:.1f}%)")
        print(f"  Conflicts (eligible):  {eligible_conflict_count}")
        print(f"  Not-listed (eligible): {eligible_not_listed_count}")
        print(f"  True gaps:             {true_gaps}")
        print(f"  Inferred HF IDs:       {inferred_hf_id_count}")
        print(f"  Match methods:         {match_methods}")
        print("=" * 60)
        print("")
        
        # Log top unmatched ELIGIBLE models (these are the ones that matter)
        if unmatched_eligible_details:
            self.logger.info("Top unmatched ELIGIBLE models (should investigate):")
            for item in unmatched_eligible_details[:15]:
                outcome_str = item.get("outcome") or item["status"]
                conflict_str = f" | conflicts={item.get('conflict_candidates', '')}" if item.get("conflict_candidates") else ""
                self.logger.info("  %s | candidate=%s | outcome=%s | score=%.2f%s", 
                               item["slug"], item["candidate_hf_id"], 
                               outcome_str, item["score"] or 0, conflict_str)
        
        return df
