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
        ("List the 10 biggest cities in Spain", ["Madrid", "Barcelona", "Valencia"]),
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


def test_city_list_respects_requested_count(client):
    payload = OrchestrationRequest(
        prompt="List the 3 largest cities in Spain",
        models=["gpt-4"],
    )
    response = client.post("/api/v1/orchestration/", json=payload.model_dump())

    assert response.status_code == 200
    data = response.json()
    content = data["initial_responses"][0]["content"]

    lines = [line for line in content.splitlines() if line.strip() and line[0].isdigit()]
    assert len(lines) == 3, f"Expected exactly 3 lines, got {len(lines)}: {content}"
    assert "Madrid" in content and "Barcelona" in content and "Valencia" in content


def test_florida_cities_with_population(client):
    payload = OrchestrationRequest(
        prompt="List the 5 largest cities in Florida with their population",
        models=["gpt-4"],
    )
    response = client.post("/api/v1/orchestration/", json=payload.model_dump())

    assert response.status_code == 200
    data = response.json()
    content = data["initial_responses"][0]["content"]

    assert "Florida" in content
    assert "population" in content.lower()
    for city in ["Jacksonville", "Miami", "Tampa"]:
        assert city in content, f"Expected {city} to appear in response: {content}"


def test_best_coding_model_question(client):
    payload = OrchestrationRequest(
        prompt="Which is the best AI LLM model for coding?",
        models=["gpt-4"],
    )
    response = client.post("/api/v1/orchestration/", json=payload.model_dump())

    assert response.status_code == 200
    data = response.json()
    content = data["initial_responses"][0]["content"]

    assert "stub response" not in content.lower()
    for model_name in ["GPT-4.1", "Claude 3 Opus", "Gemini 1.5 Pro"]:
        assert model_name in content, f"Expected {model_name} in answer: {content}"


def test_affordable_housing_developers_in_florida(client):
    payload = OrchestrationRequest(
        prompt="list the largest development companies in Florida that specialize in affordable housing",
        models=["gpt-4"],
    )
    response = client.post("/api/v1/orchestration/", json=payload.model_dump())

    assert response.status_code == 200
    data = response.json()

    initial_content = data["initial_responses"][0]["content"]
    assert "stub response" not in initial_content.lower()
    for expected in [
        "Housing Trust Group",
        "Atlantic Pacific Communities",
        "Related Urban",
        "Pinnacle Housing Group",
        "Carrfour Supportive Housing",
    ]:
        assert expected in initial_content, f"Expected '{expected}' in response: {initial_content}"

    final_content = data["final_response"]
    assert "stub response" not in final_content.lower()
    assert "affordable" in final_content.lower()
    assert "Florida" in final_content


def test_affluent_miami_dade_cities(client):
    payload = OrchestrationRequest(
        prompt="List the 10 most affluent cities in Miami Dade county Florida",
        models=["gpt-4"],
    )
    response = client.post("/api/v1/orchestration/", json=payload.model_dump())

    assert response.status_code == 200
    data = response.json()
    content = data["initial_responses"][0]["content"]

    assert "stub response" not in content.lower()
    assert "miami-dade county" in content.lower()
    assert "affluent" in content.lower()

    lines = [line for line in content.splitlines() if line.strip() and line.strip()[0].isdigit()]
    assert len(lines) == 10, f"Expected 10 affluent cities, got {len(lines)}: {content}"

    for city in [
        "Pinecrest",
        "Key Biscayne",
        "Coral Gables",
        "Palmetto Bay",
        "Bal Harbour",
    ]:
        assert city in content, f"Expected {city} in affluent city list: {content}"
