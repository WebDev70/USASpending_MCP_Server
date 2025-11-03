
import asyncio
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from contextlib import AsyncExitStack

async def main():
    async with AsyncExitStack() as stack:
        # Connect to the HTTP server
        async with streamablehttp_client("http://localhost:3002/mcp") as (read_stream, write_stream, get_session_id):
            session = await stack.enter_async_context(ClientSession(write_stream.send, read_stream.recv))
            await session.initialize()

            # Call the tool
            result = await session.call_tool(
                "get_recipient_details",
                arguments={
                    "recipient_name": "Accenture"
                }
            )

            if result.content:
                for content in result.content:
                    if hasattr(content, 'text'):
                        print(content.text)
                    else:
                        print(content)
            else:
                print("No results returned")

if __name__ == "__main__":
    asyncio.run(main())
