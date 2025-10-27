import os
import json
import logging
from datetime import datetime, timezone
from typing import Optional

from fastmcp import FastMCP
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.auth.transport.requests import Request

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Initialize FastMCP
mcp = FastMCP("google-calendar")

# Google Calendar scope
SCOPES = ["https://www.googleapis.com/auth/calendar"]

# Port configuration
PORT = int(os.environ.get("PORT", 8000))


CLIENT_SECRETS_PATH = os.environ.get("GOOGLE_CLIENT_SECRETS", "creds.json")  # your OAuth client file
TOKEN_PATH = os.environ.get("GOOGLE_TOKEN_PATH", "token.json")

def _save_creds(creds: Credentials, to_env: bool):
    data = {
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "scopes": list(creds.scopes or SCOPES),
    }
    if to_env:
        os.environ["GOOGLE_TOKEN_JSON"] = json.dumps(data)
    else:
        with open(TOKEN_PATH, "w") as f:
            json.dump(data, f)

def get_calendar_service():
    """
    Load existing user tokens if present; otherwise run OAuth flow once
    (using client_secret.json) to create token.json. Then refresh & persist as needed.
    """
    # 1) Try env or file token first
    token_data_str = os.environ.get("GOOGLE_TOKEN_JSON")
    creds = None
    token_from_env = False

    if token_data_str:
        token_from_env = True
        token_data = json.loads(token_data_str)
        creds = Credentials.from_authorized_user_info(token_data, SCOPES)
    elif os.path.exists(TOKEN_PATH):
        with open(TOKEN_PATH, "r") as f:
            token_data = json.load(f)
        creds = Credentials.from_authorized_user_info(token_data, SCOPES)

    # 2) If no creds yet, run the user-consent flow (Desktop app best for local)
    if not creds:
        if not os.path.exists(CLIENT_SECRETS_PATH):
            raise RuntimeError(
                "No token.json/GOOGLE_TOKEN_JSON and no client secrets file found. "
                "Provide GOOGLE_TOKEN_JSON or place client_secret.json next to the server."
            )
        flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS_PATH, SCOPES)
        # For local dev with a browser:
        creds = flow.run_local_server(port=0)   # opens a browser once
        # For headless servers, use:
        # creds = flow.run_console()

        # Persist the new token (file is typical)
        _save_creds(creds, to_env=False)

    # 3) Refresh if needed and persist updates
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        _save_creds(creds, to_env=token_from_env)  # write back to env var or file

    return build("calendar", "v3", credentials=creds)


@mcp.tool("create_calendar_event")
def create_calendar_event(
    summary: str,
    start_time: str,
    end_time: str,
    timezone: str = "America/Los_Angeles"
):
    """Create a Google Calendar event.
    
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
        logger.info(f"Created event: {created['id']}")
        return {
            "status": "success",
            "event_id": created["id"],
            "event_link": created.get("htmlLink")
        }
    except Exception as e:
        logger.error(f"Failed to create calendar event: {e}")
        return {"status": "error", "message": str(e)}


@mcp.tool("list_calendar_events")
def list_calendar_events(max_results: int = 10, time_min: Optional[str] = None):
    """List upcoming Google Calendar events.
    
    Args:
        max_results: Maximum number of events to return (default: 10)
        time_min: Lower bound for event start times (ISO format, default: now)
    """
    try:
        service = get_calendar_service()
        
        if not time_min:
            time_min = datetime.now(timezone.utc).isoformat() + 'Z'
        
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
        
        logger.info(f"Listed {len(formatted_events)} events")
        return {"status": "success", "events": formatted_events}
    except Exception as e:
        logger.error(f"Failed to list calendar events: {e}")
        return {"status": "error", "message": str(e)}


@mcp.tool("delete_calendar_event")
def delete_calendar_event(event_id: str):
    """Delete a Google Calendar event by ID.
    
    Args:
        event_id: The ID of the event to delete
    """
    try:
        service = get_calendar_service()
        service.events().delete(calendarId='primary', eventId=event_id).execute()
        logger.info(f"Deleted event: {event_id}")
        return {"status": "success", "message": f"Event {event_id} deleted successfully"}
    except Exception as e:
        logger.error(f"Failed to delete calendar event: {e}")
        return {"status": "error", "message": str(e)}


if __name__ == "__main__":
    # Run MCP server directly
    logger.info(f"Starting Google Calendar MCP server on port {PORT}")
    mcp.run(transport="streamable-http", host="0.0.0.0", port=PORT)
