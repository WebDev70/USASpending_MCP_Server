#!/bin/bash

# Change to the script's directory
cd "$(dirname "$0")"

# Kill any existing server on port 3002
echo "Stopping any existing server..."
lsof -ti:3002 | xargs kill -9 2>/dev/null || true

echo "Starting USASpending MCP Server..."
echo "Press Ctrl+C to stop the server"
echo ""

# Start the server in background
./venv/bin/python mcp_server.py &
SERVER_PID=$!

# Wait a moment for server to start
sleep 3

# Test the server with example client
echo "Testing server with example client..."
./venv/bin/python example_client.py

# Keep the server running
echo ""
echo "Server is running on http://localhost:3002"
echo "You can now use it with Claude Desktop!"
echo "Press Ctrl+C to stop the server"

# Cleanup function
cleanup() {
    echo ""
    echo "Shutting down server..."
    kill $SERVER_PID 2>/dev/null || true
    exit 0
}

trap cleanup SIGINT
wait $SERVER_PID