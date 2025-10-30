#!/bin/bash
# Start MCP Server with automatic port cleanup
# This script delegates to server_manager.py for robust server lifecycle management

# Change to the script's directory
cd "$(dirname "$0")"

# Use server_manager.py to start the server (handles port cleanup, auto-kill, etc.)
./.venv/bin/python server_manager.py start "$@"