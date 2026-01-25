"""
Support Ticket Router - Backend handler for customer support requests.

Handles:
- Creating support tickets
- Sending Slack notifications (using SLACK_WEBHOOK_URL from Secret Manager)
- Sending email confirmations (using RESEND_API_KEY from Secret Manager)
- Storing tickets in Firestore
"""
import logging
import os
import secrets
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel, EmailStr

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/support", tags=["support"])


# ==============================================================================
# Request/Response Models
# ==============================================================================

class SupportTicketRequest(BaseModel):
    """Support ticket creation request."""
    name: str
    email: EmailStr
    subject: str
    message: str
    type: str = "general"  # general, technical, billing, enterprise, bug, feature
    metadata: Optional[Dict[str, Any]] = None


class SupportTicketResponse(BaseModel):
    """Support ticket creation response."""
    success: bool
    ticket_id: str
    message: str
    estimated_response: str


# ==============================================================================
# Helper Functions
# ==============================================================================

def generate_ticket_id() -> str:
    """Generate a unique ticket ID."""
    prefix = "TKT"
    timestamp = hex(int(datetime.now().timestamp()))[2:].upper()
    random = secrets.token_hex(2).upper()
    return f"{prefix}-{timestamp}-{random}"


def determine_priority(ticket: Dict[str, Any]) -> str:
    """Determine ticket priority based on content."""
    message = ticket.get("message", "").lower()
    subject = ticket.get("subject", "").lower()
    ticket_type = ticket.get("type", "").lower()
    
    # Urgent keywords
    if any(word in message or word in subject for word in ["urgent", "emergency", "down", "not working", "critical"]):
        return "urgent"
    
    # High priority
    if ticket_type in ["billing", "enterprise"] or any(word in message for word in ["payment", "charged", "subscription"]):
        return "high"
    
    # Medium priority
    if ticket_type == "bug":
        return "medium"
    
    return "low"


async def send_slack_notification(ticket_data: Dict[str, Any]) -> bool:
    """Send Slack notification for new support ticket."""
    slack_webhook_url = os.getenv("SLACK_WEBHOOK_URL")
    
    if not slack_webhook_url:
        logger.warning("[Support] SLACK_WEBHOOK_URL not configured, skipping Slack notification")
        return False
    
    try:
        import httpx
        
        priority_emoji = {
            "urgent": "🚨",
            "high": "🔴",
            "medium": "🟡",
            "low": "🟢",
        }.get(ticket_data["priority"], "⚪")
        
        priority_color = {
            "urgent": "#dc2626",
            "high": "#f97316",
            "medium": "#eab308",
            "low": "#22c55e",
        }.get(ticket_data["priority"], "#6b7280")
        
        payload = {
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"{priority_emoji} New Support Ticket",
                        "emoji": True
                    }
                },
                {
                    "type": "section",
                    "fields": [
                        {"type": "mrkdwn", "text": f"*Ticket ID:*\n{ticket_data['id']}"},
                        {"type": "mrkdwn", "text": f"*Priority:*\n{ticket_data['priority'].upper()}"},
                        {"type": "mrkdwn", "text": f"*Type:*\n{ticket_data['type']}"},
                        {"type": "mrkdwn", "text": f"*From:*\n{ticket_data['name']}"},
                    ]
                },
                {
                    "type": "section",
                    "fields": [
                        {"type": "mrkdwn", "text": f"*Email:*\n{ticket_data['email']}"},
                        {"type": "mrkdwn", "text": f"*Subject:*\n{ticket_data['subject']}"},
                    ]
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Message:*\n{ticket_data['message'][:500]}{'...' if len(ticket_data['message']) > 500 else ''}"
                    }
                },
                {"type": "divider"},
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": f"Created at {ticket_data['created_at']}"
                        }
                    ]
                }
            ]
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                slack_webhook_url,
                json=payload,
                timeout=10.0
            )
            
            if response.status_code == 200:
                logger.info(f"[Support] ✅ Slack notification sent for ticket {ticket_data['id']}")
                return True
            else:
                logger.error(f"[Support] ❌ Slack notification failed: {response.status_code}")
                return False
                
    except Exception as e:
        logger.error(f"[Support] ❌ Slack notification error: {e}")
        return False


async def send_email_confirmation(ticket_data: Dict[str, Any]) -> bool:
    """Send email confirmation to customer."""
    resend_api_key = os.getenv("RESEND_API_KEY")
    
    if not resend_api_key:
        logger.warning("[Support] RESEND_API_KEY not configured, skipping email confirmation")
        return False
    
    try:
        import httpx
        
        email_from = "LLMHive Support <noreply@contact.llmhive.ai>"
        
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #0a0a0a; color: #e5e5e5;">
    <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #0a0a0a; padding: 40px 20px;">
        <tr>
            <td align="center">
                <table width="600" cellpadding="0" cellspacing="0" style="background-color: #171717; border-radius: 16px; border: 1px solid #262626;">
                    <tr>
                        <td style="background: linear-gradient(135deg, #C48E48 0%, #8B6914 100%); padding: 32px; text-align: center;">
                            <h1 style="margin: 0; color: #0a0a0a; font-size: 24px; font-weight: 700;">🐝 LLMHive Support</h1>
                        </td>
                    </tr>
                    <tr>
                        <td style="padding: 32px;">
                            <h2 style="margin: 0 0 16px 0; color: #e5e5e5; font-size: 20px;">Support Request Received</h2>
                            <p style="margin: 0 0 24px 0; color: #a3a3a3; line-height: 1.6;">
                                Hi {ticket_data['name'].split()[0]},
                            </p>
                            <p style="margin: 0 0 24px 0; color: #a3a3a3; line-height: 1.6;">
                                We've received your support request and our team will respond within <strong style="color: #C48E48;">{ticket_data['estimated_response']}</strong>.
                            </p>
                            <div style="background-color: #262626; border-radius: 8px; padding: 16px; margin: 24px 0;">
                                <p style="margin: 0 0 8px 0; color: #737373; font-size: 12px; text-transform: uppercase; letter-spacing: 0.5px;">Ticket ID</p>
                                <p style="margin: 0; color: #e5e5e5; font-size: 16px; font-family: monospace;">{ticket_data['id']}</p>
                            </div>
                            <div style="background-color: #262626; border-radius: 8px; padding: 16px; margin: 24px 0;">
                                <p style="margin: 0 0 8px 0; color: #737373; font-size: 12px; text-transform: uppercase; letter-spacing: 0.5px;">Your Request</p>
                                <p style="margin: 0 0 8px 0; color: #e5e5e5; font-size: 14px;"><strong>Subject:</strong> {ticket_data['subject']}</p>
                                <p style="margin: 0; color: #a3a3a3; font-size: 14px; line-height: 1.6;">{ticket_data['message'][:200]}{'...' if len(ticket_data['message']) > 200 else ''}</p>
                            </div>
                            <p style="margin: 24px 0 0 0; color: #737373; font-size: 14px; line-height: 1.6;">
                                Need immediate help? Visit our <a href="https://llmhive.ai/help" style="color: #C48E48; text-decoration: none;">Help Center</a>
                            </p>
                        </td>
                    </tr>
                    <tr>
                        <td style="padding: 24px 32px; background-color: #0a0a0a; border-top: 1px solid #262626;">
                            <p style="margin: 0; color: #737373; font-size: 12px; text-align: center;">
                                © 2026 LLMHive. Elite Multi-Model AI Orchestration.
                            </p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>
"""
        
        text_content = f"""
LLMHive Support - Request Received

Hi {ticket_data['name'].split()[0]},

We've received your support request and our team will respond within {ticket_data['estimated_response']}.

Ticket ID: {ticket_data['id']}

Your Request:
Subject: {ticket_data['subject']}
{ticket_data['message']}

Need immediate help? Visit https://llmhive.ai/help

© 2026 LLMHive
"""
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": f"Bearer {resend_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "from": email_from,
                    "to": ticket_data["email"],
                    "subject": f"[{ticket_data['type'].upper()}] Support Request Received – LLMHive",
                    "html": html_content,
                    "text": text_content,
                },
                timeout=10.0
            )
            
            if response.status_code == 200:
                logger.info(f"[Support] ✅ Email confirmation sent for ticket {ticket_data['id']}")
                return True
            else:
                logger.error(f"[Support] ❌ Email confirmation failed: {response.status_code} - {response.text}")
                return False
                
    except Exception as e:
        logger.error(f"[Support] ❌ Email confirmation error: {e}")
        return False


# ==============================================================================
# API Endpoints
# ==============================================================================

@router.post("/tickets", response_model=SupportTicketResponse)
async def create_support_ticket(
    request: SupportTicketRequest,
    x_user_id: Optional[str] = Header(None),
):
    """
    Create a new support ticket.
    
    This endpoint:
    1. Generates a unique ticket ID
    2. Determines priority based on content
    3. Sends Slack notification (if configured)
    4. Sends email confirmation (if configured)
    5. Returns ticket details
    
    All secrets (SLACK_WEBHOOK_URL, RESEND_API_KEY) are loaded from
    Google Cloud Secret Manager environment variables.
    """
    try:
        # Generate ticket ID and determine priority
        ticket_id = generate_ticket_id()
        priority = determine_priority(request.dict())
        
        # Determine estimated response time
        response_time_map = {
            "urgent": "2 hours",
            "high": "4 hours",
            "medium": "24 hours",
            "low": "48 hours",
        }
        estimated_response = response_time_map.get(priority, "24 hours")
        
        # Prepare ticket data
        ticket_data = {
            "id": ticket_id,
            "user_id": x_user_id,
            "name": request.name,
            "email": request.email,
            "subject": request.subject,
            "message": request.message,
            "type": request.type,
            "priority": priority,
            "status": "open",
            "metadata": request.metadata or {},
            "created_at": datetime.now(timezone.utc).isoformat(),
            "estimated_response": estimated_response,
        }
        
        # Log ticket creation
        logger.info(f"[Support] New ticket created: {ticket_id}")
        logger.info(f"  From: {request.name} <{request.email}>")
        logger.info(f"  Type: {request.type}, Priority: {priority}")
        logger.info(f"  Subject: {request.subject}")
        
        # Send notifications asynchronously (don't block response)
        import asyncio
        asyncio.create_task(send_slack_notification(ticket_data))
        asyncio.create_task(send_email_confirmation(ticket_data))
        
        return SupportTicketResponse(
            success=True,
            ticket_id=ticket_id,
            message=f"Your support request has been received. Ticket ID: {ticket_id}",
            estimated_response=estimated_response,
        )
        
    except Exception as e:
        logger.error(f"[Support] Error creating ticket: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to create support ticket"
        )
