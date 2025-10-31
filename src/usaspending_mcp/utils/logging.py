"""
Structured logging configuration for USASpending MCP Server.

Provides JSON-formatted logs with structured context for better
observability and debugging in production environments.
"""

import logging
import logging.handlers
import sys
import json
import time
from datetime import datetime
from typing import Any, Optional
from pathlib import Path
from pythonjsonlogger import jsonlogger
from functools import wraps
from contextlib import contextmanager


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter with additional context fields."""

    def add_fields(self, log_record: dict, record: logging.LogRecord, message_dict: dict) -> None:
        """Add custom fields to log record."""
        super().add_fields(log_record, record, message_dict)

        # Add timestamp in ISO format
        log_record["timestamp"] = datetime.utcnow().isoformat() + "Z"

        # Add log level name
        log_record["level"] = record.levelname

        # Add module name
        log_record["module"] = record.name

        # Add thread and process info for debugging
        log_record["thread"] = record.thread
        log_record["process"] = record.process

        # Add function and line number
        log_record["function"] = record.funcName
        log_record["line_number"] = record.lineno

        # Remove message if it's already in log_record (avoid duplication)
        if "message" not in log_record:
            log_record["message"] = message_dict.get("message", record.getMessage())


def setup_structured_logging(
    log_level: str = "INFO",
    json_output: bool = True,
    log_file: Optional[str] = None,
) -> logging.Logger:
    """
    Configure structured logging for the application.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_output: If True, output JSON format; if False, use plain text
        log_file: Optional file path to write logs to (uses default if not specified)

    Returns:
        Configured logger instance
    """
    # Remove existing handlers
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Set root logger level - use WARNING for third-party libraries
    root_logger.setLevel(getattr(logging, log_level))

    # Suppress verbose logging from mcp and fastmcp libraries (especially during stdio mode)
    logging.getLogger("mcp").setLevel(logging.WARNING)
    logging.getLogger("fastmcp").setLevel(logging.WARNING)
    logging.getLogger("uvicorn").setLevel(logging.WARNING)

    # Create formatters
    if json_output:
        formatter = CustomJsonFormatter(
            fmt="%(timestamp)s %(level)s %(name)s %(message)s"
        )
        file_formatter = logging.Formatter(
            fmt="%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    else:
        formatter = logging.Formatter(
            fmt="%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_formatter = formatter

    # Console handler - use stderr to avoid interfering with stdout streams (MCP protocol, etc)
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Set up file logging with automatic rotation
    # If no log file specified, use default location in project logs directory
    if log_file is None:
        # Get the project root (go up from src/usaspending_mcp/utils/)
        project_root = Path(__file__).resolve().parent.parent.parent.parent
        logs_dir = project_root / "logs"
        logs_dir.mkdir(exist_ok=True)
        log_file = str(logs_dir / "usaspending_mcp.log")

    # Create logs directory if it doesn't exist
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    # All logs file handler with rotation (10 MB per file, keep 5 backups)
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=5
    )
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)

    # Error log file handler (only ERROR and CRITICAL)
    error_log_file = str(log_path.parent / "usaspending_mcp_errors.log")
    error_handler = logging.handlers.RotatingFileHandler(
        error_log_file,
        maxBytes=5 * 1024 * 1024,  # 5 MB
        backupCount=3
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(file_formatter)
    root_logger.addHandler(error_handler)

    # Get application logger
    app_logger = logging.getLogger("usaspending_mcp")
    return app_logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger for a specific module."""
    return logging.getLogger(f"usaspending_mcp.{name}")


def log_api_call(func):
    """
    Decorator to log API calls with timing and error information.

    Usage:
        @log_api_call
        async def my_api_function(url: str, params: dict) -> dict:
            ...
    """

    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        logger = logging.getLogger("usaspending_mcp.api")
        start_time = time.time()
        call_id = datetime.utcnow().timestamp()

        # Extract useful context from arguments
        url = kwargs.get("url") or (args[1] if len(args) > 1 else "unknown")
        method = kwargs.get("method") or (args[0] if len(args) > 0 else "unknown")

        logger.info(
            "API call started",
            extra={
                "call_id": call_id,
                "method": method,
                "url": url,
                "extra_context": {
                    "params_keys": list(kwargs.get("params", {}).keys())
                    if "params" in kwargs
                    else [],
                },
            },
        )

        try:
            result = await func(*args, **kwargs)
            elapsed = time.time() - start_time

            logger.info(
                "API call succeeded",
                extra={
                    "call_id": call_id,
                    "method": method,
                    "url": url,
                    "duration_seconds": round(elapsed, 3),
                    "status": "success",
                },
            )
            return result

        except Exception as e:
            elapsed = time.time() - start_time

            logger.error(
                f"API call failed: {str(e)}",
                extra={
                    "call_id": call_id,
                    "method": method,
                    "url": url,
                    "duration_seconds": round(elapsed, 3),
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "status": "error",
                },
                exc_info=True,
            )
            raise

    @wraps(func)
    def sync_wrapper(*args, **kwargs):
        logger = logging.getLogger("usaspending_mcp.api")
        start_time = time.time()
        call_id = datetime.utcnow().timestamp()

        url = kwargs.get("url") or (args[1] if len(args) > 1 else "unknown")
        method = kwargs.get("method") or (args[0] if len(args) > 0 else "unknown")

        logger.info(
            "API call started",
            extra={
                "call_id": call_id,
                "method": method,
                "url": url,
            },
        )

        try:
            result = func(*args, **kwargs)
            elapsed = time.time() - start_time

            logger.info(
                "API call succeeded",
                extra={
                    "call_id": call_id,
                    "method": method,
                    "url": url,
                    "duration_seconds": round(elapsed, 3),
                    "status": "success",
                },
            )
            return result

        except Exception as e:
            elapsed = time.time() - start_time

            logger.error(
                f"API call failed: {str(e)}",
                extra={
                    "call_id": call_id,
                    "method": method,
                    "url": url,
                    "duration_seconds": round(elapsed, 3),
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "status": "error",
                },
                exc_info=True,
            )
            raise

    # Check if it's async or sync function
    if hasattr(func, "__await__"):
        return async_wrapper
    else:
        # Try to detect if it's a coroutine function
        import inspect

        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper


def log_tool_execution(func):
    """
    Decorator to log tool executions with input/output.

    Usage:
        @app.tool()
        @log_tool_execution
        async def my_tool(query: str) -> list[TextContent]:
            ...
    """

    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        logger = logging.getLogger("usaspending_mcp.tools")
        start_time = time.time()
        tool_name = func.__name__

        logger.info(
            f"Tool '{tool_name}' execution started",
            extra={
                "tool_name": tool_name,
                "args_count": len(args),
                "kwargs_keys": list(kwargs.keys()),
            },
        )

        try:
            result = await func(*args, **kwargs)
            elapsed = time.time() - start_time

            result_info = {
                "type": type(result).__name__,
                "length": len(result) if hasattr(result, "__len__") else None,
            }

            logger.info(
                f"Tool '{tool_name}' execution succeeded",
                extra={
                    "tool_name": tool_name,
                    "duration_seconds": round(elapsed, 3),
                    "result_info": result_info,
                    "status": "success",
                },
            )
            return result

        except Exception as e:
            elapsed = time.time() - start_time

            logger.error(
                f"Tool '{tool_name}' execution failed: {str(e)}",
                extra={
                    "tool_name": tool_name,
                    "duration_seconds": round(elapsed, 3),
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "status": "error",
                },
                exc_info=True,
            )
            raise

    @wraps(func)
    def sync_wrapper(*args, **kwargs):
        logger = logging.getLogger("usaspending_mcp.tools")
        start_time = time.time()
        tool_name = func.__name__

        logger.info(
            f"Tool '{tool_name}' execution started",
            extra={
                "tool_name": tool_name,
                "args_count": len(args),
                "kwargs_keys": list(kwargs.keys()),
            },
        )

        try:
            result = func(*args, **kwargs)
            elapsed = time.time() - start_time

            logger.info(
                f"Tool '{tool_name}' execution succeeded",
                extra={
                    "tool_name": tool_name,
                    "duration_seconds": round(elapsed, 3),
                    "status": "success",
                },
            )
            return result

        except Exception as e:
            elapsed = time.time() - start_time

            logger.error(
                f"Tool '{tool_name}' execution failed: {str(e)}",
                extra={
                    "tool_name": tool_name,
                    "duration_seconds": round(elapsed, 3),
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "status": "error",
                },
                exc_info=True,
            )
            raise

    import inspect

    if inspect.iscoroutinefunction(func):
        return async_wrapper
    else:
        return sync_wrapper


@contextmanager
def log_context(logger: logging.Logger, event_name: str, **context: Any):
    """
    Context manager for logging a specific operation with context.

    Usage:
        with log_context(logger, "database_query", user_id=123, query_type="search"):
            # Do operation
    """
    start_time = time.time()
    logger.info(f"{event_name} started", extra={"event": event_name, **context})

    try:
        yield
    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(
            f"{event_name} failed: {str(e)}",
            extra={
                "event": event_name,
                "duration_seconds": round(elapsed, 3),
                "error_type": type(e).__name__,
                "error_message": str(e),
                "status": "error",
                **context,
            },
            exc_info=True,
        )
        raise
    else:
        elapsed = time.time() - start_time
        logger.info(
            f"{event_name} completed",
            extra={
                "event": event_name,
                "duration_seconds": round(elapsed, 3),
                "status": "success",
                **context,
            },
        )
