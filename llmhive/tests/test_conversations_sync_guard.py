"""Backend guard: refuse full sync that would wipe existing Firestore data."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from llmhive.app.services.conversations_firestore import (
    DESTRUCTIVE_EMPTY_SYNC_MSG,
    ConversationsFirestoreService,
    ProjectsFirestoreService,
)


def _mock_collection(existing_ids: set[str]):
    collection = MagicMock()
    doc_mocks = []
    for doc_id in existing_ids:
        doc = MagicMock()
        doc.id = doc_id
        doc_mocks.append(doc)
    collection.stream.return_value = doc_mocks
    collection.document.return_value = MagicMock()
    return collection


@pytest.mark.parametrize("service_cls", [ConversationsFirestoreService, ProjectsFirestoreService])
def test_sync_all_refuses_empty_payload_when_existing(service_cls):
    service = service_cls()
    service.db = MagicMock()
    service.db.batch.return_value = MagicMock()

    with patch.object(service, "_get_user_collection") as get_col:
        get_col.return_value = _mock_collection({"existing-1"})

        with pytest.raises(ValueError, match=DESTRUCTIVE_EMPTY_SYNC_MSG):
            if service_cls is ConversationsFirestoreService:
                service.sync_all_conversations("user_test", [])
            else:
                service.sync_all_projects("user_test", [])


def test_sync_all_allows_empty_when_nothing_existing():
    service = ConversationsFirestoreService()
    service.db = MagicMock()
    batch = MagicMock()
    service.db.batch.return_value = batch

    with patch.object(service, "_get_user_collection") as get_col:
        get_col.return_value = _mock_collection(set())
        count = service.sync_all_conversations("user_test", [])
        assert count == 0
        batch.commit.assert_called_once()
