"""
Conversations Router - User conversation and project management.

This router provides endpoints for:
- CRUD operations on conversations (stored in Firestore)
- CRUD operations on projects (stored in Firestore)
- Automatic indexing to Pinecone for semantic search

All data is persistent and synced across devices/browsers.
"""

import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel

from ..services.conversations_firestore import (
    get_conversations_service,
    get_projects_service,
)
from ..memory.vector_store import get_global_vector_store, MemoryRecord
from ..feature_flags import is_feature_enabled, FeatureFlags

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/data", tags=["conversations"])


# ==============================================================================
# Request/Response Models
# ==============================================================================

class MessageData(BaseModel):
    role: str
    content: str
    timestamp: Optional[str] = None


class ConversationData(BaseModel):
    id: str
    title: str
    messages: List[MessageData] = []
    createdAt: Optional[str] = None
    updatedAt: Optional[str] = None
    model: Optional[str] = None
    pinned: bool = False
    archived: bool = False
    projectId: Optional[str] = None


class ProjectData(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    conversations: List[str] = []
    createdAt: Optional[str] = None
    color: Optional[str] = None
    icon: Optional[str] = None
    pinned: bool = False
    archived: bool = False


class ConversationSyncRequest(BaseModel):
    conversations: List[ConversationData]


class ProjectSyncRequest(BaseModel):
    projects: List[ProjectData]


class ConversationCreateRequest(BaseModel):
    conversation: ConversationData


class ConversationUpdateRequest(BaseModel):
    conversationId: str
    updates: Dict[str, Any]


class ProjectCreateRequest(BaseModel):
    project: ProjectData


class ProjectUpdateRequest(BaseModel):
    projectId: str
    updates: Dict[str, Any]


class ProjectConversationRequest(BaseModel):
    projectId: str
    conversationId: str


class ConversationsResponse(BaseModel):
    conversations: List[Dict[str, Any]]
    count: int
    storage: str = "firestore"


class ProjectsResponse(BaseModel):
    projects: List[Dict[str, Any]]
    count: int
    storage: str = "firestore"


class SuccessResponse(BaseModel):
    success: bool
    message: Optional[str] = None


# ==============================================================================
# Helper Functions
# ==============================================================================

def get_user_id_from_header(x_user_id: Optional[str] = Header(None)) -> str:
    """Extract and validate user ID from header."""
    if not x_user_id:
        raise HTTPException(status_code=401, detail="User ID required")
    return x_user_id


async def index_conversation_to_pinecone(user_id: str, conversation: Dict[str, Any]):
    """Index conversation Q&A pairs to Pinecone for semantic search."""
    if not is_feature_enabled(FeatureFlags.VECTOR_MEMORY):
        return
    
    try:
        vector_store = get_global_vector_store()
        namespace = f"user_{user_id}"
        
        messages = conversation.get("messages", [])
        conv_id = conversation.get("id", "")
        conv_title = conversation.get("title", "")
        
        records = []
        for i in range(len(messages) - 1):
            msg = messages[i]
            next_msg = messages[i + 1]
            
            # Index Q&A pairs
            if msg.get("role") == "user" and next_msg.get("role") == "assistant":
                question = msg.get("content", "")
                answer = next_msg.get("content", "")
                
                record = MemoryRecord(
                    id=f"{conv_id}_{i}",
                    text=answer,
                    metadata={
                        "conversation_id": conv_id,
                        "conversation_title": conv_title[:100],
                        "question": question[:500],
                        "user_id": user_id,
                        "type": "qa_pair",
                    }
                )
                records.append(record)
        
        if records:
            vector_store.upsert(records, namespace=namespace)
            logger.debug("Indexed %d Q&A pairs for conversation %s", len(records), conv_id[:8])
            
    except Exception as e:
        logger.warning("Failed to index conversation to Pinecone: %s", e)
        # Don't fail the main operation


# ==============================================================================
# Conversations Endpoints
# ==============================================================================

@router.get("/conversations", response_model=ConversationsResponse)
async def get_conversations(x_user_id: str = Header(...)):
    """Get all conversations for the authenticated user."""
    try:
        service = get_conversations_service()
        conversations = service.get_all_conversations(x_user_id)
        
        logger.info("GET conversations for user %s: %d items", x_user_id[:8], len(conversations))
        
        return ConversationsResponse(
            conversations=conversations,
            count=len(conversations),
            storage="firestore"
        )
        
    except Exception as e:
        logger.error("Failed to get conversations: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/conversations/sync", response_model=SuccessResponse)
async def sync_conversations(
    request: ConversationSyncRequest,
    x_user_id: str = Header(...),
):
    """Full sync - replace all conversations for the user."""
    try:
        service = get_conversations_service()
        
        # Convert Pydantic models to dicts
        conversations = [conv.model_dump() for conv in request.conversations]
        
        count = service.sync_all_conversations(x_user_id, conversations)
        
        # Index all conversations to Pinecone
        for conv in conversations:
            await index_conversation_to_pinecone(x_user_id, conv)
        
        logger.info("SYNC conversations for user %s: %d items", x_user_id[:8], count)
        
        return SuccessResponse(
            success=True,
            message=f"Synced {count} conversations"
        )
        
    except Exception as e:
        logger.error("Failed to sync conversations: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/conversations/create", response_model=SuccessResponse)
async def create_conversation(
    request: ConversationCreateRequest,
    x_user_id: str = Header(...),
):
    """Create a new conversation."""
    try:
        service = get_conversations_service()
        conv_data = request.conversation.model_dump()
        
        result = service.create_conversation(x_user_id, conv_data)
        
        if result:
            await index_conversation_to_pinecone(x_user_id, result)
            
            logger.info("CREATE conversation %s for user %s", result.get("id", "")[:8], x_user_id[:8])
            return SuccessResponse(success=True, message="Conversation created")
        else:
            return SuccessResponse(success=False, message="Failed to create conversation")
            
    except Exception as e:
        logger.error("Failed to create conversation: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/conversations/update", response_model=SuccessResponse)
async def update_conversation(
    request: ConversationUpdateRequest,
    x_user_id: str = Header(...),
):
    """Update a conversation."""
    try:
        service = get_conversations_service()
        
        success = service.update_conversation(
            x_user_id,
            request.conversationId,
            request.updates,
        )
        
        if success and "messages" in request.updates:
            # Re-index if messages changed
            conv = service.get_conversation(x_user_id, request.conversationId)
            if conv:
                await index_conversation_to_pinecone(x_user_id, conv)
        
        logger.info("UPDATE conversation %s for user %s", request.conversationId[:8], x_user_id[:8])
        return SuccessResponse(success=success)
        
    except Exception as e:
        logger.error("Failed to update conversation: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/conversations/delete", response_model=SuccessResponse)
async def delete_conversation(
    conversationId: str,
    x_user_id: str = Header(...),
):
    """Delete a conversation."""
    try:
        service = get_conversations_service()
        success = service.delete_conversation(x_user_id, conversationId)
        
        # TODO: Also delete from Pinecone
        
        logger.info("DELETE conversation %s for user %s", conversationId[:8], x_user_id[:8])
        return SuccessResponse(success=success)
        
    except Exception as e:
        logger.error("Failed to delete conversation: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# ==============================================================================
# Projects Endpoints
# ==============================================================================

@router.get("/projects", response_model=ProjectsResponse)
async def get_projects(x_user_id: str = Header(...)):
    """Get all projects for the authenticated user."""
    try:
        service = get_projects_service()
        projects = service.get_all_projects(x_user_id)
        
        logger.info("GET projects for user %s: %d items", x_user_id[:8], len(projects))
        
        return ProjectsResponse(
            projects=projects,
            count=len(projects),
            storage="firestore"
        )
        
    except Exception as e:
        logger.error("Failed to get projects: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/projects/sync", response_model=SuccessResponse)
async def sync_projects(
    request: ProjectSyncRequest,
    x_user_id: str = Header(...),
):
    """Full sync - replace all projects for the user."""
    try:
        service = get_projects_service()
        
        projects = [proj.model_dump() for proj in request.projects]
        count = service.sync_all_projects(x_user_id, projects)
        
        logger.info("SYNC projects for user %s: %d items", x_user_id[:8], count)
        
        return SuccessResponse(
            success=True,
            message=f"Synced {count} projects"
        )
        
    except Exception as e:
        logger.error("Failed to sync projects: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/projects/create", response_model=SuccessResponse)
async def create_project(
    request: ProjectCreateRequest,
    x_user_id: str = Header(...),
):
    """Create a new project."""
    try:
        service = get_projects_service()
        proj_data = request.project.model_dump()
        
        result = service.create_project(x_user_id, proj_data)
        
        if result:
            logger.info("CREATE project %s for user %s", result.get("id", "")[:8], x_user_id[:8])
            return SuccessResponse(success=True, message="Project created")
        else:
            return SuccessResponse(success=False, message="Failed to create project")
            
    except Exception as e:
        logger.error("Failed to create project: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/projects/update", response_model=SuccessResponse)
async def update_project(
    request: ProjectUpdateRequest,
    x_user_id: str = Header(...),
):
    """Update a project."""
    try:
        service = get_projects_service()
        
        success = service.update_project(
            x_user_id,
            request.projectId,
            request.updates,
        )
        
        logger.info("UPDATE project %s for user %s", request.projectId[:8], x_user_id[:8])
        return SuccessResponse(success=success)
        
    except Exception as e:
        logger.error("Failed to update project: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/projects/delete", response_model=SuccessResponse)
async def delete_project(
    projectId: str,
    x_user_id: str = Header(...),
):
    """Delete a project."""
    try:
        service = get_projects_service()
        success = service.delete_project(x_user_id, projectId)
        
        logger.info("DELETE project %s for user %s", projectId[:8], x_user_id[:8])
        return SuccessResponse(success=success)
        
    except Exception as e:
        logger.error("Failed to delete project: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/projects/add-conversation", response_model=SuccessResponse)
async def add_conversation_to_project(
    request: ProjectConversationRequest,
    x_user_id: str = Header(...),
):
    """Add a conversation to a project."""
    try:
        service = get_projects_service()
        success = service.add_conversation_to_project(
            x_user_id,
            request.projectId,
            request.conversationId,
        )
        
        return SuccessResponse(success=success)
        
    except Exception as e:
        logger.error("Failed to add conversation to project: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/projects/remove-conversation", response_model=SuccessResponse)
async def remove_conversation_from_project(
    request: ProjectConversationRequest,
    x_user_id: str = Header(...),
):
    """Remove a conversation from a project."""
    try:
        service = get_projects_service()
        success = service.remove_conversation_from_project(
            x_user_id,
            request.projectId,
            request.conversationId,
        )
        
        return SuccessResponse(success=success)
        
    except Exception as e:
        logger.error("Failed to remove conversation from project: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

