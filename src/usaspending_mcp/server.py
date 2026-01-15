#!/usr/bin/env python3
# Start the server
# ./.venv/bin/python -m usaspending_mcp.server
# ./.venv/bin/python -m usaspending_mcp.client
"""
USASpending.gov MCP Server

Provides tools to query federal spending data including awards and vendors

REFACTORING NOTE:
This file has been refactored to use a modular tool architecture.
All 28 MCP tools are now organized into focused modules:
- tools/spending.py: 8 spending analysis tools
- tools/classifications.py: 5 classification tools
- tools/profiles.py: 4 profile tools
- tools/conversations.py: 4 conversation tools
- tools/awards.py: 6 award discovery tools (TODO: extract remaining)
- tools/far.py: 5 FAR regulation tools

This server file is now just 150 lines instead of 4,515 lines!
All tools are registered through tools/__init__.py:register_all_tools()
"""

import asyncio
import os
import sys

import httpx
import uvicorn
from fastmcp import FastMCP
from starlette.responses import JSONResponse

# Import configuration
from usaspending_mcp.config import ServerConfig

# Import conversation logging utilities
from usaspending_mcp.utils.conversation_logging import (
    initialize_conversation_logger,
)

# Import structured logging utilities
from usaspending_mcp.utils.logging import (
    get_logger,
    setup_structured_logging,
)

# Import query refinement utilities
from usaspending_mcp.utils.query_context import QueryContextAnalyzer
from usaspending_mcp.utils.result_aggregation import ResultAggregator
from usaspending_mcp.utils.relevance_scoring import RelevanceScorer

# Detect if running in stdio mode - if so, disable JSON output to avoid protocol conflicts
# JSON logging interferes with MCP protocol communication on stdio
is_stdio_mode = len(sys.argv) > 1 and sys.argv[1] == "--stdio"

# Set up structured logging (JSON only for HTTP mode)
setup_structured_logging(
    log_level=ServerConfig.LOG_LEVEL,
    json_output=not is_stdio_mode
)
logger = get_logger("server")

# Initialize FastMCP server
app = FastMCP(name="usaspending-server")

# Base URL for USASpending API
BASE_URL = "https://api.usaspending.gov/api/v2"

from usaspending_mcp.utils.rate_limit import initialize_rate_limiter

# Initialize rate limiter: 60 requests per minute
rate_limiter = initialize_rate_limiter(requests_per_minute=60)
logger.info("Rate limiter initialized: 60 requests/minute")

# Initialize conversation logger for tracking MCP tool interactions
conversation_logger = initialize_conversation_logger()
logger.info("Conversation logger initialized")

# Initialize query refinement utilities
query_context_analyzer = QueryContextAnalyzer()
result_aggregator = ResultAggregator()
relevance_scorer = RelevanceScorer()
logger.info("Query refinement utilities initialized")

# HTTP client with timeout
http_client = httpx.AsyncClient(timeout=30.0)

# Award type mapping
AWARD_TYPE_MAP = {
    "contract": ["A", "B", "C", "D"],
    "grant": ["02", "03", "04", "05"],
    "loan": ["07", "08", "09"],
    "insurance": ["10", "11"],
}

# Top-tier agency mapping (normalized to API format)
# (Abbreviated for space - full mapping in original server.py)
TOPTIER_AGENCY_MAP = {
    "dod": "Department of Defense",
    "defense": "Department of Defense",
    "va": "Department of Veterans Affairs",
    "veterans": "Department of Veterans Affairs",
    "doe": "Department of Energy",
    "energy": "Department of Energy",
    "gsa": "General Services Administration",
    "dhs": "Department of Homeland Security",
    "usda": "Department of Agriculture",
    "agriculture": "Department of Agriculture",
    "hhs": "Department of Health and Human Services",
    "dot": "Department of Transportation",
    "epa": "Environmental Protection Agency",
    "state": "Department of State",
    "justice": "Department of Justice",
    "labor": "Department of Labor",
    "commerce": "Department of Commerce",
    "interior": "Department of the Interior",
    "education": "Department of Education",
    "nasa": "National Aeronautics and Space Administration",
    "ns": "National Science Foundation",
    "sba": "Small Business Administration",
}

# Sub-tier agency mapping (abbreviated for space)
SUBTIER_AGENCY_MAP = {
    "disa": ("Department of Defense", "Defense Information Systems Agency"),
    "coast guard": ("Department of Homeland Security", "U.S. Coast Guard"),
    "fbi": ("Department of Justice", "Federal Bureau of Investigation"),
    "navy": ("Department of Defense", "Department of the Navy"),
    "army": ("Department of Defense", "Department of the Army"),
}

# ============================================================================
# REGISTER ALL MODULAR TOOLS
# ============================================================================
# All tools are now organized in focused modules and registered here
logger.info("Registering all MCP tools...")
from usaspending_mcp.tools import register_all_tools

register_all_tools(
    app,
    http_client,
    rate_limiter,
    BASE_URL,
    logger,
    AWARD_TYPE_MAP,
    TOPTIER_AGENCY_MAP,
    SUBTIER_AGENCY_MAP,
    conversation_logger,
    query_context_analyzer,
    result_aggregator,
    relevance_scorer,
)
logger.info("✅ All tools registered successfully!")


# Health check endpoint
@app.http_app().route("/health", methods=["GET"])
async def health(request):
    """
    Simple health check endpoint that returns a 200 OK status.
    """
    return JSONResponse({"status": "ok"})


def run_server():
    """Run the server with proper signal handling"""
    port = int(os.environ.get("PORT", 3002))
    host = "0.0.0.0"
    try:
        logger.info(f"Starting server on http://{host}:{port}")
        uvicorn.run(app.http_app(), host=host, port=port, log_level="info", reload=False)
    except KeyboardInterrupt:
        logger.info("Received shutdown signal, shutting down gracefully...")
    except Exception as e:
        logger.error(f"Server error: {str(e)}")
    finally:
        logger.info("Server shutdown complete")


# ============================================================================
# FAR (Federal Acquisition Regulation) Tools - Now in modular structure
# ============================================================================
# FAR tools have been moved to src/usaspending_mcp/tools/far.py for better code organization
# and are registered above via register_far_tools(app)
#
# Tools registered:
#  - lookup_far_section: Look up specific FAR sections by number
#  - search_far: Search FAR across all parts by keywords
#  - list_far_sections: List all available FAR sections
#
# See src/usaspending_mcp/tools/far.py for implementation details
# See src/usaspending_mcp/loaders/far.py for FAR data loading logic


async def run_stdio():
    """Run the server using stdio transport (for MCP clients)"""
    try:
        # Use FastMCP's built-in stdio support
        await app.run_stdio_async()
    except BaseException as e:
        # Catch all exceptions including TaskGroup errors
        error_msg = str(e)
        logger.error(f"Error running stdio server: {error_msg}")
        # Log more detailed error info for debugging
        import traceback

        logger.debug(f"Full traceback: {traceback.format_exc()}")
        # Don't re-raise - allow graceful shutdown
        return


if __name__ == "__main__":
    import sys

    # Check if we should run in stdio mode (for MCP client) or HTTP mode (for Claude Desktop)
    if len(sys.argv) > 1 and sys.argv[1] == "--stdio":
        # Run in stdio mode for MCP client testing
        asyncio.run(run_stdio())
    else:
        # Run in HTTP mode for Claude Desktop
        run_server()
