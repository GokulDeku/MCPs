import asyncio
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

URL = "https://mcps-tp4l.onrender.com/mcp"  # no trailing slash

async def main():
    async with streamablehttp_client(URL) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools = await session.list_tools()
            print("Tools:", [t.name for t in tools.tools])

            # Call your tool (use valid ISO datetimes)
            res = await session.call_tool(
                "create_calendar_event",
                {"summary":"Ping from MCP",
                 "start_time":"2025-10-23T23:30:00-07:00",
                 "end_time":"2025-10-23T23:45:00-07:00"}
            )
            print("Result:", res)

asyncio.run(main())
