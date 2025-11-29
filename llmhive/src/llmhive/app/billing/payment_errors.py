"""Payment error handling and retry logic for Stripe."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Stripe integration (optional)
try:
    import stripe
    STRIPE_AVAILABLE = True
except ImportError:
    STRIPE_AVAILABLE = False
    stripe = None  # type: ignore


class PaymentErrorHandler:
    """Handles payment errors and implements retry logic."""

    # Retryable error codes from Stripe
    RETRYABLE_ERRORS = {
        'card_declined',
        'expired_card',
        'insufficient_funds',
        'processing_error',
        'rate_limit',
        'service_unavailable',
    }

    # Non-retryable errors (permanent failures)
    PERMANENT_ERRORS = {
        'invalid_number',
        'invalid_cvc',
        'invalid_expiry_month',
        'invalid_expiry_year',
        'card_not_supported',
        'generic_decline',
    }

    @classmethod
    def is_retryable(cls, error_code: str) -> bool:
        """Check if an error is retryable.
        
        Args:
            error_code: Stripe error code
            
        Returns:
            True if error is retryable
        """
        return error_code in cls.RETRYABLE_ERRORS

    @classmethod
    def is_permanent(cls, error_code: str) -> bool:
        """Check if an error is permanent.
        
        Args:
            error_code: Stripe error code
            
        Returns:
            True if error is permanent
        """
        return error_code in cls.PERMANENT_ERRORS

    @classmethod
    def handle_payment_error(
        cls,
        error: Exception,
        subscription_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Handle a payment error and determine action.
        
        Args:
            error: The exception that occurred
            subscription_id: Optional subscription ID
            user_id: Optional user ID
            
        Returns:
            Error handling result with recommended action
        """
        error_info = {
            "error_type": "unknown",
            "error_message": str(error),
            "retryable": False,
            "action": "log",
            "subscription_id": subscription_id,
            "user_id": user_id,
            "timestamp": datetime.utcnow().isoformat(),
        }

        if not STRIPE_AVAILABLE:
            error_info.update({
                "error_type": "stripe_unavailable",
                "error_message": "Stripe SDK not available",
                "action": "notify_admin",
            })
            return error_info

        # Handle Stripe-specific errors
        if isinstance(error, stripe.error.StripeError):
            error_info["error_type"] = type(error).__name__
            error_info["error_message"] = str(error)
            
            # Get error code if available
            error_code = getattr(error, 'code', None)
            if error_code:
                error_info["error_code"] = error_code
                error_info["retryable"] = cls.is_retryable(error_code)
                
                if cls.is_permanent(error_code):
                    error_info["action"] = "cancel_subscription"
                elif cls.is_retryable(error_code):
                    error_info["action"] = "retry_payment"
                else:
                    error_info["action"] = "notify_user"
            else:
                # Check error type
                if isinstance(error, stripe.error.CardError):
                    error_info["action"] = "notify_user"
                elif isinstance(error, stripe.error.RateLimitError):
                    error_info["retryable"] = True
                    error_info["action"] = "retry_payment"
                elif isinstance(error, stripe.error.APIError):
                    error_info["retryable"] = True
                    error_info["action"] = "retry_payment"
                else:
                    error_info["action"] = "notify_admin"

        # Log the error
        logger.error(
            f"Payment error: {error_info['error_type']} - {error_info['error_message']}",
            extra={
                "subscription_id": subscription_id,
                "user_id": user_id,
                "retryable": error_info["retryable"],
            }
        )

        return error_info

    @classmethod
    def should_retry_payment(
        cls,
        error_info: Dict[str, Any],
        retry_count: int = 0,
        max_retries: int = 3,
    ) -> bool:
        """Determine if payment should be retried.
        
        Args:
            error_info: Error information from handle_payment_error
            retry_count: Current retry attempt number
            max_retries: Maximum number of retries
            
        Returns:
            True if payment should be retried
        """
        if retry_count >= max_retries:
            return False
        
        if not error_info.get("retryable", False):
            return False
        
        if error_info.get("action") == "retry_payment":
            return True
        
        return False

    @classmethod
    def get_retry_delay(cls, retry_count: int) -> timedelta:
        """Calculate retry delay with exponential backoff.
        
        Args:
            retry_count: Current retry attempt number
            
        Returns:
            Time to wait before retry
        """
        # Exponential backoff: 1 hour, 6 hours, 24 hours
        delays = [timedelta(hours=1), timedelta(hours=6), timedelta(hours=24)]
        if retry_count < len(delays):
            return delays[retry_count]
        return delays[-1]  # Max delay


class WebhookErrorHandler:
    """Handles webhook processing errors."""

    @classmethod
    def handle_webhook_error(
        cls,
        error: Exception,
        event_type: Optional[str] = None,
        event_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Handle a webhook processing error.
        
        Args:
            error: The exception that occurred
            event_type: Type of webhook event
            event_id: Stripe event ID
            
        Returns:
            Error handling result
        """
        error_info = {
            "error_type": type(error).__name__,
            "error_message": str(error),
            "event_type": event_type,
            "event_id": event_id,
            "timestamp": datetime.utcnow().isoformat(),
            "action": "log",
        }

        # Determine action based on error type
        if isinstance(error, ValueError):
            error_info["action"] = "reject_webhook"
        elif isinstance(error, Exception):
            error_info["action"] = "retry_webhook"
        
        logger.error(
            f"Webhook error: {error_info['error_type']} - {error_info['error_message']}",
            extra={
                "event_type": event_type,
                "event_id": event_id,
            }
        )

        return error_info

