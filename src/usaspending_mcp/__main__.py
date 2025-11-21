"""
USASpending MCP Server Entry Point

This module provides the command-line entry point for the MCP server.
"""

import asyncio
import sys


def main():
    """Main entry point for the MCP server."""
    from usaspending_mcp.server import run_server, run_stdio

    # Check if we should run in stdio mode (for MCP client) or HTTP mode (for Claude Desktop)
    if len(sys.argv) > 1 and sys.argv[1] == "--stdio":
        # Run in stdio mode for MCP client testing
        asyncio.run(run_stdio())
    else:
        # Run in HTTP mode for Claude Desktop
        run_server()


if __name__ == "__main__":
    main()
