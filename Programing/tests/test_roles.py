import pytest
from app.roles import LeadResponder, Researcher, Critic, Synthesizer, AgentRole


def test_lead_responder():
    lead = LeadResponder("LeadResponder")
    result = lead.execute({"input": "Test input"})
    assert "draft" in result
    assert result["draft"] == "Generated main draft response"


def test_researcher():
    researcher = Researcher("Researcher")
    result = researcher.execute({"input": "Test input"})
    assert "research" in result
    assert result["research"] == "Fetched supporting information"


def test_critic():
    critic = Critic("Critic")
    result = critic.execute({"draft": "Test draft", "research": "Test research"})
    assert "critique" in result
    assert result["critique"] == "Critique of the draft provided"


def test_synthesizer():
    synthesizer = Synthesizer("Synthesizer")
    result = synthesizer.execute({"draft": "Test draft", "research": "Test research"})
    assert "final_response" in result
    assert result["final_response"] == "Synthesized final response"


def test_agent_role_base_class():
    """Test that the base AgentRole class raises NotImplementedError."""
    agent = AgentRole("BaseAgent")
    with pytest.raises(NotImplementedError):
        agent.execute({})
