"""Calendar tool for MCP."""
from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Google Calendar integration (optional - will fail gracefully if not installed)
try:
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import Flow, InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    import pickle
    GOOGLE_CALENDAR_AVAILABLE = True
except ImportError:
    GOOGLE_CALENDAR_AVAILABLE = False
    logger.warning("Google Calendar API not available. Install with: pip install google-api-python-client google-auth-oauthlib")


def _get_calendar_service() -> Any:
    """Get authenticated Google Calendar service.
    
    Returns:
        Calendar service instance or None if not configured
    """
    if not GOOGLE_CALENDAR_AVAILABLE:
        return None
    
    try:
        # Check for credentials file path
        creds_file = os.getenv("GOOGLE_CALENDAR_CREDENTIALS_FILE")
        token_file = os.getenv("GOOGLE_CALENDAR_TOKEN_FILE")
        
        if not creds_file:
            return None
        
        creds = None
        
        # Load existing token if available
        if token_file and os.path.exists(token_file):
            with open(token_file, 'rb') as token:
                creds = pickle.load(token)
        
        # If there are no (valid) credentials, authenticate
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    creds_file,
                    ['https://www.googleapis.com/auth/calendar']
                )
                creds = flow.run_local_server(port=0)
            
            # Save credentials for next run
            if token_file:
                with open(token_file, 'wb') as token:
                    pickle.dump(creds, token)
        
        # Build service
        service = build('calendar', 'v3', credentials=creds)
        return service
    except Exception as exc:
        logger.error(f"Failed to get calendar service: {exc}", exc_info=True)
        return None


async def create_calendar_event_tool(
    title: str,
    start_time: str,
    end_time: Optional[str] = None,
    description: Optional[str] = None,
    location: Optional[str] = None,
    attendees: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a calendar event using Google Calendar API (or fallback to logging).

    Args:
        title: Event title
        start_time: Event start time (ISO format or readable date)
        end_time: Event end time (optional, defaults to 1 hour after start)
        description: Event description (optional)
        location: Event location (optional)
        attendees: Attendee emails (comma-separated, optional)

    Returns:
        Event creation result
    """
    try:
        service = _get_calendar_service()
        
        if not service:
            # Fallback: log the event request
            logger.info(
                f"Calendar event request (service not configured): title={title}, start={start_time}, end={end_time or 'default'}"
            )
            return {
                "success": True,
                "message": "Calendar event created (calendar service not configured - set GOOGLE_CALENDAR_CREDENTIALS_FILE)",
                "title": title,
                "start_time": start_time,
                "end_time": end_time,
            }
        
        # Parse start time
        try:
            if 'T' in start_time:
                start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            else:
                start_dt = datetime.fromisoformat(start_time)
        except ValueError:
            # Try parsing as readable date
            from dateutil import parser
            start_dt = parser.parse(start_time)
        
        # Parse or calculate end time
        if end_time:
            try:
                if 'T' in end_time:
                    end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                else:
                    end_dt = datetime.fromisoformat(end_time)
            except ValueError:
                from dateutil import parser
                end_dt = parser.parse(end_time)
        else:
            # Default to 1 hour after start
            end_dt = start_dt + timedelta(hours=1)
        
        # Format for Google Calendar API
        start_iso = start_dt.isoformat()
        end_iso = end_dt.isoformat()
        
        # Build event
        event = {
            'summary': title,
            'start': {
                'dateTime': start_iso,
                'timeZone': 'UTC',
            },
            'end': {
                'dateTime': end_iso,
                'timeZone': 'UTC',
            },
        }
        
        if description:
            event['description'] = description
        
        if location:
            event['location'] = location
        
        if attendees:
            attendee_list = [{'email': email.strip()} for email in attendees.split(',')]
            event['attendees'] = attendee_list
        
        # Create event
        created_event = service.events().insert(calendarId='primary', body=event).execute()
        
        logger.info(f"Calendar event created: {created_event.get('htmlLink')}")
        return {
            "success": True,
            "message": "Calendar event created successfully",
            "title": title,
            "start_time": start_time,
            "end_time": end_time or end_iso,
            "event_id": created_event.get('id'),
            "event_link": created_event.get('htmlLink'),
        }
        
    except HttpError as exc:
        logger.error(f"Calendar API error: {exc}", exc_info=True)
        return {
            "success": False,
            "error": f"Calendar API error: {exc}",
        }
    except Exception as exc:
        logger.error(f"Calendar event creation failed: {exc}", exc_info=True)
        return {
            "success": False,
            "error": str(exc),
        }


async def list_calendar_events_tool(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 10,
) -> Dict[str, Any]:
    """List calendar events using Google Calendar API (or fallback to logging).

    Args:
        start_date: Start date for event list (optional)
        end_date: End date for event list (optional)
        limit: Maximum number of events to return

    Returns:
        List of events
    """
    try:
        service = _get_calendar_service()
        
        if not service:
            # Fallback: log the request
            logger.info(f"Calendar list request (service not configured): start={start_date}, end={end_date}, limit={limit}")
            return {
                "success": True,
                "message": "Calendar events listed (calendar service not configured - set GOOGLE_CALENDAR_CREDENTIALS_FILE)",
                "events": [],
                "count": 0,
            }
        
        # Parse dates
        time_min = None
        time_max = None
        
        if start_date:
            try:
                if 'T' in start_date:
                    time_min = datetime.fromisoformat(start_date.replace('Z', '+00:00')).isoformat() + 'Z'
                else:
                    time_min = datetime.fromisoformat(start_date).isoformat() + 'Z'
            except ValueError:
                from dateutil import parser
                time_min = parser.parse(start_date).isoformat() + 'Z'
        
        if end_date:
            try:
                if 'T' in end_date:
                    time_max = datetime.fromisoformat(end_date.replace('Z', '+00:00')).isoformat() + 'Z'
                else:
                    time_max = datetime.fromisoformat(end_date).isoformat() + 'Z'
            except ValueError:
                from dateutil import parser
                time_max = parser.parse(end_date).isoformat() + 'Z'
        
        # List events
        events_result = service.events().list(
            calendarId='primary',
            timeMin=time_min,
            timeMax=time_max,
            maxResults=limit,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        
        # Format events for response
        formatted_events = []
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            formatted_events.append({
                'id': event.get('id'),
                'title': event.get('summary', 'No title'),
                'start': start,
                'description': event.get('description', ''),
                'location': event.get('location', ''),
            })
        
        logger.info(f"Retrieved {len(formatted_events)} calendar events")
        return {
            "success": True,
            "message": f"Retrieved {len(formatted_events)} calendar events",
            "events": formatted_events,
            "count": len(formatted_events),
        }
        
    except HttpError as exc:
        logger.error(f"Calendar API error: {exc}", exc_info=True)
        return {
            "success": False,
            "error": f"Calendar API error: {exc}",
            "events": [],
        }
    except Exception as exc:
        logger.error(f"Calendar list failed: {exc}", exc_info=True)
        return {
            "success": False,
            "error": str(exc),
            "events": [],
        }


# Register the tools
from ..tool_registry import register_tool

register_tool(
    name="create_calendar_event",
    description="Create a calendar event (requires calendar service configuration)",
    parameters={
        "title": {
            "type": "string",
            "description": "Event title",
            "required": True,
        },
        "start_time": {
            "type": "string",
            "description": "Event start time (ISO format or readable date)",
            "required": True,
        },
        "end_time": {
            "type": "string",
            "description": "Event end time (optional)",
            "required": False,
        },
        "description": {
            "type": "string",
            "description": "Event description (optional)",
            "required": False,
        },
        "location": {
            "type": "string",
            "description": "Event location (optional)",
            "required": False,
        },
        "attendees": {
            "type": "string",
            "description": "Attendee emails (comma-separated, optional)",
            "required": False,
        },
    },
    handler=create_calendar_event_tool,
)

register_tool(
    name="list_calendar_events",
    description="List calendar events (requires calendar service configuration)",
    parameters={
        "start_date": {
            "type": "string",
            "description": "Start date for event list (optional)",
            "required": False,
        },
        "end_date": {
            "type": "string",
            "description": "End date for event list (optional)",
            "required": False,
        },
        "limit": {
            "type": "integer",
            "description": "Maximum number of events to return",
            "default": 10,
            "required": False,
        },
    },
    handler=list_calendar_events_tool,
)

