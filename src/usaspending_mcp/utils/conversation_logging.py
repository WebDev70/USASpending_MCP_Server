"""
Conversation logging for MCP tool interactions.

Stores complete conversation context including tool calls, parameters, responses,
and execution metrics for debugging, analytics, and conversation reconstruction.
"""

import json
import logging
import time
from datetime import datetime
from functools import wraps
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4
import inspect

logger = logging.getLogger(__name__)

# Default conversations storage location
CONVERSATIONS_BASE_DIR = Path("/tmp/mcp_conversations")


class ConversationLogger:
    """Log and retrieve MCP conversation context."""

    def __init__(
        self,
        conversations_dir: Optional[Path] = None,
        config: Optional[Dict] = None
    ):
        """
        Initialize conversation logger.

        Args:
            conversations_dir: Optional custom path for conversations storage
            config: Optional configuration dict with keys:
                - conversations_dir: Directory for conversation files (default: /tmp/mcp_conversations)
                - max_message_length: Max chars to store per response (default: None, unlimited)
        """
        self.config = config or {}

        # Determine conversations directory
        if conversations_dir:
            self.conversations_dir = conversations_dir
        else:
            self.conversations_dir = Path(
                self.config.get("conversations_dir", CONVERSATIONS_BASE_DIR)
            )

        self.conversations_dir.mkdir(parents=True, exist_ok=True)
        self.max_message_length = self.config.get("max_message_length", None)

        logger.debug(f"ConversationLogger initialized at {self.conversations_dir}")

    def log_tool_call(
        self,
        tool_name: str,
        input_params: Dict[str, Any],
        output_response: str,
        execution_time_ms: float,
        user_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
        message_index: Optional[int] = None,
        status: str = "success",
        error_message: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Log a tool call within a conversation.

        Args:
            tool_name: Name of the tool called
            input_params: Dictionary of input parameters
            output_response: The response/output from the tool
            execution_time_ms: Execution time in milliseconds
            user_id: Optional user identifier
            conversation_id: Optional conversation ID (auto-generated if None)
            message_index: Optional message sequence number
            status: Status of execution (success, error, timeout)
            error_message: Optional error message if status is error
            metadata: Optional additional metadata

        Returns:
            Dictionary with logged record including conversation_id
        """
        # Generate IDs if not provided
        conversation_id = conversation_id or str(uuid4())
        user_id = user_id or "anonymous"

        # Truncate response if needed
        response_text = output_response
        if self.max_message_length and len(response_text) > self.max_message_length:
            response_text = (
                response_text[:self.max_message_length]
                + f"\n[... truncated {len(output_response) - self.max_message_length} chars ...]"
            )

        record = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "conversation_id": conversation_id,
            "user_id": user_id,
            "message_index": message_index,
            "tool_name": tool_name,
            "status": status,
            "execution_time_ms": execution_time_ms,
            "input_params": input_params,
            "output_response": response_text,
            "error_message": error_message,
        }

        # Add optional metadata
        if metadata:
            record.update(metadata)

        # Store to file with user_id and conversation_id naming
        conversation_file = (
            self.conversations_dir / user_id / f"{conversation_id}.jsonl"
        )
        conversation_file.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(conversation_file, "a") as f:
                f.write(json.dumps(record) + "\n")
            logger.debug(
                f"Logged tool call: {tool_name} in conversation {conversation_id}"
            )
        except Exception as e:
            logger.error(f"Failed to log conversation: {e}")

        return record

    def get_conversation(
        self,
        conversation_id: str,
        user_id: str = "anonymous"
    ) -> List[Dict[str, Any]]:
        """
        Retrieve a complete conversation by ID.

        Args:
            conversation_id: The conversation ID
            user_id: The user ID (default: anonymous)

        Returns:
            List of tool call records in chronological order
        """
        conversation_file = (
            self.conversations_dir / user_id / f"{conversation_id}.jsonl"
        )

        if not conversation_file.exists():
            logger.warning(f"Conversation {conversation_id} not found for user {user_id}")
            return []

        records = []
        try:
            with open(conversation_file, "r") as f:
                for line in f:
                    records.append(json.loads(line))
            logger.debug(f"Retrieved {len(records)} records from conversation {conversation_id}")
            return records
        except Exception as e:
            logger.error(f"Failed to retrieve conversation {conversation_id}: {e}")
            return []

    def list_user_conversations(
        self,
        user_id: str = "anonymous",
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        List all conversations for a user.

        Args:
            user_id: The user ID
            limit: Maximum conversations to return

        Returns:
            List of conversation metadata (ID, tool count, timestamps)
        """
        user_dir = self.conversations_dir / user_id
        if not user_dir.exists():
            return []

        conversations = []
        try:
            for conv_file in sorted(user_dir.glob("*.jsonl"), key=lambda x: x.stat().st_mtime, reverse=True)[:limit]:
                conversation_id = conv_file.stem
                records = []
                with open(conv_file, "r") as f:
                    records = [json.loads(line) for line in f]

                if records:
                    conversations.append({
                        "conversation_id": conversation_id,
                        "user_id": user_id,
                        "message_count": len(records),
                        "first_message": records[0]["timestamp"],
                        "last_message": records[-1]["timestamp"],
                        "tools_used": list(set(r["tool_name"] for r in records)),
                        "success_count": sum(1 for r in records if r["status"] == "success"),
                        "error_count": sum(1 for r in records if r["status"] == "error"),
                    })
        except Exception as e:
            logger.error(f"Failed to list conversations for user {user_id}: {e}")

        return conversations

    def search_conversations(
        self,
        tool_name: Optional[str] = None,
        user_id: str = "anonymous",
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search conversations by tool name.

        Args:
            tool_name: Filter by specific tool name
            user_id: The user ID
            limit: Maximum conversations to return

        Returns:
            List of matching conversations with metadata
        """
        conversations = self.list_user_conversations(user_id, limit=100)

        if tool_name:
            conversations = [
                c for c in conversations
                if tool_name in c.get("tools_used", [])
            ]

        return conversations[:limit]

    def get_conversation_summary(
        self,
        conversation_id: str,
        user_id: str = "anonymous"
    ) -> Optional[Dict[str, Any]]:
        """
        Get summary statistics for a conversation.

        Args:
            conversation_id: The conversation ID
            user_id: The user ID

        Returns:
            Dictionary with conversation statistics
        """
        records = self.get_conversation(conversation_id, user_id)

        if not records:
            return None

        total_time_ms = sum(r.get("execution_time_ms", 0) for r in records)
        success_count = sum(1 for r in records if r.get("status") == "success")
        error_count = sum(1 for r in records if r.get("status") == "error")

        return {
            "conversation_id": conversation_id,
            "user_id": user_id,
            "message_count": len(records),
            "tools_used": list(set(r["tool_name"] for r in records)),
            "first_message_time": records[0]["timestamp"],
            "last_message_time": records[-1]["timestamp"],
            "total_execution_time_ms": total_time_ms,
            "avg_execution_time_ms": total_time_ms / len(records) if records else 0,
            "success_count": success_count,
            "error_count": error_count,
            "success_rate": (success_count / len(records) * 100) if records else 0,
            "status_breakdown": {
                "success": success_count,
                "error": error_count,
                "other": len(records) - success_count - error_count,
            }
        }

    def get_tool_usage_stats(
        self,
        user_id: str = "anonymous"
    ) -> Dict[str, Any]:
        """
        Get statistics on tool usage for a user.

        Args:
            user_id: The user ID

        Returns:
            Dictionary with tool usage statistics
        """
        conversations = self.list_user_conversations(user_id, limit=1000)
        tool_stats = {}

        for conv in conversations:
            for tool in conv.get("tools_used", []):
                if tool not in tool_stats:
                    tool_stats[tool] = {
                        "uses": 0,
                        "success_count": 0,
                        "error_count": 0,
                        "conversations": 0,
                    }
                tool_stats[tool]["uses"] += conv["message_count"]
                tool_stats[tool]["success_count"] += conv["success_count"]
                tool_stats[tool]["error_count"] += conv["error_count"]
                tool_stats[tool]["conversations"] += 1

        # Calculate success rates
        for tool, stats in tool_stats.items():
            stats["success_rate"] = (
                (stats["success_count"] / stats["uses"] * 100)
                if stats["uses"] > 0
                else 0
            )

        return {
            "user_id": user_id,
            "total_conversations": len(conversations),
            "total_tool_calls": sum(c["message_count"] for c in conversations),
            "tools": tool_stats,
        }

    def export_conversation(
        self,
        conversation_id: str,
        user_id: str = "anonymous",
        format: str = "json"
    ) -> Optional[str]:
        """
        Export a conversation in various formats.

        Args:
            conversation_id: The conversation ID
            user_id: The user ID
            format: Export format (json, txt, csv)

        Returns:
            Formatted conversation string
        """
        records = self.get_conversation(conversation_id, user_id)

        if not records:
            return None

        if format == "json":
            return json.dumps(records, indent=2)

        elif format == "txt":
            lines = [
                f"=== Conversation {conversation_id} ===",
                f"User: {user_id}",
                f"Messages: {len(records)}",
                ""
            ]
            for i, record in enumerate(records, 1):
                lines.append(f"--- Message {i} ---")
                lines.append(f"Tool: {record['tool_name']}")
                lines.append(f"Time: {record['timestamp']}")
                lines.append(f"Status: {record['status']}")
                lines.append(f"Duration: {record.get('execution_time_ms', 0):.0f}ms")
                lines.append(f"\nInput: {json.dumps(record.get('input_params', {}), indent=2)}")
                lines.append(f"\nOutput:\n{record.get('output_response', '')}")
                if record.get("error_message"):
                    lines.append(f"\nError: {record['error_message']}")
                lines.append("")

            return "\n".join(lines)

        elif format == "csv":
            lines = [
                "timestamp,conversation_id,user_id,tool_name,status,execution_time_ms"
            ]
            for record in records:
                lines.append(
                    f"{record['timestamp']},{record['conversation_id']},{record['user_id']},"
                    f"{record['tool_name']},{record['status']},{record['execution_time_ms']}"
                )
            return "\n".join(lines)

        return None


# Global conversation logger instance
_conversation_logger: Optional[ConversationLogger] = None


def initialize_conversation_logger(
    config: Optional[Dict] = None
) -> ConversationLogger:
    """
    Initialize global conversation logger instance.

    Args:
        config: Optional configuration dictionary

    Returns:
        ConversationLogger instance
    """
    global _conversation_logger
    _conversation_logger = ConversationLogger(config=config)
    logger.info("Conversation logger initialized")
    return _conversation_logger


def get_conversation_logger() -> ConversationLogger:
    """
    Get or create global conversation logger instance.

    Returns:
        ConversationLogger instance
    """
    global _conversation_logger
    if _conversation_logger is None:
        _conversation_logger = ConversationLogger()
    return _conversation_logger


def log_conversation(
    user_id: Optional[str] = None,
    conversation_id: Optional[str] = None
):
    """
    Decorator to automatically log MCP tool calls to conversation history.

    Captures tool name, input parameters, output response, execution time,
    and status. Should be applied after @app.tool decorator.

    Usage:
        @app.tool(name="search_awards", description="...")
        @log_conversation(user_id="user123", conversation_id="conv456")
        async def search_awards(query: str) -> list[TextContent]:
            ...

    Args:
        user_id: Optional user identifier (default: anonymous)
        conversation_id: Optional conversation ID (auto-generated if None)
    """

    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            conv_logger = get_conversation_logger()
            start_time = time.time()
            tool_name = func.__name__
            status = "success"
            error_msg = None
            output_text = ""

            try:
                # Call the tool function
                result = await func(*args, **kwargs)

                # Extract text from TextContent response
                if isinstance(result, list):
                    # Handle list[TextContent]
                    output_parts = []
                    for item in result:
                        if hasattr(item, 'text'):
                            output_parts.append(item.text)
                        else:
                            output_parts.append(str(item))
                    output_text = "\n".join(output_parts)
                else:
                    output_text = str(result)

            except Exception as e:
                status = "error"
                error_msg = str(e)
                output_text = f"Error: {error_msg}"

            # Calculate execution time
            execution_time_ms = (time.time() - start_time) * 1000

            # Log to conversation
            conv_logger.log_tool_call(
                tool_name=tool_name,
                input_params=dict(kwargs) if kwargs else {},
                output_response=output_text,
                execution_time_ms=execution_time_ms,
                user_id=user_id or "anonymous",
                conversation_id=conversation_id,
                status=status,
                error_message=error_msg
            )

            # Re-raise if there was an error
            if status == "error":
                raise Exception(error_msg)

            return result

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            conv_logger = get_conversation_logger()
            start_time = time.time()
            tool_name = func.__name__
            status = "success"
            error_msg = None
            output_text = ""

            try:
                # Call the tool function
                result = func(*args, **kwargs)

                # Extract text from TextContent response
                if isinstance(result, list):
                    output_parts = []
                    for item in result:
                        if hasattr(item, 'text'):
                            output_parts.append(item.text)
                        else:
                            output_parts.append(str(item))
                    output_text = "\n".join(output_parts)
                else:
                    output_text = str(result)

            except Exception as e:
                status = "error"
                error_msg = str(e)
                output_text = f"Error: {error_msg}"

            # Calculate execution time
            execution_time_ms = (time.time() - start_time) * 1000

            # Log to conversation
            conv_logger.log_tool_call(
                tool_name=tool_name,
                input_params=dict(kwargs) if kwargs else {},
                output_response=output_text,
                execution_time_ms=execution_time_ms,
                user_id=user_id or "anonymous",
                conversation_id=conversation_id,
                status=status,
                error_message=error_msg
            )

            # Re-raise if there was an error
            if status == "error":
                raise Exception(error_msg)

            return result

        # Detect async vs sync
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator
