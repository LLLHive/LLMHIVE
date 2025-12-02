"""Personalization Agent for LLMHive.

This agent manages user profiles and personalizes interactions.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional
from dataclasses import dataclass, field

from .base import BaseAgent, AgentConfig, AgentResult, AgentTask, AgentType, AgentPriority

logger = logging.getLogger(__name__)


@dataclass
class UserProfile:
    """User profile for personalization."""
    user_id: str
    display_name: Optional[str] = None
    
    # Preferences
    preferred_style: str = "balanced"  # formal, casual, technical, balanced
    expertise_level: str = "intermediate"  # novice, intermediate, expert
    verbosity: str = "medium"  # brief, medium, detailed
    
    # Behavior patterns
    common_topics: list = field(default_factory=list)
    preferred_models: list = field(default_factory=list)
    tools_used: list = field(default_factory=list)
    
    # History
    total_conversations: int = 0
    total_queries: int = 0
    feedback_scores: list = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "display_name": self.display_name,
            "preferred_style": self.preferred_style,
            "expertise_level": self.expertise_level,
            "verbosity": self.verbosity,
            "common_topics": self.common_topics,
            "preferred_models": self.preferred_models,
        }


class PersonalizationAgent(BaseAgent):
    """Agent that manages user profiles and personalizes interactions.
    
    Responsibilities:
    - Maintain user profiles
    - Learn from interaction patterns
    - Customize response style
    - Suggest personalized features
    """
    
    def __init__(self, config: Optional[AgentConfig] = None):
        if config is None:
            config = AgentConfig(
                name="personalization_agent",
                agent_type=AgentType.REACTIVE,
                priority=AgentPriority.MEDIUM,
                max_tokens_per_run=2000,
                can_access_user_data=True,
                memory_namespace="personalization",
            )
        super().__init__(config)
        self._profiles: Dict[str, UserProfile] = {}
    
    async def execute(self, task: Optional[AgentTask] = None) -> AgentResult:
        """Execute personalization tasks."""
        if not task:
            return AgentResult(success=False, error="No task provided")
        
        # TODO: Implement profile management
        return AgentResult(
            success=True,
            output={"status": "Personalization completed (stub)"},
        )
    
    def get_capabilities(self) -> Dict[str, Any]:
        return {
            "name": "Personalization Agent",
            "type": "reactive",
            "purpose": "Manage user profiles and personalize interactions",
        }
    
    async def get_profile(self, user_id: str) -> UserProfile:
        """Get or create a user profile."""
        if user_id not in self._profiles:
            self._profiles[user_id] = UserProfile(user_id=user_id)
        return self._profiles[user_id]
    
    async def get_style_prompt(self, user_id: str) -> str:
        """Generate a style prompt for the user."""
        profile = await self.get_profile(user_id)
        
        style_guides = {
            "formal": "Use professional, formal language. Avoid contractions and slang.",
            "casual": "Use friendly, conversational language. Be approachable.",
            "technical": "Include technical details. Assume familiarity with domain concepts.",
            "balanced": "Balance clarity with depth. Adapt to the question's complexity.",
        }
        
        expertise_guides = {
            "novice": "Explain concepts from basics. Define technical terms.",
            "intermediate": "Assume general knowledge. Focus on application.",
            "expert": "Assume deep expertise. Focus on nuances and edge cases.",
        }
        
        return (
            f"USER PROFILE:\n"
            f"Style: {style_guides.get(profile.preferred_style, style_guides['balanced'])}\n"
            f"Level: {expertise_guides.get(profile.expertise_level, expertise_guides['intermediate'])}\n"
        )

