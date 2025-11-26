"""
Unit tests for conversation logging functionality.

Tests the ConversationLogger class to ensure proper logging, retrieval,
and analysis of MCP tool interactions.
"""

import json
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from usaspending_mcp.utils.conversation_logging import (
    ConversationLogger,
    get_conversation_logger,
    initialize_conversation_logger,
    log_conversation,
)


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test conversations."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def conversation_logger(temp_dir):
    """Create a conversation logger with temporary directory."""
    return ConversationLogger(conversations_dir=temp_dir)


class TestConversationLogger:
    """Test ConversationLogger functionality."""

    def test_log_tool_call(self, conversation_logger):
        """Test logging a single tool call."""
        result = conversation_logger.log_tool_call(
            tool_name="search_federal_awards",
            input_params={"query": "software development"},
            output_response="Found 5 awards",
            execution_time_ms=123.45,
            user_id="test_user",
            conversation_id="conv123",
        )

        assert result["tool_name"] == "search_federal_awards"
        assert result["status"] == "success"
        assert result["execution_time_ms"] == 123.45
        assert result["user_id"] == "test_user"
        assert result["conversation_id"] == "conv123"

    def test_log_tool_call_with_error(self, conversation_logger):
        """Test logging a tool call with error."""
        result = conversation_logger.log_tool_call(
            tool_name="get_award_by_id",
            input_params={"award_id": "invalid"},
            output_response="",
            execution_time_ms=50.0,
            status="error",
            error_message="Award not found",
        )

        assert result["status"] == "error"
        assert result["error_message"] == "Award not found"

    def test_get_conversation(self, conversation_logger):
        """Test retrieving a conversation."""
        conv_id = "test_conv_123"
        user_id = "test_user"

        # Log multiple tool calls in same conversation
        for i in range(3):
            conversation_logger.log_tool_call(
                tool_name=f"tool_{i}",
                input_params={"index": i},
                output_response=f"Result {i}",
                execution_time_ms=100.0 + i,
                user_id=user_id,
                conversation_id=conv_id,
            )

        # Retrieve the conversation
        records = conversation_logger.get_conversation(conv_id, user_id)

        assert len(records) == 3
        assert records[0]["tool_name"] == "tool_0"
        assert records[2]["tool_name"] == "tool_2"

    def test_get_nonexistent_conversation(self, conversation_logger):
        """Test retrieving a nonexistent conversation."""
        records = conversation_logger.get_conversation("nonexistent", "test_user")
        assert records == []

    def test_list_user_conversations(self, conversation_logger):
        """Test listing all conversations for a user."""
        user_id = "test_user"

        # Create multiple conversations
        for conv_id in ["conv1", "conv2", "conv3"]:
            for i in range(2):
                conversation_logger.log_tool_call(
                    tool_name="search_federal_awards",
                    input_params={"query": f"test_{i}"},
                    output_response=f"Results {i}",
                    execution_time_ms=100.0,
                    user_id=user_id,
                    conversation_id=conv_id,
                )

        conversations = conversation_logger.list_user_conversations(user_id)

        assert len(conversations) == 3
        assert conversations[0]["message_count"] == 2
        assert "search_federal_awards" in conversations[0]["tools_used"]

    def test_get_conversation_summary(self, conversation_logger):
        """Test getting conversation summary."""
        conv_id = "test_conv_summary"
        user_id = "test_user"

        # Log successful and failed calls
        conversation_logger.log_tool_call(
            tool_name="search_federal_awards",
            input_params={"query": "test"},
            output_response="Found 5 awards",
            execution_time_ms=100.0,
            user_id=user_id,
            conversation_id=conv_id,
            status="success",
        )

        conversation_logger.log_tool_call(
            tool_name="get_award_by_id",
            input_params={"award_id": "bad"},
            output_response="",
            execution_time_ms=50.0,
            user_id=user_id,
            conversation_id=conv_id,
            status="error",
            error_message="Not found",
        )

        summary = conversation_logger.get_conversation_summary(conv_id, user_id)

        assert summary is not None
        assert summary["message_count"] == 2
        assert summary["success_count"] == 1
        assert summary["error_count"] == 1
        assert summary["success_rate"] == 50.0
        assert "search_federal_awards" in summary["tools_used"]
        assert "get_award_by_id" in summary["tools_used"]

    def test_get_tool_usage_stats(self, conversation_logger):
        """Test getting tool usage statistics."""
        user_id = "test_user"

        # Log several tool calls
        conversation_logger.log_tool_call(
            tool_name="search_federal_awards",
            input_params={"query": "test"},
            output_response="Found 5 awards",
            execution_time_ms=100.0,
            user_id=user_id,
            status="success",
        )

        conversation_logger.log_tool_call(
            tool_name="search_federal_awards",
            input_params={"query": "test2"},
            output_response="Found 3 awards",
            execution_time_ms=80.0,
            user_id=user_id,
            status="success",
        )

        conversation_logger.log_tool_call(
            tool_name="get_award_by_id",
            input_params={"award_id": "123"},
            output_response="Award details",
            execution_time_ms=50.0,
            user_id=user_id,
            status="success",
        )

        stats = conversation_logger.get_tool_usage_stats(user_id)

        assert stats["total_tool_calls"] == 3
        assert "search_federal_awards" in stats["tools"]
        assert "get_award_by_id" in stats["tools"]
        assert stats["tools"]["search_federal_awards"]["uses"] == 2
        assert stats["tools"]["get_award_by_id"]["uses"] == 1
        assert stats["tools"]["search_federal_awards"]["success_rate"] == 100.0

    def test_export_conversation_json(self, conversation_logger):
        """Test exporting conversation as JSON."""
        conv_id = "test_conv_export"
        user_id = "test_user"

        conversation_logger.log_tool_call(
            tool_name="search_federal_awards",
            input_params={"query": "test"},
            output_response="Found 5 awards",
            execution_time_ms=100.0,
            user_id=user_id,
            conversation_id=conv_id,
        )

        export = conversation_logger.export_conversation(conv_id, user_id, format="json")

        assert export is not None
        data = json.loads(export)
        assert len(data) == 1
        assert data[0]["tool_name"] == "search_federal_awards"

    def test_export_conversation_txt(self, conversation_logger):
        """Test exporting conversation as text."""
        conv_id = "test_conv_export_txt"
        user_id = "test_user"

        conversation_logger.log_tool_call(
            tool_name="search_federal_awards",
            input_params={"query": "test"},
            output_response="Found 5 awards",
            execution_time_ms=100.0,
            user_id=user_id,
            conversation_id=conv_id,
        )

        export = conversation_logger.export_conversation(conv_id, user_id, format="txt")

        assert export is not None
        assert "Conversation" in export
        assert "search_federal_awards" in export
        assert "Found 5 awards" in export

    def test_response_truncation(self):
        """Test response text truncation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = ConversationLogger(
                conversations_dir=Path(tmpdir), config={"max_message_length": 50}
            )

            long_response = "A" * 200

            result = logger.log_tool_call(
                tool_name="test_tool",
                input_params={},
                output_response=long_response,
                execution_time_ms=100.0,
            )

            # Verify truncation
            assert len(result["output_response"]) < len(long_response)
            assert "[... truncated" in result["output_response"]

    def test_anonymous_user_default(self, conversation_logger):
        """Test that anonymous user is used by default."""
        result = conversation_logger.log_tool_call(
            tool_name="test_tool",
            input_params={},
            output_response="Result",
            execution_time_ms=100.0,
            # Note: no user_id specified
        )

        assert result["user_id"] == "anonymous"

    def test_auto_conversation_id_generation(self, conversation_logger):
        """Test that conversation ID is auto-generated if not provided."""
        result = conversation_logger.log_tool_call(
            tool_name="test_tool",
            input_params={},
            output_response="Result",
            execution_time_ms=100.0,
            # Note: no conversation_id specified
        )

        assert result["conversation_id"] is not None
        assert len(result["conversation_id"]) > 0

    def test_initialize_and_get_logger(self):
        """Test global logger initialization and retrieval."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = {"conversations_dir": tmpdir}
            logger = initialize_conversation_logger(config=config)

            assert logger is not None
            assert isinstance(logger, ConversationLogger)

            # Get the same logger instance
            logger2 = get_conversation_logger()
            assert logger2 is logger


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
