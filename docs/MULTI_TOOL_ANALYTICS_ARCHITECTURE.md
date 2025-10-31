# Multi-Tool Analytics Architecture

## Overview

The SearchAnalytics module provides a configurable, reusable analytics framework that supports multiple MCP tools across the server. Rather than implementing separate analytics systems for each tool, this architecture uses a single configurable class that adapts to any tool's needs.

## Architecture Principles

### 1. Single Implementation, Multiple Instances

Instead of duplicating code, we have:
- **One SearchAnalytics class** in `src/usaspending_mcp/utils/search_analytics.py`
- **Multiple instances** managed by a global registry, one per tool
- **Configurable behavior** via tool-specific configuration

### 2. Tool-Aware Design

Each analytics instance knows:
- Which tool it belongs to (e.g., "far", "usaspending")
- What filter field name to use (e.g., "part" for FAR, "agency" for USASpending)
- Where to store data (separate JSONL file per tool)
- How to generate reports (tool-specific insights)

### 3. Minimal Tool Integration

Tools don't need special imports or complex setup. Simple calls:

```python
# Get or create analytics instance for this tool
analytics = get_analytics("far")

# Log a search event
analytics.log_search(
    keyword="best value",
    results_count=5,
    filter_value="15"  # Generic "filter_value" param
)
```

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│              MCP Tools (Multiple)                           │
│  ┌───────────────┐  ┌──────────────┐  ┌───────────────┐    │
│  │  FAR Tools    │  │ USASpending  │  │ Other Tools   │    │
│  │               │  │ Tools        │  │               │    │
│  └───────┬───────┘  └──────┬───────┘  └───────┬───────┘    │
│          │                  │                  │             │
└──────────┼──────────────────┼──────────────────┼─────────────┘
           │                  │                  │
           │ get_analytics()   │ get_analytics()  │ get_analytics()
           ▼                  ▼                  ▼
┌─────────────────────────────────────────────────────────────┐
│         Global Analytics Instance Registry                  │
│   _analytics_instances: Dict[str, SearchAnalytics]          │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ "far":          SearchAnalytics(                    │   │
│  │                   tool_name="far",                  │   │
│  │                   config={"filter_name": "part"}    │   │
│  │                 )                                   │   │
│  │                                                      │   │
│  │ "usaspending":  SearchAnalytics(                    │   │
│  │                   tool_name="usaspending",          │   │
│  │                   config={"filter_name": "agency"}  │   │
│  │                 )                                   │   │
│  │                                                      │   │
│  │ "other_tool":   SearchAnalytics(...)                │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
           │                  │                  │
           │ log_search()     │ log_search()     │ log_search()
           ▼                  ▼                  ▼
┌─────────────────────────────────────────────────────────────┐
│         Analytics Data Storage (JSONL Files)                │
│  ┌──────────────────┐  ┌──────────────────┐                │
│  │ /tmp/mcp_analytics│  │ /tmp/mcp_analytics│                │
│  │ /far_analytics.  │  │ /usaspending_   │                │
│  │  jsonl           │  │ analytics.jsonl │                │
│  └──────────────────┘  └──────────────────┘                │
│         ▲                       ▲                           │
│         │                       │                           │
│         └───────────┬───────────┘                           │
│                     │                                       │
│         Report Generation & Analysis                        │
│              (generate_report())                            │
└─────────────────────────────────────────────────────────────┘
```

## Configuration System

### Tool Configuration

Each tool provides a configuration dict that specifies how analytics should behave:

```python
# FAR tool configuration
far_config = {
    "filter_name": "part",        # FAR uses "part" filter
    "analytics_dir": "/tmp/mcp_analytics"
}

# USASpending tool configuration
usaspending_config = {
    "filter_name": "agency",      # USASpending uses "agency" filter
    "analytics_dir": "/tmp/mcp_analytics"
}

# Initialize with configuration
analytics_far = initialize_analytics("far", far_config)
analytics_usaspending = initialize_analytics("usaspending", usaspending_config)
```

### Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `filter_name` | str | "part" | Name of the filter field (e.g., "part", "agency", "region") |
| `analytics_dir` | str | "/tmp/mcp_analytics" | Directory where analytics JSONL files are stored |

## Data Model

### Log Record Format

Each search event creates a record in the analytics JSONL file:

```json
{
  "timestamp": "2025-10-31T02:40:54.783188Z",
  "tool": "far",
  "keyword": "best value",
  "search_type": "keyword",
  "results_count": 5,
  "part": null,
  "user_id": "anonymous",
  "success": true
}
```

**Key Fields:**
- `timestamp`: ISO 8601 UTC timestamp
- `tool`: Tool name that logged this event
- `keyword`: Search term or query
- `search_type`: Type of search (keyword, section, topic, award, etc.)
- `results_count`: Number of results returned
- **Dynamic filter field**: The field name matches tool's `filter_name` config
  - FAR uses `"part": "15"`
  - USASpending uses `"agency": "DOD"`
  - Custom tools can define their own
- `user_id`: Optional user identifier
- `success`: Boolean (results_count > 0)

**Important**: The filter field name is **dynamic**. The `log_search()` method uses the configured `filter_name` to set the correct field:

```python
# For FAR: filter_name = "part"
record = {
    ...
    "part": filter_value,  # Dynamic key name!
    ...
}

# For USASpending: filter_name = "agency"
record = {
    ...
    "agency": filter_value,  # Different key name!
    ...
}
```

## Adding a New Tool with Analytics

### Step 1: Create Tool Module

Create your tool module in `src/usaspending_mcp/tools/`:

```python
# src/usaspending_mcp/tools/my_tool.py
from usaspending_mcp.utils.search_analytics import get_analytics

async def search_my_database(keyword: str, region: str = None) -> dict:
    """Search my custom database."""
    try:
        # Perform search
        results = search_database(keyword, region)

        # Log to analytics
        analytics = get_analytics("my_tool")
        analytics.log_search(
            keyword=keyword,
            results_count=len(results),
            filter_value=region,
            search_type="keyword"
        )

        return {
            "status": "success",
            "results": results
        }
    except Exception as e:
        logger.error(f"Search error: {e}")
        return {"status": "error", "message": str(e)}
```

### Step 2: Initialize Analytics

In your server setup code:

```python
from usaspending_mcp.utils.search_analytics import initialize_analytics

# Configure analytics for your tool
my_tool_config = {
    "filter_name": "region",  # Your tool's filter field
    "analytics_dir": "/tmp/mcp_analytics"
}

# Initialize when server starts
initialize_analytics("my_tool", my_tool_config)
```

### Step 3: That's It!

Your tool now has:
- Automatic search logging
- Analytics reports via `generate_report()`
- Trending analysis
- Zero-result detection
- Cross-filter insights
- All with zero code duplication!

## Report Generation

### Single-Tool Reports

Generate reports for a specific tool:

```python
from usaspending_mcp.utils.search_analytics import get_analytics

# Get FAR analytics
far_analytics = get_analytics("far")
far_report = far_analytics.generate_report()

# Get USASpending analytics
usaspending_analytics = get_analytics("usaspending")
usaspending_report = usaspending_analytics.generate_report()
```

### All-Tools Reports

View analytics across all tools:

```python
from usaspending_mcp.utils.search_analytics import get_all_analytics

all_analytics = get_all_analytics()

for tool_name, analytics in all_analytics.items():
    print(f"\n{tool_name.upper()} Analytics:")
    report = analytics.generate_report()
    print(f"  Total searches: {report['summary']['total_searches']}")
    print(f"  Top trending: {report['trending_topics'][0]['keyword']}")
```

### Report Structure

Each report includes:

```python
{
    "timestamp": "2025-10-31T02:40:54.783188Z",
    "tool": "far",
    "filter_name": "part",  # Reflects tool's config
    "trending_topics": [...],      # Top 10 searches by frequency
    "zero_result_searches": [...], # Searches with 0 results
    "cross_filter_topics": [...],  # Searches without filter that succeeded
    "summary": {
        "total_searches": 245,
        "avg_results_per_search": 4.2,
        "zero_result_percentage": 8.2
    }
}
```

## Key Methods

### SearchAnalytics Class

#### Initialization

```python
analytics = SearchAnalytics(
    tool_name: str = "far",
    analytics_file: Optional[Path] = None,
    config: Optional[Dict] = None
)
```

#### Logging

```python
analytics.log_search(
    keyword: str,
    results_count: int,
    filter_value: Optional[str] = None,
    search_type: str = "keyword",
    user_id: Optional[str] = None,
    metadata: Optional[Dict] = None
)
```

#### Analysis

```python
# Get trending topics (most popular searches)
trending = analytics.get_trending_topics(limit=20)

# Get searches that returned zero results
zero_results = analytics.get_zero_result_searches()

# Get searches using filters (spanning multiple filter values)
cross_filter = analytics.get_cross_filter_searches(min_count=3)

# Legacy name (deprecated)
cross_part = analytics.get_cross_part_searches()  # Alias for backward compatibility

# Generate full report
report = analytics.generate_report()
```

### Module-Level Functions

```python
# Initialize analytics for a tool
initialize_analytics(
    tool_name: str = "far",
    config: Optional[Dict] = None
) -> SearchAnalytics

# Get existing analytics instance
get_analytics(tool_name: str = "far") -> SearchAnalytics

# Get all analytics instances
get_all_analytics() -> Dict[str, SearchAnalytics]
```

## Design Patterns

### 1. Lazy Initialization

Analytics instances are created on-demand:

```python
# First call to get_analytics("new_tool") creates the instance
analytics = get_analytics("new_tool")  # Creates SearchAnalytics instance

# Subsequent calls return the same instance
analytics2 = get_analytics("new_tool")  # Returns same instance (cached)
```

### 2. Configurable Behavior

The same SearchAnalytics class adapts to different tools:

```python
# FAR configuration
far_analytics = SearchAnalytics(
    tool_name="far",
    config={"filter_name": "part"}
)
# Creates records with "part" field

# USASpending configuration
usaspending_analytics = SearchAnalytics(
    tool_name="usaspending",
    config={"filter_name": "agency"}
)
# Creates records with "agency" field
```

### 3. Tool-Aware Data Storage

Each tool stores data separately:

```
/tmp/mcp_analytics/
├── far_analytics.jsonl          # FAR searches
├── usaspending_analytics.jsonl  # USASpending searches
└── my_tool_analytics.jsonl      # Custom tool searches
```

This isolation provides:
- **Independence**: Tools don't interfere with each other
- **Scalability**: Can add unlimited tools without affecting others
- **Organization**: Easy to archive or delete data per tool

### 4. Backward Compatibility

The system maintains backward compatibility:

```python
# Old code still works
analytics = get_analytics()  # Defaults to "far"

# New code is more explicit
analytics = get_analytics("far")

# Legacy method name still works
cross_part = analytics.get_cross_part_searches()  # Alias
```

## Performance Characteristics

### Storage

| Metric | Size |
|--------|------|
| Per search record | ~500 bytes |
| 100 searches | ~50 KB |
| 1,000 searches | ~500 KB |
| 10,000 searches | ~5 MB |

### Speed

| Operation | Time |
|-----------|------|
| Log search | <1 ms |
| Get trending (100 records) | ~5 ms |
| Generate report | ~20 ms |
| Filter analysis | ~10 ms |

### Scaling Recommendations

| Scale | Recommendation |
|-------|-----------------|
| < 1K searches | No action needed |
| 1K - 10K searches | Consider archiving old records |
| > 10K searches | Archive monthly, delete old months |

Example cleanup:

```python
# Archive current analytics
import shutil
shutil.copy(
    "/tmp/mcp_analytics/far_analytics.jsonl",
    "/backups/far_analytics_2025-10.jsonl"
)

# Reset for next month
Path("/tmp/mcp_analytics/far_analytics.jsonl").unlink()
```

## Integration with MCP Tools

### Tool Registration

When registering tools with the MCP server, initialize analytics:

```python
# In server setup
from usaspending_mcp.utils.search_analytics import initialize_analytics

def register_tools(app):
    # Initialize analytics for FAR
    initialize_analytics("far", {"filter_name": "part"})

    # Initialize analytics for USASpending
    initialize_analytics("usaspending", {"filter_name": "agency"})

    # Register tool handlers
    register_far_tools(app)
    register_usaspending_tools(app)
```

### Data Flow

```
User Query
    ↓
MCP Tool Handler
    ↓
Tool Performs Search
    ↓
Tool Logs to Analytics: analytics.log_search(...)
    ↓
Analytics Record Appended to JSONL
    ↓
Return Results to User
```

## Best Practices

### For Tool Developers

1. **Always use get_analytics()**
   ```python
   analytics = get_analytics("my_tool")  # Not get_analytics()
   ```

2. **Log with appropriate search_type**
   ```python
   # Good: Specific search type
   analytics.log_search(keyword, results_count, search_type="section")

   # Less good: Generic
   analytics.log_search(keyword, results_count)  # Defaults to "keyword"
   ```

3. **Use filter_value for optional filters**
   ```python
   # With filter
   analytics.log_search(keyword, results_count, filter_value="15")

   # Without filter
   analytics.log_search(keyword, results_count, filter_value=None)
   ```

4. **Include metadata for complex tools**
   ```python
   analytics.log_search(
       keyword=query,
       results_count=len(results),
       filter_value=filter_val,
       metadata={
           "execution_time_ms": 150,
           "cache_hit": True,
           "retry_count": 0
       }
   )
   ```

### For Operators

1. **Monitor zero-result rate**
   - Target: < 10%
   - Action: Improve topic mappings or indexing

2. **Review trending searches monthly**
   - Identify user interests
   - Improve documentation for popular topics
   - Add missing search capabilities

3. **Archive analytics periodically**
   - Monthly: Archive previous month's data
   - Quarterly: Deep-dive analysis of 3-month trends
   - Annually: Yearly trend reports

4. **Track tool adoption**
   ```python
   from usaspending_mcp.utils.search_analytics import get_all_analytics

   all_analytics = get_all_analytics()
   for tool_name, analytics in all_analytics.items():
       report = analytics.generate_report()
       total = report['summary']['total_searches']
       print(f"{tool_name}: {total} searches")
   ```

## Troubleshooting

### Analytics Not Recording

**Problem**: No analytics data appears for a tool.

**Solution**:
1. Verify `get_analytics()` is called in tool code
2. Check that `initialize_analytics()` was called during setup
3. Verify `/tmp/mcp_analytics/` directory exists and is writable

### Different Tools' Records Mixed

**Problem**: Analytics JSONL file contains records from wrong tool.

**Solution**: This shouldn't happen—each tool has its own file. If it does:
1. Check tool name in `get_analytics("correct_tool_name")`
2. Verify no copy/paste errors in tool initialization
3. Reset analytics: `rm /tmp/mcp_analytics/*.jsonl`

### Report Generation Slow

**Problem**: `generate_report()` takes > 1 second.

**Solution**:
1. Analytics file is large (> 100K records)
2. Archive old data: Copy JSONL to backup, reset
3. Consider sampling: Use `get_trending_topics(limit=10)` instead of full report

## Summary

The multi-tool analytics architecture provides:
- **Code reuse**: Single SearchAnalytics implementation
- **Tool flexibility**: Configurable for any tool
- **Data isolation**: Separate storage per tool
- **Scalability**: Grow from 1 tool to many
- **Simplicity**: Minimal integration effort

To add a new tool, you only need:
1. Call `get_analytics("tool_name")` in tool code
2. Call `analytics.log_search()` after searches
3. Initialize analytics in server setup

That's it. The rest is automatic.
