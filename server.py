import os
import json
import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv
from fastmcp import FastMCP
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

# Configure logging for production
log_level = os.environ.get("LOG_LEVEL", "INFO")
logging.basicConfig(level=getattr(logging, log_level), format="%(asctime)s - %(levelname)s - %(message)s")

load_dotenv()

# Get port from environment (Render sets this automatically)
port = int(os.environ.get("PORT", 8000))
mcp = FastMCP("google-calendar")

SCOPES = ["https://www.googleapis.com/auth/calendar"]

def get_calendar_service():
    """Get Google Calendar service using OAuth2 credentials"""
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
    service = get_calendar_service()
    event = {
        "summary": summary,
        "start": {"dateTime": start_time, "timeZone": timezone},
        "end": {"dateTime": end_time, "timeZone": timezone},
    }
    created = service.events().insert(calendarId="primary", body=event).execute()
    return {"status": "success", "event_id": created["id"], "event_link": created.get("htmlLink")}


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    mcp.run(transport="streamable-http", host="0.0.0.0", port=port)
