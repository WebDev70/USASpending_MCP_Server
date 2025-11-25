"""
Tool registration and coordination module.

WHAT'S IN THIS FILE?
This file is the "central switchboard" for all MCP tools.
When the application starts, it calls register_all_tools() to
register every tool available in the system.

WHY HAVE THIS FILE?
Instead of having all 28 tools in server.py, we spread them across
multiple focused modules (awards.py, spending.py, etc.).
This file coordinates all those modules and registers them with the app.

HOW IT WORKS:
1. server.py imports this module
2. server.py calls register_all_tools(app, ...)
3. This function imports each tool module
4. Each tool module's register_tools() function is called
5. All tools are now registered with the app

WORKFLOW:
┌─────────────────┐
│   server.py     │  Creates app, http_client, rate_limiter
└────────┬────────┘
         │
         ▼
┌─────────────────────────────┐
│ register_all_tools(app, ...) │  Coordinates registration
└────────┬────────────────────┘
         │
    ┌────┴────┬─────────────────┬──────────────┐
    │         │                 │              │
    ▼         ▼                 ▼              ▼
 awards  spending         classifications  profiles
 register  register         register        register
 _tools    _tools         _tools          _tools
"""

import logging
from typing import TYPE_CHECKING

import httpx
from fastmcp import FastMCP

if TYPE_CHECKING:
    # These imports are just for type hints, not runtime
    from usaspending_mcp.tools import awards, spending, classifications, profiles, conversations, far

logger = logging.getLogger(__name__)


def register_all_tools(
    app: FastMCP,
    http_client: httpx.AsyncClient,
    rate_limiter,
    base_url: str,
    logger_instance,
    award_type_map: dict,
    toptier_agency_map: dict,
    subtier_agency_map: dict,
) -> None:
    """
    Register all MCP tools with the FastMCP application.

    WHAT DOES THIS DO?
    This is the main registration function. It:
    1. Imports all tool modules
    2. Calls each module's register_tools() function
    3. Passes all shared dependencies to each module

    WHY PASS ALL THESE PARAMETERS?
    Each tool module needs access to:
    - app: To register tools
    - http_client: To make API requests
    - rate_limiter: To respect rate limits
    - base_url: The USASpending API base URL
    - logger_instance: For logging
    - Agency maps: For normalizing agency names

    Instead of having these be global variables scattered
    everywhere, we pass them explicitly. This is cleaner
    and follows professional Python practices.

    Args:
        app: FastMCP application instance
        http_client: HTTP client for making API requests
        rate_limiter: Rate limiter to control request frequency
        base_url: Base URL for USASpending API
        logger_instance: Logger instance for logging
        award_type_map: Dictionary mapping award types to codes
        toptier_agency_map: Dictionary mapping agency names to official names
        subtier_agency_map: Dictionary mapping sub-agencies
    """

    # Import each tool module
    # We import here (not at the top) so they're only imported when needed
    from usaspending_mcp.tools import far, awards, spending, classifications, profiles, conversations  # Modular tools

    logger_instance.info("Starting tool registration...")

    # ============ REGISTER AWARD DISCOVERY TOOLS ============
    logger_instance.debug("Registering award discovery tools...")
    try:
        awards.register_tools(
            app, http_client, rate_limiter, base_url, logger_instance,
            award_type_map, toptier_agency_map, subtier_agency_map
        )
        logger_instance.info("✓ Award discovery tools registered (6 tools)")
    except Exception as e:
        logger_instance.warning(f"Could not register award tools: {e}")

    # ============ REGISTER SPENDING TOOLS ============
    logger_instance.debug("Registering spending tools...")
    try:
        spending.register_tools(
            app, http_client, rate_limiter, base_url, logger_instance,
            award_type_map, toptier_agency_map, subtier_agency_map
        )
        logger_instance.info("✓ Spending tools registered (8 tools)")
    except Exception as e:
        logger_instance.warning(f"Could not register spending tools: {e}")

    # ============ REGISTER CLASSIFICATION TOOLS ============
    logger_instance.debug("Registering classification tools...")
    try:
        classifications.register_tools(
            app, http_client, rate_limiter, base_url, logger_instance,
            award_type_map, toptier_agency_map, subtier_agency_map
        )
        logger_instance.info("✓ Classification tools registered (5 tools)")
    except Exception as e:
        logger_instance.warning(f"Could not register classification tools: {e}")

    # ============ REGISTER PROFILE TOOLS ============
    logger_instance.debug("Registering profile tools...")
    try:
        profiles.register_tools(
            app, http_client, rate_limiter, base_url, logger_instance,
            award_type_map, toptier_agency_map, subtier_agency_map
        )
        logger_instance.info("✓ Profile tools registered (4 tools)")
    except Exception as e:
        logger_instance.warning(f"Could not register profile tools: {e}")

    # ============ REGISTER CONVERSATION TOOLS ============
    logger_instance.debug("Registering conversation tools...")
    try:
        conversations.register_tools(
            app, http_client, rate_limiter, base_url, logger_instance,
            award_type_map, toptier_agency_map, subtier_agency_map
        )
        logger_instance.info("✓ Conversation tools registered (4 tools)")
    except Exception as e:
        logger_instance.warning(f"Could not register conversation tools: {e}")

    # ============ REGISTER FAR TOOLS ============
    logger_instance.debug("Registering FAR tools...")
    try:
        far.register_far_tools(app)
        logger_instance.info("✓ FAR tools registered (5 tools)")
    except Exception as e:
        logger_instance.warning(f"Could not register FAR tools: {e}")

    logger_instance.info("✅ All tool modules registered successfully! (27 total tools)")
    logger_instance.info("   - Award discovery: 6 tools")
    logger_instance.info("   - Spending analysis: 8 tools")
    logger_instance.info("   - Classifications: 5 tools")
    logger_instance.info("   - Profiles: 4 tools")
    logger_instance.info("   - Conversations: 4 tools")
    logger_instance.info("   - FAR regulations: 5 tools")
