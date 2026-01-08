"""
Firestore service for conversation and project storage.

This module provides persistent storage for:
- User conversations (full chat history)
- User projects (conversation organization)

Data is also indexed to Pinecone for semantic search.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ..firestore_db import get_firestore_client

logger = logging.getLogger(__name__)


class ConversationsFirestoreService:
    """Manage conversations in Firestore with Pinecone indexing."""
    
    COLLECTION = "conversations"
    
    def __init__(self):
        self.db = get_firestore_client()
    
    def _get_user_collection(self, user_id: str):
        """Get user's conversations subcollection."""
        if not self.db:
            return None
        return self.db.collection("users").document(user_id).collection(self.COLLECTION)
    
    def get_all_conversations(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all conversations for a user."""
        if not self.db:
            logger.warning("Firestore not available")
            return []
        
        try:
            collection = self._get_user_collection(user_id)
            if not collection:
                return []
            
            docs = collection.order_by("updatedAt", direction="DESCENDING").stream()
            conversations = [doc.to_dict() for doc in docs]
            
            logger.info("Retrieved %d conversations for user %s", len(conversations), user_id[:8])
            return conversations
            
        except Exception as e:
            logger.error("Failed to get conversations: %s", e)
            return []
    
    def get_conversation(self, user_id: str, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Get a single conversation by ID."""
        if not self.db:
            return None
        
        try:
            collection = self._get_user_collection(user_id)
            if not collection:
                return None
            
            doc = collection.document(conversation_id).get()
            if doc.exists:
                return doc.to_dict()
            return None
            
        except Exception as e:
            logger.error("Failed to get conversation: %s", e)
            return None
    
    def create_conversation(
        self,
        user_id: str,
        conversation: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """Create a new conversation."""
        if not self.db:
            logger.error("Firestore not available")
            return None
        
        try:
            collection = self._get_user_collection(user_id)
            if not collection:
                return None
            
            conv_id = conversation.get("id")
            if not conv_id:
                logger.error("Conversation ID required")
                return None
            
            now = datetime.now(timezone.utc).isoformat()
            conversation["createdAt"] = conversation.get("createdAt", now)
            conversation["updatedAt"] = now
            conversation["userId"] = user_id
            
            collection.document(conv_id).set(conversation)
            logger.info("Created conversation %s for user %s", conv_id, user_id[:8])
            
            return conversation
            
        except Exception as e:
            logger.error("Failed to create conversation: %s", e)
            return None
    
    def update_conversation(
        self,
        user_id: str,
        conversation_id: str,
        updates: Dict[str, Any],
    ) -> bool:
        """Update a conversation."""
        if not self.db:
            return False
        
        try:
            collection = self._get_user_collection(user_id)
            if not collection:
                return False
            
            updates["updatedAt"] = datetime.now(timezone.utc).isoformat()
            collection.document(conversation_id).update(updates)
            logger.info("Updated conversation %s", conversation_id)
            return True
            
        except Exception as e:
            logger.error("Failed to update conversation: %s", e)
            return False
    
    def delete_conversation(self, user_id: str, conversation_id: str) -> bool:
        """Delete a conversation."""
        if not self.db:
            return False
        
        try:
            collection = self._get_user_collection(user_id)
            if not collection:
                return False
            
            collection.document(conversation_id).delete()
            logger.info("Deleted conversation %s", conversation_id)
            return True
            
        except Exception as e:
            logger.error("Failed to delete conversation: %s", e)
            return False
    
    def sync_all_conversations(
        self,
        user_id: str,
        conversations: List[Dict[str, Any]],
    ) -> int:
        """Full sync - replace all conversations for a user."""
        if not self.db:
            return 0
        
        try:
            collection = self._get_user_collection(user_id)
            if not collection:
                return 0
            
            # Batch write for efficiency
            batch = self.db.batch()
            
            # Get existing conversation IDs
            existing_docs = collection.stream()
            existing_ids = {doc.id for doc in existing_docs}
            
            # Add/update new conversations
            new_ids = set()
            now = datetime.now(timezone.utc).isoformat()
            
            for conv in conversations:
                conv_id = conv.get("id")
                if not conv_id:
                    continue
                
                new_ids.add(conv_id)
                conv["userId"] = user_id
                conv["updatedAt"] = now
                
                doc_ref = collection.document(conv_id)
                batch.set(doc_ref, conv, merge=True)
            
            # Delete removed conversations
            for old_id in existing_ids - new_ids:
                batch.delete(collection.document(old_id))
            
            batch.commit()
            logger.info("Synced %d conversations for user %s", len(conversations), user_id[:8])
            
            return len(conversations)
            
        except Exception as e:
            logger.error("Failed to sync conversations: %s", e)
            return 0


class ProjectsFirestoreService:
    """Manage projects in Firestore."""
    
    COLLECTION = "projects"
    
    def __init__(self):
        self.db = get_firestore_client()
    
    def _get_user_collection(self, user_id: str):
        """Get user's projects subcollection."""
        if not self.db:
            return None
        return self.db.collection("users").document(user_id).collection(self.COLLECTION)
    
    def get_all_projects(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all projects for a user."""
        if not self.db:
            return []
        
        try:
            collection = self._get_user_collection(user_id)
            if not collection:
                return []
            
            docs = collection.order_by("createdAt", direction="DESCENDING").stream()
            projects = [doc.to_dict() for doc in docs]
            
            logger.info("Retrieved %d projects for user %s", len(projects), user_id[:8])
            return projects
            
        except Exception as e:
            logger.error("Failed to get projects: %s", e)
            return []
    
    def create_project(
        self,
        user_id: str,
        project: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """Create a new project."""
        if not self.db:
            return None
        
        try:
            collection = self._get_user_collection(user_id)
            if not collection:
                return None
            
            proj_id = project.get("id")
            if not proj_id:
                return None
            
            now = datetime.now(timezone.utc).isoformat()
            project["createdAt"] = project.get("createdAt", now)
            project["userId"] = user_id
            
            collection.document(proj_id).set(project)
            logger.info("Created project %s for user %s", proj_id, user_id[:8])
            
            return project
            
        except Exception as e:
            logger.error("Failed to create project: %s", e)
            return None
    
    def update_project(
        self,
        user_id: str,
        project_id: str,
        updates: Dict[str, Any],
    ) -> bool:
        """Update a project."""
        if not self.db:
            return False
        
        try:
            collection = self._get_user_collection(user_id)
            if not collection:
                return False
            
            collection.document(project_id).update(updates)
            logger.info("Updated project %s", project_id)
            return True
            
        except Exception as e:
            logger.error("Failed to update project: %s", e)
            return False
    
    def delete_project(self, user_id: str, project_id: str) -> bool:
        """Delete a project."""
        if not self.db:
            return False
        
        try:
            collection = self._get_user_collection(user_id)
            if not collection:
                return False
            
            collection.document(project_id).delete()
            logger.info("Deleted project %s", project_id)
            return True
            
        except Exception as e:
            logger.error("Failed to delete project: %s", e)
            return False
    
    def sync_all_projects(
        self,
        user_id: str,
        projects: List[Dict[str, Any]],
    ) -> int:
        """Full sync - replace all projects for a user."""
        if not self.db:
            return 0
        
        try:
            collection = self._get_user_collection(user_id)
            if not collection:
                return 0
            
            batch = self.db.batch()
            
            # Get existing project IDs
            existing_docs = collection.stream()
            existing_ids = {doc.id for doc in existing_docs}
            
            # Add/update new projects
            new_ids = set()
            
            for proj in projects:
                proj_id = proj.get("id")
                if not proj_id:
                    continue
                
                new_ids.add(proj_id)
                proj["userId"] = user_id
                
                doc_ref = collection.document(proj_id)
                batch.set(doc_ref, proj, merge=True)
            
            # Delete removed projects
            for old_id in existing_ids - new_ids:
                batch.delete(collection.document(old_id))
            
            batch.commit()
            logger.info("Synced %d projects for user %s", len(projects), user_id[:8])
            
            return len(projects)
            
        except Exception as e:
            logger.error("Failed to sync projects: %s", e)
            return 0
    
    def add_conversation_to_project(
        self,
        user_id: str,
        project_id: str,
        conversation_id: str,
    ) -> bool:
        """Add a conversation to a project."""
        if not self.db:
            return False
        
        try:
            collection = self._get_user_collection(user_id)
            if not collection:
                return False
            
            from google.cloud.firestore import ArrayUnion
            collection.document(project_id).update({
                "conversations": ArrayUnion([conversation_id])
            })
            return True
            
        except Exception as e:
            logger.error("Failed to add conversation to project: %s", e)
            return False
    
    def remove_conversation_from_project(
        self,
        user_id: str,
        project_id: str,
        conversation_id: str,
    ) -> bool:
        """Remove a conversation from a project."""
        if not self.db:
            return False
        
        try:
            collection = self._get_user_collection(user_id)
            if not collection:
                return False
            
            from google.cloud.firestore import ArrayRemove
            collection.document(project_id).update({
                "conversations": ArrayRemove([conversation_id])
            })
            return True
            
        except Exception as e:
            logger.error("Failed to remove conversation from project: %s", e)
            return False


# Singleton instances
_conversations_service: Optional[ConversationsFirestoreService] = None
_projects_service: Optional[ProjectsFirestoreService] = None


def get_conversations_service() -> ConversationsFirestoreService:
    """Get conversations service singleton."""
    global _conversations_service
    if _conversations_service is None:
        _conversations_service = ConversationsFirestoreService()
    return _conversations_service


def get_projects_service() -> ProjectsFirestoreService:
    """Get projects service singleton."""
    global _projects_service
    if _projects_service is None:
        _projects_service = ProjectsFirestoreService()
    return _projects_service

