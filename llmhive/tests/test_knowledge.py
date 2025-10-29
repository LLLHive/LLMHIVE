from llmhive.app.knowledge import KnowledgeBase
from llmhive.app.models import KnowledgeDocument


def test_knowledge_store_round_trip(db_session):
    kb = KnowledgeBase(db_session)
    assert db_session.query(KnowledgeDocument).count() == 0

    kb.record_interaction(
        user_id="alice",
        prompt="What is retrieval augmented generation?",
        response="RAG combines retrieval with generation to ground answers.",
        conversation_id=None,
        supporting_notes=["Uses vector search to fetch evidence."],
    )
    db_session.flush()

    hits = kb.search("alice", "Explain RAG" , limit=2)
    assert hits
    assert hits[0].score > 0
    context_block = KnowledgeBase.to_prompt_block(hits)
    assert context_block and "Grounding knowledge" in context_block
