import os
import json
import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv
from fastmcp import FastMCP
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

# Configure logging for production
log_level = os.environ.get("LOG_LEVEL", "INFO")
logging.basicConfig(level=getattr(logging, log_level), format="%(asctime)s - %(levelname)s - %(message)s")

load_dotenv()

# Get port from environment (Render sets this automatically)
port = int(os.environ.get("PORT", 8000))
mcp = FastMCP("google-calendar")

SCOPES = ["https://www.googleapis.com/auth/calendar"]

def get_calendar_service():
    """Get Google Calendar service using OAuth2 credentials with token refresh"""
    try:
        # Try to load from environment variable first (for production)
        token_data_str = os.environ.get("GOOGLE_TOKEN_JSON")
        if token_data_str:
            token_data = json.loads(token_data_str)
        else:
            # Fallback to local file (for development)
            with open("token.json", "r") as token_file:
                token_data = json.load(token_file)
        
        creds = Credentials.from_authorized_user_info(token_data, SCOPES)
        
        # Refresh token if expired
        if creds.expired and creds.refresh_token:
            logging.info("Token expired, refreshing...")
            creds.refresh(Request())
            logging.info("Token refreshed successfully")
        
        service = build("calendar", "v3", credentials=creds)
        return service
    except Exception as e:
        logging.error(f"Failed to initialize Google Calendar service: {e}")
        raise

@mcp.tool("create_calendar_event")
def create_calendar_event(summary: str, start_time: str, end_time: str, timezone: str = "America/Los_Angeles"):
    """
    Create a Google Calendar event using OAuth2 credentials.
    
    Args:
        summary: Event title
        start_time: Start time in ISO format (e.g., "2024-01-15T14:00:00")
        end_time: End time in ISO format (e.g., "2024-01-15T15:00:00")
        timezone: Timezone (default: America/Los_Angeles)
    """
    try:
        service = get_calendar_service()
        event = {
            "summary": summary,
            "start": {"dateTime": start_time, "timeZone": timezone},
            "end": {"dateTime": end_time, "timeZone": timezone},
        }
        created = service.events().insert(calendarId="primary", body=event).execute()
        return {"status": "success", "event_id": created["id"], "event_link": created.get("htmlLink")}
    except Exception as e:
        logging.error(f"Failed to create calendar event: {e}")
        return {"status": "error", "message": str(e)}

@mcp.tool("list_calendar_events")
def list_calendar_events(max_results: int = 10, time_min: str = None):
    """
    List upcoming calendar events.
    
    Args:
        max_results: Maximum number of events to return (default: 10)
        time_min: Lower bound for event start times (ISO format, default: now)
    """
    try:
        service = get_calendar_service()
        
        if not time_min:
            time_min = datetime.utcnow().isoformat() + 'Z'
        
        events_result = service.events().list(
            calendarId='primary',
            timeMin=time_min,
            maxResults=max_results,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        
        formatted_events = []
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            formatted_events.append({
                'id': event['id'],
                'summary': event.get('summary', 'No Title'),
                'start': start,
                'link': event.get('htmlLink')
            })
        
        return {"status": "success", "events": formatted_events}
    except Exception as e:
        logging.error(f"Failed to list calendar events: {e}")
        return {"status": "error", "message": str(e)}

@mcp.tool("delete_calendar_event")
def delete_calendar_event(event_id: str):
    """
    Delete a calendar event by ID.
    
    Args:
        event_id: The ID of the event to delete
    """
    try:
        service = get_calendar_service()
        service.events().delete(calendarId='primary', eventId=event_id).execute()
        return {"status": "success", "message": f"Event {event_id} deleted successfully"}
    except Exception as e:
        logging.error(f"Failed to delete calendar event: {e}")
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="0.0.0.0", port=port)
