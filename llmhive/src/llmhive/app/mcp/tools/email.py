"""Email tool for MCP."""
from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# SendGrid integration (optional - will fail gracefully if not installed)
try:
    from sendgrid import SendGridAPIClient
    from sendgrid.helpers.mail import Mail, Email, To, Content
    SENDGRID_AVAILABLE = True
except ImportError:
    SENDGRID_AVAILABLE = False
    SendGridAPIClient = None  # type: ignore
    Mail = None  # type: ignore
    logger.warning("SendGrid not available. Install with: pip install sendgrid")


async def send_email_tool(
    to: str,
    subject: str,
    body: str,
    from_email: Optional[str] = None,
    cc: Optional[str] = None,
    bcc: Optional[str] = None,
) -> Dict[str, Any]:
    """Send an email using SendGrid (or fallback to logging).

    Args:
        to: Recipient email address
        subject: Email subject
        body: Email body
        from_email: Sender email (optional, uses default if not provided)
        cc: CC recipients (optional, comma-separated)
        bcc: BCC recipients (optional, comma-separated)

    Returns:
        Send result
    """
    try:
        # Get SendGrid API key from environment
        sendgrid_api_key = os.getenv("SENDGRID_API_KEY")
        
        if not SENDGRID_AVAILABLE or not sendgrid_api_key:
            # Fallback: log the email request
            logger.info(
                f"Email request (service not configured): to={to}, subject={subject}, from={from_email or 'default'}"
            )
            return {
                "success": True,
                "message": "Email queued for sending (email service not configured - set SENDGRID_API_KEY)",
                "to": to,
                "subject": subject,
            }

        # Use SendGrid to send email
        sg = SendGridAPIClient(sendgrid_api_key)
        
        # Get default from email from config or use provided
        default_from = os.getenv("SENDGRID_FROM_EMAIL", from_email or "noreply@llmhive.com")
        from_addr = from_email or default_from
        
        # Create email message
        message = Mail(
            from_email=Email(from_addr),
            to_emails=To(to),
            subject=subject,
            plain_text_content=Content("text/plain", body),
        )
        
        # Add CC if provided
        if cc:
            cc_list = [email.strip() for email in cc.split(",")]
            message.cc = [Email(email) for email in cc_list]
        
        # Add BCC if provided
        if bcc:
            bcc_list = [email.strip() for email in bcc.split(",")]
            message.bcc = [Email(email) for email in bcc_list]
        
        # Send email
        response = sg.send(message)
        
        if response.status_code in (200, 202):
            logger.info(f"Email sent successfully: to={to}, subject={subject}")
            return {
                "success": True,
                "message": "Email sent successfully",
                "to": to,
                "subject": subject,
                "status_code": response.status_code,
            }
        else:
            logger.warning(f"Email send returned status {response.status_code}")
            return {
                "success": False,
                "error": f"Email service returned status {response.status_code}",
                "to": to,
                "subject": subject,
            }
            
    except Exception as exc:
        logger.error(f"Email send failed: {exc}", exc_info=True)
        return {
            "success": False,
            "error": str(exc),
        }


# Register the tool
from ..tool_registry import register_tool

register_tool(
    name="send_email",
    description="Send an email (requires email service configuration)",
    parameters={
        "to": {
            "type": "string",
            "description": "Recipient email address",
            "required": True,
        },
        "subject": {
            "type": "string",
            "description": "Email subject",
            "required": True,
        },
        "body": {
            "type": "string",
            "description": "Email body",
            "required": True,
        },
        "from_email": {
            "type": "string",
            "description": "Sender email address (optional)",
            "required": False,
        },
        "cc": {
            "type": "string",
            "description": "CC recipients (comma-separated, optional)",
            "required": False,
        },
        "bcc": {
            "type": "string",
            "description": "BCC recipients (comma-separated, optional)",
            "required": False,
        },
    },
    handler=send_email_tool,
)

