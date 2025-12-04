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


if SQLALCHEMY_AVAILABLE:
    class Subscription(Base):
        """Subscription model for billing."""
        __tablename__ = "subscriptions"
        
        id = Column(Integer, primary_key=True, index=True)
        user_id = Column(String(255), nullable=False, index=True)
        tier_name = Column(String(50), nullable=False, default="free")
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
    "Subscription",
    "SubscriptionStatus",
    "UsageRecord",
    "UserFeedback",
    "SQLALCHEMY_AVAILABLE",
]

