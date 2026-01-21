"""Database models for LLMHive.

This module defines SQLAlchemy models for:
- Subscriptions and billing
- Usage tracking
- User data

When database is not available, these models can still be used
for type hints and data validation.
"""
from __future__ import annotations

import datetime
import enum
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Try to import SQLAlchemy
try:
    from sqlalchemy import Column, Integer, String, DateTime, Float, Boolean, Enum, Text
    from sqlalchemy.orm import declarative_base  # Updated import (SQLAlchemy 2.0+)
    SQLALCHEMY_AVAILABLE = True
    Base = declarative_base()
except ImportError:
    SQLALCHEMY_AVAILABLE = False
    Base = object  # type: ignore
    # Create stub column types for type hints
    Column = None  # type: ignore
    Integer = String = DateTime = Float = Boolean = Enum = Text = None  # type: ignore
    logger.warning("SQLAlchemy not available, using stub models")


class SubscriptionStatus(str, enum.Enum):
    """Status of a subscription."""
    ACTIVE = "active"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    PAST_DUE = "past_due"
    TRIALING = "trialing"
    PENDING = "pending"


class AccountTier(str, enum.Enum):
    """User account tier levels - SIMPLIFIED 4-TIER STRUCTURE (January 2026)."""
    LITE = "lite"           # Entry-level: $9.99/mo
    PRO = "pro"             # Power users: $29.99/mo
    ENTERPRISE = "enterprise"  # Organizations: $35/seat/mo (min 5 seats)
    MAXIMUM = "maximum"     # Mission-critical: $499/mo
    # Legacy fallback for unsubscribed users
    FREE = "free"           # Maps to LITE with trial limits


class FeedbackOutcome(str, enum.Enum):
    """Outcome of model feedback."""
    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"
    TIMEOUT = "timeout"
    ERROR = "error"


if SQLALCHEMY_AVAILABLE:
    class User(Base):
        """User model."""
        __tablename__ = "users"
        
        id = Column(Integer, primary_key=True, index=True)
        user_id = Column(String(255), unique=True, nullable=False, index=True)
        email = Column(String(255), nullable=True)
        account_tier = Column(Enum(AccountTier), nullable=False, default=AccountTier.LITE)
        created_at = Column(DateTime, default=datetime.datetime.utcnow)
        updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
        
        def __repr__(self):
            return f"<User(id={self.id}, user_id={self.user_id}, tier={self.account_tier})>"


    class Conversation(Base):
        """Conversation model for chat history."""
        __tablename__ = "conversations"
        
        id = Column(Integer, primary_key=True, index=True)
        user_id = Column(String(255), nullable=False, index=True)
        topic = Column(String(500), nullable=True)
        created_at = Column(DateTime, default=datetime.datetime.utcnow)
        updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
        
        def __repr__(self):
            return f"<Conversation(id={self.id}, user_id={self.user_id}, topic={self.topic})>"


    class MemoryEntry(Base):
        """Memory entry for persistent storage."""
        __tablename__ = "memory_entries"
        
        id = Column(Integer, primary_key=True, index=True)
        user_id = Column(String(255), nullable=False, index=True)
        conversation_id = Column(Integer, nullable=True)
        content = Column(Text, nullable=False)
        metadata_json = Column(Text, nullable=True)  # JSON string
        is_encrypted = Column(Boolean, default=False)
        created_at = Column(DateTime, default=datetime.datetime.utcnow)
        expires_at = Column(DateTime, nullable=True)
        
        def __repr__(self):
            return f"<MemoryEntry(id={self.id}, user_id={self.user_id})>"


    class KnowledgeDocument(Base):
        """Knowledge document for RAG."""
        __tablename__ = "knowledge_documents"
        
        id = Column(Integer, primary_key=True, index=True)
        user_id = Column(String(255), nullable=True, index=True)
        title = Column(String(500), nullable=True)
        content = Column(Text, nullable=False)
        source = Column(String(500), nullable=True)
        embedding_id = Column(String(255), nullable=True)  # Vector store ID
        created_at = Column(DateTime, default=datetime.datetime.utcnow)
        
        def __repr__(self):
            return f"<KnowledgeDocument(id={self.id}, title={self.title})>"


    class Task(Base):
        """Task model for orchestration tracking."""
        __tablename__ = "tasks"
        
        id = Column(Integer, primary_key=True, index=True)
        session_id = Column(String(255), nullable=True, index=True)
        query = Column(Text, nullable=False)
        status = Column(String(50), default="pending")
        created_at = Column(DateTime, default=datetime.datetime.utcnow)
        completed_at = Column(DateTime, nullable=True)
        
        def __repr__(self):
            return f"<Task(id={self.id}, status={self.status})>"


    class ModelFeedback(Base):
        """Model feedback for performance tracking."""
        __tablename__ = "model_feedback"
        
        id = Column(Integer, primary_key=True, index=True)
        task_id = Column(Integer, nullable=True)
        session_id = Column(String(255), nullable=True)
        model_name = Column(String(100), nullable=False)
        outcome = Column(Enum(FeedbackOutcome), nullable=False)
        was_used_in_final = Column(Boolean, default=False)
        response_time_ms = Column(Float, nullable=True)
        token_usage = Column(Integer, nullable=True)
        confidence_score = Column(Float, nullable=True)
        quality_score = Column(Float, nullable=True)
        notes = Column(Text, nullable=True)
        created_at = Column(DateTime, default=datetime.datetime.utcnow)
        
        def __repr__(self):
            return f"<ModelFeedback(id={self.id}, model={self.model_name}, outcome={self.outcome})>"


    class ModelMetric(Base):
        """Aggregate model metrics."""
        __tablename__ = "model_metrics"
        
        id = Column(Integer, primary_key=True, index=True)
        model_name = Column(String(100), unique=True, nullable=False, index=True)
        total_calls = Column(Integer, default=0)
        success_count = Column(Integer, default=0)
        failure_count = Column(Integer, default=0)
        avg_response_time_ms = Column(Float, default=0.0)
        avg_quality_score = Column(Float, default=0.0)
        updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
        
        def __repr__(self):
            return f"<ModelMetric(model={self.model_name}, calls={self.total_calls})>"


    class Subscription(Base):
        """Subscription model for billing."""
        __tablename__ = "subscriptions"
        
        id = Column(Integer, primary_key=True, index=True)
        user_id = Column(String(255), nullable=False, index=True)
        tier_name = Column(String(50), nullable=False, default="lite")
        status = Column(Enum(SubscriptionStatus), nullable=False, default=SubscriptionStatus.ACTIVE)
        billing_cycle = Column(String(20), default="monthly")  # monthly, yearly
        
        # Stripe integration
        stripe_customer_id = Column(String(255), nullable=True)
        stripe_subscription_id = Column(String(255), nullable=True, unique=True)
        
        # Period tracking
        current_period_start = Column(DateTime, nullable=True)
        current_period_end = Column(DateTime, nullable=True)
        
        # Timestamps
        created_at = Column(DateTime, default=datetime.datetime.utcnow)
        updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
        cancelled_at = Column(DateTime, nullable=True)
        
        def __repr__(self):
            return f"<Subscription(id={self.id}, user_id={self.user_id}, tier={self.tier_name}, status={self.status})>"


    class UsageRecord(Base):
        """Usage tracking model."""
        __tablename__ = "usage_records"
        
        id = Column(Integer, primary_key=True, index=True)
        user_id = Column(String(255), nullable=False, index=True)
        subscription_id = Column(Integer, nullable=True)
        
        # Usage metrics
        tokens_used = Column(Integer, default=0)
        requests_count = Column(Integer, default=0)
        cost_usd = Column(Float, default=0.0)
        
        # Period
        period_start = Column(DateTime, nullable=False)
        period_end = Column(DateTime, nullable=False)
        
        # Timestamps
        created_at = Column(DateTime, default=datetime.datetime.utcnow)
        updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
        
        def __repr__(self):
            return f"<UsageRecord(id={self.id}, user_id={self.user_id}, tokens={self.tokens_used})>"


    class UserFeedback(Base):
        """User feedback model for RLHF."""
        __tablename__ = "user_feedback"
        
        id = Column(Integer, primary_key=True, index=True)
        user_id = Column(String(255), nullable=True)
        query = Column(Text, nullable=False)
        answer = Column(Text, nullable=False)
        feedback_type = Column(String(50), nullable=False)  # thumbs_up, thumbs_down, rating, etc.
        rating = Column(Float, nullable=True)  # 0-1 scale
        model_used = Column(String(100), nullable=True)
        created_at = Column(DateTime, default=datetime.datetime.utcnow)
        
        def __repr__(self):
            return f"<UserFeedback(id={self.id}, type={self.feedback_type}, rating={self.rating})>"

else:
    # Stub classes for when SQLAlchemy is not available
    class User:
        """Stub User class for type hints."""
        id: int
        user_id: str
        email: Optional[str]
        account_tier: AccountTier
        created_at: datetime.datetime
        updated_at: datetime.datetime
    
    class Conversation:
        """Stub Conversation class for type hints."""
        id: int
        user_id: str
        topic: Optional[str]
        created_at: datetime.datetime
        updated_at: datetime.datetime
    
    class MemoryEntry:
        """Stub MemoryEntry class for type hints."""
        id: int
        user_id: str
        conversation_id: Optional[int]
        content: str
        metadata_json: Optional[str]
        is_encrypted: bool
        created_at: datetime.datetime
        expires_at: Optional[datetime.datetime]
    
    class KnowledgeDocument:
        """Stub KnowledgeDocument class for type hints."""
        id: int
        user_id: Optional[str]
        title: Optional[str]
        content: str
        source: Optional[str]
        embedding_id: Optional[str]
        created_at: datetime.datetime
    
    class Task:
        """Stub Task class for type hints."""
        id: int
        session_id: Optional[str]
        query: str
        status: str
        created_at: datetime.datetime
        completed_at: Optional[datetime.datetime]
    
    class ModelFeedback:
        """Stub ModelFeedback class for type hints."""
        id: int
        task_id: Optional[int]
        session_id: Optional[str]
        model_name: str
        outcome: FeedbackOutcome
        was_used_in_final: bool
        response_time_ms: Optional[float]
        token_usage: Optional[int]
        confidence_score: Optional[float]
        quality_score: Optional[float]
        notes: Optional[str]
        created_at: datetime.datetime
    
    class ModelMetric:
        """Stub ModelMetric class for type hints."""
        id: int
        model_name: str
        total_calls: int
        success_count: int
        failure_count: int
        avg_response_time_ms: float
        avg_quality_score: float
        updated_at: datetime.datetime
    
    class Subscription:
        """Stub Subscription class for type hints."""
        id: int
        user_id: str
        tier_name: str
        status: SubscriptionStatus
        billing_cycle: str
        stripe_customer_id: Optional[str]
        stripe_subscription_id: Optional[str]
        current_period_start: Optional[datetime.datetime]
        current_period_end: Optional[datetime.datetime]
        created_at: datetime.datetime
        updated_at: datetime.datetime
        cancelled_at: Optional[datetime.datetime]
    
    class UsageRecord:
        """Stub UsageRecord class for type hints."""
        id: int
        user_id: str
        subscription_id: Optional[int]
        tokens_used: int
        requests_count: int
        cost_usd: float
        period_start: datetime.datetime
        period_end: datetime.datetime
    
    class UserFeedback:
        """Stub UserFeedback class for type hints."""
        id: int
        user_id: Optional[str]
        query: str
        answer: str
        feedback_type: str
        rating: Optional[float]
        model_used: Optional[str]
        created_at: datetime.datetime


# Export all models
__all__ = [
    "Base",
    "SQLALCHEMY_AVAILABLE",
    # Enums
    "AccountTier",
    "FeedbackOutcome",
    "SubscriptionStatus",
    # Core models
    "User",
    "Conversation",
    "MemoryEntry",
    "KnowledgeDocument",
    "Task",
    # Feedback models
    "ModelFeedback",
    "ModelMetric",
    # Billing models
    "Subscription",
    "UsageRecord",
    "UserFeedback",
]

