#!/bin/bash
set -e

# Run the server, binding to 0.0.0.0 instead of 127.0.0.1 for Docker compatibility
# This is a workaround since the server.py hardcodes 127.0.0.1

# Use Python to start the server with modified binding
python3 << 'EOF'
import asyncio
import sys
import logging
import uvicorn
from usaspending_mcp.utils.logging import setup_structured_logging, get_logger

# Set up logging
setup_structured_logging(log_level="INFO", json_output=True)
logger = get_logger("docker-entrypoint")

async def run_server():
    """Run the FastMCP server with 0.0.0.0 binding for Docker"""
    try:
        from usaspending_mcp.server import app, rate_limiter
        logger.info("Starting USASpending MCP Server on 0.0.0.0:3002")

        # Run with 0.0.0.0 instead of 127.0.0.1 for Docker accessibility
        uvicorn.run(
            app.http_app(),
            host="0.0.0.0",
            port=3002,
            log_level="info",
            reload=False
        )
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
    except Exception as e:
        logger.error(f"Server error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(run_server())
EOF
