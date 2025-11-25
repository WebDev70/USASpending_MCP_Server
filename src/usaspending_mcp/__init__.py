"""
USASpending MCP Server Package

This is the main package for the USASpending MCP Server application.

WHAT IS THIS PROJECT?
Think of this like a library system:
- The server is a librarian that knows about federal spending
- When Claude asks a question, the librarian finds the answer
- The Model Context Protocol (MCP) is the language we use to talk to Claude

KEY FEATURES:
1. Search federal contracts, grants, and loans
2. Look up Federal Acquisition Regulation (FAR) rules
3. Track federal spending patterns
4. Analyze data about government purchases

ARCHITECTURE:
- server.py: The main application that handles requests
- tools/: The tools that Claude can use (FAR lookups, spending search, etc.)
- utils/: Helper functions for common tasks (logging, rate limiting, etc.)
- loaders/: Functions that load data from files
- config.py: Settings for the application

EXAMPLE USAGE:
    # When Claude wants to search for contracts:
    >>> from usaspending_mcp import app
    >>> # Claude sends a request through the MCP protocol
    >>> # The server processes it and returns results
"""

# Version number of this package
# We update this when we make changes to the code
__version__ = "1.0.0"

# Who wrote this code
__author__ = "Ronald Blake Jr"

# Import the main FastMCP app from server.py
# This is the heart of the application - it handles all requests
from usaspending_mcp.server import app

# __all__ tells Python what we want to export from this package
# This means when someone does "from usaspending_mcp import *",
# they only get the "app" object (not all the internal stuff)
__all__ = ["app"]
