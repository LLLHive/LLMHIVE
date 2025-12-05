"""Tests for PersonalizationAgent."""
import pytest
from llmhive.app.agents.personalization_agent import (
    PersonalizationAgent,
    UserProfile,
    PersonalizedContext,
    STYLE_GUIDES,
    EXPERTISE_GUIDES,
    VERBOSITY_GUIDES,
)
from llmhive.app.agents.base import AgentTask


class TestUserProfile:
    """Tests for UserProfile dataclass."""
    
    def test_default_values(self):
        """Test default profile values."""
        profile = UserProfile(user_id="user-1")
        
        assert profile.user_id == "user-1"
        assert profile.preferred_style == "balanced"
        assert profile.expertise_level == "intermediate"
        assert profile.verbosity == "medium"
        assert profile.is_learning_enabled is True
    
    def test_to_dict(self):
        """Test serialization."""
        profile = UserProfile(
            user_id="user-1",
            display_name="Test User",
            preferred_style="technical",
            expertise_level="expert",
        )
        data = profile.to_dict()
        
        assert data["user_id"] == "user-1"
        assert data["display_name"] == "Test User"
        assert data["preferences"]["style"] == "technical"
        assert data["preferences"]["expertise_level"] == "expert"
    
    def test_to_dict_with_topics(self):
        """Test serialization limits topics."""
        profile = UserProfile(user_id="user-1")
        profile.common_topics = [f"topic-{i}" for i in range(20)]
        
        data = profile.to_dict()
        
        # Should only include top 10
        assert len(data["learned_patterns"]["common_topics"]) <= 10


class TestPersonalizedContext:
    """Tests for PersonalizedContext dataclass."""
    
    def test_to_dict(self):
        """Test serialization."""
        context = PersonalizedContext(
            style_instructions="Be formal",
            domain_context="User is expert in Python",
            recommended_model="gpt-4o",
            recommended_tools=["calculator", "web_search"],
        )
        data = context.to_dict()
        
        assert data["style_instructions"] == "Be formal"
        assert data["recommended_model"] == "gpt-4o"
        assert "calculator" in data["recommended_tools"]


class TestStyleGuides:
    """Tests for style guides."""
    
    def test_all_styles_have_guides(self):
        """Test that all expected styles have guides."""
        expected = ["formal", "casual", "technical", "balanced"]
        for style in expected:
            assert style in STYLE_GUIDES
            assert len(STYLE_GUIDES[style]) > 0
    
    def test_all_expertise_levels_have_guides(self):
        """Test that all expertise levels have guides."""
        expected = ["novice", "intermediate", "expert"]
        for level in expected:
            assert level in EXPERTISE_GUIDES
            assert len(EXPERTISE_GUIDES[level]) > 0
    
    def test_all_verbosity_levels_have_guides(self):
        """Test that all verbosity levels have guides."""
        expected = ["brief", "medium", "detailed"]
        for level in expected:
            assert level in VERBOSITY_GUIDES
            assert len(VERBOSITY_GUIDES[level]) > 0


class TestPersonalizationAgent:
    """Tests for PersonalizationAgent."""
    
    @pytest.fixture
    def agent(self):
        """Create agent instance."""
        return PersonalizationAgent()
    
    def test_initialization(self, agent):
        """Test agent initialization."""
        assert agent.config.name == "personalization_agent"
        assert agent._profiles == {}
    
    def test_get_capabilities(self, agent):
        """Test capabilities reporting."""
        caps = agent.get_capabilities()
        
        assert caps["name"] == "Personalization Agent"
        assert "get_profile" in caps["task_types"]
        assert "supported_styles" in caps
    
    @pytest.mark.asyncio
    async def test_no_task_returns_error(self, agent):
        """Test that no task returns error."""
        result = await agent.execute(None)
        
        assert not result.success
        assert "No task provided" in result.error
    
    @pytest.mark.asyncio
    async def test_get_profile_creates_new(self, agent):
        """Test getting profile creates new one."""
        task = AgentTask(
            task_id="test-1",
            task_type="get_profile",
            payload={"user_id": "new-user"},
        )
        result = await agent.execute(task)
        
        assert result.success
        assert result.output["user_id"] == "new-user"
        assert "new-user" in agent._profiles
    
    @pytest.mark.asyncio
    async def test_get_profile_returns_existing(self, agent):
        """Test getting existing profile."""
        # Create profile first
        agent._profiles["existing-user"] = UserProfile(
            user_id="existing-user",
            display_name="Existing",
        )
        
        task = AgentTask(
            task_id="test-2",
            task_type="get_profile",
            payload={"user_id": "existing-user"},
        )
        result = await agent.execute(task)
        
        assert result.success
        assert result.output["display_name"] == "Existing"
    
    @pytest.mark.asyncio
    async def test_get_profile_no_user_id(self, agent):
        """Test getting profile without user_id."""
        task = AgentTask(
            task_id="test-3",
            task_type="get_profile",
            payload={},
        )
        result = await agent.execute(task)
        
        assert not result.success
        assert "No user_id" in result.error
    
    @pytest.mark.asyncio
    async def test_update_profile_preferences(self, agent):
        """Test updating profile preferences."""
        task = AgentTask(
            task_id="test-4",
            task_type="update_profile",
            payload={
                "user_id": "user-1",
                "preferences": {
                    "style": "technical",
                    "expertise_level": "expert",
                    "verbosity": "detailed",
                },
            },
        )
        result = await agent.execute(task)
        
        assert result.success
        profile = agent._profiles["user-1"]
        assert profile.preferred_style == "technical"
        assert profile.expertise_level == "expert"
        assert profile.verbosity == "detailed"
    
    @pytest.mark.asyncio
    async def test_update_profile_domains(self, agent):
        """Test updating profile domains."""
        task = AgentTask(
            task_id="test-5",
            task_type="update_profile",
            payload={
                "user_id": "user-1",
                "preferred_domains": ["python", "machine learning"],
                "avoided_topics": ["violence"],
            },
        )
        result = await agent.execute(task)
        
        assert result.success
        profile = agent._profiles["user-1"]
        assert "python" in profile.preferred_domains
        assert "violence" in profile.avoided_topics
    
    @pytest.mark.asyncio
    async def test_update_profile_display_name(self, agent):
        """Test updating display name."""
        task = AgentTask(
            task_id="test-6",
            task_type="update_profile",
            payload={
                "user_id": "user-1",
                "display_name": "John Doe",
            },
        )
        result = await agent.execute(task)
        
        assert result.success
        assert agent._profiles["user-1"].display_name == "John Doe"
    
    @pytest.mark.asyncio
    async def test_get_context_without_user(self, agent):
        """Test getting context without user returns default."""
        task = AgentTask(
            task_id="test-7",
            task_type="get_context",
            payload={"query": "How do I code?"},
        )
        result = await agent.execute(task)
        
        assert result.success
        # Should return default/empty context
    
    @pytest.mark.asyncio
    async def test_get_context_with_user(self, agent):
        """Test getting context with user profile."""
        # Create user with preferences
        await agent.execute(AgentTask(
            task_id="t1",
            task_type="update_profile",
            payload={
                "user_id": "user-2",
                "preferences": {"style": "technical"},
                "preferred_domains": ["python"],
            },
        ))
        
        task = AgentTask(
            task_id="test-8",
            task_type="get_context",
            payload={
                "user_id": "user-2",
                "query": "How do I write a function?",
            },
        )
        result = await agent.execute(task)
        
        assert result.success
        assert "style_instructions" in result.output
        assert "technical" in result.output["style_instructions"].lower() or "Style" in result.output["style_instructions"]
    
    @pytest.mark.asyncio
    async def test_learn_from_interaction(self, agent):
        """Test learning from interaction."""
        task = AgentTask(
            task_id="test-9",
            task_type="learn_from_interaction",
            payload={
                "user_id": "user-3",
                "query": "How do I debug Python?",
                "detected_topics": ["python", "debugging"],
                "model_used": "gpt-4o",
                "tools_used": ["code_executor"],
                "new_conversation": True,
            },
        )
        result = await agent.execute(task)
        
        assert result.success
        profile = agent._profiles["user-3"]
        assert profile.total_queries == 1
        assert profile.total_conversations == 1
        assert "python" in profile.common_topics
        assert "gpt-4o" in profile.preferred_models
        assert "code_executor" in profile.tools_used
    
    @pytest.mark.asyncio
    async def test_learn_from_interaction_disabled(self, agent):
        """Test learning respects disabled flag."""
        # Create user with learning disabled
        agent._profiles["user-4"] = UserProfile(
            user_id="user-4",
            is_learning_enabled=False,
        )
        
        task = AgentTask(
            task_id="test-10",
            task_type="learn_from_interaction",
            payload={
                "user_id": "user-4",
                "detected_topics": ["new_topic"],
            },
        )
        result = await agent.execute(task)
        
        assert result.success
        assert "Learning disabled" in result.output["message"]
        assert "new_topic" not in agent._profiles["user-4"].common_topics
    
    @pytest.mark.asyncio
    async def test_learn_from_interaction_feedback(self, agent):
        """Test learning records feedback."""
        task = AgentTask(
            task_id="test-11",
            task_type="learn_from_interaction",
            payload={
                "user_id": "user-5",
                "feedback_score": 5,
            },
        )
        result = await agent.execute(task)
        
        assert result.success
        assert 5 in agent._profiles["user-5"].feedback_scores
    
    @pytest.mark.asyncio
    async def test_get_recommendations(self, agent):
        """Test getting recommendations."""
        # Create user with some history
        profile = UserProfile(user_id="user-6", total_queries=15)
        agent._profiles["user-6"] = profile
        
        task = AgentTask(
            task_id="test-12",
            task_type="get_recommendations",
            payload={"user_id": "user-6"},
        )
        result = await agent.execute(task)
        
        assert result.success
        assert "features" in result.output
        assert "models" in result.output
        assert "settings" in result.output
    
    @pytest.mark.asyncio
    async def test_reset_profile(self, agent):
        """Test resetting profile."""
        # Create user with data
        agent._profiles["user-7"] = UserProfile(
            user_id="user-7",
            preferred_style="technical",
            total_queries=100,
        )
        
        task = AgentTask(
            task_id="test-13",
            task_type="reset_profile",
            payload={
                "user_id": "user-7",
                "keep_engagement": True,
            },
        )
        result = await agent.execute(task)
        
        assert result.success
        profile = agent._profiles["user-7"]
        assert profile.preferred_style == "balanced"  # Reset to default
        assert profile.total_queries == 100  # Kept engagement
    
    @pytest.mark.asyncio
    async def test_reset_profile_full(self, agent):
        """Test full profile reset."""
        agent._profiles["user-8"] = UserProfile(
            user_id="user-8",
            total_queries=50,
        )
        
        task = AgentTask(
            task_id="test-14",
            task_type="reset_profile",
            payload={
                "user_id": "user-8",
                "keep_engagement": False,
            },
        )
        result = await agent.execute(task)
        
        assert result.success
        assert agent._profiles["user-8"].total_queries == 0
    
    @pytest.mark.asyncio
    async def test_unknown_task_type(self, agent):
        """Test with unknown task type."""
        task = AgentTask(
            task_id="test-15",
            task_type="unknown_type",
            payload={},
        )
        result = await agent.execute(task)
        
        assert not result.success
        assert "Unknown task type" in result.error
    
    @pytest.mark.asyncio
    async def test_get_profile_helper(self, agent):
        """Test the get_profile helper method."""
        profile = await agent.get_profile("helper-user")
        
        assert profile.user_id == "helper-user"
        assert "helper-user" in agent._profiles
    
    @pytest.mark.asyncio
    async def test_get_style_prompt_helper(self, agent):
        """Test the get_style_prompt helper method."""
        agent._profiles["style-user"] = UserProfile(
            user_id="style-user",
            preferred_style="formal",
            expertise_level="expert",
        )
        
        prompt = await agent.get_style_prompt("style-user")
        
        assert "USER PROFILE" in prompt
        assert "Style" in prompt
        assert "Level" in prompt


class TestToolRecommendations:
    """Tests for tool recommendation logic."""
    
    @pytest.fixture
    def agent(self):
        return PersonalizationAgent()
    
    def test_recommends_calculator_for_math(self, agent):
        """Test calculator recommended for math queries."""
        profile = UserProfile(user_id="test")
        tools = agent._recommend_tools("Please calculate 2 + 2", profile)
        assert "calculator" in tools
    
    def test_recommends_search_for_research(self, agent):
        """Test web search recommended for research."""
        profile = UserProfile(user_id="test")
        tools = agent._recommend_tools("Search for Python tutorials", profile)
        assert "web_search" in tools
    
    def test_recommends_code_executor_for_code(self, agent):
        """Test code executor recommended for coding."""
        profile = UserProfile(user_id="test")
        tools = agent._recommend_tools("Debug this function", profile)
        assert "code_executor" in tools
    
    def test_includes_user_preferred_tools(self, agent):
        """Test user's preferred tools are included."""
        profile = UserProfile(user_id="test")
        profile.tools_used = ["custom_tool"]
        tools = agent._recommend_tools("Generic query", profile)
        assert "custom_tool" in tools


class TestModelRecommendations:
    """Tests for model recommendation logic."""
    
    @pytest.fixture
    def agent(self):
        return PersonalizationAgent()
    
    def test_returns_user_preference(self, agent):
        """Test returns user's preferred model."""
        profile = UserProfile(user_id="test")
        profile.preferred_models = ["claude-3-opus"]
        model = agent._recommend_model("Any query", profile)
        assert model == "claude-3-opus"
    
    def test_recommends_for_coding(self, agent):
        """Test recommendation for coding queries."""
        profile = UserProfile(user_id="test")
        model = agent._recommend_model("How do I code a function?", profile)
        assert model is not None
    
    def test_recommends_mini_for_brief(self, agent):
        """Test mini model for brief verbosity."""
        profile = UserProfile(user_id="test", verbosity="brief")
        model = agent._recommend_model("Simple question", profile)
        # Should recommend a fast model for brief responses
        assert model in [None, "gpt-4o-mini"]
