"""Test that critique authors are correctly assigned."""
import pytest
from llmhive.app.schemas import OrchestrationRequest


def test_critique_authors_are_correct(client):
    """Test that critique authors match the model that provided the critique."""
    payload = OrchestrationRequest(
        prompt="What is the capital of Spain?",
        models=["gpt-4", "gpt-5", "grok"]
    )
    response = client.post("/api/v1/orchestration/", json=payload.model_dump())

    assert response.status_code == 200
    data = response.json()
    
    # Verify we have critiques
    assert len(data["critiques"]) > 0
    
    # Verify each critique's author matches the model name in the feedback
    for critique in data["critiques"]:
        author = critique["author"]
        feedback = critique["feedback"]
        
        # The feedback should start with the author's name
        # Format: "{author} suggests clarifying details about..."
        assert feedback.startswith(f"{author} suggests"), \
            f"Critique feedback doesn't start with author name. Author: {author}, Feedback: {feedback}"


def test_critique_authors_with_multiple_models(client):
    """Test critique authors with various model combinations."""
    test_cases = [
        (["gpt-4", "claude-3"], 2),  # 2 models = 2 critiques (each critiques the other)
        (["gpt-4", "gpt-5", "grok"], 6),  # 3 models = 6 critiques (3*2)
        (["gpt-4", "gpt-5", "grok", "claude-3"], 12),  # 4 models = 12 critiques (4*3)
    ]
    
    for models, expected_critique_count in test_cases:
        payload = OrchestrationRequest(
            prompt="Test prompt",
            models=models
        )
        response = client.post("/api/v1/orchestration/", json=payload.model_dump())
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify critique count
        assert len(data["critiques"]) == expected_critique_count, \
            f"Expected {expected_critique_count} critiques for {len(models)} models, got {len(data['critiques'])}"
        
        # Verify all authors are in the model list
        for critique in data["critiques"]:
            assert critique["author"] in models, \
                f"Critique author {critique['author']} not in model list {models}"
            assert critique["target"] in models, \
                f"Critique target {critique['target']} not in model list {models}"
            assert critique["author"] != critique["target"], \
                "Critique author and target should not be the same"


def test_final_response_not_truncated(client):
    """Test that final response doesn't contain synthesis prompt text."""
    payload = OrchestrationRequest(
        prompt="If a plane is on a treadmill moving at the same speed but in the opposite direction, can it take off?",
        models=["gpt-4", "gpt-5", "grok"]
    )
    response = client.post("/api/v1/orchestration/", json=payload.model_dump())

    assert response.status_code == 200
    data = response.json()
    
    final_response = data["final_response"]
    
    # Should not contain the synthesis prompt
    assert "You are synthesizing answers" not in final_response, \
        "Final response should not contain synthesis prompt text"
    
    # Should not be truncated to show partial synthesis prompt
    assert "Original user prompt:" not in final_response, \
        "Final response should not contain synthesis prompt structure"
    
    # Should contain some actual content
    assert len(final_response) > 0, "Final response should not be empty"


def test_capital_question_final_response(client):
    """Test that capital questions get proper final responses."""
    payload = OrchestrationRequest(
        prompt="What is the capital of Spain?",
        models=["gpt-4"]
    )
    response = client.post("/api/v1/orchestration/", json=payload.model_dump())

    assert response.status_code == 200
    data = response.json()
    
    # Final response should mention Madrid
    assert "Madrid" in data["final_response"], \
        f"Final response should mention Madrid. Got: {data['final_response']}"
