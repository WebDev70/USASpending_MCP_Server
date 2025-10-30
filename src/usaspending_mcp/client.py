#!/usr/bin/env python3
"""
Proper MCP Client for testing the USASpending MCP Server

This client uses the MCP library to communicate with the FastMCP server
using the StreamableHTTP transport.
"""

import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from contextlib import AsyncExitStack


async def main():
    """
    Test client that connects to the USASpending MCP Server via stdio.
    """
    # Get search parameters from user
    keyword = input("Enter search keyword (e.g., 'space', 'dell', 'construction'): ").strip()
    if not keyword:
        print("Keyword is required. Using 'space' as default.")
        keyword = "space"
    
    try:
        limit = int(input("Enter number of results to show (default 3): ").strip() or "3")
    except ValueError:
        print("Invalid number. Using default limit of 3.")
        limit = 3
    
    print("\nConnecting to MCP server...")
    
    # Use AsyncExitStack to manage the context managers
    async with AsyncExitStack() as stack:
        # Start the MCP server as a subprocess using stdio
        server_params = StdioServerParameters(
            command="./.venv/bin/python",
            args=["mcp_server.py", "--stdio"],
            env=None
        )
        
        # Connect to the server
        stdio_transport = await stack.enter_async_context(stdio_client(server_params))
        stdio, write = stdio_transport
        
        # Create a session
        session = await stack.enter_async_context(ClientSession(stdio, write))
        
        # Initialize the session
        await session.initialize()
        
        print("✓ Connected to MCP server\n")
        
        # List available tools
        print("Listing available tools...")
        tools_list = await session.list_tools()
        print(f"✓ Found {len(tools_list.tools)} tool(s):\n")
        
        for tool in tools_list.tools:
            print(f"  - {tool.name}: {tool.description[:100]}...")
        
        print(f"\nCalling tool: search_federal_awards")
        print(f"Query: {keyword}")
        print(f"Max results: {limit}\n")
        
        # Call the tool
        result = await session.call_tool(
            "search_federal_awards",
            arguments={
                "query": keyword,
                "max_results": limit
            }
        )
        
        # Display the results
        print("=" * 80)
        print("RESULTS:")
        print("=" * 80)
        
        if result.content:
            for content in result.content:
                if hasattr(content, 'text'):
                    print(content.text)
                else:
                    print(content)
        else:
            print("No results returned")
        
        print("=" * 80)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nExiting client...")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
