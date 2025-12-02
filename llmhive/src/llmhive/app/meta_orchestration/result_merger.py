"""Result Merger - Combines outputs from multiple instances."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum, auto

logger = logging.getLogger(__name__)


class MergeStrategy(Enum):
    """Strategies for merging results."""
    CONCATENATE = auto()      # Simple concatenation
    SYNTHESIZE = auto()       # LLM-based synthesis
    BEST_OF = auto()          # Select best single result
    WEIGHTED_MERGE = auto()   # Weight by confidence
    HIERARCHICAL = auto()     # Structure by task hierarchy


@dataclass
class MergedResult:
    """A merged result from multiple instances."""
    content: str
    sources: List[str] = field(default_factory=list)  # instance_ids
    confidence: float = 1.0
    merge_strategy: str = "unknown"
    metadata: Dict[str, Any] = field(default_factory=dict)


class ResultMerger:
    """Merges results from multiple orchestrator instances.
    
    Handles:
    - Result synthesis from different domains
    - Conflict resolution
    - Confidence-weighted combination
    - Quality assessment
    """
    
    def __init__(self, strategy: MergeStrategy = MergeStrategy.SYNTHESIZE):
        self.strategy = strategy
    
    async def merge(
        self,
        results: List[Dict[str, Any]],
        original_query: str,
        task_structure: Optional[Dict] = None,
    ) -> MergedResult:
        """Merge multiple results into one coherent output.
        
        Args:
            results: List of results from instances
            original_query: The original user query
            task_structure: Optional structure showing task hierarchy
            
        Returns:
            Merged result
        """
        if not results:
            return MergedResult(
                content="No results to merge",
                confidence=0.0,
                merge_strategy=self.strategy.name,
            )
        
        # Filter successful results
        successful = [r for r in results if r.get("success", False)]
        
        if not successful:
            return MergedResult(
                content="All sub-tasks failed",
                sources=[r.get("instance_id", "unknown") for r in results],
                confidence=0.0,
                merge_strategy=self.strategy.name,
            )
        
        # Apply merge strategy
        if self.strategy == MergeStrategy.CONCATENATE:
            merged = await self._concatenate(successful)
        elif self.strategy == MergeStrategy.BEST_OF:
            merged = await self._select_best(successful)
        elif self.strategy == MergeStrategy.WEIGHTED_MERGE:
            merged = await self._weighted_merge(successful)
        elif self.strategy == MergeStrategy.HIERARCHICAL:
            merged = await self._hierarchical_merge(successful, task_structure)
        else:  # SYNTHESIZE
            merged = await self._synthesize(successful, original_query)
        
        return merged
    
    async def _concatenate(self, results: List[Dict]) -> MergedResult:
        """Simple concatenation of results."""
        parts = []
        sources = []
        
        for i, r in enumerate(results):
            output = r.get("output", "")
            parts.append(f"### Part {i + 1}\n{output}")
            sources.append(r.get("instance_id", "unknown"))
        
        return MergedResult(
            content="\n\n".join(parts),
            sources=sources,
            confidence=0.8,  # Lower confidence for simple concat
            merge_strategy="CONCATENATE",
        )
    
    async def _select_best(self, results: List[Dict]) -> MergedResult:
        """Select the best single result."""
        # Score by confidence/quality indicators
        def score_result(r: Dict) -> float:
            return r.get("confidence", 0.5) * (1 if r.get("success") else 0)
        
        best = max(results, key=score_result)
        
        return MergedResult(
            content=best.get("output", ""),
            sources=[best.get("instance_id", "unknown")],
            confidence=score_result(best),
            merge_strategy="BEST_OF",
        )
    
    async def _weighted_merge(self, results: List[Dict]) -> MergedResult:
        """Merge with weighting by confidence."""
        # For text, this is complex - for now, use concatenation with labels
        parts = []
        sources = []
        total_confidence = 0
        
        for r in results:
            confidence = r.get("confidence", 0.5)
            output = r.get("output", "")
            label = f"[Confidence: {confidence:.0%}]"
            parts.append(f"{label}\n{output}")
            sources.append(r.get("instance_id", "unknown"))
            total_confidence += confidence
        
        avg_confidence = total_confidence / len(results) if results else 0
        
        return MergedResult(
            content="\n\n".join(parts),
            sources=sources,
            confidence=avg_confidence,
            merge_strategy="WEIGHTED_MERGE",
        )
    
    async def _hierarchical_merge(
        self,
        results: List[Dict],
        structure: Optional[Dict]
    ) -> MergedResult:
        """Merge respecting task hierarchy."""
        if not structure:
            return await self._concatenate(results)
        
        # Organize results by task hierarchy
        # In production, structure outputs according to task tree
        return await self._concatenate(results)
    
    async def _synthesize(
        self,
        results: List[Dict],
        original_query: str
    ) -> MergedResult:
        """Use LLM to synthesize results into coherent output."""
        # In production, call an LLM with synthesis prompt
        # For now, structured concatenation with context
        
        intro = f"Based on analysis of your request: '{original_query[:100]}...'\n\n"
        
        parts = []
        sources = []
        
        for i, r in enumerate(results):
            domain = r.get("domain", "general")
            output = r.get("output", "")
            parts.append(f"**{domain.capitalize()} Analysis:**\n{output}")
            sources.append(r.get("instance_id", "unknown"))
        
        content = intro + "\n\n".join(parts)
        
        # Add synthesis conclusion
        content += "\n\n**Summary:** Multiple specialized systems analyzed your request, providing complementary perspectives above."
        
        return MergedResult(
            content=content,
            sources=sources,
            confidence=0.85,
            merge_strategy="SYNTHESIZE",
        )

