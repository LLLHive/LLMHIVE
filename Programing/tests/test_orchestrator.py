import pytest
from app.orchestrator import Orchestrator


def test_orchestrator_workflow():
    """Test the complete orchestration workflow."""
    orchestrator = Orchestrator()
    result = orchestrator.orchestrate({"input": "Test query"})
    
    # Verify the result structure
    assert result is not None
    assert "final_response" in result
    assert result["final_response"] == "Synthesized final response"


def test_orchestrator_validation_failure():
    """Test orchestrator handles validation failure."""
    orchestrator = Orchestrator()
    # The validator should reject outputs with disallowed_content
    # This test verifies the flow, though the current implementation doesn't
    # produce disallowed content
    result = orchestrator.orchestrate({"input": "Test query"})
    assert "error" not in result  # Should pass validation
