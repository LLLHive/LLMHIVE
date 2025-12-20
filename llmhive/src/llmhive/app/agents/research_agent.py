"""Research & Development Agent for LLMHive.

This persistent agent continuously monitors AI research, model releases,
and industry developments to propose system improvements.

Responsibilities:
- Monitor AI research publications
- Track model leaderboard changes
- Identify promising techniques
- Draft upgrade proposals
- Maintain state-of-the-art knowledge base
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
import json

from .base import (
    BaseAgent,
    AgentConfig,
    AgentResult,
    AgentTask,
    AgentType,
    AgentPriority,
)

logger = logging.getLogger(__name__)


@dataclass
class ResearchFinding:
    """A research finding from the R&D agent."""
    title: str
    source: str
    summary: str
    relevance_score: float  # 0-1, how relevant to LLMHive
    category: str  # model, technique, paper, tool
    potential_impact: str  # high, medium, low
    integration_proposal: Optional[str] = None
    discovered_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "source": self.source,
            "summary": self.summary,
            "relevance_score": self.relevance_score,
            "category": self.category,
            "potential_impact": self.potential_impact,
            "integration_proposal": self.integration_proposal,
            "discovered_at": self.discovered_at.isoformat(),
        }


class ResearchAgent(BaseAgent):
    """Agent that monitors AI research and proposes improvements.
    
    This agent runs continuously in the background:
    1. Scans research sources for new developments
    2. Evaluates relevance to LLMHive
    3. Generates integration proposals
    4. Posts findings to blackboard for Planning Agent
    """
    
    # Sources to monitor
    RESEARCH_SOURCES = [
        "arxiv.org/list/cs.CL",  # Computation and Language
        "arxiv.org/list/cs.AI",  # Artificial Intelligence
        "arxiv.org/list/cs.LG",  # Machine Learning
        "huggingface.co/models",  # Model releases
        "openai.com/blog",       # OpenAI updates
        "anthropic.com/research", # Anthropic updates
    ]
    
    # Topics of interest
    RELEVANT_TOPICS = [
        "language models",
        "reasoning",
        "chain of thought",
        "multi-agent",
        "orchestration",
        "retrieval augmented",
        "RAG",
        "prompt engineering",
        "fine-tuning",
        "model evaluation",
        "benchmark",
    ]
    
    def __init__(self, config: Optional[AgentConfig] = None):
        """Initialize the Research Agent.
        
        Args:
            config: Optional configuration override
        """
        if config is None:
            config = AgentConfig(
                name="research_agent",
                agent_type=AgentType.PERSISTENT,
                priority=AgentPriority.MEDIUM,
                max_tokens_per_run=5000,
                max_runtime_seconds=600,  # 10 minutes
                schedule_interval_seconds=86400,  # Daily
                allowed_tools=["web_search", "read_url"],
                can_modify_prompts=False,
                can_modify_routing=False,
                memory_namespace="research",
            )
        
        super().__init__(config)
        
        self._findings: List[ResearchFinding] = []
        self._last_scan: Optional[datetime] = None
        self._known_papers: set = set()  # Avoid duplicates
    
    async def execute(self, task: Optional[AgentTask] = None) -> AgentResult:
        """Execute research scanning and analysis.
        
        Args:
            task: Optional specific task
            
        Returns:
            AgentResult with findings
        """
        start_time = datetime.now()
        findings = []
        tokens_used = 0
        
        try:
            # Check if we should run (rate limiting)
            if self._last_scan:
                time_since_scan = datetime.now() - self._last_scan
                if time_since_scan < timedelta(hours=1):
                    logger.debug("Research scan too recent, skipping")
                    return AgentResult(
                        success=True,
                        output="Scan skipped (too recent)",
                        tokens_used=0,
                    )
            
            # Phase 1: Scan for new research
            logger.info("Research Agent: Starting scan for new developments")
            
            # In production, this would use web_search tool
            # For now, we simulate with mock data
            raw_findings = await self._scan_sources()
            
            # Phase 2: Evaluate relevance
            for raw in raw_findings:
                relevance = await self._evaluate_relevance(raw)
                if relevance > 0.3:  # Minimum relevance threshold
                    finding = await self._create_finding(raw, relevance)
                    findings.append(finding)
                    self._findings.append(finding)
            
            # Phase 3: Generate integration proposals for high-impact findings
            for finding in findings:
                if finding.potential_impact == "high":
                    finding.integration_proposal = await self._generate_proposal(finding)
            
            # Phase 4: Post to blackboard
            for finding in findings:
                await self.write_to_blackboard(
                    key=f"finding:{finding.discovered_at.timestamp()}",
                    value=finding.to_dict(),
                    ttl_seconds=604800,  # 1 week
                )
            
            # Phase 5: Persist to Model Knowledge Store (Pinecone)
            # This enables long-term learning and cross-session intelligence
            await self._persist_findings_to_knowledge_store(findings)
            
            # Update scan time
            self._last_scan = datetime.now()
            
            # Prepare summary
            high_impact = [f for f in findings if f.potential_impact == "high"]
            summary = {
                "total_findings": len(findings),
                "high_impact": len(high_impact),
                "categories": self._count_categories(findings),
                "scan_time": start_time.isoformat(),
            }
            
            logger.info(
                f"Research Agent: Found {len(findings)} relevant items "
                f"({len(high_impact)} high-impact)"
            )
            
            return AgentResult(
                success=True,
                output=summary,
                tokens_used=tokens_used,
                findings=[f.to_dict() for f in findings],
                recommendations=[
                    f"Consider: {f.integration_proposal}"
                    for f in high_impact
                    if f.integration_proposal
                ],
            )
            
        except Exception as e:
            logger.error(f"Research Agent execution failed: {e}")
            return AgentResult(
                success=False,
                error=str(e),
                tokens_used=tokens_used,
            )
    
    def get_capabilities(self) -> Dict[str, Any]:
        """Return agent capabilities."""
        return {
            "name": "Research & Development Agent",
            "type": "persistent",
            "purpose": "Monitor AI research and propose system improvements",
            "sources": self.RESEARCH_SOURCES,
            "topics": self.RELEVANT_TOPICS,
            "outputs": [
                "Research findings",
                "Integration proposals",
                "Weekly research summaries",
            ],
            "tools_used": ["web_search", "read_url"],
        }
    
    async def _scan_sources(self) -> List[Dict[str, Any]]:
        """Scan research sources for new developments.
        
        In production, this would use the web_search tool.
        For now, returns simulated data.
        """
        # Simulated research findings
        # In production: use MCP tools to search arXiv, HuggingFace, etc.
        return [
            {
                "title": "Adaptive Mixture-of-Experts for Multi-Task Learning",
                "source": "arxiv.org",
                "abstract": "We propose a novel approach to dynamically routing tokens to specialized expert models based on task requirements...",
                "date": datetime.now().isoformat(),
                "url": "https://arxiv.org/abs/2501.00001",
            },
            {
                "title": "Self-Consistency Improves Chain of Thought Reasoning in Language Models",
                "source": "arxiv.org",
                "abstract": "We show that sampling multiple reasoning paths and aggregating answers significantly improves accuracy on complex reasoning tasks...",
                "date": datetime.now().isoformat(),
                "url": "https://arxiv.org/abs/2501.00002",
            },
            {
                "title": "GPT-5.2 Release Notes",
                "source": "openai.com",
                "abstract": "Introducing GPT-5.2 with improved reasoning, reduced hallucinations, and 2x faster inference...",
                "date": datetime.now().isoformat(),
                "url": "https://openai.com/gpt-5-2",
            },
        ]
    
    async def _evaluate_relevance(self, raw_finding: Dict[str, Any]) -> float:
        """Evaluate how relevant a finding is to LLMHive.
        
        Args:
            raw_finding: Raw finding data
            
        Returns:
            Relevance score 0-1
        """
        text = f"{raw_finding.get('title', '')} {raw_finding.get('abstract', '')}"
        text_lower = text.lower()
        
        # Count topic matches
        matches = sum(1 for topic in self.RELEVANT_TOPICS if topic in text_lower)
        
        # Base relevance on topic coverage
        relevance = min(1.0, matches / 3)  # 3+ topics = max relevance
        
        # Boost for certain keywords
        if "orchestr" in text_lower or "multi-agent" in text_lower:
            relevance = min(1.0, relevance + 0.3)
        
        if "llm" in text_lower or "language model" in text_lower:
            relevance = min(1.0, relevance + 0.2)
        
        return relevance
    
    async def _create_finding(
        self,
        raw: Dict[str, Any],
        relevance: float
    ) -> ResearchFinding:
        """Create a structured finding from raw data.
        
        Args:
            raw: Raw finding data
            relevance: Relevance score
            
        Returns:
            ResearchFinding object
        """
        # Determine category
        source = raw.get("source", "").lower()
        title = raw.get("title", "").lower()
        
        if "release" in title or "gpt-" in title or "claude" in title:
            category = "model"
        elif "arxiv" in source:
            category = "paper"
        elif "technique" in title or "method" in title:
            category = "technique"
        else:
            category = "other"
        
        # Determine impact
        if relevance > 0.7:
            impact = "high"
        elif relevance > 0.4:
            impact = "medium"
        else:
            impact = "low"
        
        return ResearchFinding(
            title=raw.get("title", "Unknown"),
            source=raw.get("source", "Unknown"),
            summary=raw.get("abstract", "")[:500],
            relevance_score=relevance,
            category=category,
            potential_impact=impact,
        )
    
    async def _generate_proposal(self, finding: ResearchFinding) -> str:
        """Generate an integration proposal for a high-impact finding.
        
        Args:
            finding: The finding to propose integration for
            
        Returns:
            Integration proposal text
        """
        # In production, this would use an LLM to generate a detailed proposal
        proposals = {
            "model": f"Integrate {finding.title} into model routing. Test against current models on standard benchmarks.",
            "technique": f"Implement {finding.title} in quality_booster.py. A/B test against current methods.",
            "paper": f"Review findings from '{finding.title}' for applicable improvements to orchestration pipeline.",
        }
        
        return proposals.get(
            finding.category,
            f"Evaluate {finding.title} for potential integration into LLMHive."
        )
    
    def _count_categories(self, findings: List[ResearchFinding]) -> Dict[str, int]:
        """Count findings by category."""
        counts: Dict[str, int] = {}
        for f in findings:
            counts[f.category] = counts.get(f.category, 0) + 1
        return counts
    
    async def get_weekly_summary(self) -> Dict[str, Any]:
        """Generate a weekly research summary.
        
        Returns:
            Summary of findings from the past week
        """
        week_ago = datetime.now() - timedelta(days=7)
        recent = [f for f in self._findings if f.discovered_at > week_ago]
        
        return {
            "period": f"{week_ago.date()} to {datetime.now().date()}",
            "total_findings": len(recent),
            "high_impact": len([f for f in recent if f.potential_impact == "high"]),
            "by_category": self._count_categories(recent),
            "top_findings": [
                f.to_dict() for f in sorted(
                    recent,
                    key=lambda x: x.relevance_score,
                    reverse=True
                )[:5]
            ],
        }
    
    async def _persist_findings_to_knowledge_store(
        self,
        findings: List[ResearchFinding],
    ) -> int:
        """
        Persist research findings to the Model Knowledge Store (Pinecone).
        
        This enables long-term learning about AI developments across sessions.
        The Planning Agent can later query these findings to make decisions.
        
        Args:
            findings: List of research findings to store
            
        Returns:
            Number of findings stored successfully
        """
        try:
            from ..knowledge import MODEL_KNOWLEDGE_AVAILABLE, get_model_knowledge_store
            
            if not MODEL_KNOWLEDGE_AVAILABLE:
                logger.debug("Model Knowledge Store not available for research findings")
                return 0
            
            store = get_model_knowledge_store()
            stored_count = 0
            
            for finding in findings:
                try:
                    # Map finding category to relevance description
                    relevance = f"Relevant to LLMHive {finding.category}: {finding.summary[:200]}"
                    
                    record_id = await store.store_ai_development(
                        title=finding.title,
                        summary=finding.summary,
                        source=finding.source,
                        impact=finding.potential_impact,
                        relevance_to_orchestration=relevance,
                        integration_proposal=finding.integration_proposal,
                    )
                    
                    if record_id:
                        stored_count += 1
                        
                except Exception as e:
                    logger.warning("Failed to store finding '%s': %s", finding.title[:50], e)
            
            if stored_count > 0:
                logger.info(
                    "Persisted %d/%d research findings to Model Knowledge Store",
                    stored_count, len(findings)
                )
            
            return stored_count
            
        except Exception as e:
            logger.warning("Failed to persist findings to knowledge store: %s", e)
            return 0

