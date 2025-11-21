# USASpending MCP Server: Junior Developer Guide

A comprehensive guide to understanding, extending, and maintaining this FastMCP-based federal spending data server.

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Project Structure & Rationale](#project-structure--rationale)
3. [Core Components Deep Dive](#core-components-deep-dive)
4. [Design Patterns Used](#design-patterns-used)
5. [Adding New Features](#adding-new-features)
6. [Testing Strategy](#testing-strategy)
7. [Debugging & Troubleshooting](#debugging--troubleshooting)
8. [Performance Optimization](#performance-optimization)
9. [Security & Reliability](#security--reliability)
10. [Deployment & Operations](#deployment--operations)
11. [Common Pitfalls](#common-pitfalls)

---

## Architecture Overview

### System Architecture Diagram

```
┌──────────────────────────────────────────────────────────────────┐
│                    MCP CLIENTS (Claude, Tools, etc.)             │
└───────────────────────┬────────────────────────────────────────┘
                        │
        ┌───────────────┴────────────────┐
        │                                │
    HTTP Transport                   Stdio Transport
    (Port 3002)                      (Testing)
        │                                │
        └───────────────┬────────────────┘
                        │
            ┌───────────▼───────────┐
            │   FastMCP Framework   │
            │ (Tool Registration &  │
            │  Protocol Handling)   │
            └───────────┬───────────┘
                        │
        ┌───────────────┴────────────────┐
        │                                │
    ┌───▼──────────┐            ┌───────▼────┐
    │ Tool Layer   │            │ Util Layer │
    │              │            │            │
    │ 22 Spending  │            │ Rate Limit │
    │ Tools        │            │ Retry      │
    │ 5 FAR Tools  │            │ Logging    │
    │ 4 Convo      │            │ Analytics  │
    │ Tools        │            │            │
    └───┬──────────┘            └───────┬────┘
        │                               │
        └───────────────┬───────────────┘
                        │
            ┌───────────▼────────────────┐
            │   Rate Limiter Check       │
            │ (Token Bucket Algorithm)   │
            └───────────┬────────────────┘
                        │
            ┌───────────▼────────────────┐
            │   Retry Logic              │
            │ (Exponential Backoff)      │
            └───────────┬────────────────┘
                        │
            ┌───────────▼────────────────┐
            │   HTTP Client (httpx)      │
            └───────────┬────────────────┘
                        │
            ┌───────────▼────────────────┐
            │  USASpending.gov API v2    │
            │  https://api.usaspending   │
            │  .gov/api/v2/...          │
            └────────────────────────────┘
```

### Request-Response Flow

```
1. Request Arrives (via HTTP/Stdio)
   ↓
2. FastMCP Router matches tool name
   ↓
3. Tool function is invoked
   ↓
4. Rate Limiter acquires token (or waits)
   ↓
5. Validation happens (input checks)
   ↓
6. API request is built (URL, params, headers)
   ↓
7. Retry wrapper executes request
   ↓
8. Response parsed and formatted
   ↓
9. Logging and analytics recorded
   ↓
10. TextContent returned to client
```

### Key Architectural Decisions & Rationale

| Decision | Why? | Benefit |
|----------|------|---------|
| **FastMCP over raw MCP** | Reduces boilerplate, handles protocol details | Less code, fewer bugs, faster development |
| **Global rate limiter** | Shared across all tools, prevents API abuse | Fair resource usage, predictable load |
| **Token bucket algorithm** | Smooth traffic, no cascading failures | Better UX than hard rate limit |
| **Exponential backoff retry** | Gives failing services time to recover | Higher reliability, fewer cascading failures |
| **Structured JSON logging** | Machine-readable logs enable analytics | Better observability, debugging, analytics |
| **Dual transport modes** | Different use cases (prod vs. testing) | Flexibility without code duplication |
| **FAR data as JSON files** | No API calls, instant lookup | Faster FAR searches, works offline |
| **Async/await throughout** | Handle multiple concurrent requests | Better resource utilization |
| **Modular utils layer** | Separate concerns (logging, rate limit, retry) | Reusable, testable, maintainable |

---

## Project Structure & Rationale

### Directory Structure with Explanations

```
usaspending-mcp/
│
├── src/usaspending_mcp/              # Main package
│   ├── __main__.py                   # Entry point: routes to run_server or run_stdio
│   ├── __init__.py                   # Package exports
│   ├── server.py                     # Core server: 31 tools + FastMCP setup (~2000 lines)
│   ├── client.py                     # Test client for stdio mode development
│   │
│   ├── tools/                        # Tool registration modules
│   │   ├── __init__.py
│   │   └── far.py                    # FAR tool definitions (5 tools)
│   │
│   ├── loaders/                      # Data loaders for initialization
│   │   ├── __init__.py
│   │   └── far.py                    # Load FAR JSON files into memory
│   │
│   └── utils/                        # Reusable utilities
│       ├── __init__.py
│       ├── rate_limit.py             # Token bucket rate limiter
│       ├── retry.py                  # Exponential backoff retry logic
│       ├── logging.py                # Structured logging setup
│       ├── search_analytics.py       # Track search patterns
│       └── far.py                    # FAR database query engine
│
├── docs/                             # Documentation
│   ├── data/
│   │   └── far/                      # FAR regulation JSON files (Parts 14, 15, 16, 19)
│   ├── guides/                       # User and developer guides
│   └── dev/                          # Development documentation
│
├── tests/                            # Test suite
│   ├── conftest.py                   # Pytest fixtures and configuration
│   ├── unit/                         # Unit tests (fast, isolated)
│   └── integration/                  # Integration tests (slow, require network)
│
├── logs/                             # Generated log files (gitignored)
├── .venv/                            # Virtual environment (gitignored)
├── pyproject.toml                    # Project metadata and dependencies
├── requirements.txt                  # Pinned dependency versions
├── pytest.ini                        # Pytest configuration
├── start_mcp_server.sh               # Startup script for HTTP mode
├── server_manager.py                 # Manage running server instances
└── README.md                         # Project overview
```

### Why This Structure?

1. **`src/` layout** - Following Python best practices for package distribution
2. **Separated `tools/` and `utils/`** - Clear distinction between business logic and infrastructure
3. **`loaders/` directory** - Explicit data initialization phase
4. **`tests/` mirror** - Test structure mirrors source structure
5. **`docs/data/`** - Offline data that doesn't need API calls
6. **Dual scripts** - `start_mcp_server.sh` and `server_manager.py` for operations

---

## Core Components Deep Dive

### 1. FastMCP Application (`server.py`)

This is the largest file (~2000 lines) and contains the FastMCP app initialization and all tool definitions.

#### Structure of `server.py`

```python
# SECTION 1: Imports
from fastmcp import FastMCP
from mcp.types import TextContent
import httpx
from utils.rate_limit import initialize_rate_limiter
from utils.logging import setup_structured_logging
# ... more imports

# SECTION 2: Global instances
app = FastMCP(name="usaspending-server")
rate_limiter = None  # Initialized in startup
http_client = None   # Initialized in startup
logger = None        # Initialized in startup

# SECTION 3: Startup/Shutdown hooks
@app.on_startup
async def startup():
    global rate_limiter, http_client, logger
    # Initialize everything here
    pass

@app.on_shutdown
async def shutdown():
    # Cleanup here
    pass

# SECTION 4: Helper functions
async def make_api_request(endpoint: str, params: dict) -> httpx.Response:
    """Wrapper for API calls that applies rate limiting"""
    await rate_limiter.wait_if_needed("default")
    url = f"https://api.usaspending.gov/api/v2/{endpoint}"
    return await http_client.get(url, params=params)

def format_currency(value: float) -> str:
    """Convert 500000000 to $500M"""
    pass

# SECTION 5: Tool definitions (31 tools: 22 spending, 5 FAR, 4 conversation)
@app.tool(name="search_federal_awards", ...)
async def search_federal_awards(...) -> TextContent:
    pass

# ... more tools ...

# SECTION 6: Run functions
async def run_stdio():
    """Run in stdio mode for testing"""
    pass

def run_server():
    """Run HTTP server"""
    pass
```

#### Important Pattern: Tool Anatomy

Every tool follows this pattern:

```python
@app.tool(
    name="tool_name",
    description="What this tool does and what parameters it accepts"
)
async def tool_name(
    param1: str,           # Required parameter
    param2: int = 10,      # Optional parameter with default
    param3: str = None     # Optional parameter (nullable)
) -> TextContent:
    """
    Extended description of what this tool does.

    This docstring helps users understand:
    - What the tool does
    - What each parameter means
    - What kind of output to expect
    """

    # Step 1: Rate limit
    await rate_limiter.wait_if_needed("default")

    # Step 2: Validate inputs
    if not param1 or len(param1.strip()) == 0:
        return [TextContent(type="text", text="Error: param1 cannot be empty")]

    # Step 3: Build request
    params = {
        "filters": {"keywords": [param1]},
        "limit": min(param2, 100)  # Cap at 100
    }

    # Step 4: Make API call
    try:
        response = await make_api_request("awards/search/", params)
    except Exception as e:
        logger.error(f"API call failed: {str(e)}")
        return [TextContent(type="text", text=f"Error: {str(e)}")]

    # Step 5: Parse and format
    data = response.json()
    output = f"# Results for {param1}\n\n"

    for item in data.get("results", [])[:param2]:
        output += f"- {item['name']}\n"

    # Step 6: Log
    logger.info(f"Tool executed: {tool_name}, Results: {len(data.get('results', []))}")

    # Step 7: Return
    return [TextContent(type="text", text=output)]
```

#### Error Handling Pattern

Always return a TextContent even on error:

```python
try:
    response = await make_api_request(endpoint, params)
    if response.status_code != 200:
        error_msg = f"API returned {response.status_code}: {response.text}"
        logger.error(error_msg)
        return [TextContent(type="text", text=f"Error: {error_msg}")]

    data = response.json()
except httpx.TimeoutException as e:
    logger.error(f"Request timeout: {str(e)}")
    return [TextContent(type="text", text="Error: Request timed out. Server may be busy.")]
except httpx.ConnectError as e:
    logger.error(f"Connection error: {str(e)}")
    return [TextContent(type="text", text="Error: Cannot connect to server.")]
except json.JSONDecodeError as e:
    logger.error(f"JSON decode error: {str(e)}")
    return [TextContent(type="text", text="Error: Server returned invalid JSON.")]
except Exception as e:
    logger.error(f"Unexpected error: {str(e)}")
    return [TextContent(type="text", text=f"Error: An unexpected error occurred.")]
```

### 2. Rate Limiter (`utils/rate_limit.py`)

Implements a **token bucket algorithm** for rate limiting.

#### How Token Bucket Works

```
Imagine a bucket:
  - Capacity: 60 tokens
  - Fill rate: 60 tokens per 60 seconds (1 token/sec)
  - Initial: 60 tokens

When a request comes in:
  - Need 1 token to proceed
  - If tokens available: consume 1, continue immediately
  - If tokens empty: wait for new token (every 1 second)

Visual:
  Time: 0s   Tokens: 60  → Request comes in → Tokens: 59
  Time: 1s   Tokens: 60  (refilled) → Request comes in → Tokens: 59
  Time: 0.5s Tokens: 59.5 → Request comes in → Tokens: 58.5
```

#### Key Code

```python
class RateLimiter:
    def __init__(self, capacity: int = 60, refill_rate: int = 60):
        self.capacity = capacity                           # Max tokens
        self.refill_rate = refill_rate                     # Tokens per minute
        self.tokens = capacity                             # Current tokens
        self.last_refill_time = asyncio.get_event_loop().time()

    async def wait_if_needed(self, identifier: str = "default"):
        """Wait until a token is available, then consume it"""
        while self.tokens < 1:
            # Calculate how long until next token
            time_since_refill = asyncio.get_event_loop().time() - self.last_refill_time
            tokens_to_add = (time_since_refill * self.refill_rate) / 60
            self.tokens += tokens_to_add
            self.last_refill_time = asyncio.get_event_loop().time()

            if self.tokens < 1:
                # Wait a bit before checking again
                await asyncio.sleep(0.1)

        self.tokens -= 1  # Consume a token
```

#### Why Token Bucket?

| Algorithm | Pros | Cons |
|-----------|------|------|
| **Token Bucket** | Smooth traffic, allows bursts, fair, no rejection | Slightly complex |
| **Fixed Window** | Simple | Allows abuse at boundary, unfair |
| **Sliding Window** | Fair | Can be complex, memory overhead |
| **Leaky Bucket** | Smooth, predictable | No bursts allowed |

Token bucket is best because it smooths traffic while allowing short bursts (like 5 consecutive requests).

### 3. Retry Logic (`utils/retry.py`)

Implements **exponential backoff** retry logic using the `tenacity` library.

#### How Exponential Backoff Works

```
Scenario: API returns 503 Service Unavailable

Attempt 1: Try immediately → FAIL (503)
           Wait 1 second (base_wait_time ^ 1)

Attempt 2: Try again → FAIL (503)
           Wait 2 seconds (base_wait_time ^ 2)

Attempt 3: Try again → FAIL (503)
           Wait 4 seconds (base_wait_time ^ 3)

Max 3 attempts, max 10 second wait.

This gives the server time to recover!
```

#### Key Code

```python
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    retry_if_result
)

def make_api_call_with_retry(func):
    """Decorator: retry function with exponential backoff"""
    return retry(
        # Retry conditions
        stop=stop_after_attempt(3),                # Max 3 attempts
        wait=wait_exponential(multiplier=1, min=1, max=10),  # 1-10 sec wait
        retry=retry_if_exception_type((
            httpx.TimeoutException,
            httpx.ConnectError,
            httpx.ReadError,
        )),
        # Retry on specific HTTP status codes
        retry=retry_if_result(lambda r: r.status_code in [
            408,  # Request Timeout
            429,  # Too Many Requests
            500,  # Internal Server Error
            502,  # Bad Gateway
            503,  # Service Unavailable
            504,  # Gateway Timeout
        ]),
    )(func)
```

#### Why These Status Codes?

- **408, 500, 502, 503, 504** - Server errors (likely transient)
- **429** - Rate limited (should wait and retry)
- **Timeout/Connection errors** - Network issues (likely transient)

Don't retry on 400, 401, 403, 404 (client errors - permanent).

### 4. Structured Logging (`utils/logging.py`)

Provides both **JSON logging** (production) and **plain text logging** (development).

#### Dual-Mode Logging

```python
def setup_structured_logging(json_mode: bool = True):
    """
    json_mode=True:  Log as JSON (for production aggregation)
    json_mode=False: Log as text (for development console)
    """

    if json_mode:
        # Use python-json-logger for JSON output
        handler = logging.StreamHandler()
        formatter = pythonjsonlogger.JsonFormatter()
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    else:
        # Use standard formatter for text output
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
```

#### JSON Log Example

```json
{
  "timestamp": "2024-11-13T14:32:16.234Z",
  "level": "INFO",
  "logger": "usaspending_mcp.server",
  "message": "Tool executed",
  "tool_name": "search_federal_awards",
  "query": "space",
  "results_count": 5,
  "execution_time_ms": 845,
  "status": "success",
  "hostname": "macbook-pro.local",
  "process_id": 12345,
  "thread_id": 56789
}
```

#### Why JSON?

- **Machine-readable** - Tools can parse and analyze
- **Centralized logging** - Can send to ELK, Datadog, CloudWatch
- **Analytics** - Query logs to find patterns
- **Alert-ready** - Can set up alerts based on log patterns

#### Using Decorators for Logging

```python
@log_api_call
async def search_federal_awards(query: str):
    """Automatically logs: tool name, start time, end time, duration"""
    # Your code here
    pass

@log_tool_execution
async def get_award_details(award_id: str):
    """Automatically logs: inputs, outputs, execution time"""
    # Your code here
    pass
```

### 5. FAR Data Loader (`loaders/far.py`)

Loads Federal Acquisition Regulation data from JSON files once, caches it in memory.

#### Why Load to Memory?

```
Without caching:
  User 1 searches FAR → Load JSON → Search → Return
  User 2 searches FAR → Load JSON → Search → Return  (unnecessary reload!)
  User 3 searches FAR → Load JSON → Search → Return  (unnecessary reload!)

With caching:
  Startup → Load JSON once, cache in memory
  User 1 searches FAR → Search cache → Return (fast!)
  User 2 searches FAR → Search cache → Return (fast!)
  User 3 searches FAR → Search cache → Return (fast!)

Result: Faster FAR searches, less CPU/disk I/O
```

#### Implementation

```python
from functools import lru_cache

@lru_cache(maxsize=1)
def load_far_all_parts() -> dict:
    """
    Load all FAR parts from JSON files.

    LRU cache with maxsize=1 means:
    - First call: Loads files and caches result
    - Subsequent calls: Return cached result (no reload)

    Returns:
        {
            14: { "sections": [...] },
            15: { "sections": [...] },
            16: { "sections": [...] },
            19: { "sections": [...] }
        }
    """
    far_data = {}
    for part_num in [14, 15, 16, 19]:
        with open(f"docs/data/far/far_part{part_num}.json") as f:
            far_data[part_num] = json.load(f)
    return far_data
```

### 6. FAR Database Query Engine (`utils/far.py`)

Provides search capabilities for FAR data.

#### FARDatabase Features

```python
class FARDatabase:
    def __init__(self, far_data: dict):
        self.far_data = far_data
        self._build_indices()  # Create search indices for speed

    def search_keyword(self, keyword: str, top_n: int = 20) -> list:
        """
        Full-text search across all FAR sections.

        Search strategy:
        1. Check if keyword is exact match in section title
        2. Check if keyword is in section text (case-insensitive)
        3. Rank by relevance (title match > text match)
        4. Return top N results
        """
        results = []
        for section in self.all_sections:
            relevance = 0
            if keyword.lower() in section["title"].lower():
                relevance += 10  # Title match worth more
            if keyword.lower() in section["text"].lower():
                relevance += 1   # Text match

            if relevance > 0:
                results.append({
                    "relevance": relevance,
                    "section": section,
                })

        results.sort(key=lambda x: x["relevance"], reverse=True)
        return [r["section"] for r in results[:top_n]]

    def get_section(self, section_number: str) -> dict:
        """Direct lookup: "14.101" -> section data"""
        # Use pre-built index for O(1) lookup
        return self.section_index.get(section_number)

    def _build_indices(self):
        """Create search indices during initialization"""
        self.section_index = {}           # section_number -> section data
        self.topic_index = {}             # topic -> [section numbers]
        self.all_sections = []            # All sections for full search

        for section in self.far_data:
            self.section_index[section["number"]] = section
            self.all_sections.append(section)

            # Index by topic
            for topic in section.get("topics", []):
                if topic not in self.topic_index:
                    self.topic_index[topic] = []
                self.topic_index[topic].append(section["number"])
```

### 7. Conversation Management Tools (`utils/conversation_logging.py`)

Provides tools for tracking and analyzing conversation history and user behavior patterns.

#### Conversation Tracking Features

```python
class ConversationManager:
    """Manages conversation history and analytics"""

    async def log_tool_execution(self, conversation_id: str, tool_name: str,
                                  inputs: dict, outputs: dict, duration_ms: float):
        """Record a tool execution in conversation history"""
        # Stores: tool name, inputs, outputs, execution time
        # Updates: conversation timestamps, tool usage counts
        pass

    async def get_conversation(self, conversation_id: str) -> dict:
        """Retrieve complete conversation history"""
        # Returns: all tool calls, inputs, outputs, timeline
        pass

    async def get_conversation_summary(self, conversation_id: str) -> dict:
        """Get statistics for a conversation"""
        # Returns: tool counts, most used tools, avg execution time
        # Returns: user patterns, common queries
        pass

    async def get_tool_usage_stats(self, user_id: str) -> dict:
        """Get tool usage patterns across all conversations"""
        # Returns: total calls per tool, avg response times
        # Returns: most frequently used tools, user behavior patterns
        pass
```

#### Why Conversation Tracking?

```
Benefits:
- Understand user behavior and search patterns
- Monitor which tools are most valuable
- Identify performance bottlenecks
- Track conversation effectiveness
- Support conversation-based analytics

Use Cases:
- "Which tools does NASA typically use?"
- "What's the average execution time for spending analysis?"
- "Show me all conversations about infrastructure spending"
- "Which agencies are most queried?"
- "Trending search topics over time"
```

#### Conversation Storage

```python
# Conversation data structure
{
    "conversation_id": "conv_abc123",
    "user_id": "user_xyz",
    "created_at": "2024-11-20T10:30:00Z",
    "updated_at": "2024-11-20T10:45:00Z",
    "tool_calls": [
        {
            "tool_name": "search_federal_awards",
            "inputs": {"query": "space", "max_results": 5},
            "outputs": {"results_count": 5, "status": "success"},
            "duration_ms": 845,
            "timestamp": "2024-11-20T10:30:15Z"
        },
        # ... more tool calls
    ],
    "statistics": {
        "total_tools_used": 3,
        "total_execution_time_ms": 2500,
        "success_rate": 0.95,
        "most_used_tool": "search_federal_awards"
    }
}
```

---

## Design Patterns Used

### 1. Decorator Pattern

Used extensively for cross-cutting concerns:

```python
# Rate limiting
@app.tool(name="search_federal_awards")
async def search_federal_awards(...):
    await rate_limiter.wait_if_needed("default")

# Retry logic
@make_api_call_with_retry
async def fetch_data(url):
    return await http_client.get(url)

# Logging
@log_api_call
@log_tool_execution
async def some_tool(...):
    pass
```

**Benefits:**
- Separates concerns (what the tool does vs. how it handles failures)
- Can be applied to multiple functions without code duplication
- Easy to remove or modify

### 2. Singleton Pattern (Implicit)

Global instances created once and reused:

```python
# In server.py
rate_limiter = None      # Created once in startup()
http_client = None       # Created once in startup()
logger = None            # Created once in startup()

# Used by all tools
await rate_limiter.wait_if_needed("default")
response = await http_client.get(url)
logger.info("Something happened")
```

**Benefits:**
- Consistent state across all tools
- No repeated initialization
- Easy to mock in tests

### 3. Factory Pattern (Implicit)

Helper functions create formatted responses:

```python
def format_currency(value: float) -> str:
    """Factory for currency strings"""
    if value >= 1_000_000_000:
        return f"${value / 1_000_000_000:.1f}B"
    elif value >= 1_000_000:
        return f"${value / 1_000_000:.1f}M"
    else:
        return f"${value:,.0f}"

def generate_award_url(award_id: int) -> str:
    """Factory for award URLs"""
    return f"https://www.usaspending.gov/award/{award_id}"
```

### 4. Strategy Pattern

Different API endpoints for different data types:

```python
# Strategy 1: Award search
endpoint = "awards/search/"
params = {"filters": {"keywords": [query]}}

# Strategy 2: Agency analysis
endpoint = "agencies/{agency_id}/spending_breakdown/"
params = {"filters": {"time_period": time_period}}

# Strategy 3: Spending trends
endpoint = "spending/spending_over_time/"
params = {"group_by": "agency"}

# All use same make_api_request function
response = await make_api_request(endpoint, params)
```

### 5. Facade Pattern

`make_api_request` hides complexity:

```python
# Without facade (complex):
await rate_limiter.wait_if_needed("default")
url = f"https://api.usaspending.gov/api/v2/{endpoint}"
headers = {"timeout": 30}
response = await http_client.get(url, params=params)

# With facade (simple):
response = await make_api_request(endpoint, params)
```

### 6. Repository Pattern (Implicit)

FAR database acts as a repository:

```python
# Users don't need to know how FAR data is stored
far_db = get_far_database()

# Clean interface
sections = far_db.search_keyword("small business")
section = far_db.get_section("14.101")
topics = far_db.get_by_topic("competition")
```

---

## Adding New Features

### Adding a New Tool (Step-by-Step)

#### Step 1: Understand the Pattern

Look at an existing tool to understand the structure:

```python
@app.tool(
    name="search_federal_awards",
    description="Search for federal awards..."
)
async def search_federal_awards(
    query: str,
    max_results: int = 10
) -> TextContent:
    # ... implementation
```

#### Step 2: Choose the Right Endpoint

Check USASpending.gov API v2 documentation to find the right endpoint:

```
GET /api/v2/awards/search/           → Search awards
GET /api/v2/awards/{id}/             → Get award details
GET /api/v2/agencies/                → List agencies
GET /api/v2/agencies/{id}/spending    → Agency spending data
GET /api/v2/idvs/                     → IDV (contract vehicle) search
```

#### Step 3: Write the Tool

```python
@app.tool(
    name="get_idv_details",
    description="Get details about an Indefinite Delivery Vehicle (IDV) contract"
)
async def get_idv_details(idv_id: str) -> TextContent:
    """
    Retrieve comprehensive details about an IDV contract.

    Args:
        idv_id: The ID of the IDV to retrieve

    Returns:
        Formatted IDV details or error message
    """

    # Step 1: Validate input
    if not idv_id or not idv_id.strip():
        return [TextContent(type="text", text="Error: IDV ID cannot be empty")]

    # Step 2: Rate limit
    await rate_limiter.wait_if_needed("default")

    # Step 3: Build request
    params = {}  # IDV endpoints typically use path parameter

    # Step 4: Make API call with retry
    try:
        response = await make_api_request(f"idvs/{idv_id}/", params)
        response.raise_for_status()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return [TextContent(type="text", text=f"Error: IDV {idv_id} not found")]
        logger.error(f"API error: {e}")
        return [TextContent(type="text", text="Error: Failed to retrieve IDV details")]
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return [TextContent(type="text", text="Error: An unexpected error occurred")]

    # Step 5: Parse response
    data = response.json()

    # Step 6: Format output
    output = f"""# IDV Details: {data.get('award_id', 'Unknown')}

**Vehicle Type:** {data.get('type_of_idc', 'Unknown')}
**Agency:** {data.get('awarding_agency', {}).get('name', 'Unknown')}
**Total Value:** {format_currency(data.get('total_obligation', 0))}
**Start Date:** {data.get('date_signed', 'Unknown')}
**Number of Orders:** {data.get('count_of_orders', 0)}

**Ordering Information:**
- Minimum:** {format_currency(data.get('minimum_value', 0))}
- Maximum:** {format_currency(data.get('maximum_value', 0))}

**Details:**
{data.get('description', 'No description available')}
"""

    # Step 7: Log
    logger.info(f"Tool executed: get_idv_details, IDV: {idv_id}")

    # Step 8: Return
    return [TextContent(type="text", text=output)]
```

#### Step 4: Add Tests

```python
# tests/unit/test_tools.py

import pytest
from unittest.mock import patch, AsyncMock

@pytest.mark.asyncio
async def test_get_idv_details_success():
    """Test successful IDV details retrieval"""
    mock_response = {
        "award_id": "IDV-123456",
        "type_of_idc": "GWAC",
        "total_obligation": 500000000,
        "awarding_agency": {"name": "GSA"},
        "count_of_orders": 42
    }

    with patch("httpx.AsyncClient.get") as mock_get:
        mock_get.return_value = AsyncMock(
            status_code=200,
            json=AsyncMock(return_value=mock_response)
        )

        result = await get_idv_details("IDV-123456")

        assert "IDV-123456" in result[0].text
        assert "500" in result[0].text  # Check formatted currency


@pytest.mark.asyncio
async def test_get_idv_details_not_found():
    """Test when IDV is not found"""
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_response = AsyncMock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError("Not found")
        mock_get.return_value = mock_response

        result = await get_idv_details("INVALID-ID")

        assert "not found" in result[0].text.lower()


@pytest.mark.asyncio
async def test_get_idv_details_empty_input():
    """Test validation of empty input"""
    result = await get_idv_details("")
    assert "Error" in result[0].text
```

#### Step 5: Test Manually

```bash
# Run the server in stdio mode
PYTHONPATH=src ./.venv/bin/python -m usaspending_mcp.server --stdio

# Or use the test client
PYTHONPATH=src ./.venv/bin/python -m usaspending_mcp.client
# Select your tool from the menu
```

#### Step 6: Commit

```bash
git add -A
git commit -m "Add get_idv_details tool for IDV contract lookup

- Retrieve comprehensive details for Indefinite Delivery Vehicles
- Includes vehicle type, value, agency, and order count
- Uses USASpending.gov /idvs/ endpoint with retry logic
- Includes unit tests and error handling"
```

### Extending Rate Limiter Behavior

If you need per-user rate limiting instead of global:

```python
# Current: Global rate limiter
await rate_limiter.wait_if_needed("default")

# Enhanced: Per-user rate limiting
user_id = get_user_id_from_request()  # Extract from request headers
await rate_limiter.wait_if_needed(f"user_{user_id}")
```

The rate limiter already supports multiple identifiers, just use different keys.

### Adding a New Data Source

If you want to integrate another API:

```python
# Step 1: Create a new loader
# loaders/sam_gov.py
@lru_cache(maxsize=1)
def load_sam_gov_data() -> dict:
    """Load SAM.gov entity registration data"""
    # Fetch and cache data
    pass

# Step 2: Use in tools
@app.tool(name="check_sam_gov_registration")
async def check_sam_gov_registration(entity_id: str):
    sam_data = load_sam_gov_data()
    # ... search and return
```

---

## Testing Strategy

### Test Organization

```
tests/
├── conftest.py              # Shared fixtures
├── unit/
│   ├── test_tools.py        # Test individual tools
│   ├── test_utils_retry.py  # Test retry logic
│   ├── test_utils_logging.py
│   └── test_utils_rate_limit.py
└── integration/
    ├── test_api_calls.py    # Test against real API
    └── test_e2e.py          # End-to-end tests
```

### Unit Testing Pattern

```python
import pytest
from unittest.mock import patch, AsyncMock, MagicMock

@pytest.fixture
async def rate_limiter_mock():
    """Mock rate limiter to avoid waiting in tests"""
    mock = AsyncMock()
    mock.wait_if_needed = AsyncMock()
    return mock

@pytest.mark.asyncio
async def test_search_federal_awards_with_mock_api(rate_limiter_mock):
    """Test tool with mocked API response"""

    # Arrange: Set up mocks
    mock_response = {
        "results": [
            {
                "id": "123",
                "recipient": {"name": "Contractor Inc"},
                "amount": 1000000
            }
        ]
    }

    with patch("httpx.AsyncClient.get") as mock_get:
        mock_get.return_value = AsyncMock(
            status_code=200,
            json=AsyncMock(return_value=mock_response)
        )

        # Act: Call the tool
        result = await search_federal_awards("test query")

        # Assert: Verify output
        assert len(result) == 1
        assert "Contractor Inc" in result[0].text
        assert "1,000,000" in result[0].text
```

### Integration Testing Pattern

```python
import pytest
import httpx

@pytest.mark.integration
@pytest.mark.asyncio
async def test_search_federal_awards_real_api():
    """Test against real API (requires network)"""

    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://api.usaspending.gov/api/v2/awards/search/",
            params={"filters": {"keywords": ["space"]}, "limit": 5}
        )

        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert len(data["results"]) > 0
```

### Running Tests

```bash
# All tests
pytest

# Only unit tests (fast)
pytest -m "not integration"

# Only integration tests
pytest -m integration

# Specific test file
pytest tests/unit/test_tools.py

# Specific test
pytest tests/unit/test_tools.py::test_search_federal_awards_with_mock_api -v

# With coverage
pytest --cov=src/usaspending_mcp --cov-report=html

# Watch mode (re-run on file change)
pytest-watch
```

### Testing Async Code

```python
import pytest
import asyncio

# Use pytest-asyncio for async tests
@pytest.mark.asyncio
async def test_async_function():
    result = await some_async_function()
    assert result == expected_value

# Fixture for event loop
@pytest.fixture
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()
```

---

## Debugging & Troubleshooting

### Common Issues and Solutions

#### Issue 1: "Request Timeout"

**Symptoms:**
```
Error: Request timed out. Server may be busy.
```

**Root Causes:**
1. API is actually slow
2. Network is slow
3. Your machine is overloaded
4. Rate limit is causing queue buildup

**Debug Steps:**
```python
# Add timing to see where time is spent
import time

start = time.time()
await rate_limiter.wait_if_needed("default")
rate_limit_time = time.time() - start
logger.info(f"Rate limit wait: {rate_limit_time:.2f}s")

start = time.time()
response = await http_client.get(url, timeout=60)  # Longer timeout temporarily
api_call_time = time.time() - start
logger.info(f"API call: {api_call_time:.2f}s")
```

**Solutions:**
1. Check if api.usaspending.gov is down (curl it)
2. Increase timeout temporarily: `httpx.AsyncClient(timeout=60.0)`
3. Check system resources: `top` or `Activity Monitor`
4. Reduce rate limit: `initialize_rate_limiter(30)` (30 req/min)

#### Issue 2: "Rate Limiter Always Blocking"

**Symptoms:**
```
Every request waits 1+ seconds even though you haven't made many requests
```

**Root Causes:**
1. Rate limit initialized too low
2. Another process is hammering the API
3. Token bucket algorithm bug

**Debug:**
```python
logger.info(f"Available tokens: {rate_limiter.get_available_tokens()}")
logger.info(f"Rate limiter stats: {rate_limiter.get_stats()}")
```

**Solution:**
```python
# Increase rate limit
rate_limiter = initialize_rate_limiter(requests_per_minute=120)
```

#### Issue 3: "API Returning 500 Error"

**Symptoms:**
```
Error: API returned 500: Internal Server Error
```

**Debug:**
```python
# Check if error is transient by retrying
try:
    response = await http_client.get(url, params=params)
    response.raise_for_status()
except httpx.HTTPStatusError as e:
    logger.error(f"Status: {e.response.status_code}")
    logger.error(f"Response body: {e.response.text}")

    # Try again manually
    await asyncio.sleep(5)
    response = await http_client.get(url, params=params)
```

**Solutions:**
1. Wait a few minutes (server might be restarting)
2. Check USASpending.gov status page
3. Try with simpler parameters

#### Issue 4: "JSON Parsing Fails"

**Symptoms:**
```
Error: Server returned invalid JSON.
json.decoder.JSONDecodeError
```

**Debug:**
```python
response = await http_client.get(url, params=params)
logger.error(f"Response status: {response.status_code}")
logger.error(f"Response content type: {response.headers.get('content-type')}")
logger.error(f"Response body (first 500 chars): {response.text[:500]}")

# Try parsing
try:
    data = response.json()
except json.JSONDecodeError as e:
    logger.error(f"JSON decode error at line {e.lineno}, col {e.colno}")
```

**Solutions:**
1. Check if API changed response format
2. Check if you're getting HTML error page instead of JSON
3. Verify URL encoding of parameters

### Debugging Tools

#### Using Logging

```python
# Set log level to DEBUG for more details
import logging
logging.basicConfig(level=logging.DEBUG)

# Log at different levels
logger.debug("Detailed information")
logger.info("General information")
logger.warning("Something might be wrong")
logger.error("Something is definitely wrong")
logger.critical("Everything is broken")
```

#### Using Print Debugging (Quick & Dirty)

```python
print(f"DEBUG: response status = {response.status_code}")
print(f"DEBUG: response body = {response.text[:200]}")
```

#### Using Python Debugger

```python
# Set breakpoint
breakpoint()

# Or
import pdb; pdb.set_trace()

# Then in debugger:
# n - next line
# s - step into function
# c - continue
# l - list code
# p variable_name - print variable
```

#### Using Logging Requests

```python
# Log every HTTP request
import httpx
import logging

# Enable httpx debug logging
logging.getLogger("httpx").setLevel(logging.DEBUG)

# Now you'll see:
# INFO:httpx:HTTP Request: GET https://api.usaspending.gov/api/v2/awards/search/
# INFO:httpx:HTTP Response: 200 OK
```

### Reading Log Files

```bash
# View all logs
tail -f logs/usaspending_mcp.log

# View errors only
tail -f logs/usaspending_mcp_errors.log

# Search for specific errors
grep "timeout" logs/usaspending_mcp.log

# Count errors by type
grep "Error" logs/usaspending_mcp_errors.log | cut -d: -f2 | sort | uniq -c

# Parse JSON logs
tail logs/usaspending_mcp.log | jq '.[] | select(.level == "ERROR")'
```

---

## Performance Optimization

### Identifying Bottlenecks

#### Method 1: Logging with Timing

```python
import time
from functools import wraps

def time_it(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start = time.time()
        result = await func(*args, **kwargs)
        duration = time.time() - start
        logger.info(f"{func.__name__} took {duration:.2f}s")
        return result
    return wrapper

@time_it
async def search_federal_awards(query: str):
    # ... implementation
    pass
```

#### Method 2: Profiling

```python
import cProfile
import pstats

# Profile a function
profiler = cProfile.Profile()
profiler.enable()

# ... run your code ...

profiler.disable()
stats = pstats.Stats(profiler)
stats.sort_stats('cumulative')
stats.print_stats(10)  # Show top 10 functions by cumulative time
```

### Common Optimization Techniques

#### 1. Caching

```python
from functools import lru_cache

@lru_cache(maxsize=128)
def get_agency_name(agency_id: str) -> str:
    """Cache agency lookups"""
    # First call: fetch from API
    # Subsequent calls: return cached result
    pass

# Clear cache if needed
get_agency_name.cache_clear()

# Check cache stats
print(get_agency_name.cache_info())
# CacheInfo(hits=99, misses=1, maxsize=128, currsize=1)
```

#### 2. Batch API Calls

```python
# Instead of:
for award_id in award_ids:
    response = await make_api_request(f"awards/{award_id}/")  # N requests!

# Do:
response = await make_api_request("awards/search/", params={
    "filters": {"award_ids": award_ids}  # 1 request!
})
```

#### 3. Reduce Response Size

```python
# Instead of:
response = await make_api_request("awards/search/", {
    "limit": 1000
})

# Do:
response = await make_api_request("awards/search/", {
    "limit": 100,  # Smaller page
    "fields": ["id", "recipient_name", "amount"]  # Only needed fields
})
```

#### 4. Parallelize Requests

```python
import asyncio

# Instead of:
for item in items:
    result = await process_item(item)  # Sequential: item1, then item2, then item3

# Do:
results = await asyncio.gather(
    process_item(items[0]),
    process_item(items[1]),
    process_item(items[2]),
)  # Parallel: all three at once!
```

### Rate Limiter Tuning

```python
# Current default: 60 requests/minute
rate_limiter = initialize_rate_limiter(requests_per_minute=60)

# For high-concurrency scenarios: increase
rate_limiter = initialize_rate_limiter(requests_per_minute=120)

# For conservative use: decrease
rate_limiter = initialize_rate_limiter(requests_per_minute=30)
```

### Timeout Tuning

```python
# Current: 30 seconds per request
http_client = httpx.AsyncClient(timeout=30.0)

# For slow networks: increase
http_client = httpx.AsyncClient(timeout=60.0)

# For fast networks: decrease
http_client = httpx.AsyncClient(timeout=10.0)
```

---

## Security & Reliability

### Input Validation

```python
def validate_award_id(award_id: str) -> bool:
    """Validate award ID format"""
    # Award IDs should be numeric or have specific format
    if not award_id or len(award_id) == 0:
        return False
    if not award_id.isdigit():
        return False
    if len(award_id) > 20:  # Sanity check
        return False
    return True

# Use in tool
if not validate_award_id(award_id):
    return [TextContent(type="text", text="Error: Invalid award ID format")]
```

### Parameter Sanitization

```python
def sanitize_search_query(query: str) -> str:
    """Remove potentially dangerous characters"""
    # Strip whitespace
    query = query.strip()

    # Limit length to prevent DoS
    if len(query) > 1000:
        query = query[:1000]

    # Remove special characters that could break the API
    # (this depends on what the API accepts)

    return query

# Use in tool
safe_query = sanitize_search_query(query)
```

### Error Information Disclosure

```python
# DON'T: Expose internal errors to users
return [TextContent(type="text", text=f"Error: {e}")]  # Might leak paths, secrets

# DO: Return generic error message
logger.error(f"Internal error: {e}", exc_info=True)  # Log the real error
return [TextContent(type="text", text="Error: An unexpected error occurred")]
```

### Rate Limiting as Security

The rate limiter protects against abuse:

```python
# Limits to 60 requests/minute prevents:
# - Brute force attacks
# - Resource exhaustion
# - Crawling the entire database
# - DoS attacks
```

### Dependency Management

```bash
# Always pin dependencies to prevent unexpected changes
# requirements.txt:
fastmcp==1.0.5
httpx==0.27.0
uvicorn[standard]==0.28.0

# Check for security vulnerabilities
pip install safety
safety check

# Update safely
pip install --upgrade-strategy only-if-needed -r requirements.txt
```

### Environment Variables

```python
# DON'T hardcode secrets
API_KEY = "sk_live_abc123..."

# DO use environment variables
import os
API_KEY = os.getenv("USASPENDING_API_KEY")

# Or use .env file
from dotenv import load_dotenv
load_dotenv()
API_KEY = os.getenv("USASPENDING_API_KEY")
```

---

## Deployment & Operations

### Development vs. Production

```python
# server.py setup differs by environment

if os.getenv("ENVIRONMENT") == "production":
    # Production: JSON logging, monitoring
    setup_structured_logging(json_mode=True)
    logger.setLevel(logging.INFO)
    rate_limiter = initialize_rate_limiter(120)  # Higher limit
else:
    # Development: Text logging, debug mode
    setup_structured_logging(json_mode=False)
    logger.setLevel(logging.DEBUG)
    rate_limiter = initialize_rate_limiter(60)
```

### Startup Sequence

```bash
# 1. Activate environment
source .venv/bin/activate

# 2. Check dependencies
pip install -r requirements.txt

# 3. Start server
./start_mcp_server.sh

# Or manually:
python -m usaspending_mcp  # HTTP mode on port 3002
```

### Monitoring

```python
# Health check endpoint (if needed)
@app.route("/health", methods=["GET"])
async def health_check():
    return {
        "status": "healthy",
        "rate_limiter_tokens": rate_limiter.get_available_tokens(),
        "uptime": time.time() - start_time
    }
```

### Graceful Shutdown

```python
@app.on_shutdown
async def shutdown():
    """Clean up resources on shutdown"""
    await http_client.aclose()
    logger.info("Server shutdown gracefully")
```

### Server Management

```bash
# Using provided script
./start_mcp_server.sh        # Start server
python server_manager.py stop  # Stop all servers
python server_manager.py stop 3002  # Stop specific port
```

---

## Common Pitfalls

### Pitfall 1: Forgetting to Await Async Functions

```python
# WRONG: Not awaiting
response = http_client.get(url)  # Returns coroutine, not response!

# CORRECT: Awaiting
response = await http_client.get(url)  # Actually gets the response
```

### Pitfall 2: Blocking the Event Loop

```python
# WRONG: Blocking operation in async function
import time
time.sleep(5)  # Blocks entire event loop!

# CORRECT: Using async sleep
await asyncio.sleep(5)  # Only pauses this coroutine
```

### Pitfall 3: Not Handling Exceptions

```python
# WRONG: Exception propagates unhandled
response = await make_api_request(endpoint, params)
data = response.json()  # Could raise if not valid JSON

# CORRECT: Handle exceptions
try:
    response = await make_api_request(endpoint, params)
    data = response.json()
except Exception as e:
    logger.error(f"Error: {e}")
    return [TextContent(type="text", text="Error occurred")]
```

### Pitfall 4: Creating Multiple Rate Limiters

```python
# WRONG: Creates multiple independent rate limiters
def tool1():
    limiter = initialize_rate_limiter(60)
    await limiter.wait_if_needed("default")

def tool2():
    limiter = initialize_rate_limiter(60)  # Different instance!
    await limiter.wait_if_needed("default")

# Each tool has its own 60 req/min limit = 120 total (defeats purpose!)

# CORRECT: Use global rate limiter
# In server.py:
rate_limiter = initialize_rate_limiter(60)  # Created once

# Then in all tools:
await rate_limiter.wait_if_needed("default")
```

### Pitfall 5: Sensitive Data in Logs

```python
# WRONG: Logging API response with sensitive data
logger.info(f"Response: {response.json()}")  # Might contain secrets!

# CORRECT: Log selectively
logger.info(f"Response: {response.status_code}, results: {len(data)}")
# Or log to separate secure file
```

### Pitfall 6: Not Testing Edge Cases

```python
# WRONG: Only test happy path
async def test_search():
    result = await search_federal_awards("space")
    assert "results" in str(result)

# CORRECT: Test edge cases
async def test_search_empty_query():
    result = await search_federal_awards("")
    assert "Error" in str(result)

async def test_search_special_characters():
    result = await search_federal_awards("<script>alert(1)</script>")
    # Should either be escaped or rejected

async def test_search_very_large_limit():
    result = await search_federal_awards("test", max_results=999999)
    # Should cap at reasonable limit
```

### Pitfall 7: Inconsistent Error Handling

```python
# WRONG: Different error handling in different tools
def tool1():
    try:
        response = await make_api_request(...)
    except:
        return [TextContent(type="text", text="Something went wrong")]

def tool2():
    try:
        response = await make_api_request(...)
    except Exception as e:
        return [TextContent(type="text", text=f"Error: {type(e).__name__}")]

# CORRECT: Extract to helper function
async def safe_api_call(endpoint: str, params: dict):
    """Make API call with consistent error handling"""
    try:
        response = await make_api_request(endpoint, params)
        response.raise_for_status()
        return response.json()
    except httpx.TimeoutException:
        logger.error("Request timeout")
        return None
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP {e.response.status_code}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return None

# Use in all tools
data = await safe_api_call(endpoint, params)
if data is None:
    return [TextContent(type="text", text="Error: Failed to retrieve data")]
```

---

## Code Quality & Best Practices

### Code Style

Follow PEP 8:

```bash
# Format code with black
black src/ tests/

# Sort imports
isort src/ tests/

# Check style
flake8 src/ tests/

# Type check
mypy src/
```

### Documentation

```python
def search_federal_awards(
    query: str,
    max_results: int = 10,
    agency_name: str = None
) -> TextContent:
    """
    Search for federal awards matching criteria.

    Searches the USASpending.gov API for awards matching the provided
    query. Results can be filtered by agency. The function automatically
    applies rate limiting and retry logic.

    Args:
        query: The search term (required). Can include keywords like
            "space", "infrastructure", etc. Minimum 1 character.
        max_results: Maximum number of results to return (default 10).
            Capped at 100 to prevent excessive API load. Must be positive.
        agency_name: Optional agency name to filter results. If provided,
            only awards from this agency are returned. Example: "NASA".

    Returns:
        TextContent: Formatted text with search results or error message.
        Each result includes award ID, recipient name, amount, and link.

    Raises:
        No exceptions are raised; errors are returned as TextContent.

    Examples:
        >>> result = await search_federal_awards("space contracts")
        >>> print(result[0].text)
        # Results for space contracts

        - SpaceX: $500,000,000
        - Blue Origin: $250,000,000

        >>> result = await search_federal_awards("nasa", agency_name="NASA")
        >>> # Returns only NASA awards

    Notes:
        - Rate limit: 60 requests/minute (global)
        - Retry policy: 3 attempts with exponential backoff
        - Timeout: 30 seconds per request
        - API: https://api.usaspending.gov/api/v2/
    """
    # Implementation
```

### Commit Messages

```bash
# Good commit message
git commit -m "Add get_idv_details tool

- Retrieve comprehensive details for Indefinite Delivery Vehicles
- Includes vehicle type, total value, agency, and order count
- Uses USASpending.gov /idvs/{id}/ endpoint with retry logic
- Add unit tests covering success, not found, and empty input cases
- Adds 5-minute rate limiting per IDV to prevent hammering API"

# Bad commit message
git commit -m "fix bug"
git commit -m "update stuff"
git commit -m "WIP"
```

---

## Learning Resources

### Within This Repository

- `docs/guides/QUICKSTART.md` - Get running in 5 minutes
- `docs/dev/ARCHITECTURE_GUIDE.md` - Deep architecture dive
- `docs/dev/TESTING_GUIDE.md` - Testing strategies
- `docs/guides/CONVERSATION_LOGGING_GUIDE.md` - Conversation tracking and analytics
- `docs/API_RESOURCES.md` - USASpending.gov API reference
- Existing tests - Learn from test patterns
- Existing tools - See how tools are implemented

### External Resources

**Python Async:**
- [Real Python: Async IO](https://realpython.com/async-io-python/)
- [Python docs: asyncio](https://docs.python.org/3/library/asyncio.html)
- [Async patterns](https://github.com/aio-libs/aiohttp)

**MCP & FastMCP:**
- [MCP Spec](https://spec.modelcontextprotocol.io/)
- [FastMCP GitHub](https://github.com/jlouis/fastmcp)
- [MCP Examples](https://github.com/anthropics/mcp-server-fastmcp)

**API Design:**
- [REST API Best Practices](https://restfulapi.net/)
- [API Error Handling](https://www.rfc-editor.org/rfc/rfc9110#name-status-codes)
- [Rate Limiting Patterns](https://cloud.google.com/architecture/rate-limiting-strategies-techniques)

**Python Best Practices:**
- [PEP 8](https://www.python.org/dev/peps/pep-0008/)
- [PEP 257 - Docstrings](https://www.python.org/dev/peps/pep-0257/)
- [Real Python](https://realpython.com/)

---

## Next Steps

### Immediate (This Week)

1. **Clone and run** the server locally
2. **Read** `server.py` and understand tool structure
3. **Write a test** for an existing tool
4. **Run all tests** and understand test patterns
5. **Trace a request** through the code with debugger

### Short Term (This Month)

1. **Add a new tool** to analyze a different spending category
2. **Optimize** a slow tool using profiling
3. **Write integration tests** for your new tool
4. **Improve error handling** in an existing tool
5. **Add caching** to a frequently-called tool
6. **Explore conversation tracking** - understand how tools are used across conversations

### Long Term (This Quarter)

1. **Refactor** utilities into separate package
2. **Add metrics/monitoring** for production
3. **Implement caching layer** (Redis or similar)
4. **Create dashboard** for monitoring FAR searches and conversation analytics
5. **Optimize** rate limiter for multi-process deployment
6. **Build analytics engine** for conversation patterns and tool usage trends

---

## Conclusion

This USASpending MCP Server demonstrates many important software engineering concepts:

- **Architecture patterns** - Decorators, singleton, facade, repository
- **Async programming** - Concurrent requests, non-blocking I/O
- **Resilience** - Rate limiting, retries, graceful degradation
- **Observability** - Structured logging, search analytics, conversation tracking
- **Testing** - Unit tests, integration tests, mocking
- **Security** - Input validation, error handling, dependency management
- **Operations** - Deployment, monitoring, graceful shutdown

Use this codebase to:
1. Understand how production systems are built
2. Learn best practices for API integration
3. Master async Python programming
4. Get familiar with testing and debugging
5. Build your own projects with confidence

**Happy coding!**
