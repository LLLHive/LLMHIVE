from llmhive.app.models import KnowledgeDocument


def test_diagnostics_endpoint_reports_stub_only(client):
    response = client.get("/api/v1/diagnostics")
    assert response.status_code == 200
    payload = response.json()

    assert "providers_configured" in payload
    assert payload["stub_only"] is True
    assert any("stub provider" in warning.lower() for warning in payload["warnings"])
    assert isinstance(payload["knowledge_documents"], int)
    assert isinstance(payload["memory_conversations"], int)


def test_diagnostics_endpoint_with_knowledge_samples(client, db_session):
    document = KnowledgeDocument(
        user_id="diagnostics-user",
        conversation_id=None,
        content="Question: test?\nAnswer: yes", 
        embedding={"test": 1.0},
        payload={"source": "unit-test"},
    )
    db_session.add(document)
    db_session.commit()

    response = client.get(
        "/api/v1/diagnostics",
        params={"user_id": "diagnostics-user"},
    )
    assert response.status_code == 200
    payload = response.json()

    assert payload["knowledge_documents"] >= 1
    assert payload["knowledge_samples"], "Expected at least one knowledge sample"
    assert not any(
        "knowledge base is empty" in warning.lower() for warning in payload["warnings"]
    )

    db_session.delete(document)
    db_session.commit()
