"""
LLMHive Techniques Knowledge Base Access Layer

Provides runtime access to the KB for:
- Technique lookup by ID, name, category
- Ranking retrieval by category and reasoning type
- Technique recommendation based on context

Usage:
    from llmhive.kb import get_technique_kb
    
    kb = get_technique_kb()
    tech = kb.get_technique_by_id("TECH_0001")
    recommendations = kb.recommend_techniques({
        "reasoning_type": "mathematical_reasoning",
        "risk_level": "low",
        "latency_budget": 5000,
    })
"""
from __future__ import annotations

import json
import logging
import os
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)

# KB file path - navigate from llmhive/src/llmhive/kb/ to repo root
# Path: kb/technique_kb.py -> kb/ -> llmhive/ -> src/ -> llmhive/ -> (repo root) -> kb/
_THIS_FILE = Path(__file__).resolve()
_REPO_ROOT = _THIS_FILE.parent.parent.parent.parent.parent  # llmhive/src/llmhive/kb -> llmhive/src/llmhive -> llmhive/src -> llmhive -> repo_root
KB_DIR = _REPO_ROOT / "kb" / "llmhive_techniques_kb"
KB_JSON = KB_DIR / "LLMHive_Techniques_KB_v1.json"

# Singleton instance
_kb_instance: Optional["TechniqueKB"] = None
_kb_lock = threading.Lock()


@dataclass
class Technique:
    """A reasoning/agentic technique from the KB."""
    technique_id: str
    name: str
    category: str
    subcategory: str = ""
    summary_short: str = ""
    summary_long: str = ""
    canonical_sources: str = ""
    architecture_pattern: str = ""
    cost_estimate: str = "medium"
    complexity: str = "medium"
    risk_level: str = "low"
    ideal_for: List[str] = field(default_factory=list)
    raw_data: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Technique":
        """Create Technique from dictionary."""
        ideal_for = data.get("ideal_for", "")
        if isinstance(ideal_for, str):
            ideal_for = [x.strip() for x in ideal_for.split(",") if x.strip()]
        
        return cls(
            technique_id=data.get("technique_id", ""),
            name=data.get("name", ""),
            category=data.get("category", ""),
            subcategory=data.get("subcategory", ""),
            summary_short=data.get("summary_short", ""),
            summary_long=data.get("summary_long", ""),
            canonical_sources=data.get("canonical_sources", ""),
            architecture_pattern=data.get("architecture_pattern", ""),
            cost_estimate=data.get("cost_estimate", "medium"),
            complexity=data.get("complexity", "medium"),
            risk_level=data.get("risk_level", "low"),
            ideal_for=ideal_for,
            raw_data=data,
        )


@dataclass
class Ranking:
    """A technique ranking entry from the KB."""
    ranking_id: str
    category: str
    reasoning_type: str
    technique_id: str
    rank: int
    score: float = 0.0
    notes: str = ""
    raw_data: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Ranking":
        """Create Ranking from dictionary."""
        rank = data.get("rank", 0)
        if isinstance(rank, str):
            try:
                rank = int(rank)
            except ValueError:
                rank = 0
        
        score = data.get("score", 0.0)
        if isinstance(score, str):
            try:
                score = float(score)
            except ValueError:
                score = 0.0
        
        return cls(
            ranking_id=data.get("ranking_id", ""),
            category=data.get("category", ""),
            reasoning_type=data.get("reasoning_type", ""),
            technique_id=data.get("technique_id", ""),
            rank=rank,
            score=score,
            notes=data.get("notes", ""),
            raw_data=data,
        )


class TechniqueKB:
    """
    Knowledge Base access layer for LLMHive techniques.
    
    Loads from JSON file and provides query methods.
    Thread-safe and supports hot-reload in dev mode.
    """
    
    def __init__(self, kb_path: Optional[Path] = None, hot_reload: bool = False):
        """
        Initialize the KB.
        
        Args:
            kb_path: Path to KB JSON file (default: standard location)
            hot_reload: If True, check for file changes on each access
        """
        self.kb_path = kb_path or KB_JSON
        self.hot_reload = hot_reload
        self._last_mtime: float = 0
        self._data: Dict[str, Any] = {}
        self._techniques: Dict[str, Technique] = {}
        self._rankings: List[Ranking] = []
        self._lock = threading.RLock()
        
        # Load on init
        self._load()
    
    def _load(self) -> None:
        """Load KB data from JSON file."""
        with self._lock:
            if not self.kb_path.exists():
                logger.warning(f"KB file not found: {self.kb_path}")
                self._data = {"status": "not_found"}
                return
            
            try:
                mtime = self.kb_path.stat().st_mtime
                if mtime == self._last_mtime and self._data:
                    return  # No change
                
                with open(self.kb_path, "r", encoding="utf-8") as f:
                    self._data = json.load(f)
                
                self._last_mtime = mtime
                
                # Parse techniques
                self._techniques = {}
                for tech_data in self._data.get("techniques", []):
                    tech = Technique.from_dict(tech_data)
                    if tech.technique_id:
                        self._techniques[tech.technique_id] = tech
                
                # Parse rankings
                self._rankings = []
                for rank_data in self._data.get("rankings", []):
                    self._rankings.append(Ranking.from_dict(rank_data))
                
                logger.info(f"Loaded KB: {len(self._techniques)} techniques, {len(self._rankings)} rankings")
                
            except Exception as e:
                logger.error(f"Failed to load KB: {e}")
                self._data = {"status": "error", "error": str(e)}
    
    def _maybe_reload(self) -> None:
        """Reload KB if hot_reload is enabled and file changed."""
        if self.hot_reload:
            self._load()
    
    @property
    def is_loaded(self) -> bool:
        """Check if KB is loaded successfully."""
        return bool(self._techniques)
    
    @property
    def metadata(self) -> Dict[str, Any]:
        """Get KB metadata."""
        self._maybe_reload()
        return self._data.get("metadata", {})
    
    def get_technique_by_id(self, technique_id: str) -> Optional[Technique]:
        """Get technique by ID (e.g., TECH_0001)."""
        self._maybe_reload()
        return self._techniques.get(technique_id)
    
    def get_technique_by_name(self, name: str) -> Optional[Technique]:
        """Get technique by name (case-insensitive partial match)."""
        self._maybe_reload()
        name_lower = name.lower()
        for tech in self._techniques.values():
            if name_lower in tech.name.lower():
                return tech
        return None
    
    def search_techniques(
        self,
        query: Optional[str] = None,
        category: Optional[str] = None,
        subcategory: Optional[str] = None,
        architecture_pattern: Optional[str] = None,
    ) -> List[Technique]:
        """
        Search techniques by various criteria.
        
        Args:
            query: Text search in name and summaries
            category: Filter by category
            subcategory: Filter by subcategory
            architecture_pattern: Filter by architecture pattern
        
        Returns:
            List of matching techniques
        """
        self._maybe_reload()
        results = list(self._techniques.values())
        
        if category:
            category_lower = category.lower()
            results = [t for t in results if category_lower in t.category.lower()]
        
        if subcategory:
            subcategory_lower = subcategory.lower()
            results = [t for t in results if subcategory_lower in t.subcategory.lower()]
        
        if architecture_pattern:
            arch_lower = architecture_pattern.lower()
            results = [t for t in results if arch_lower in t.architecture_pattern.lower()]
        
        if query:
            query_lower = query.lower()
            results = [t for t in results if (
                query_lower in t.name.lower() or
                query_lower in t.summary_short.lower() or
                query_lower in t.summary_long.lower()
            )]
        
        return results
    
    def get_rankings(
        self,
        category: Optional[str] = None,
        reasoning_type: Optional[str] = None,
    ) -> List[Ranking]:
        """
        Get technique rankings filtered by category and reasoning type.
        
        Args:
            category: Filter by category (e.g., "agentic_planning")
            reasoning_type: Filter by reasoning type (e.g., "mathematical_reasoning")
        
        Returns:
            List of rankings, sorted by rank (ascending)
        """
        self._maybe_reload()
        results = self._rankings.copy()
        
        if category:
            category_lower = category.lower()
            results = [r for r in results if category_lower in r.category.lower()]
        
        if reasoning_type:
            rt_lower = reasoning_type.lower()
            results = [r for r in results if rt_lower in r.reasoning_type.lower()]
        
        # Sort by rank
        results.sort(key=lambda r: (r.rank, -r.score))
        
        return results
    
    def recommend_techniques(
        self,
        context: Dict[str, Any],
    ) -> List[Technique]:
        """
        Recommend techniques based on context.
        
        Args:
            context: Dict with keys:
                - reasoning_type: Type of reasoning needed
                - risk_level: "low", "medium", "high"
                - tools_available: List of available tools
                - latency_budget: Max latency in ms
                - cost_budget: Cost constraint ("low", "medium", "high")
        
        Returns:
            List of recommended techniques, ordered by suitability
        """
        self._maybe_reload()
        
        reasoning_type = context.get("reasoning_type", "")
        risk_level = context.get("risk_level", "low")
        cost_budget = context.get("cost_budget", "medium")
        
        # Start with rankings for the reasoning type
        rankings = self.get_rankings(reasoning_type=reasoning_type)
        
        if rankings:
            # Use ranked techniques
            technique_ids = [r.technique_id for r in rankings]
            techniques = [self._techniques[tid] for tid in technique_ids if tid in self._techniques]
        else:
            # Fall back to category-based search
            techniques = self.search_techniques(category=reasoning_type)
        
        if not techniques:
            # Fall back to all techniques
            techniques = list(self._techniques.values())
        
        # Filter by risk level if high-risk context
        if risk_level == "high":
            # Prefer techniques with verification/safety features
            high_risk_categories = {"verification", "safety", "critic", "debate"}
            preferred = [t for t in techniques if any(
                cat in t.category.lower() or cat in t.subcategory.lower()
                for cat in high_risk_categories
            )]
            if preferred:
                techniques = preferred + [t for t in techniques if t not in preferred]
        
        # Filter by cost if budget constrained
        if cost_budget == "low":
            low_cost = [t for t in techniques if t.cost_estimate in ("low", "very_low")]
            if low_cost:
                techniques = low_cost
        
        return techniques[:10]  # Return top 10
    
    def get_technique_ids_for_pipeline(self, pipeline_name: str) -> List[str]:
        """
        Get technique IDs associated with a pipeline.
        
        Maps pipeline names to their constituent technique IDs.
        """
        pipeline_techniques = {
            "PIPELINE_RAG_CITATION_COVE": ["TECH_0013", "TECH_0014", "TECH_0010"],
            "PIPELINE_MATH_REASONING": ["TECH_0027", "TECH_0012", "TECH_0028"],
            "PIPELINE_CODING_AGENT": ["TECH_0001", "TECH_0004", "TECH_0011", "TECH_0003", "TECH_0026"],
            "PIPELINE_TOOL_USE_REACT": ["TECH_0002", "TECH_0021", "TECH_0035"],
            "PIPELINE_CRITIC_OR_DEBATE": ["TECH_0007", "TECH_0008"],
            "PIPELINE_COST_OPTIMIZED_ROUTING": ["TECH_0005", "TECH_0006"],
        }
        return pipeline_techniques.get(pipeline_name, [])
    
    def get_all_techniques(self) -> List[Technique]:
        """Get all techniques."""
        self._maybe_reload()
        return list(self._techniques.values())
    
    def get_sources(self) -> List[Dict[str, Any]]:
        """Get all sources."""
        self._maybe_reload()
        return self._data.get("sources", [])
    
    def get_benchmarks(self) -> List[Dict[str, Any]]:
        """Get all benchmarks."""
        self._maybe_reload()
        return self._data.get("benchmarks", [])


def get_technique_kb(
    kb_path: Optional[Path] = None,
    hot_reload: bool = False,
) -> TechniqueKB:
    """
    Get the singleton TechniqueKB instance.
    
    Thread-safe singleton pattern for shared KB access.
    """
    global _kb_instance
    
    with _kb_lock:
        if _kb_instance is None:
            _kb_instance = TechniqueKB(kb_path=kb_path, hot_reload=hot_reload)
        return _kb_instance


def reset_kb_instance() -> None:
    """Reset the singleton KB instance (for testing)."""
    global _kb_instance
    with _kb_lock:
        _kb_instance = None
