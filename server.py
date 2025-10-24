import os, json, logging
from fastapi import FastAPI
from starlette.responses import PlainTextResponse
from mcp.server.fastmcp import FastMCP

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

# Show tracebacks in JSON-RPC responses while debugging (turn off later)
mcp = FastMCP(
    "google-calendar",
    mask_error_details=False,   # show full error payloads in JSON-RPC error
    log_level="DEBUG"
)

app = FastAPI()
# Mount the MCP transport under /mcp (supports GET stream + POST JSON-RPC on same path)
app.mount("/mcp", mcp.streamable_http_app())

# Simple health probe
@mcp.custom_route("/health", methods=["GET"])
async def health(_):
    return PlainTextResponse("OK")

# ---- Tool ----
@mcp.tool("create_calendar_event")
def create_calendar_event(summary: str, start_time: str, end_time: str):
    """
    Create a Google Calendar event using a service account.
    Tip: 'primary' here is the service account's calendar. Share your calendar with the SA
    and use that calendar ID if you want to see events in your account.
    """
    # Do lazy imports so listing tools doesn't import Google libs (avoids 500 on /mcp)
    from google.oauth2.service_account import Credentials
    from googleapiclient.discovery import build

    SCOPES = ["https://www.googleapis.com/auth/calendar"]

    svc_json = os.environ.get("GOOGLE_CREDS_JSON")
    if not svc_json:
        raise RuntimeError("GOOGLE_CREDS_JSON is not set on the server")

    svc_info = json.loads(svc_json)
    creds = Credentials.from_service_account_info(info=svc_info, scopes=SCOPES)
    service = build("calendar", "v3", credentials=creds)

    event = {
        "summary": summary,
        "start": {"dateTime": start_time, "timeZone": "America/Los_Angeles"},
        "end": {"dateTime": end_time, "timeZone": "America/Los_Angeles"},
    }
    created = service.events().insert(calendarId="primary", body=event).execute()
    return {"status": "success", "event_id": created["id"]}

# Optional: keep a normal root
@app.get("/")
def root():
    return {"status": "running", "mcp": "/mcp", "health": "/mcp/health"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
