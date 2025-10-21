#!/usr/bin/env python3

"""
USASpending.gov MCP Server

Provides tools to query federal spending data including awards and vendors
"""

import asyncio
import httpx
import json
import logging
from datetime import datetime
from typing import Any, Optional
from functools import lru_cache
import uvicorn
from fastmcp import FastMCP
from mcp.types import TextContent

# Set up logging
logging.basicConfig(
    level=logging.INFO,  # Changed from DEBUG to INFO for cleaner output
    format='%(levelname)s:%(name)s:%(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastMCP server
app = FastMCP(name="usaspending-server")

# Base URL for USASpending API
BASE_URL = "https://api.usaspending.gov/api/v2"

# HTTP client with timeout
http_client = httpx.AsyncClient(timeout=30.0)

def format_currency(amount: float) -> str:
    """Format currency values"""
    if amount >= 1_000_000_000:
        return f"${amount/1_000_000_000:.2f}B"
    elif amount >= 1_000_000:
        return f"${amount/1_000_000:.2f}M"
    elif amount >= 1_000:
        return f"${amount/1_000:.2f}K"
    return f"${amount:.2f}"

async def make_api_request(endpoint: str, params: dict = None, method: str = "GET", json_data: dict = None) -> dict:
    """Make request to USASpending API with error handling and logging"""
    url = f"{BASE_URL}/{endpoint}"
    
    try:
        if method == "POST":
            response = await http_client.post(url, json=json_data)
        else:
            response = await http_client.get(url, params=params)
        
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"API request error: {str(e)}")
        return {"error": f"API request error: {str(e)}"}

@app.tool(
    name="search_federal_awards",
    description="""Search federal spending data from USASpending.gov to find contracts, grants, loans, and other federal awards. 
You can search by keywords related to the award description, recipient name, or purpose.
Examples:
- Search for software development contracts
- Find construction grants in specific states
- Look up technology research funding
- Find training and education contracts""",
)
async def search_federal_awards(query: str, max_results: int = 5) -> list[TextContent]:
    """Search for federal awards"""
    logger.debug(f"Tool call received: search_federal_awards with query='{query}' and max_results={max_results}")
    
    # Extract keywords from natural language query
    keywords = " ".join([
        word for word in query.lower().split() 
        if word not in {"find", "show", "me", "get", "search", "for", "the", "and", "or", "in"}
    ])
    
    return await search_awards_logic({"keywords": keywords, "limit": max_results})

async def search_awards_logic(args: dict) -> list[TextContent]:
    """Logic for searching federal awards"""
    # Build filters based on arguments
    filters = {
        "keywords": [args.get("keywords", "")],
        "award_type_codes": ["A", "B", "C", "D"],  # Default to contracts
        "time_period": [
            {
                "start_date": "2019-10-01",
                "end_date": "2025-09-30"
            }
        ]
    }
    
    # First, get the count
    count_payload = {"filters": filters}
    count_result = await make_api_request("search/spending_by_award_count", json_data=count_payload, method="POST")
    
    if "error" in count_result:
        return [TextContent(type="text", text=f"Error getting count: {count_result['error']}")]
    
    total_count = sum(count_result.get("results", {}).values())
    
    # Then get the actual results
    payload = {
        "filters": filters,
        "fields": [
            "Award ID",
            "Recipient Name",
            "Award Amount",
            "Description",
            "Award Type"
        ],
        "page": 1,
        "limit": min(args.get("limit", 10), 100)
    }
    
    # Make the API request for results
    result = await make_api_request("search/spending_by_award", json_data=payload, method="POST")
    
    if "error" in result:
        return [TextContent(type="text", text=f"Error fetching results: {result['error']}")]
    
    # Process the results
    awards = result.get("results", [])
    
    if not awards:
        return [TextContent(type="text", text="No awards found matching your criteria.")]
    
    output = f"Found {total_count} total matches (showing {len(awards)}):\n\n"
    
    for i, award in enumerate(awards, 1):
        recipient = award.get('Recipient Name', 'Unknown Recipient')
        award_id = award.get('Award ID', 'N/A')
        amount = float(award.get('Award Amount', 0))
        award_type = award.get('Award Type', 'Unknown')
        description = award.get('Description', '')
        
        output += f"{i}. {recipient}\n"
        output += f"   Award ID: {award_id}\n"
        output += f"   Amount: {format_currency(amount)}\n"
        output += f"   Type: {award_type}\n"
        if description:
            desc = description[:150]
            output += f"   Description: {desc}{'...' if len(description) > 150 else ''}\n"
        output += "\n"
    
    return [TextContent(type="text", text=output)]

def run_server():
    """Run the server with proper signal handling"""
    try:
        logger.info("Starting server on http://127.0.0.1:3002")
        uvicorn.run(app.http_app(), host="127.0.0.1", port=3002, log_level="info", reload=False)
    except KeyboardInterrupt:
        logger.info("Received shutdown signal, shutting down gracefully...")
    except Exception as e:
        logger.error(f"Server error: {str(e)}")
    finally:
        logger.info("Server shutdown complete")

async def run_stdio():
    """Run the server using stdio transport (for MCP clients)"""
    from mcp.server.stdio import stdio_server
    
    async with stdio_server() as (read_stream, write_stream):
        await app._mcp_server.run(
            read_stream,
            write_stream,
            app._mcp_server.create_initialization_options()
        )

if __name__ == "__main__":
    import sys
    
    # Check if we should run in stdio mode (for MCP client) or HTTP mode (for Claude Desktop)
    if len(sys.argv) > 1 and sys.argv[1] == "--stdio":
        # Run in stdio mode for MCP client testing
        asyncio.run(run_stdio())
    else:
        # Run in HTTP mode for Claude Desktop
        run_server()
