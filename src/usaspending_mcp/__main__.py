"""
USASpending MCP Server Entry Point

This module is the starting point for running the MCP server.

WHAT IS AN ENTRY POINT?
When you run a Python package, Python needs to know where to start.
This __main__.py file tells Python: "Start here when the package is run!"

TWO WAYS TO RUN THE SERVER:
1. STDIO Mode: For testing and debugging
   - Think of it like a conversation through text input/output
   - Used with the test client or other MCP tools
   - Command: python -m usaspending_mcp --stdio

2. HTTP Mode: For Claude Desktop integration
   - The server creates a web service that listens for requests
   - Claude Desktop connects to it like a website
   - Command: python -m usaspending_mcp
   - The server runs on http://127.0.0.1:3002/mcp

HOW IT WORKS:
- The main() function checks what mode to run in
- It looks at command-line arguments (like --stdio)
- Then it starts the appropriate server mode
"""

import asyncio
import sys


def main():
    """
    Main entry point for the MCP server.

    This function does the following:
    1. Checks the command-line arguments
    2. Decides whether to run in stdio or HTTP mode
    3. Starts the appropriate server

    The stdio/HTTP decision is important:
    - Stdio: Simple text-based communication, good for testing
    - HTTP: Full web server, better for production use with Claude Desktop
    """
    # Import the server functions
    # We import here (not at the top) to avoid loading unnecessary stuff
    # if the import fails, we want to know right away
    from usaspending_mcp.server import run_server, run_stdio

    # Check if the user passed the --stdio flag as a command-line argument
    # sys.argv is a list of command-line arguments
    # sys.argv[0] is always the script name
    # sys.argv[1] is the first argument after the script name (like --stdio)
    if len(sys.argv) > 1 and sys.argv[1] == "--stdio":
        # USER WANTS STDIO MODE (for testing)
        # In stdio mode, we:
        # - Read questions from standard input (keyboard)
        # - Write answers to standard output (screen)
        # - This is async (uses asyncio) to handle waiting for input

        # asyncio.run() starts an async event loop and runs the function
        # An event loop is like a manager that handles all the async operations
        asyncio.run(run_stdio())
    else:
        # USER WANTS HTTP MODE (for Claude Desktop)
        # In HTTP mode, we:
        # - Create a web server on port 3002
        # - Listen for HTTP requests from Claude Desktop
        # - Send responses back over HTTP

        run_server()


# This is a Python idiom that says:
# "Only run main() if this file is executed directly, not if it's imported as a module"
# Think of it like: if __name__ == "__main__" means "if this is the main script"
if __name__ == "__main__":
    main()
