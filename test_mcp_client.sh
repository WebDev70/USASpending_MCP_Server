#!/bin/bash
# Test the MCP server using the proper MCP client
# ✅ This is the RECOMMENDED way to test the server

# Change to the script's directory
cd "$(dirname "$0")"

echo "✅ Testing USASpending MCP Server with MCP Client..."
echo "This uses the MCP protocol with stdio transport"
echo ""

# Run the MCP client
./.venv/bin/python mcp_client.py
