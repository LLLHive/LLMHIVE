"""Collaboration Models for LLMHive.

This module defines database models and Pydantic schemas for the collaboration
feature, enabling multi-user shared sessions with persistent state.

Database Models:
- CollaborativeSession: Persistent session with participants and access control
- SessionMessage: Messages within a collaborative session
- SessionParticipant: Participants and their permissions

Pydantic Schemas:
- Request/Response models for API endpoints
"""
from __future__ import annotations

import datetime
import enum
import secrets
import uuid
import logging
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Try to import SQLAlchemy
try:
    from sqlalchemy import Column, Integer, String, DateTime, Float, Boolean, Enum, Text, ForeignKey
    from sqlalchemy.orm import relationship
    from . import Base, SQLALCHEMY_AVAILABLE
except ImportError:
    SQLALCHEMY_AVAILABLE = False
    Base = object  # type: ignore
    Column = Integer = String = DateTime = Float = Boolean = Enum = Text = ForeignKey = None  # type: ignore
    relationship = None  # type: ignore


# ==============================================================================
# Enums
# ==============================================================================

class SessionAccessLevel(str, enum.Enum):
    """Access level for session participants."""
    OWNER = "owner"          # Full control, can delete session
    EDITOR = "editor"        # Can send messages and modify
    VIEWER = "viewer"        # Read-only access


class SessionStatus(str, enum.Enum):
    """Status of a collaborative session."""
    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"


# ==============================================================================
# Database Models (SQLAlchemy)
# ==============================================================================

if SQLALCHEMY_AVAILABLE:
    class CollaborativeSession(Base):
        """A collaborative session that multiple users can join.
        
        Stores session metadata and provides access control via invite tokens.
        """
        __tablename__ = "collaborative_sessions"
        
        id = Column(Integer, primary_key=True, index=True)
        session_id = Column(String(255), unique=True, nullable=False, index=True)
        
        # Metadata
        title = Column(String(500), nullable=True)
        description = Column(Text, nullable=True)
        status = Column(Enum(SessionStatus), nullable=False, default=SessionStatus.ACTIVE)
        
        # Owner info
        owner_user_id = Column(String(255), nullable=False, index=True)
        
        # Access control
        invite_token = Column(String(255), unique=True, nullable=False, index=True)
        is_public = Column(Boolean, default=False)  # Anyone with link can join
        max_participants = Column(Integer, default=10)
        
        # Timestamps
        created_at = Column(DateTime, default=datetime.datetime.utcnow)
        updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
        last_activity_at = Column(DateTime, default=datetime.datetime.utcnow)
        
        # Relationships
        # messages = relationship("SessionMessage", back_populates="session")
        # participants = relationship("SessionParticipant", back_populates="session")
        
        def __repr__(self):
            return f"<CollaborativeSession(id={self.session_id}, owner={self.owner_user_id})>"


    class SessionMessage(Base):
        """A message within a collaborative session."""
        __tablename__ = "session_messages"
        
        id = Column(Integer, primary_key=True, index=True)
        session_id = Column(String(255), nullable=False, index=True)
        
        # Message content
        message_type = Column(String(50), nullable=False, default="user")  # user, system, ai
        content = Column(Text, nullable=False)
        metadata_json = Column(Text, nullable=True)  # JSON for additional data
        
        # Sender info
        sender_user_id = Column(String(255), nullable=True)
        sender_name = Column(String(255), nullable=True)
        
        # Ordering
        sequence_number = Column(Integer, nullable=False, index=True)
        
        # Timestamps
        created_at = Column(DateTime, default=datetime.datetime.utcnow)
        
        # Relationships
        # session = relationship("CollaborativeSession", back_populates="messages")
        
        def __repr__(self):
            return f"<SessionMessage(id={self.id}, session={self.session_id}, type={self.message_type})>"


    class SessionParticipant(Base):
        """A participant in a collaborative session."""
        __tablename__ = "session_participants"
        
        id = Column(Integer, primary_key=True, index=True)
        session_id = Column(String(255), nullable=False, index=True)
        user_id = Column(String(255), nullable=False, index=True)
        
        # Participant info
        display_name = Column(String(255), nullable=True)
        access_level = Column(Enum(SessionAccessLevel), nullable=False, default=SessionAccessLevel.VIEWER)
        
        # Status
        is_active = Column(Boolean, default=True)
        last_seen_at = Column(DateTime, default=datetime.datetime.utcnow)
        
        # Timestamps
        joined_at = Column(DateTime, default=datetime.datetime.utcnow)
        
        # Relationships
        # session = relationship("CollaborativeSession", back_populates="participants")
        
        def __repr__(self):
            return f"<SessionParticipant(user={self.user_id}, session={self.session_id})>"

else:
    # Stub classes for type hints
    class CollaborativeSession:
        id: int
        session_id: str
        title: Optional[str]
        description: Optional[str]
        status: SessionStatus
        owner_user_id: str
        invite_token: str
        is_public: bool
        max_participants: int
        created_at: datetime.datetime
        updated_at: datetime.datetime
        last_activity_at: datetime.datetime
    
    class SessionMessage:
        id: int
        session_id: str
        message_type: str
        content: str
        metadata_json: Optional[str]
        sender_user_id: Optional[str]
        sender_name: Optional[str]
        sequence_number: int
        created_at: datetime.datetime
    
    class SessionParticipant:
        id: int
        session_id: str
        user_id: str
        display_name: Optional[str]
        access_level: SessionAccessLevel
        is_active: bool
        last_seen_at: datetime.datetime
        joined_at: datetime.datetime


# ==============================================================================
# Pydantic Request/Response Schemas
# ==============================================================================

class CreateSessionRequest(BaseModel):
    """Request to create a new collaborative session."""
    title: Optional[str] = Field(None, max_length=500, description="Session title")
    description: Optional[str] = Field(None, description="Session description")
    is_public: bool = Field(False, description="Allow anyone with link to join")
    max_participants: int = Field(10, ge=2, le=100, description="Maximum participants")


class CreateSessionResponse(BaseModel):
    """Response after creating a session."""
    session_id: str
    invite_token: str
    invite_url: str
    title: Optional[str]
    created_at: str


class JoinSessionRequest(BaseModel):
    """Request to join a collaborative session."""
    invite_token: str = Field(..., min_length=8, description="Invite token from URL")
    display_name: Optional[str] = Field(None, max_length=100, description="Display name in session")


class JoinSessionResponse(BaseModel):
    """Response after joining a session."""
    session_id: str
    title: Optional[str]
    access_level: str
    participant_count: int
    message_count: int


class SessionInfoResponse(BaseModel):
    """Information about a collaborative session."""
    session_id: str
    title: Optional[str]
    description: Optional[str]
    status: str
    owner_user_id: str
    is_public: bool
    participant_count: int
    message_count: int
    created_at: str
    last_activity_at: str


class SessionMessageSchema(BaseModel):
    """Schema for a session message."""
    id: int
    message_type: str
    content: str
    sender_user_id: Optional[str]
    sender_name: Optional[str]
    created_at: str
    metadata: Optional[Dict[str, Any]] = None


class SendMessageRequest(BaseModel):
    """Request to send a message in a session."""
    content: str = Field(..., min_length=1, max_length=10000, description="Message content")
    message_type: str = Field("user", description="Message type: user, system, ai")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class SessionHistoryResponse(BaseModel):
    """Response with session message history."""
    session_id: str
    messages: List[SessionMessageSchema]
    total_messages: int
    has_more: bool


class ParticipantSchema(BaseModel):
    """Schema for a session participant."""
    user_id: str
    display_name: Optional[str]
    access_level: str
    is_active: bool
    joined_at: str
    last_seen_at: str


class SessionParticipantsResponse(BaseModel):
    """Response with session participants."""
    session_id: str
    participants: List[ParticipantSchema]
    total: int


# ==============================================================================
# Helper Functions
# ==============================================================================

def generate_session_id() -> str:
    """Generate a unique session ID."""
    return str(uuid.uuid4())


def generate_invite_token() -> str:
    """Generate a secure invite token."""
    return secrets.token_urlsafe(24)


def build_invite_url(base_url: str, invite_token: str) -> str:
    """Build a shareable invite URL."""
    return f"{base_url}/collaborate/join?token={invite_token}"


# ==============================================================================
# Exports
# ==============================================================================

__all__ = [
    # Enums
    "SessionAccessLevel",
    "SessionStatus",
    # Database models
    "CollaborativeSession",
    "SessionMessage",
    "SessionParticipant",
    # Pydantic schemas
    "CreateSessionRequest",
    "CreateSessionResponse",
    "JoinSessionRequest",
    "JoinSessionResponse",
    "SessionInfoResponse",
    "SessionMessageSchema",
    "SendMessageRequest",
    "SessionHistoryResponse",
    "ParticipantSchema",
    "SessionParticipantsResponse",
    # Helpers
    "generate_session_id",
    "generate_invite_token",
    "build_invite_url",
]

