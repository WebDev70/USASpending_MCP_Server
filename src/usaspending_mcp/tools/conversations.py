"""
Conversation history and analytics tools.

WHAT'S IN THIS FILE?
Tools for managing and analyzing conversation history.

TOOLS IN THIS FILE (4 total):
1. get_conversation - Retrieve complete conversation history
2. list_conversations - List all conversations with pagination support
3. get_conversation_summary - Get statistics and summary for a conversation
4. get_tool_usage_stats - Get tool usage patterns and statistics

WHY SEPARATE FROM server.py?
server.py became too large (4,515 lines with 28 tools).
By separating into focused modules, we:
- Make code easier to find and modify
- Enable multiple developers to work in parallel
- Follow professional software engineering practices
- Make it easier to test individual tools
- Make it clearer what each file's responsibility is

DESIGN PATTERN USED:
Each tool module has a register_tools() function that:
1. Receives all dependencies it needs (http_client, logger, etc.)
2. Defines all tools for that module
3. Registers them with the FastMCP app
This is called "dependency injection" and is a professional pattern.
"""

import logging
from typing import Optional

import httpx
from fastmcp import FastMCP
from mcp.types import TextContent

# Import utilities we need
from usaspending_mcp.utils.logging import log_tool_execution
from usaspending_mcp.utils.conversation_logging import get_conversation_logger

# Module logger
logger = logging.getLogger(__name__)


def register_tools(
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
    Register all conversation management tools with the FastMCP application.

    WHY IS THIS A FUNCTION?
    Instead of decorators at module level (which won't work when the
    app and http_client are defined elsewhere), we use a registration
    function. This gives tools access to the objects they need.

    DEPENDENCY INJECTION:
    All the parameters (http_client, rate_limiter, etc.) are "injected"
    into this function. Each tool can use them through closure variables.

    Args:
        app: The FastMCP application instance
        http_client: The HTTP client for making API requests
        rate_limiter: Rate limiter to control request frequency
        base_url: Base URL for USASpending API
        logger_instance: Logger instance for this module
        award_type_map: Dictionary mapping award types to codes
        toptier_agency_map: Dictionary mapping agency names to official names
        subtier_agency_map: Dictionary mapping sub-agencies to tuples
    """

    @app.tool(
        name="get_conversation",
        description="""Retrieve a complete MCP conversation history by ID.

    This tool retrieves all tool calls within a specific conversation session,
    including inputs, outputs, execution times, and timestamps.

    PARAMETERS:
    - conversation_id: The unique identifier of the conversation
    - user_id: Optional user identifier (default: "anonymous")

    RETURNS:
    - List of tool call records with complete context
    - Each record includes: tool name, parameters, response, execution time, timestamp, status

    EXAMPLE:
    - conversation_id="550e8400-e29b-41d4-a716-446655440000" → Returns all tool calls in that conversation
    """,
    )
    async def get_conversation(conversation_id: str, user_id: str = "anonymous") -> list[TextContent]:
        """Retrieve a conversation by ID"""
        conv_logger = get_conversation_logger()
        records = conv_logger.get_conversation(conversation_id, user_id)

        if not records:
            return [TextContent(type="text", text=f"No conversation found with ID: {conversation_id}")]

        output = f"=== Conversation {conversation_id} ===\n"
        output += f"User: {user_id}\n"
        output += f"Messages: {len(records)}\n"
        output += "=" * 80 + "\n\n"

        for i, record in enumerate(records, 1):
            output += f"--- Message {i} ---\n"
            output += f"Tool: {record['tool_name']}\n"
            output += f"Time: {record['timestamp']}\n"
            output += f"Status: {record['status']}\n"
            output += f"Duration: {record.get('execution_time_ms', 0):.1f}ms\n"
            output += f"\nInput:\n{json.dumps(record.get('input_params', {}), indent=2)}\n"
            output += f"\nOutput:\n{record.get('output_response', '')[:500]}...\n"
            if record.get("error_message"):
                output += f"Error: {record['error_message']}\n"
            output += "\n"

        return [TextContent(type="text", text=output)]



    @app.tool(
        name="list_conversations",
        description="""List all conversations for a user.

    This tool retrieves metadata about recent conversations, including
    message count, tools used, success rates, and time ranges.

    PARAMETERS:
    - user_id: Optional user identifier (default: "anonymous")
    - limit: Maximum number of conversations to return (default: 20, max: 100)

    RETURNS:
    - List of conversation metadata with:
      - conversation_id: Unique identifier
      - message_count: Number of tool calls in conversation
      - tools_used: List of tool names
      - first_message: Timestamp of first message
      - last_message: Timestamp of last message
      - success_count: Number of successful tool calls
      - error_count: Number of failed tool calls

    EXAMPLE:
    - Calling with user_id="user123" → Returns their recent conversations
    """,
    )
    async def list_conversations(user_id: str = "anonymous", limit: int = 20) -> list[TextContent]:
        """List conversations for a user"""
        conv_logger = get_conversation_logger()
        conversations = conv_logger.list_user_conversations(user_id, limit=min(limit, 100))

        if not conversations:
            return [TextContent(type="text", text=f"No conversations found for user: {user_id}")]

        output = f"=== Conversations for {user_id} ===\n"
        output += f"Found {len(conversations)} conversations\n"
        output += "=" * 80 + "\n\n"

        for i, conv in enumerate(conversations, 1):
            output += f"{i}. Conversation ID: {conv['conversation_id']}\n"
            output += f"   Messages: {conv['message_count']}\n"
            output += f"   Tools: {', '.join(conv['tools_used'])}\n"
            output += f"   Time Range: {conv['first_message']} to {conv['last_message']}\n"
            output += f"   Success Rate: {conv['success_count']}/{conv['message_count']} "
            output += f"({100*conv['success_count']/conv['message_count']:.1f}%)\n\n"

        return [TextContent(type="text", text=output)]



    @app.tool(
        name="get_conversation_summary",
        description="""Get statistics and summary for a specific conversation.

    This tool provides analytics on a conversation including total execution time,
    tool breakdown, success rates, and error analysis.

    PARAMETERS:
    - conversation_id: The unique identifier of the conversation
    - user_id: Optional user identifier (default: "anonymous")

    RETURNS:
    - Conversation statistics:
      - Message count
      - Tools used
      - Total and average execution times
      - Success/error counts and rates
      - Time range (first to last message)

    EXAMPLE:
    - conversation_id="550e8400-e29b-41d4-a716-446655440000" → Returns statistics
    """,
    )
    async def get_conversation_summary(
        conversation_id: str, user_id: str = "anonymous"
    ) -> list[TextContent]:
        """Get conversation summary statistics"""
        conv_logger = get_conversation_logger()
        summary = conv_logger.get_conversation_summary(conversation_id, user_id)

        if not summary:
            return [TextContent(type="text", text=f"No conversation found with ID: {conversation_id}")]

        output = "=== Conversation Summary ===\n"
        output += f"ID: {summary['conversation_id']}\n"
        output += f"User: {summary['user_id']}\n"
        output += f"Messages: {summary['message_count']}\n"
        output += f"Tools Used: {', '.join(summary['tools_used'])}\n\n"

        output += "Execution Time:\n"
        output += f"  Total: {summary['total_execution_time_ms']:.1f}ms\n"
        output += f"  Average per call: {summary['avg_execution_time_ms']:.1f}ms\n\n"

        output += "Results:\n"
        output += f"  Success: {summary['success_count']}\n"
        output += f"  Errors: {summary['error_count']}\n"
        output += f"  Success Rate: {summary['success_rate']:.1f}%\n\n"

        output += "Time Range:\n"
        output += f"  First: {summary['first_message_time']}\n"
        output += f"  Last: {summary['last_message_time']}\n"

        return [TextContent(type="text", text=output)]



    @app.tool(
        name="get_tool_usage_stats",
        description="""Get tool usage statistics for a user.

    This tool analyzes which tools have been used most frequently,
    their success rates, and how many conversations they appear in.

    PARAMETERS:
    - user_id: Optional user identifier (default: "anonymous")

    RETURNS:
    - Tool usage statistics including:
      - Total number of times each tool was used
      - Success/error counts per tool
      - Success rate percentage
      - Number of conversations containing each tool

    EXAMPLE:
    - user_id="user123" → Returns their tool usage patterns
    """,
    )
    async def get_tool_usage_stats(user_id: str = "anonymous") -> list[TextContent]:
        """Get tool usage statistics for a user"""
        conv_logger = get_conversation_logger()
        stats = conv_logger.get_tool_usage_stats(user_id)

        output = f"=== Tool Usage Statistics for {user_id} ===\n"
        output += f"Total Conversations: {stats['total_conversations']}\n"
        output += f"Total Tool Calls: {stats['total_tool_calls']}\n"
        output += "=" * 80 + "\n\n"

        if not stats["tools"]:
            output += "No tool usage found.\n"
        else:
            # Sort by usage count
            sorted_tools = sorted(stats["tools"].items(), key=lambda x: x[1]["uses"], reverse=True)

            for tool_name, tool_stats in sorted_tools:
                output += f"Tool: {tool_name}\n"
                output += f"  Uses: {tool_stats['uses']}\n"
                output += f"  Success Rate: {tool_stats['success_rate']:.1f}%\n"
                output += f"  Successes: {tool_stats['success_count']}\n"
                output += f"  Errors: {tool_stats['error_count']}\n"
                output += f"  Conversations: {tool_stats['conversations']}\n\n"

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


    logger_instance.info("Conversation management tools registered successfully")
