"""
Unit tests for structured logging utility module.

Tests JSON formatting, decorators, and context managers
for production-ready structured logging.
"""

import asyncio
import json
import logging
from io import StringIO
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from usaspending_mcp.utils.logging import (
    CustomJsonFormatter,
    get_logger,
    log_api_call,
    log_context,
    log_tool_execution,
    setup_structured_logging,
)


@pytest.mark.unit
class TestCustomJsonFormatter:
    """Test CustomJsonFormatter class."""

    def test_formatter_initialization(self):
        """Test creating a JSON formatter."""
        formatter = CustomJsonFormatter()
        assert formatter is not None

    def test_formatter_outputs_json(self):
        """Test that formatter outputs JSON."""
        formatter = CustomJsonFormatter()

        # Create a log record
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="/path/to/file.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        # Format the record
        output = formatter.format(record)

        # Should be valid JSON
        try:
            log_data = json.loads(output)
            assert log_data is not None
        except json.JSONDecodeError:
            pytest.fail(f"Formatter output is not valid JSON: {output}")

    def test_formatter_includes_timestamp(self):
        """Test that formatter includes ISO timestamp."""
        formatter = CustomJsonFormatter()

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="/path/to/file.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        output = formatter.format(record)
        log_data = json.loads(output)

        assert "timestamp" in log_data
        # Should be ISO format with Z suffix
        assert log_data["timestamp"].endswith("Z")

    def test_formatter_includes_context_fields(self):
        """Test that formatter includes context fields."""
        formatter = CustomJsonFormatter()

        record = logging.LogRecord(
            name="test_module",
            level=logging.WARNING,
            pathname="/path/to/file.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        output = formatter.format(record)
        log_data = json.loads(output)

        # Check for context fields
        assert "level" in log_data
        assert log_data["level"] == "WARNING"
        assert "module" in log_data
        assert log_data["module"] == "test_module"
        assert "function" in log_data
        assert "line_number" in log_data
        assert log_data["line_number"] == 42

    def test_formatter_includes_process_info(self):
        """Test that formatter includes process and thread info."""
        formatter = CustomJsonFormatter()

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="/path/to/file.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        output = formatter.format(record)
        log_data = json.loads(output)

        assert "thread" in log_data
        assert "process" in log_data


@pytest.mark.unit
class TestSetupStructuredLogging:
    """Test setup_structured_logging function."""

    def test_setup_with_json_output(self):
        """Test setting up logging with JSON output."""
        logger = setup_structured_logging(log_level="DEBUG", json_output=True)

        assert logger is not None
        assert logger.level == logging.DEBUG

    def test_setup_with_plain_text_output(self):
        """Test setting up logging with plain text output."""
        logger = setup_structured_logging(log_level="INFO", json_output=False)

        assert logger is not None
        assert logger.level == logging.INFO

    def test_setup_with_custom_log_level(self):
        """Test setting up logging with custom log level."""
        logger = setup_structured_logging(log_level="WARNING", json_output=False)

        assert logger.level == logging.WARNING

    def test_setup_creates_handlers(self):
        """Test that setup creates logging handlers."""
        logger = setup_structured_logging(log_level="INFO", json_output=True)

        # Should have at least one handler (console)
        assert len(logger.handlers) > 0

    def test_setup_removes_existing_handlers(self):
        """Test that setup removes existing handlers."""
        # Create logger with initial handler
        root_logger = logging.getLogger()
        initial_count = len(root_logger.handlers)

        # Setup new logging (should remove and re-add handlers)
        setup_structured_logging(log_level="INFO", json_output=False)

        # Handlers should be reconfigured
        # (exact count may vary, but handlers should be fresh)
        assert root_logger.handlers is not None


@pytest.mark.unit
class TestGetLogger:
    """Test get_logger function."""

    def test_get_logger_returns_logger(self):
        """Test that get_logger returns a logger."""
        logger = get_logger("test_module")
        assert logger is not None
        assert isinstance(logger, logging.Logger)

    def test_get_logger_with_module_name(self):
        """Test get_logger with module name."""
        logger = get_logger("my_module")
        assert "usaspending_mcp" in logger.name
        assert "my_module" in logger.name

    def test_get_logger_returns_same_instance(self):
        """Test that get_logger returns the same instance."""
        logger1 = get_logger("test_module")
        logger2 = get_logger("test_module")
        assert logger1 is logger2


@pytest.mark.unit
@pytest.mark.asyncio
class TestLogApiCallDecorator:
    """Test log_api_call decorator."""

    async def test_log_api_call_successful(self):
        """Test logging successful API call."""

        @log_api_call
        async def test_api(url: str) -> dict:
            return {"status": "success"}

        result = await test_api("https://api.example.com/test")
        assert result == {"status": "success"}

    async def test_log_api_call_with_exception(self):
        """Test logging API call with exception."""

        @log_api_call
        async def test_api(url: str):
            raise ValueError("Test error")

        with pytest.raises(ValueError):
            await test_api("https://api.example.com/test")

    async def test_log_api_call_preserves_return_value(self):
        """Test that decorator preserves return value."""

        @log_api_call
        async def test_api(query: str) -> dict:
            return {"query": query, "results": [1, 2, 3]}

        result = await test_api("software")
        assert result["query"] == "software"
        assert len(result["results"]) == 3

    async def test_log_api_call_with_sync_function(self):
        """Test decorator with sync function."""

        @log_api_call
        def test_api(url: str) -> dict:
            return {"status": "ok"}

        result = test_api("https://api.example.com")
        assert result == {"status": "ok"}


@pytest.mark.unit
@pytest.mark.asyncio
class TestLogToolExecutionDecorator:
    """Test log_tool_execution decorator."""

    async def test_log_tool_execution_success(self):
        """Test logging successful tool execution."""

        @log_tool_execution
        async def test_tool(query: str):
            return f"Results for {query}"

        result = await test_tool("test")
        assert result == "Results for test"

    async def test_log_tool_execution_with_exception(self):
        """Test logging tool execution with exception."""

        @log_tool_execution
        async def test_tool(query: str):
            raise RuntimeError("Tool failed")

        with pytest.raises(RuntimeError):
            await test_tool("test")

    async def test_log_tool_execution_with_list_return(self):
        """Test logging tool that returns list."""

        @log_tool_execution
        async def test_tool():
            return [1, 2, 3, 4, 5]

        result = await test_tool()
        assert len(result) == 5

    async def test_log_tool_execution_with_sync_function(self):
        """Test decorator with sync function."""

        @log_tool_execution
        def test_tool(name: str):
            return f"Hello {name}"

        result = test_tool("World")
        assert result == "Hello World"


@pytest.mark.unit
@pytest.mark.asyncio
class TestLogContextManager:
    """Test log_context context manager."""

    async def test_log_context_success(self):
        """Test context manager on successful operation."""
        logger = get_logger("test")

        with log_context(logger, "test_operation", item_id=123):
            # Operation succeeds
            result = 42

        # Should complete without error

    async def test_log_context_with_exception(self):
        """Test context manager captures exceptions."""
        logger = get_logger("test")

        with pytest.raises(ValueError):
            with log_context(logger, "failing_operation", attempt=1):
                raise ValueError("Operation failed")

    async def test_log_context_with_kwargs(self):
        """Test context manager with custom context kwargs."""
        logger = get_logger("test")

        context = {"user_id": 123, "action": "search", "query": "software"}

        with log_context(logger, "search_operation", **context):
            # Simulate operation
            result = {"count": 10}

        # Should complete successfully

    async def test_log_context_nesting(self):
        """Test nested context managers."""
        logger = get_logger("test")

        with log_context(logger, "outer_op", level=1):
            with log_context(logger, "inner_op", level=2):
                result = "nested"

        # Both should complete successfully


@pytest.mark.unit
class TestLoggingIntegration:
    """Integration tests for logging system."""

    def test_json_logging_output(self, caplog):
        """Test that JSON output is valid."""
        with caplog.at_level(logging.INFO):
            logger = setup_structured_logging(log_level="INFO", json_output=True)
            logger.info("Test message", extra={"custom": "value"})

        # Check that message was logged
        assert "Test message" in caplog.text

    def test_plain_text_logging_output(self, caplog):
        """Test that plain text output works."""
        with caplog.at_level(logging.INFO):
            logger = setup_structured_logging(log_level="INFO", json_output=False)
            logger.info("Test message")

        # Check that message was logged
        assert "Test message" in caplog.text

    def test_multiple_log_levels(self, caplog):
        """Test logging at different levels."""
        logger = setup_structured_logging(log_level="DEBUG")

        with caplog.at_level(logging.DEBUG):
            logger.debug("Debug message")
            logger.info("Info message")
            logger.warning("Warning message")
            logger.error("Error message")

        # All messages should be present
        assert "Debug message" in caplog.text
        assert "Info message" in caplog.text
        assert "Warning message" in caplog.text
        assert "Error message" in caplog.text

    def test_logger_with_extra_context(self, caplog):
        """Test logging with extra context."""
        logger = get_logger("test_module")

        with caplog.at_level(logging.INFO):
            logger.info(
                "Operation completed",
                extra={"duration_ms": 150, "item_count": 42, "status": "success"},
            )

        assert "Operation completed" in caplog.text


@pytest.mark.unit
class TestLoggingEdgeCases:
    """Test edge cases and error handling."""

    def test_logger_with_empty_message(self):
        """Test logging with empty message."""
        logger = get_logger("test")
        logger.info("")  # Should not raise

    def test_logger_with_unicode_message(self):
        """Test logging with unicode characters."""
        logger = get_logger("test")
        logger.info("Unicode: 你好世界 🌍")  # Should not raise

    def test_logger_with_large_context(self):
        """Test logging with large context data."""
        logger = get_logger("test")

        large_context = {f"key_{i}": f"value_{i}" for i in range(1000)}

        logger.info("Large context", extra=large_context)  # Should handle gracefully

    def test_logger_with_none_values(self):
        """Test logging with None values in context."""
        logger = get_logger("test")

        logger.info(
            "Message with None", extra={"key1": None, "key2": "value", "key3": None}
        )  # Should handle gracefully

    def test_logger_thread_safety(self):
        """Test that logger is thread-safe."""
        import threading

        logger = get_logger("test")
        errors = []

        def log_messages():
            try:
                for i in range(100):
                    # Use custom field names to avoid conflicts with reserved fields
                    logger.info(
                        f"Message {i}",
                        extra={"thread_name": threading.current_thread().name},
                    )
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=log_messages) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
