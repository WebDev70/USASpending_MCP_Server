#!/bin/bash

# Change to the script's directory
cd "$(dirname "$0")"

echo "Testing USASpending MCP Server..."
echo "Make sure the MCP server is running first (./start_mcp_server.sh)"
echo ""

# Test the server with example client
./venv/bin/python example_client.py