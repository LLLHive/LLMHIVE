"""Firestore database integration for LLMHive.

This module provides Firestore connectivity for:
- Subscriptions and billing
- User data
- Usage tracking

No Vertex AI required - we use Pinecone for embeddings.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Try to import Firestore
try:
    from google.cloud import firestore
    FIRESTORE_AVAILABLE = True
except ImportError:
    FIRESTORE_AVAILABLE = False
    firestore = None  # type: ignore
    logger.warning("google-cloud-firestore not installed. Run: pip install google-cloud-firestore")


# Global Firestore client
_db: Optional[Any] = None


def get_firestore_client():
    """Get or create Firestore client."""
    global _db
    
    if not FIRESTORE_AVAILABLE:
        logger.error("Firestore not available - install google-cloud-firestore")
        return None
    
    if _db is None:
        try:
            # Uses default credentials from environment (GOOGLE_APPLICATION_CREDENTIALS)
            # or from the service account running in Cloud Run
            project_id = os.getenv("GOOGLE_CLOUD_PROJECT", os.getenv("GCP_PROJECT", "llmhive-orchestrator"))
            _db = firestore.Client(project=project_id)
            logger.info("Firestore client initialized for project: %s", project_id)
        except Exception as e:
            logger.error("Failed to initialize Firestore: %s", e)
            return None
    
    return _db


# ==============================================================================
# Subscription Operations
# ==============================================================================

class FirestoreSubscriptionService:
    """Manage subscriptions in Firestore."""
    
    COLLECTION = "subscriptions"
    
    def __init__(self):
        self.db = get_firestore_client()
    
    def create_subscription(
        self,
        user_id: str,
        tier_name: str = "free",
        billing_cycle: str = "monthly",
        stripe_customer_id: Optional[str] = None,
        stripe_subscription_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Create a new subscription."""
        if not self.db:
            logger.error("Firestore not available")
            return None
        
        try:
            doc_ref = self.db.collection(self.COLLECTION).document()
            
            subscription_data = {
                "id": doc_ref.id,
                "user_id": user_id,
                "tier_name": tier_name,
                "status": "active",
                "billing_cycle": billing_cycle,
                "stripe_customer_id": stripe_customer_id,
                "stripe_subscription_id": stripe_subscription_id,
                "current_period_start": datetime.now(timezone.utc),
                "current_period_end": None,
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
                "cancelled_at": None,
            }
            
            doc_ref.set(subscription_data)
            logger.info("Created subscription %s for user %s (tier: %s)", doc_ref.id, user_id, tier_name)
            
            return subscription_data
            
        except Exception as e:
            logger.error("Failed to create subscription: %s", e)
            return None
    
    def get_subscription(self, subscription_id: str) -> Optional[Dict[str, Any]]:
        """Get a subscription by ID."""
        if not self.db:
            return None
        
        try:
            doc = self.db.collection(self.COLLECTION).document(subscription_id).get()
            if doc.exists:
                return doc.to_dict()
            return None
        except Exception as e:
            logger.error("Failed to get subscription: %s", e)
            return None
    
    def get_user_subscription(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get the active subscription for a user."""
        if not self.db:
            return None
        
        try:
            query = (
                self.db.collection(self.COLLECTION)
                .where("user_id", "==", user_id)
                .where("status", "==", "active")
                .order_by("created_at", direction=firestore.Query.DESCENDING)
                .limit(1)
            )
            
            docs = query.stream()
            for doc in docs:
                return doc.to_dict()
            
            return None
            
        except Exception as e:
            logger.error("Failed to get user subscription: %s", e)
            return None
    
    def get_subscription_by_stripe_id(self, stripe_subscription_id: str) -> Optional[Dict[str, Any]]:
        """Get subscription by Stripe subscription ID."""
        if not self.db:
            return None
        
        try:
            query = (
                self.db.collection(self.COLLECTION)
                .where("stripe_subscription_id", "==", stripe_subscription_id)
                .limit(1)
            )
            
            docs = query.stream()
            for doc in docs:
                return doc.to_dict()
            
            return None
            
        except Exception as e:
            logger.error("Failed to get subscription by Stripe ID: %s", e)
            return None
    
    def update_subscription(
        self,
        subscription_id: str,
        updates: Dict[str, Any],
    ) -> bool:
        """Update a subscription."""
        if not self.db:
            return False
        
        try:
            updates["updated_at"] = datetime.now(timezone.utc)
            self.db.collection(self.COLLECTION).document(subscription_id).update(updates)
            logger.info("Updated subscription %s", subscription_id)
            return True
        except Exception as e:
            logger.error("Failed to update subscription: %s", e)
            return False
    
    def cancel_subscription(self, subscription_id: str) -> bool:
        """Cancel a subscription."""
        return self.update_subscription(subscription_id, {
            "status": "cancelled",
            "cancelled_at": datetime.now(timezone.utc),
        })
    
    def update_subscription_status(self, subscription_id: str, status: str) -> bool:
        """Update subscription status."""
        return self.update_subscription(subscription_id, {"status": status})
    
    def update_subscription_period(
        self,
        subscription_id: str,
        period_start: datetime,
        period_end: datetime,
    ) -> bool:
        """Update subscription period dates."""
        return self.update_subscription(subscription_id, {
            "current_period_start": period_start,
            "current_period_end": period_end,
        })


# ==============================================================================
# Usage Tracking
# ==============================================================================

class FirestoreUsageService:
    """Track usage in Firestore."""
    
    COLLECTION = "usage_records"
    
    def __init__(self):
        self.db = get_firestore_client()
    
    def record_usage(
        self,
        user_id: str,
        tokens_used: int = 0,
        requests_count: int = 1,
        cost_usd: float = 0.0,
        model_used: Optional[str] = None,
    ) -> bool:
        """Record usage for a user."""
        if not self.db:
            return False
        
        try:
            doc_ref = self.db.collection(self.COLLECTION).document()
            
            usage_data = {
                "id": doc_ref.id,
                "user_id": user_id,
                "tokens_used": tokens_used,
                "requests_count": requests_count,
                "cost_usd": cost_usd,
                "model_used": model_used,
                "timestamp": datetime.now(timezone.utc),
            }
            
            doc_ref.set(usage_data)
            return True
            
        except Exception as e:
            logger.error("Failed to record usage: %s", e)
            return False
    
    def get_user_usage(
        self,
        user_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Get aggregated usage for a user."""
        if not self.db:
            return {"tokens_used": 0, "requests_count": 0, "cost_usd": 0.0}
        
        try:
            query = self.db.collection(self.COLLECTION).where("user_id", "==", user_id)
            
            if start_date:
                query = query.where("timestamp", ">=", start_date)
            if end_date:
                query = query.where("timestamp", "<=", end_date)
            
            total_tokens = 0
            total_requests = 0
            total_cost = 0.0
            
            for doc in query.stream():
                data = doc.to_dict()
                total_tokens += data.get("tokens_used", 0)
                total_requests += data.get("requests_count", 0)
                total_cost += data.get("cost_usd", 0.0)
            
            return {
                "tokens_used": total_tokens,
                "requests_count": total_requests,
                "cost_usd": total_cost,
            }
            
        except Exception as e:
            logger.error("Failed to get user usage: %s", e)
            return {"tokens_used": 0, "requests_count": 0, "cost_usd": 0.0}


# ==============================================================================
# User Feedback (for RLHF)
# ==============================================================================

class FirestoreFeedbackService:
    """Store user feedback for RLHF training.
    
    Note: The actual embeddings are stored in Pinecone.
    This stores the raw feedback data for analysis.
    """
    
    COLLECTION = "user_feedback"
    
    def __init__(self):
        self.db = get_firestore_client()
    
    def record_feedback(
        self,
        query: str,
        answer: str,
        feedback_type: str,  # thumbs_up, thumbs_down, rating
        rating: Optional[float] = None,
        user_id: Optional[str] = None,
        model_used: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> Optional[str]:
        """Record user feedback on an answer."""
        if not self.db:
            return None
        
        try:
            doc_ref = self.db.collection(self.COLLECTION).document()
            
            feedback_data = {
                "id": doc_ref.id,
                "query": query,
                "answer": answer,
                "feedback_type": feedback_type,
                "rating": rating,
                "user_id": user_id,
                "model_used": model_used,
                "session_id": session_id,
                "created_at": datetime.now(timezone.utc),
            }
            
            doc_ref.set(feedback_data)
            logger.info("Recorded feedback %s (type: %s)", doc_ref.id, feedback_type)
            
            return doc_ref.id
            
        except Exception as e:
            logger.error("Failed to record feedback: %s", e)
            return None
    
    def get_feedback_for_training(
        self,
        min_rating: float = 0.7,
        limit: int = 1000,
    ) -> List[Dict[str, Any]]:
        """Get high-quality feedback for RLHF training."""
        if not self.db:
            return []
        
        try:
            # Get thumbs up feedback
            query = (
                self.db.collection(self.COLLECTION)
                .where("feedback_type", "==", "thumbs_up")
                .order_by("created_at", direction=firestore.Query.DESCENDING)
                .limit(limit)
            )
            
            results = []
            for doc in query.stream():
                results.append(doc.to_dict())
            
            # Also get high-rated feedback
            rating_query = (
                self.db.collection(self.COLLECTION)
                .where("rating", ">=", min_rating)
                .order_by("rating", direction=firestore.Query.DESCENDING)
                .limit(limit)
            )
            
            for doc in rating_query.stream():
                data = doc.to_dict()
                if data not in results:
                    results.append(data)
            
            return results[:limit]
            
        except Exception as e:
            logger.error("Failed to get feedback for training: %s", e)
            return []


# ==============================================================================
# Convenience functions
# ==============================================================================

def get_subscription_service() -> FirestoreSubscriptionService:
    """Get subscription service instance."""
    return FirestoreSubscriptionService()


def get_usage_service() -> FirestoreUsageService:
    """Get usage service instance."""
    return FirestoreUsageService()


def get_feedback_service() -> FirestoreFeedbackService:
    """Get feedback service instance."""
    return FirestoreFeedbackService()


def is_firestore_available() -> bool:
    """Check if Firestore is available."""
    return FIRESTORE_AVAILABLE and get_firestore_client() is not None

