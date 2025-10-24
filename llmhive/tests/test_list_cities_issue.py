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


def test_various_list_questions(client):
    """Test various list-based questions to ensure they all work properly."""
    test_cases = [
        ("List Europe's 5 largest cities", ["Istanbul", "Moscow", "London"]),
        ("What are the biggest cities in Europe?", ["Istanbul", "Moscow", "London"]),
        ("List the world's 5 largest cities", ["Tokyo", "Delhi", "Shanghai"]),
        ("What are the 5 largest cities in the United States?", ["New York", "Los Angeles", "Chicago"]),
        ("List the largest US cities", ["New York", "Los Angeles", "Chicago"]),
    ]
    
    for prompt, expected_keywords in test_cases:
        payload = OrchestrationRequest(
            prompt=prompt,
            models=["gpt-4"]
        )
        response = client.post("/api/v1/orchestration/", json=payload.model_dump())
        
        assert response.status_code == 200
        data = response.json()
        initial_content = data["initial_responses"][0]["content"]
        
        # Should not return stub response
        assert "This is a stub response" not in initial_content, \
            f"Got stub response for '{prompt}': {initial_content}"
        
        # Should contain at least one expected keyword
        assert any(keyword in initial_content for keyword in expected_keywords), \
            f"Expected one of {expected_keywords} in response to '{prompt}': {initial_content}"
