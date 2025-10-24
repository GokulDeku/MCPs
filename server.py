import os
import json
import logging
from fastapi import FastAPI
import fastapi
from fastapi.responses import PlainTextResponse
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from mcp.server.fastmcp import FastMCP
import mcp as mcp_pkg
import fastmcp as fastmcp_pkg
import starlette

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

app = FastAPI()
mcp = FastMCP("google-calendar")

app.mount("/mcp/", mcp.streamable_http_app())

@app.get("/health")
def health():
    return {"ok": True}

@app.get("/debug/routes", response_class=PlainTextResponse)
def debug_routes():
    lines = []
    lines.append(f"fastapi={fastapi.__version__} starlette={starlette.__version__}")
    try:
        lines.append(f"mcp={mcp_pkg.__version__} fastmcp={fastmcp_pkg.__version__}")
    except Exception:
        pass
    lines.append("ROOT APP ROUTES:")
    for r in app.router.routes:
        lines.append(f"  {getattr(r, 'path', '?')}  -> {type(r).__name__}")
    # Peek into the mounted MCP sub-app
    mcp_app = app.routes[-2].app  # the Mount you just added (heuristic but works here)
    if hasattr(mcp_app, "routes"):
        lines.append("MCP SUB-APP ROUTES:")
        for r in mcp_app.routes:
            lines.append(f"  {getattr(r, 'path', '?')}  -> {type(r).__name__}")
    return "\n".join(lines)

SCOPES = ["https://www.googleapis.com/auth/calendar"]

SERVICE_ACCOUNT_JSON = os.environ.get("GOOGLE_CREDS_JSON")
if not SERVICE_ACCOUNT_JSON:
    raise RuntimeError("Environment variable GOOGLE_CREDS_JSON is not set")

SERVICE_ACCOUNT_INFO = json.loads(SERVICE_ACCOUNT_JSON)

def get_calendar_service():
    creds = Credentials.from_service_account_info(
        info=SERVICE_ACCOUNT_INFO,
        scopes=SCOPES
    )
    service = build("calendar", "v3", credentials=creds)
    return service

@mcp.tool("create_calendar_event")
def create_calendar_event(summary: str, start_time: str, end_time: str):
    """
    Create a Google Calendar event using service account.
    """
    service = get_calendar_service()
    event = {
        "summary": summary,
        "start": {"dateTime": start_time, "timeZone": "America/Los_Angeles"},
        "end": {"dateTime": end_time, "timeZone": "America/Los_Angeles"},
    }
    created = service.events().insert(calendarId="primary", body=event).execute()
    return {"status": "success", "event_id": created["id"]}

@app.get("/")
def root():
    return {"status": "running"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
