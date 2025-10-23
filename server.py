from io import StringIO
import os
import datetime
from fastapi import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from mcp.server.fastmcp import FastMCP
import logging

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

# Initialize MCP server
mcp = FastMCP("google-calendar")

# Google Calendar API scope
SCOPES = ["https://www.googleapis.com/auth/calendar"]

def get_calendar_service():
    creds = None
    token_path = "token.json"

    # Try loading existing credentials
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)

    # If no valid credentials, log in via OAuth
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            creds_json_str = os.environ["GOOGLE_CREDS_JSON"]
            creds_file = StringIO(creds_json_str)
            flow = InstalledAppFlow.from_client_secrets_file(creds_file, SCOPES)
            creds = flow.run_local_server(open_browser=False)
        with open(token_path, "w") as token:
            token.write(creds.to_json())

    return build("calendar", "v3", credentials=creds)


@mcp.tool("create_calendar_event")
def create_calendar_event(summary: str, start_time: str, end_time: str):
    """
    Create a Google Calendar event.
    """
    service = get_calendar_service()
    event = {
        "summary": summary,
        "start": {"dateTime": start_time, "timeZone": "America/Los_Angeles"},
        "end": {"dateTime": end_time, "timeZone": "America/Los_Angeles"},
    }
    created = service.events().insert(calendarId="primary", body=event).execute()
    return {"status": "success", "event_id": created["id"]}


if __name__ == "__main__":
    mcp.run()
