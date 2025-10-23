"""Test for the specific capital question scenario from the bug report."""
import pytest
from llmhive.app.schemas import OrchestrationRequest


def test_capital_of_spain_question(client):
    """Test that 'What's the capital of Spain?' returns a proper answer."""
    payload = OrchestrationRequest(
        prompt="Whats the capital of Spain?",
        models=["gpt-4"]
    )
    response = client.post("/api/v1/orchestration/", json=payload.model_dump())

    assert response.status_code == 200
    data = response.json()
    
    # Verify the response structure
    assert data["prompt"] == payload.prompt
    assert data["models"] == ["gpt-4"]
    assert len(data["initial_responses"]) == 1
    assert data["initial_responses"][0]["model"] == "gpt-4"
    
    # Verify the content contains the actual answer
    initial_content = data["initial_responses"][0]["content"]
    assert "Madrid" in initial_content
    
    # Verify we're not getting the old stub format
    assert not initial_content.startswith("[gpt-4] Response to:")
    
    # The final response should also reference Madrid
    assert "Madrid" in data["final_response"] or "capital" in data["final_response"].lower()


def test_various_capital_questions(client):
    """Test various capital questions to ensure they all work."""
    test_cases = [
        ("What is the capital of France?", "Paris"),
        ("What is the capital of Italy?", "Rome"),
        ("What is the capital of Germany?", "Berlin"),
        ("What is the capital of Japan?", "Tokyo"),
    ]
    
    for prompt, expected_answer in test_cases:
        payload = OrchestrationRequest(
            prompt=prompt,
            models=["gpt-4"]
        )
        response = client.post("/api/v1/orchestration/", json=payload.model_dump())
        
        assert response.status_code == 200
        data = response.json()
        initial_content = data["initial_responses"][0]["content"]
        assert expected_answer in initial_content, f"Expected '{expected_answer}' in response to '{prompt}'"
