#!/bin/bash

# Change to the script's directory
cd "$(dirname "$0")"

# Activate virtual environment and start the server
echo "Starting USASpending MCP Server..."
./venv/bin/python mcp_server.py