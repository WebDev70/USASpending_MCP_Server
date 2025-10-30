#!/bin/bash
# Test the MCP server using the proper MCP client
# ✅ This is the RECOMMENDED way to test the server

# Navigate to project root (two directories up from tests/scripts/)
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$PROJECT_DIR"

echo "✅ Testing USASpending MCP Server with MCP Client..."
echo "This uses the MCP protocol with stdio transport"
echo ""

# Run the MCP client from the src directory
"${PROJECT_DIR}/.venv/bin/python" -m usaspending_mcp.client
