# Structured Logging Guide

## Overview

This document explains how to use the structured logging system in the USASpending MCP Server for better observability and debugging in production environments.

**Implementation Date**: October 30, 2025
**Last Updated**: October 31, 2025
**Status**: ✅ Phase 2 Implementation Complete + Tool Execution Logging Enabled

---

## Features

### JSON-Formatted Logs

All logs are output in JSON format for machine parsing and integration with log aggregation systems:

```json
{
  "timestamp": "2025-10-30T15:45:32.123456Z",
  "level": "INFO",
  "module": "usaspending_mcp.server",
  "message": "API call started",
  "function": "search_federal_awards",
  "line_number": 245,
  "thread": 140612345678912,
  "process": 12345,
  "call_id": 1730307932.123456
}
```

### Automatic Context Enrichment

Every log record automatically includes:
- **timestamp**: ISO 8601 UTC timestamp
- **level**: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- **module**: Python module name
- **function**: Function name where log occurred
- **line_number**: Line number in source file
- **thread**: Thread ID (for debugging async issues)
- **process**: Process ID (for multi-process deployments)

### API Call Logging

Automatically logs API calls with timing and error information using the `@log_api_call` decorator:

```python
@log_api_call
async def search_federal_awards(query: str) -> dict:
    # Logs:
    # 1. "API call started" with call_id, method, url, params
    # 2. "API call succeeded" with duration_seconds, status
    #    OR "API call failed" with error details
    pass
```

### Tool Execution Logging

Automatically logs tool execution with input/output using the `@log_tool_execution` decorator:

```python
@app.tool()
@log_tool_execution
async def my_tool(query: str) -> list[TextContent]:
    # Logs:
    # 1. "Tool 'my_tool' execution started" with args_count, kwargs_keys
    # 2. "Tool 'my_tool' execution succeeded" with duration_seconds, result_info
    #    OR "Tool 'my_tool' execution failed" with error details
    pass
```

#### Tools with Active Logging

The following USASpending tools have `@log_tool_execution` decorator enabled:

- ✅ **search_federal_awards** - Logs all keyword searches for federal awards
- ✅ **analyze_federal_spending** - Logs spending analysis queries with duration
- ✅ **get_award_by_id** - Logs direct award lookups by ID

These tools now automatically log to `usaspending_mcp.log` whenever they are called from Claude Desktop or CLI. Search analytics are also logged to `usaspending_mcp_searches.log` with query details and result counts.

### Context Manager for Operations

Use the `log_context` context manager for custom operation logging:

```python
from usaspending_mcp.utils.logging import log_context, get_logger

logger = get_logger("my_module")

with log_context(logger, "database_query", user_id=123, table="awards"):
    # Logs:
    # 1. "database_query started" with extra context
    # 2. "database_query completed" with duration_seconds
    #    OR "database_query failed" with error details
    result = await query_database()
```

---

## Configuration

### Initialize in Server Startup

The server initializes structured logging on startup:

```python
# src/usaspending_mcp/server.py
from usaspending_mcp.utils.logging import setup_structured_logging, get_logger

# Set up structured logging with JSON output
setup_structured_logging(log_level="INFO", json_output=True)
logger = get_logger("server")
```

### Configuration Options

#### setup_structured_logging(log_level, json_output, log_file)

**Parameters:**

- **log_level** (str): Logging level - "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"
  - Default: "INFO"
  - Use "DEBUG" for development, "INFO" for production

- **json_output** (bool): Output format
  - Default: True (JSON format)
  - Set to False for plain text (useful for local development)

- **log_file** (Optional[str]): File path to write logs to
  - Default: None (logs to stdout only)
  - Provide path to also write logs to file

**Examples:**

```python
# JSON output to stdout only (production)
setup_structured_logging(log_level="INFO", json_output=True)

# Plain text to stdout and file (development with backup)
setup_structured_logging(
    log_level="DEBUG",
    json_output=False,
    log_file="/var/log/usaspending-mcp.log"
)

# JSON output to both stdout and file (production with backup)
setup_structured_logging(
    log_level="INFO",
    json_output=True,
    log_file="/var/log/usaspending-mcp.json.log"
)
```

### Runtime Configuration

To change logging configuration at runtime:

```python
from usaspending_mcp.utils.logging import setup_structured_logging

# Reconfigure logging (removes old handlers, adds new ones)
setup_structured_logging(log_level="DEBUG", json_output=False)
```

---

## Usage Examples

### Example 1: Using the @log_api_call Decorator

The `@log_api_call` decorator automatically logs API calls with timing and error information. It works with both async and sync functions:

```python
from usaspending_mcp.utils.logging import log_api_call
from usaspending_mcp.utils.retry import fetch_json_with_retry
import httpx

@log_api_call
async def search_federal_awards(url: str, params: dict) -> dict:
    """Search federal spending data."""
    async with httpx.AsyncClient() as client:
        data = await fetch_json_with_retry(client, url, params=params)
    return data

# Logs:
# INFO - "API call started" with call_id, url, params
# INFO - "API call succeeded" with duration_seconds, status
#   or
# ERROR - "API call failed: ..." with error details
```

### Example 2: Using the @log_tool_execution Decorator

The `@log_tool_execution` decorator automatically logs MCP tool execution:

```python
from usaspending_mcp.utils.logging import log_tool_execution
from mcp.types import TextContent

@app.tool()
@log_tool_execution
async def search_awards(query: str, max_results: int = 5) -> list[TextContent]:
    """Search federal spending data."""
    # Your implementation here
    return [TextContent(type="text", text=f"Found {len(results)} awards")]

# Logs:
# INFO - "Tool 'search_awards' execution started" with args_count, kwargs_keys
# INFO - "Tool 'search_awards' execution succeeded" with duration_seconds, result_info
```

### Example 3: Using the log_context Context Manager

Use context managers for custom operation logging:

```python
from usaspending_mcp.utils.logging import log_context, get_logger

logger = get_logger("awards")

async def process_awards(award_ids: list[str]) -> dict:
    """Process a batch of awards."""

    with log_context(logger, "award_processing", count=len(award_ids)):
        # Logs: "award_processing started" with count=5

        for award_id in award_ids:
            award = await get_award(award_id)
            # Process award...

        # Logs: "award_processing completed" with duration_seconds, status=success
        return results

    # If exception occurs:
    # Logs: "award_processing failed: ..." with error details

```

### Example 4: Getting a Logger for Your Module

Use `get_logger()` to get a module-specific logger:

```python
from usaspending_mcp.utils.logging import get_logger

logger = get_logger("my_module")

logger.info("Starting process", extra={"user_id": 123})
logger.warning("Slow query detected", extra={"duration_ms": 5000})
logger.error("Database connection failed", extra={"error_code": 1234})
```

### Example 5: Adding Extra Context to Logs

All logging calls accept an `extra` parameter for additional context:

```python
from usaspending_mcp.utils.logging import get_logger

logger = get_logger("awards")

# Add context to any log
logger.info(
    "Award retrieved",
    extra={
        "award_id": "ABC123",
        "vendor_name": "Acme Corp",
        "contract_value": 1000000,
        "status": "active"
    }
)

# Output JSON:
# {
#   "timestamp": "2025-10-30T15:45:32Z",
#   "level": "INFO",
#   "module": "usaspending_mcp.awards",
#   "message": "Award retrieved",
#   "award_id": "ABC123",
#   "vendor_name": "Acme Corp",
#   "contract_value": 1000000,
#   "status": "active",
#   ...
# }
```

---

## Integration with Existing Code

### Step 1: Replace Hardcoded Loggers

If you have hardcoded loggers, replace them with `get_logger()`:

```python
# Before
import logging
logger = logging.getLogger(__name__)

# After
from usaspending_mcp.utils.logging import get_logger
logger = get_logger("my_module")
```

### Step 2: Add Decorators to API Calls

Add `@log_api_call` to functions that make API calls:

```python
from usaspending_mcp.utils.logging import log_api_call

@log_api_call
async def fetch_award_details(award_id: str) -> dict:
    # Implementation
    pass
```

### Step 3: Add Decorators to Tools

Add `@log_tool_execution` to MCP tool functions:

```python
@app.tool()
@log_tool_execution
async def search_federal_awards(query: str) -> list[TextContent]:
    # Implementation
    pass
```

### Step 4: Wrap Critical Sections with log_context

Use context managers for complex operations:

```python
from usaspending_mcp.utils.logging import log_context

with log_context(logger, "data_validation", record_count=1000):
    # Validate data...
    pass
```

---

## Log Levels and When to Use Them

| Level | Use Case | Example |
|-------|----------|---------|
| DEBUG | Development, detailed information | API request/response details, variable states |
| INFO | General information about progress | Server startup, tool invocation, API calls |
| WARNING | Warning messages, unexpected behavior | Rate limit approaching, slow query |
| ERROR | Error messages, operation failure | Failed API call, database error |
| CRITICAL | Critical errors, system issues | Out of memory, unable to start server |

---

## Monitoring and Log Aggregation

### Parsing JSON Logs

Since logs are JSON formatted, they integrate well with log aggregation systems:

```bash
# Parse and pretty-print logs
cat logs.jsonl | jq .

# Filter by level
cat logs.jsonl | jq 'select(.level=="ERROR")'

# Filter by module
cat logs.jsonl | jq 'select(.module=="usaspending_mcp.tools")'

# Get all logs for a specific call_id
cat logs.jsonl | jq 'select(.call_id==1730307932.123456)'
```

### Log Aggregation Integration

The JSON format is compatible with:
- **ELK Stack** (Elasticsearch, Logstash, Kibana)
- **Splunk**
- **DataDog**
- **CloudWatch**
- **Google Cloud Logging**
- Any system that accepts JSON logs

### Performance Impact

Structured logging has minimal performance impact:
- **JSON serialization**: ~0.5ms per log (minimal)
- **I/O overhead**: Similar to plain text logging
- **Memory**: Negligible (logs are typically streamed)

---

## Debugging with Structured Logs

### Finding Errors

```bash
# Find all errors
cat logs.jsonl | jq 'select(.level=="ERROR")'

# Find errors in a specific tool
cat logs.jsonl | jq 'select(.level=="ERROR" and .tool_name=="search_federal_awards")'

# Find slow operations
cat logs.jsonl | jq 'select(.duration_seconds > 5)'
```

### Tracing Execution Flow

Use the automatically added context fields to trace execution:

```bash
# See all logs from a specific function
cat logs.jsonl | jq 'select(.function=="search_federal_awards")'

# See logs from a specific thread (useful for debugging async issues)
cat logs.jsonl | jq 'select(.thread==140612345678912)'
```

### Correlating Requests

The `call_id` field can be used to correlate all logs for a single API call:

```bash
# See all logs for a specific API call
cat logs.jsonl | jq 'select(.call_id==1730307932.123456)'
```

---

## Testing Structured Logging

### Test Custom Logging

```python
import logging
from usaspending_mcp.utils.logging import setup_structured_logging, get_logger

# Set up structured logging
setup_structured_logging(log_level="DEBUG", json_output=True)

# Get logger
logger = get_logger("test")

# Log various levels
logger.debug("Debug message", extra={"debug_info": "value"})
logger.info("Info message", extra={"info": "value"})
logger.warning("Warning message", extra={"warning": "value"})
logger.error("Error message", extra={"error": "value"})
```

### Test API Call Logging

```python
from usaspending_mcp.utils.logging import log_api_call, setup_structured_logging
import asyncio

setup_structured_logging(log_level="DEBUG", json_output=True)

@log_api_call
async def test_api_call():
    await asyncio.sleep(0.1)
    return {"status": "success"}

# Run test
result = asyncio.run(test_api_call())
# Logs:
# - "API call started"
# - "API call succeeded" with duration_seconds ~0.1
```

### Test Tool Execution Logging

```python
from usaspending_mcp.utils.logging import log_tool_execution, setup_structured_logging
from mcp.types import TextContent
import asyncio

setup_structured_logging(log_level="DEBUG", json_output=True)

@log_tool_execution
async def test_tool(query: str) -> list[TextContent]:
    await asyncio.sleep(0.1)
    return [TextContent(type="text", text="Test result")]

# Run test
result = asyncio.run(test_tool("test"))
# Logs:
# - "Tool 'test_tool' execution started"
# - "Tool 'test_tool' execution succeeded" with duration_seconds ~0.1
```

---

## Best Practices

### Do's

- ✅ Use decorators (`@log_api_call`, `@log_tool_execution`) for automatic logging
- ✅ Add meaningful context with the `extra` parameter
- ✅ Use log levels appropriately (DEBUG < INFO < WARNING < ERROR < CRITICAL)
- ✅ Use context managers (`log_context`) for complex operations
- ✅ Store logs in JSON format for parsing and aggregation
- ✅ Use meaningful log messages that describe what happened

### Don'ts

- ❌ Don't log sensitive information (API keys, passwords, PII)
- ❌ Don't use plain string formatting instead of extra context (use `extra` parameter)
- ❌ Don't mix decorator levels (only apply one decorator per function)
- ❌ Don't change logging configuration in production without testing
- ❌ Don't log raw exception tracebacks without context

---

## Troubleshooting

### Logs Not Appearing

**Problem**: No log output visible

**Solution**: Check the log level
```python
# Set to DEBUG to see all messages
setup_structured_logging(log_level="DEBUG")
```

### JSON Parsing Errors

**Problem**: Logs are JSON but fail to parse

**Solution**: Ensure logs are written to stdout/file, not mixed with other output

**Check**:
```bash
# Should be valid JSON
cat logs.jsonl | jq . | head -1
```

### Performance Issues

**Problem**: Logging is slow

**Solution**:
1. Reduce log level to INFO or WARNING
2. Use async logging if available
3. Check I/O performance of log destination

---

## Reference

### File Locations

- **Logging module**: `src/usaspending_mcp/utils/logging.py`
- **Server initialization**: `src/usaspending_mcp/server.py` (lines 25-30)
- **Rate limiting guide**: `docs/RATE_LIMITING_AND_RETRY_GUIDE.md`
- **Best practices review**: `docs/MCP_BEST_PRACTICES_REVIEW.md`

### Dependencies

- `python-json-logger>=2.0.7` - JSON formatter for Python logging

### Related Features

- **Rate Limiting**: `docs/RATE_LIMITING_AND_RETRY_GUIDE.md`
- **Retry Logic**: `src/usaspending_mcp/utils/retry.py`
- **API Integration**: `src/usaspending_mcp/server.py`

---

## Future Enhancements

Planned improvements:

1. **Metrics Extraction**
   - Automatically extract metrics from logs (latency, error rates)
   - Export to Prometheus

2. **Log Sampling**
   - Sample high-volume logs to reduce storage
   - Keep important logs unsampled

3. **Correlation IDs**
   - Add distributed trace IDs for cross-service tracking
   - Useful for microservices architecture

4. **Log Compression**
   - Compress old logs to save storage
   - Automatic cleanup of old logs

5. **Dashboard**
   - Grafana dashboard for log metrics
   - Real-time monitoring and alerting

---

## Support

For issues or questions:
1. Check the source code in `src/usaspending_mcp/utils/logging.py`
2. Review examples in this guide
3. Check `docs/MCP_BEST_PRACTICES_REVIEW.md` for context
4. Check `docs/RATE_LIMITING_AND_RETRY_GUIDE.md` for related features

---

**Last Updated**: October 31, 2025
**Version**: 1.1.0
**Status**: Phase 2 Implementation Complete + Tool Execution Logging Enabled
