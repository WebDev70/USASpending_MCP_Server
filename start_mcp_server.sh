#!/bin/bash

# Change to the script's directory
cd "$(dirname "$0")"

# Kill any existing server on port 3002
echo "Stopping any existing server..."
lsof -ti:3002 | xargs kill -9 2>/dev/null || true

echo "Starting USASpending MCP Server..."
echo "Server will run on http://localhost:3002"
echo "Press Ctrl+C to stop the server"
echo ""

# Cleanup function
cleanup() {
    echo ""
    echo "Shutting down server..."
    exit 0
}

trap cleanup SIGINT

# Start the server
./venv/bin/python mcp_server.py