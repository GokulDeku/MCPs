import requests
import os
import json
import logging
from datetime import datetime
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

HF_API_URL = "https://router.huggingface.co/v1/chat/completions"
HF_API_KEY = os.environ.get("HUGGINGFACE_API_KEY")

def query_huggingface(prompt: str):
    """Send a prompt to the Hugging Face model and return generated text."""
    headers = {
        "Authorization": f"Bearer {HF_API_KEY}",
    }
    payload = {
        "model": "google/gemma-2-2b-it:nebius",
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 300,
    }
    response = requests.post(HF_API_URL, headers=headers, json=payload)
    response.raise_for_status()
    data = response.json()

    return data["choices"][0]["message"]["content"]

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

# Define the core logic as a regular function
def _create_calendar_event_logic(summary: str, start_time: str, end_time: str, timezone: str = "America/Los_Angeles"):
    """Create a Google Calendar event using OAuth2 credentials."""
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

# Wrap it as a tool
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
    return _create_calendar_event_logic(summary, start_time, end_time, timezone)

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

@mcp.tool("ai_schedule_event")
def ai_schedule_event(prompt: str):
    try:
        llm_prompt = f"""
        You are an assistant that extracts event information from text.
        Respond ONLY in JSON with keys: summary, start_time, end_time (ISO 8601 format).
        Text: {prompt}
        """

        output = query_huggingface(llm_prompt)
        import re, json
        match = re.search(r"\{.*\}", output, re.DOTALL)
        if not match:
            return {"status": "error", "message": "No valid JSON found in LLM response"}

        event_data = json.loads(match.group())
        summary = event_data["summary"]
        start_time = event_data["start_time"]
        end_time = event_data["end_time"]

        # Call the core logic function directly (not the tool wrapper)
        return _create_calendar_event_logic(
            summary=summary,
            start_time=start_time,
            end_time=end_time
        )

    except Exception as e:
        import logging
        logging.error(f"AI scheduling failed: {e}")
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="0.0.0.0", port=port)
