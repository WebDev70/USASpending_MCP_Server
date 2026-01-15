"""
Structured logging configuration for USASpending MCP Server.

Provides JSON-formatted logs with structured context for better
observability and debugging in production environments.
"""

import json
import logging
import logging.handlers
import sys
import time
from contextlib import contextmanager
from datetime import datetime
from functools import wraps
from pathlib import Path
from typing import Any, Optional

try:
    # Try new import path first (pythonjsonlogger >= 3.0.0)
    from pythonjsonlogger.json import JsonFormatter as BaseJsonFormatter
except ImportError:
    # Fall back to old import path (pythonjsonlogger < 3.0.0)
    from pythonjsonlogger.jsonlogger import JsonFormatter as BaseJsonFormatter


class CustomJsonFormatter(BaseJsonFormatter):
    """Custom JSON formatter with additional context fields."""

    def add_fields(self, log_record: dict, record: logging.LogRecord, message_dict: dict) -> None:
        """Add custom fields to log record."""
        try:
            super().add_fields(log_record, record, message_dict)
        except KeyError:
            # If there's a KeyError from the parent class (e.g., trying to overwrite
            # user-provided fields), just continue. User's extra fields take precedence.
            pass

        # Add timestamp in ISO format (ISO 8601 format with Z suffix for UTC)
        # Only add if not already in the record
        if "timestamp" not in log_record:
            log_record["timestamp"] = datetime.utcnow().isoformat() + "Z"

        # Add log level name - override with consistent naming
        if "level" not in log_record:
            log_record["level"] = record.levelname

        # Add module name (logger name)
        if "module" not in log_record:
            log_record["module"] = record.name

        # Add function and line number for debugging
        if "function" not in log_record:
            log_record["function"] = record.funcName
        if "line_number" not in log_record:
            log_record["line_number"] = record.lineno

        # Add process and thread information
        if "process" not in log_record:
            log_record["process"] = record.process
        if "thread" not in log_record:
            log_record["thread"] = record.threadName

        # Ensure message is in the log record
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
    # Get root logger
    # Don't remove handlers if we're in a test environment (preserve caplog)
    root_logger = logging.getLogger()

    # Remove existing handlers ONLY if not in test mode
    # Check if pytest is in the handler types or if we're running under pytest
    has_pytest_handler = any(
        "pytest" in str(type(h).__module__).lower()
        or "caplog" in str(type(h).__name__).lower()
        for h in root_logger.handlers
    )

    if not has_pytest_handler:
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
        formatter = CustomJsonFormatter(fmt="%(timestamp)s %(level)s %(name)s %(message)s")
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
        # Try to use project logs directory if we're in development mode
        # Otherwise fall back to a system temp directory or user home
        try:
            # Get the project root (go up from src/usaspending_mcp/utils/)
            project_root = Path(__file__).resolve().parent.parent.parent.parent
            # Check if we're in a writable development directory (not site-packages)
            if "site-packages" not in str(project_root):
                logs_dir = project_root / "logs"
                logs_dir.mkdir(exist_ok=True)
                log_file = str(logs_dir / "usaspending_mcp.log")
            else:
                # We're installed as a package, use user's home directory
                logs_dir = Path.home() / ".usaspending_mcp" / "logs"
                logs_dir.mkdir(parents=True, exist_ok=True)
                log_file = str(logs_dir / "usaspending_mcp.log")
        except (OSError, PermissionError):
            # If we can't create logs in either location, use temp directory
            import tempfile
            logs_dir = Path(tempfile.gettempdir()) / "usaspending_mcp_logs"
            logs_dir.mkdir(parents=True, exist_ok=True)
            log_file = str(logs_dir / "usaspending_mcp.log")

    # Create logs directory if it doesn't exist
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    # All logs file handler with rotation (10 MB per file, keep 10 backups)
    file_handler = logging.handlers.RotatingFileHandler(
        log_file, maxBytes=10 * 1024 * 1024, backupCount=10  # 10 MB
    )
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)

    # Error log file handler (only ERROR and CRITICAL)
    error_log_file = str(log_path.parent / "usaspending_mcp_errors.log")
    error_handler = logging.handlers.RotatingFileHandler(
        error_log_file, maxBytes=5 * 1024 * 1024, backupCount=10  # 5 MB
    )
    error_handler.setLevel(logging.DEBUG)
    error_handler.setFormatter(file_formatter)
    root_logger.addHandler(error_handler)

    # Search log file handler (successful tool searches and queries)
    search_log_file = str(log_path.parent / "usaspending_mcp_searches.log")
    search_handler = logging.handlers.RotatingFileHandler(
        search_log_file,
        maxBytes=20 * 1024 * 1024,  # 20 MB (larger since we'll log more here)
        backupCount=10,
    )
    search_handler.setLevel(logging.DEBUG)
    search_handler.setFormatter(file_formatter)
    # Only add search logs from the search logger
    search_logger = logging.getLogger("usaspending_mcp.searches")
    search_logger.addHandler(search_handler)
    search_logger.setLevel(logging.DEBUG)
    # Prevent propagation to root logger to avoid duplication
    search_logger.propagate = False

    # Get application logger and set its level
    app_logger = logging.getLogger("usaspending_mcp")
    app_logger.setLevel(getattr(logging, log_level))
    # Add console handler to app logger as well (for direct use without propagation)
    app_logger.addHandler(console_handler)
    return app_logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger for a specific module."""
    return logging.getLogger(f"usaspending_mcp.{name}")


def log_search(
    tool_name: str,
    query: str,
    results_count: int,
    execution_time_ms: float = None,
    filters: dict = None,
) -> None:
    """
    Log a successful search/query execution.

    Args:
        tool_name: Name of the tool used (e.g., "search_federal_awards")
        query: The search query string
        results_count: Number of results returned
        execution_time_ms: Execution time in milliseconds (optional)
        filters: Dictionary of filters applied (optional)
    """
    search_logger = logging.getLogger("usaspending_mcp.searches")

    # Build message with structured information
    message = f"Tool: {tool_name} | Query: {query} | Results: {results_count}"

    if execution_time_ms is not None:
        message += f" | Time: {execution_time_ms:.0f}ms"

    if filters:
        filter_str = ", ".join([f"{k}={v}" for k, v in filters.items() if v])
        if filter_str:
            message += f" | Filters: {filter_str}"

    search_logger.info(message)


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
                    "params_keys": (
                        list(kwargs.get("params", {}).keys()) if "params" in kwargs else []
                    ),
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
