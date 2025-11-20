# MCP Conversation Logging Guide

## Overview

The Conversation Logging feature stores complete MCP conversation context including tool calls, parameters, responses, execution times, and metadata. This enables debugging, analytics, audit trails, and conversation reconstruction.

## Architecture

### Storage
- **Location**: `/tmp/mcp_conversations/{user_id}/{conversation_id}.jsonl`
- **Format**: JSONL (JSON Lines) - one JSON record per line
- **Contents**: Tool call logs with inputs, outputs, execution metrics, and timestamps

### Key Components

1. **ConversationLogger** (`src/usaspending_mcp/utils/conversation_logging.py`)
   - Main class for logging and retrieving conversations
   - Handles JSONL file I/O, parsing, and analysis
   - Supports user isolation and conversation grouping

2. **Global Instance**
   - Initialized on server startup in `server.py`
   - Accessible via `get_conversation_logger()`
   - Thread-safe for concurrent tool calls

3. **Decorator** (`@log_conversation`)
   - Can be applied to tool functions to auto-log interactions
   - Captures parameters and responses automatically
   - Tracks execution time and errors

## Usage

### Automatic Logging (Recommended)

Apply the `@log_conversation` decorator to tools:

```python
from usaspending_mcp.utils.conversation_logging import log_conversation
from fastmcp import app

@app.tool(name="search_awards", description="...")
@log_conversation(user_id="optional_user_id")
async def search_awards(query: str) -> list[TextContent]:
    # Tool implementation
    results = await search_api(query)
    return [TextContent(type="text", text=results)]
```

The decorator automatically:
- Captures `query` and other parameters
- Logs the response text
- Tracks execution time (ms)
- Records timestamp and status (success/error)

### Manual Logging

For tools without the decorator:

```python
from usaspending_mcp.utils.conversation_logging import get_conversation_logger

async def my_tool(query: str):
    conv_logger = get_conversation_logger()

    # Your tool implementation
    result = await process_query(query)

    # Manual logging
    conv_logger.log_tool_call(
        tool_name="my_tool",
        input_params={"query": query},
        output_response=result,
        execution_time_ms=elapsed_ms,
        user_id="optional_user_id",
        conversation_id="optional_conv_id"
    )
```

## Querying Conversations

### MCP Tools (Available in Claude)

The server provides conversation management tools:

#### 1. `get_conversation`
Retrieve a complete conversation by ID.

**Parameters:**
- `conversation_id`: UUID of conversation
- `user_id`: User identifier (default: "anonymous")

**Returns:** All tool calls in the conversation with inputs/outputs

#### 2. `list_conversations`
List all conversations for a user with metadata.

**Parameters:**
- `user_id`: User identifier (default: "anonymous")
- `limit`: Max conversations to return (default: 20)

**Returns:** Conversation list with:
- Message count
- Tools used
- Time range
- Success rate

#### 3. `get_conversation_summary`
Get statistics for a specific conversation.

**Parameters:**
- `conversation_id`: UUID of conversation
- `user_id`: User identifier (default: "anonymous")

**Returns:** Statistics including:
- Total execution time
- Success/error counts
- Tool breakdown
- Time range

#### 4. `get_tool_usage_stats`
Get tool usage patterns for a user.

**Parameters:**
- `user_id`: User identifier (default: "anonymous")

**Returns:** Tool statistics:
- Number of uses per tool
- Success rate per tool
- Conversations containing each tool

### Python API

For programmatic access:

```python
from usaspending_mcp.utils.conversation_logging import get_conversation_logger

logger = get_conversation_logger()

# Retrieve a conversation
records = logger.get_conversation("conv-id-123", user_id="user1")

# List user conversations
conversations = logger.list_user_conversations(user_id="user1", limit=20)

# Get conversation summary
summary = logger.get_conversation_summary("conv-id-123", user_id="user1")

# Get tool usage stats
stats = logger.get_tool_usage_stats(user_id="user1")

# Export conversation
json_export = logger.export_conversation("conv-id-123", format="json")
txt_export = logger.export_conversation("conv-id-123", format="txt")
csv_export = logger.export_conversation("conv-id-123", format="csv")
```

## Conversation Record Format

Each logged tool call contains:

```json
{
  "timestamp": "2025-11-19T15:30:45.123456Z",
  "conversation_id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": "user123",
  "message_index": 1,
  "tool_name": "search_federal_awards",
  "status": "success",
  "execution_time_ms": 245.67,
  "input_params": {
    "query": "software development",
    "max_results": 10
  },
  "output_response": "Found 5 federal awards...",
  "error_message": null,
  "metadata": {}
}
```

## Configuration

### Default Settings
- **Storage Directory**: `/tmp/mcp_conversations/`
- **Max Response Length**: Unlimited (can be truncated)
- **User ID Default**: "anonymous"
- **Conversation ID**: Auto-generated UUID if not provided

### Custom Configuration

```python
from usaspending_mcp.utils.conversation_logging import initialize_conversation_logger
from pathlib import Path

config = {
    "conversations_dir": Path("/custom/path/conversations"),
    "max_message_length": 10000,  # Truncate responses to 10K chars
}

logger = initialize_conversation_logger(config=config)
```

## Use Cases

### 1. Debugging Tool Failures
```python
# Retrieve conversation with errors
summary = logger.get_conversation_summary(conv_id, user_id)
if summary["error_count"] > 0:
    records = logger.get_conversation(conv_id, user_id)
    for record in records:
        if record["status"] == "error":
            print(f"Tool {record['tool_name']} failed: {record['error_message']}")
```

### 2. Performance Analysis
```python
# Find slow tool calls
summary = logger.get_conversation_summary(conv_id, user_id)
print(f"Average execution time: {summary['avg_execution_time_ms']}ms")

# Find most used tools
stats = logger.get_tool_usage_stats(user_id)
for tool, data in stats["tools"].items():
    print(f"{tool}: {data['uses']} uses")
```

### 3. Audit Trail
```python
# Get all conversations for compliance
conversations = logger.list_user_conversations(user_id, limit=1000)
for conv in conversations:
    export = logger.export_conversation(
        conv["conversation_id"],
        user_id=user_id,
        format="json"
    )
    # Store for audit
```

### 4. Pattern Discovery
```python
# Find failed searches to improve topic mappings
summary = logger.get_conversation_summary(conv_id, user_id)
if summary["success_rate"] < 80:
    # Analyze what searches failed
    records = logger.get_conversation(conv_id, user_id)
    failed = [r for r in records if r["status"] == "error"]
    # Improve topic mappings or documentation
```

## File Organization

```
/tmp/mcp_conversations/
├── anonymous/
│   ├── 550e8400-e29b-41d4-a716-446655440000.jsonl
│   ├── 550e8400-e29b-41d4-a716-446655440001.jsonl
│   └── ...
├── user123/
│   ├── 550e8400-e29b-41d4-a716-446655440010.jsonl
│   └── ...
└── user456/
    └── ...
```

Each JSONL file can be read line-by-line for memory efficiency:

```python
with open(conversation_file, "r") as f:
    for line in f:
        record = json.loads(line)
        # Process record
```

## Performance Considerations

### Storage
- Typical tool call: ~200-500 bytes (varies with response size)
- 1000 tool calls: ~500KB (depending on response length)
- JSONL format is append-only (efficient)

### Retrieval
- Listing conversations: O(n) file system operations
- Getting single conversation: O(m) line reads (m = message count)
- Summary statistics: O(m) aggregation

### Optimization Tips
1. **Truncate long responses**: Set `max_message_length` in config
2. **Archive old conversations**: Periodically move to archive
3. **User isolation**: Separate directories by user for faster listing
4. **Batch operations**: Use Python API for programmatic access

## Security Considerations

### Data Privacy
- Conversations stored on local filesystem
- No encryption by default (use `chmod 700` for directory)
- Include sensitive data in responses - implement filtering if needed

### User Isolation
- Each user has separate directory
- Default "anonymous" user for shared systems
- No built-in authentication (integrate with your auth system)

### Audit Log
```python
# Log who accessed what conversation
import logging
logger = logging.getLogger("conversation_access")

def get_conversation_safe(conv_id, user_id, requester_id):
    logger.info(f"User {requester_id} accessed conversation {conv_id} for {user_id}")
    return get_conversation_logger().get_conversation(conv_id, user_id)
```

## Troubleshooting

### Conversations Not Appearing
1. Check that logger was initialized: `get_conversation_logger()`
2. Verify decorator applied: `@log_conversation()`
3. Check storage directory exists: `ls -la /tmp/mcp_conversations/`

### Large Storage Usage
1. Check response sizes: Review export previews
2. Implement archival: Move old conversations to backup
3. Enable truncation: Set `max_message_length` config

### Performance Issues
1. Profile retrieval times: Time `list_user_conversations()`
2. Check file count in directory: `ls /tmp/mcp_conversations/{user_id} | wc -l`
3. Consider database alternative for large scale

## Future Enhancements

Potential improvements:
- Database backend (SQLite/PostgreSQL) for efficient queries
- Encryption at rest
- Built-in retention policies
- Conversation tagging and search
- Integration with observability platforms (DataDog, New Relic)
- Real-time streaming to external systems
- Conversation replay/reconstruction
