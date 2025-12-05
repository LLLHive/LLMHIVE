"""Personalization Agent for LLMHive.

This agent manages user profiles, learns from interaction patterns,
and personalizes AI responses based on user preferences.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from .base import BaseAgent, AgentConfig, AgentResult, AgentTask, AgentType, AgentPriority

logger = logging.getLogger(__name__)


@dataclass
class UserProfile:
    """User profile for personalization."""
    user_id: str
    display_name: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    # Style preferences
    preferred_style: str = "balanced"  # formal, casual, technical, balanced
    expertise_level: str = "intermediate"  # novice, intermediate, expert
    verbosity: str = "medium"  # brief, medium, detailed
    language: str = "en"
    
    # Response preferences
    include_examples: bool = True
    include_code_snippets: bool = True
    prefer_bullet_points: bool = False
    show_confidence_scores: bool = False
    
    # Domain preferences
    preferred_domains: List[str] = field(default_factory=list)
    avoided_topics: List[str] = field(default_factory=list)
    
    # Behavior patterns (learned)
    common_topics: List[str] = field(default_factory=list)
    preferred_models: List[str] = field(default_factory=list)
    tools_used: List[str] = field(default_factory=list)
    query_patterns: List[str] = field(default_factory=list)  # e.g., "debugging", "research"
    
    # Engagement metrics
    total_conversations: int = 0
    total_queries: int = 0
    avg_session_length: float = 0.0
    feedback_scores: List[int] = field(default_factory=list)
    
    # Learning state
    is_learning_enabled: bool = True
    last_interaction: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "display_name": self.display_name,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "preferences": {
                "style": self.preferred_style,
                "expertise_level": self.expertise_level,
                "verbosity": self.verbosity,
                "language": self.language,
                "include_examples": self.include_examples,
                "include_code_snippets": self.include_code_snippets,
                "prefer_bullet_points": self.prefer_bullet_points,
            },
            "domains": {
                "preferred": self.preferred_domains,
                "avoided": self.avoided_topics,
            },
            "learned_patterns": {
                "common_topics": self.common_topics[:10],  # Top 10
                "preferred_models": self.preferred_models,
                "tools_used": self.tools_used,
                "query_patterns": self.query_patterns,
            },
            "engagement": {
                "total_conversations": self.total_conversations,
                "total_queries": self.total_queries,
                "avg_session_length": self.avg_session_length,
                "avg_feedback_score": (
                    sum(self.feedback_scores) / len(self.feedback_scores)
                    if self.feedback_scores else 0
                ),
            },
            "learning_enabled": self.is_learning_enabled,
        }


@dataclass
class PersonalizedContext:
    """Context generated for personalizing a response."""
    system_prompt_additions: str = ""
    style_instructions: str = ""
    domain_context: str = ""
    user_history_context: str = ""
    recommended_model: Optional[str] = None
    recommended_tools: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "system_prompt_additions": self.system_prompt_additions,
            "style_instructions": self.style_instructions,
            "domain_context": self.domain_context,
            "recommended_model": self.recommended_model,
            "recommended_tools": self.recommended_tools,
        }


# Style and expertise guides
STYLE_GUIDES = {
    "formal": "Use professional, formal language. Avoid contractions, slang, and colloquialisms. Maintain a respectful, business-appropriate tone.",
    "casual": "Use friendly, conversational language. Be approachable and personable. Feel free to use contractions and casual expressions.",
    "technical": "Use precise technical terminology. Assume familiarity with domain concepts. Include technical details and specifications.",
    "balanced": "Balance clarity with technical accuracy. Adapt complexity to the question. Be informative yet accessible.",
}

EXPERTISE_GUIDES = {
    "novice": "Explain concepts from the basics. Define technical terms when first used. Use analogies and simple examples. Avoid jargon without explanation.",
    "intermediate": "Assume general knowledge of the domain. Focus on application and best practices. Provide context for advanced concepts.",
    "expert": "Assume deep expertise in the domain. Focus on nuances, edge cases, and advanced techniques. Skip basic explanations unless asked.",
}

VERBOSITY_GUIDES = {
    "brief": "Be concise and to the point. Provide direct answers without unnecessary elaboration. Use short sentences.",
    "medium": "Balance thoroughness with brevity. Include key details and examples. Explain reasoning when helpful.",
    "detailed": "Provide comprehensive explanations. Include background context, multiple examples, and edge cases. Explain reasoning fully.",
}


class PersonalizationAgent(BaseAgent):
    """Agent that manages user profiles and personalizes interactions.
    
    Responsibilities:
    - Maintain user profiles
    - Learn from interaction patterns
    - Customize response style based on preferences
    - Suggest personalized features and models
    - Generate context for personalized responses
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
        """Execute personalization tasks.
        
        Task types:
        - "get_profile": Get user profile
        - "update_profile": Update user preferences
        - "get_context": Generate personalized context for a query
        - "learn_from_interaction": Update profile based on interaction
        - "get_recommendations": Get personalized recommendations
        - "reset_profile": Reset user profile to defaults
        
        Returns:
            AgentResult with personalization data
        """
        start_time = time.time()
        
        if not task:
            return AgentResult(success=False, error="No task provided")
        
        task_type = task.task_type
        payload = task.payload or {}
        
        try:
            if task_type == "get_profile":
                result = await self._get_profile(payload)
            elif task_type == "update_profile":
                result = await self._update_profile(payload)
            elif task_type == "get_context":
                result = await self._get_context(payload)
            elif task_type == "learn_from_interaction":
                result = await self._learn_from_interaction(payload)
            elif task_type == "get_recommendations":
                result = await self._get_recommendations(payload)
            elif task_type == "reset_profile":
                result = await self._reset_profile(payload)
            else:
                return AgentResult(
                    success=False,
                    error=f"Unknown task type: {task_type}",
                )
            
            result.duration_ms = int((time.time() - start_time) * 1000)
            return result
            
        except Exception as e:
            logger.exception("Personalization agent error: %s", e)
            return AgentResult(
                success=False,
                error=str(e),
                duration_ms=int((time.time() - start_time) * 1000),
            )
    
    async def _get_profile(self, payload: Dict[str, Any]) -> AgentResult:
        """Get or create a user profile."""
        user_id = payload.get("user_id")
        if not user_id:
            return AgentResult(success=False, error="No user_id provided")
        
        profile = await self.get_profile(user_id)
        
        return AgentResult(
            success=True,
            output=profile.to_dict(),
        )
    
    async def _update_profile(self, payload: Dict[str, Any]) -> AgentResult:
        """Update user profile preferences."""
        user_id = payload.get("user_id")
        if not user_id:
            return AgentResult(success=False, error="No user_id provided")
        
        profile = await self.get_profile(user_id)
        
        # Update preferences
        preferences = payload.get("preferences", {})
        
        if "style" in preferences:
            if preferences["style"] in STYLE_GUIDES:
                profile.preferred_style = preferences["style"]
        
        if "expertise_level" in preferences:
            if preferences["expertise_level"] in EXPERTISE_GUIDES:
                profile.expertise_level = preferences["expertise_level"]
        
        if "verbosity" in preferences:
            if preferences["verbosity"] in VERBOSITY_GUIDES:
                profile.verbosity = preferences["verbosity"]
        
        if "language" in preferences:
            profile.language = preferences["language"]
        
        if "include_examples" in preferences:
            profile.include_examples = bool(preferences["include_examples"])
        
        if "include_code_snippets" in preferences:
            profile.include_code_snippets = bool(preferences["include_code_snippets"])
        
        if "prefer_bullet_points" in preferences:
            profile.prefer_bullet_points = bool(preferences["prefer_bullet_points"])
        
        if "show_confidence_scores" in preferences:
            profile.show_confidence_scores = bool(preferences["show_confidence_scores"])
        
        # Update domains
        if "preferred_domains" in payload:
            profile.preferred_domains = payload["preferred_domains"]
        
        if "avoided_topics" in payload:
            profile.avoided_topics = payload["avoided_topics"]
        
        if "display_name" in payload:
            profile.display_name = payload["display_name"]
        
        if "learning_enabled" in payload:
            profile.is_learning_enabled = bool(payload["learning_enabled"])
        
        profile.updated_at = datetime.now()
        
        return AgentResult(
            success=True,
            output={
                "message": "Profile updated",
                "profile": profile.to_dict(),
            },
        )
    
    async def _get_context(self, payload: Dict[str, Any]) -> AgentResult:
        """Generate personalized context for a query."""
        user_id = payload.get("user_id")
        query = payload.get("query", "")
        
        if not user_id:
            # Return default context
            return AgentResult(
                success=True,
                output=PersonalizedContext().to_dict(),
            )
        
        profile = await self.get_profile(user_id)
        context = await self._build_personalized_context(profile, query)
        
        return AgentResult(
            success=True,
            output=context.to_dict(),
        )
    
    async def _build_personalized_context(
        self,
        profile: UserProfile,
        query: str,
    ) -> PersonalizedContext:
        """Build personalized context based on profile and query."""
        context = PersonalizedContext()
        
        # Style instructions
        style_guide = STYLE_GUIDES.get(profile.preferred_style, STYLE_GUIDES["balanced"])
        expertise_guide = EXPERTISE_GUIDES.get(profile.expertise_level, EXPERTISE_GUIDES["intermediate"])
        verbosity_guide = VERBOSITY_GUIDES.get(profile.verbosity, VERBOSITY_GUIDES["medium"])
        
        context.style_instructions = (
            f"USER PREFERENCES:\n"
            f"- Style: {style_guide}\n"
            f"- Expertise: {expertise_guide}\n"
            f"- Detail Level: {verbosity_guide}\n"
        )
        
        # Add format preferences
        format_prefs = []
        if profile.include_examples:
            format_prefs.append("Include relevant examples when helpful.")
        if profile.include_code_snippets:
            format_prefs.append("Include code snippets when applicable.")
        if profile.prefer_bullet_points:
            format_prefs.append("Use bullet points for lists and key information.")
        if profile.show_confidence_scores:
            format_prefs.append("Indicate confidence levels in claims when relevant.")
        
        if format_prefs:
            context.style_instructions += "\nFORMAT PREFERENCES:\n"
            context.style_instructions += "\n".join(f"- {p}" for p in format_prefs)
        
        # Domain context
        if profile.preferred_domains:
            context.domain_context = (
                f"User has expertise/interest in: {', '.join(profile.preferred_domains)}"
            )
        
        if profile.avoided_topics:
            context.domain_context += (
                f"\nAvoid topics: {', '.join(profile.avoided_topics)}"
            )
        
        # User history context
        if profile.common_topics:
            context.user_history_context = (
                f"User frequently asks about: {', '.join(profile.common_topics[:5])}"
            )
        
        # Recommendations based on query and profile
        context.recommended_tools = self._recommend_tools(query, profile)
        context.recommended_model = self._recommend_model(query, profile)
        
        # Build system prompt additions
        context.system_prompt_additions = context.style_instructions
        if context.domain_context:
            context.system_prompt_additions += f"\n\n{context.domain_context}"
        
        return context
    
    def _recommend_tools(self, query: str, profile: UserProfile) -> List[str]:
        """Recommend tools based on query and profile."""
        recommendations = []
        query_lower = query.lower()
        
        # Recommend based on query content
        if any(w in query_lower for w in ["calculate", "math", "compute", "sum", "average"]):
            recommendations.append("calculator")
        
        if any(w in query_lower for w in ["search", "find", "look up", "research"]):
            recommendations.append("web_search")
        
        if any(w in query_lower for w in ["code", "program", "function", "debug"]):
            recommendations.append("code_executor")
        
        # Recommend based on profile history
        for tool in profile.tools_used[:3]:  # Top 3 used tools
            if tool not in recommendations:
                recommendations.append(tool)
        
        return recommendations[:5]  # Max 5 recommendations
    
    def _recommend_model(self, query: str, profile: UserProfile) -> Optional[str]:
        """Recommend a model based on query and profile."""
        # Check profile preference
        if profile.preferred_models:
            return profile.preferred_models[0]
        
        # Recommend based on expertise level and query type
        query_lower = query.lower()
        
        if any(w in query_lower for w in ["code", "program", "debug", "function"]):
            return "gpt-4o"  # Good at coding
        
        if any(w in query_lower for w in ["analyze", "research", "deep", "complex"]):
            if profile.expertise_level == "expert":
                return "claude-3-opus"  # Deep reasoning
            return "gpt-4o"
        
        if profile.verbosity == "brief":
            return "gpt-4o-mini"  # Fast and concise
        
        return None  # Let orchestrator decide
    
    async def _learn_from_interaction(self, payload: Dict[str, Any]) -> AgentResult:
        """Update profile based on an interaction."""
        user_id = payload.get("user_id")
        if not user_id:
            return AgentResult(success=False, error="No user_id provided")
        
        profile = await self.get_profile(user_id)
        
        if not profile.is_learning_enabled:
            return AgentResult(
                success=True,
                output={"message": "Learning disabled for this user"},
            )
        
        # Update interaction metrics
        profile.total_queries += 1
        profile.last_interaction = datetime.now()
        
        # Learn from query content
        query = payload.get("query", "")
        topics = payload.get("detected_topics", [])
        
        for topic in topics:
            if topic not in profile.common_topics:
                profile.common_topics.append(topic)
        
        # Keep only top topics
        profile.common_topics = profile.common_topics[-20:]
        
        # Learn from model used
        model_used = payload.get("model_used")
        if model_used:
            if model_used not in profile.preferred_models:
                profile.preferred_models.append(model_used)
            # Limit to 5 preferred models
            profile.preferred_models = profile.preferred_models[-5:]
        
        # Learn from tools used
        tools_used = payload.get("tools_used", [])
        for tool in tools_used:
            if tool not in profile.tools_used:
                profile.tools_used.append(tool)
        profile.tools_used = profile.tools_used[-10:]
        
        # Record feedback if provided
        feedback_score = payload.get("feedback_score")
        if feedback_score is not None:
            profile.feedback_scores.append(int(feedback_score))
            # Keep last 100 scores
            profile.feedback_scores = profile.feedback_scores[-100:]
        
        # Update conversation count
        if payload.get("new_conversation", False):
            profile.total_conversations += 1
        
        profile.updated_at = datetime.now()
        
        return AgentResult(
            success=True,
            output={
                "message": "Profile updated with interaction data",
                "total_queries": profile.total_queries,
            },
        )
    
    async def _get_recommendations(self, payload: Dict[str, Any]) -> AgentResult:
        """Get personalized recommendations for a user."""
        user_id = payload.get("user_id")
        if not user_id:
            return AgentResult(success=False, error="No user_id provided")
        
        profile = await self.get_profile(user_id)
        
        recommendations = {
            "features": [],
            "models": [],
            "settings": [],
        }
        
        # Feature recommendations based on usage
        if profile.total_queries > 10:
            if not profile.prefer_bullet_points:
                recommendations["features"].append({
                    "feature": "bullet_points",
                    "reason": "Based on your query frequency, bullet points may help readability",
                })
        
        if "code" in " ".join(profile.common_topics).lower():
            if not profile.include_code_snippets:
                recommendations["features"].append({
                    "feature": "code_snippets",
                    "reason": "You frequently ask about code-related topics",
                })
        
        # Model recommendations
        if profile.feedback_scores:
            avg_score = sum(profile.feedback_scores) / len(profile.feedback_scores)
            if avg_score < 3:
                recommendations["models"].append({
                    "model": "gpt-4o",
                    "reason": "May provide higher quality responses",
                })
        
        # Settings recommendations based on expertise
        if profile.expertise_level == "novice" and profile.verbosity == "brief":
            recommendations["settings"].append({
                "setting": "verbosity",
                "suggestion": "medium",
                "reason": "More detailed explanations may be helpful at your expertise level",
            })
        
        return AgentResult(
            success=True,
            output=recommendations,
        )
    
    async def _reset_profile(self, payload: Dict[str, Any]) -> AgentResult:
        """Reset user profile to defaults."""
        user_id = payload.get("user_id")
        if not user_id:
            return AgentResult(success=False, error="No user_id provided")
        
        keep_engagement = payload.get("keep_engagement", True)
        
        if user_id in self._profiles:
            old_profile = self._profiles[user_id]
            new_profile = UserProfile(user_id=user_id)
            
            if keep_engagement:
                new_profile.total_conversations = old_profile.total_conversations
                new_profile.total_queries = old_profile.total_queries
                new_profile.feedback_scores = old_profile.feedback_scores
                new_profile.created_at = old_profile.created_at
            
            self._profiles[user_id] = new_profile
        
        return AgentResult(
            success=True,
            output={
                "message": "Profile reset to defaults",
                "profile": self._profiles.get(user_id, UserProfile(user_id=user_id)).to_dict(),
            },
        )
    
    # Public helper methods
    
    async def get_profile(self, user_id: str) -> UserProfile:
        """Get or create a user profile."""
        if user_id not in self._profiles:
            self._profiles[user_id] = UserProfile(user_id=user_id)
        return self._profiles[user_id]
    
    async def get_style_prompt(self, user_id: str) -> str:
        """Generate a style prompt for the user (convenience method)."""
        profile = await self.get_profile(user_id)
        
        style_guide = STYLE_GUIDES.get(profile.preferred_style, STYLE_GUIDES["balanced"])
        expertise_guide = EXPERTISE_GUIDES.get(profile.expertise_level, EXPERTISE_GUIDES["intermediate"])
        
        return (
            f"USER PROFILE:\n"
            f"Style: {style_guide}\n"
            f"Level: {expertise_guide}\n"
        )
    
    def get_capabilities(self) -> Dict[str, Any]:
        return {
            "name": "Personalization Agent",
            "type": "reactive",
            "purpose": "Manage user profiles and personalize interactions",
            "task_types": [
                "get_profile",
                "update_profile",
                "get_context",
                "learn_from_interaction",
                "get_recommendations",
                "reset_profile",
            ],
            "active_profiles": len(self._profiles),
            "supported_styles": list(STYLE_GUIDES.keys()),
            "supported_expertise_levels": list(EXPERTISE_GUIDES.keys()),
            "supported_verbosity_levels": list(VERBOSITY_GUIDES.keys()),
        }
