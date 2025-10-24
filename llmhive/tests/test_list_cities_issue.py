"""Test for the list cities issue from the bug report."""
import pytest
from llmhive.app.schemas import OrchestrationRequest


def test_list_europe_cities_question(client):
    """Test that 'List Europes 5 largest cities' does not return a stub response."""
    payload = OrchestrationRequest(
        prompt="List Europes 5 largest cities",
        models=["gpt-4", "gpt-5", "gpt-3", "grok"]
    )
    response = client.post("/api/v1/orchestration/", json=payload.model_dump())

    assert response.status_code == 200
    data = response.json()
    
    # Verify the response structure
    assert data["prompt"] == payload.prompt
    
    # Check that initial responses DO NOT contain stub response text
    for resp in data["initial_responses"]:
        content = resp["content"]
        print(f"\nModel {resp['model']}: {content[:200]}")
        assert "This is a stub response" not in content, \
            f"Model {resp['model']} returned stub response: {content}"
    
    # The final response should also not be a stub
    final = data["final_response"]
    print(f"\nFinal response: {final[:200]}")
    assert "This is a stub response" not in final, \
        f"Final response is a stub: {final}"
