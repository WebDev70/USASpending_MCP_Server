# USASpending MCP Server: A High School Development Guide

## Table of Contents
1. [What is This Project?](#what-is-this-project)
2. [Real-World Analogy](#real-world-analogy)
3. [How the System Works (Step-by-Step)](#how-the-system-works-step-by-step)
4. [The Key Components](#the-key-components)
5. [Following a Request Through the System](#following-a-request-through-the-system)
6. [Getting Started with Development](#getting-started-with-development)
7. [Understanding the Code](#understanding-the-code)
8. [Advanced Concepts](#advanced-concepts)

---

## What is This Project?

The **USASpending MCP Server** is a Python application that helps people find information about federal government spending. Imagine you wanted to know:

- "How much money did the government spend on space programs?"
- "Which companies got government contracts?"
- "What are the rules for federal contract bidding?"

This project answers those questions by:
1. Taking your questions (we call them "requests")
2. Connecting to the U.S. government's USASpending.gov website
3. Searching through government spending data
4. Formatting the results nicely for you

**Key Facts:**
- Built with **Python** (a programming language)
- Uses **FastMCP** (a framework for connecting to AI assistants like Claude)
- Works with **real government data** from USASpending.gov
- Can handle **27 different tools** to analyze federal spending, regulations, and conversations
- Includes **conversation management** to track and analyze interaction history
- **Recently refactored** into modular architecture (2024): server.py reduced from 4,515 lines to 199 lines!

---

## Real-World Analogy

Think of this system like a **Library Assistant Robot**:

```
You: "Find me books about space spending"
        ↓
Robot checks if it's busy (Rate Limiter)
        ↓
Robot goes to the library (USASpending.gov API)
        ↓
Robot searches the database (with retries if it fails)
        ↓
Robot finds books and brings them back
        ↓
Robot formats them nicely on a shelf
        ↓
Robot gives them to you
```

**The Components:**
- **You** = Claude AI or a user
- **Robot's ears** = MCP Protocol (how requests come in)
- **Robot's memory** = Rate Limiter (remembers how many requests we've made)
- **Robot's hands** = HTTP Client (grabs data from the internet)
- **Robot's brain** = Retry Logic (tries again if something fails)
- **Robot's notebook** = Logging (tracks everything the robot does)
- **Robot's delivery system** = Response Formatting (makes the answer look nice)

---

## How the System Works (Step-by-Step)

### Step 1: A Request Arrives

Someone (or Claude AI) asks a question:
```
"Search for federal awards related to space exploration"
```

This request comes in through the **MCP Protocol**. Think of this like a telephone line that only AI assistants can use.

### Step 2: The Request Gets Processed

The FastMCP framework:
1. Recognizes which "tool" the request wants to use
2. Checks the parameters (the specific details of the request)
3. Routes it to the correct Python function

### Step 3: Rate Limiting Check

Before doing anything, the system asks: **"Have we made too many requests lately?"**

This is like a bouncer at a concert:
- "You can enter if you have a ticket" = You can make a request if you have rate limit tokens
- "Sorry, we're full" = We've made too many requests recently, please wait

**Default limit:** 60 requests per minute (1 per second)

```python
# Example:
await rate_limiter.wait_if_needed("default")
# This either:
#   - Returns immediately if tokens available
#   - Waits a bit if we're at the limit
```

### Step 4: The API Call

The system makes a call to the real USASpending.gov API:

```
URL: https://api.usaspending.gov/api/v2/awards/search/
Parameters: {"keywords": ["space"], "limit": 5}

Response: {
  "results": [
    {
      "id": "12345",
      "recipient": "SpaceX",
      "amount": 500000000,
      ...
    },
    ...
  ]
}
```

### Step 5: Handling Failures (Retry Logic)

If something goes wrong (internet hiccup, server busy), the system automatically **retries** with exponential backoff:

```
Attempt 1: Try immediately → FAIL
         ↓ Wait 1 second
Attempt 2: Try again → FAIL
         ↓ Wait 2 seconds
Attempt 3: Try again → SUCCESS!
```

It tries up to **3 times** before giving up.

### Step 6: Formatting the Results

The raw data gets formatted nicely for humans:

```python
# Raw data:
{"amount": 500000000, "recipient": "SpaceX", "id": 12345}

# Formatted output:
Award ID: 12345
Recipient: SpaceX
Amount: $500,000,000
Link: https://www.usaspending.gov/award/12345
```

### Step 7: Logging Everything

The system writes down what it did:
- What tool was called
- How long it took
- What search terms were used
- Whether it was successful

This is useful for:
- **Debugging** (finding bugs)
- **Analytics** (understanding what people search for)
- **Monitoring** (making sure the system is healthy)

### Step 8: Sending the Response Back

The formatted results go back to Claude or the user through the MCP Protocol.

---

## The Key Components

### Component 1: `server.py` (The Headquarters - REFACTORED!)

This is the **main initialization file** that sets everything up and coordinates all tool modules.

**What it does (now very focused):**
- Creates the FastMCP app (the main framework)
- Initializes the rate limiter
- Sets up the HTTP client
- **Registers all modular tool modules** (see below)
- Handles server startup (HTTP and stdio modes)

**Analogy:** This is like the reception desk - it greets visitors, checks them in, and routes them to the right department.

**NEW: Modular Tool Architecture (2024 Refactoring)**

Instead of one giant 4,515-line file, tools are now organized into focused modules:

```
tools/
├── __init__.py         ← Coordinates all registrations
├── helpers.py          ← Shared utilities (QueryParser, formatters, URL generators)
├── awards.py           ← 6 award discovery tools
├── spending.py         ← 8 spending analysis tools
├── classifications.py  ← 5 classification analysis tools
├── profiles.py         ← 4 profile tools
├── conversations.py    ← 4 conversation management tools
└── far.py              ← 5 FAR regulation tools
```

**How registration works:**
```python
# In server.py (now only 199 lines):
from usaspending_mcp.tools import register_all_tools

register_all_tools(
    app,                    # FastMCP app
    http_client,            # For API calls
    rate_limiter,           # For rate limiting
    base_url,              # API URL
    logger,                # For logging
    award_type_map,        # For parsing queries
    toptier_agency_map,    # For agency names
    subtier_agency_map     # For sub-agency names
)
```

This pattern allows each tool module to access dependencies via **closures** (a Python concept explained in the Advanced Concepts section).

### Component 2: `tools/far.py` (The Regulation Specialist)

**FAR** = Federal Acquisition Regulation (rules for government contracts)

**What it does:**
- Provides 5 tools for searching federal regulations
- Searches across 4 parts of the FAR (Parts 14, 15, 16, 19)
- Lets people look up rules without calling the internet

**Tools:**
1. `search_far_regulations` - Keyword search
2. `get_far_section` - Look up specific sections
3. `get_far_topic_sections` - Find sections by topic
4. `get_far_analytics_report` - See which sections are popular
5. `check_far_compliance` - Check if something follows the rules

### Component 3: `utils/rate_limit.py` (The Bouncer)

**What it does:**
- Tracks how many requests we've made
- Decides if we can make another request right now
- Uses a "token bucket" algorithm

**How tokens work:**
```
Bucket capacity: 60 tokens
Refill rate: 1 token per second

Made 10 requests? 50 tokens left
Can I make another request? YES (if tokens > 0)
Wait 5 seconds? 5 new tokens added
```

### Component 4: `utils/retry.py` (The Persistent Worker)

**What it does:**
- Wraps API calls with retry logic
- Automatically tries again if something fails
- Waits longer each time (exponential backoff)

**Failures it handles:**
- Network timeouts (internet is slow)
- Connection errors (can't reach the server)
- Server errors (500, 502, 503, 504)
- Rate limit hits (429 error)

**Example:**
```python
@make_api_call_with_retry
async def get_award_details(award_id: str):
    # Try up to 3 times
    # Wait 1-10 seconds between tries
    return await http_client.get(url)
```

### Component 5: `utils/logging.py` (The Notebook)

**What it does:**
- Records everything that happens
- Creates log files for different purposes
- Writes in JSON format (easy for computers to read) or plain text

**Three log files:**
1. **usaspending_mcp.log** - All events (general logging)
2. **usaspending_mcp_errors.log** - Only errors (problems)
3. **usaspending_mcp_searches.log** - Only search events (analytics)

**What gets logged:**
```
[2024-11-13 14:32:15] Tool: search_federal_awards
[2024-11-13 14:32:15] Query: "space"
[2024-11-13 14:32:16] Results: 5 awards found
[2024-11-13 14:32:16] Execution time: 0.8 seconds
```

### Component 6: `loaders/far.py` (The Data Loader)

**What it does:**
- Loads all the FAR regulation data from JSON files
- Stores it in memory so we don't need to reload it
- Makes FAR searches instant (no internet needed)

**Process:**
```
1. Application starts
2. Load: docs/data/far/far_part14.json
3. Load: docs/data/far/far_part15.json
4. Load: docs/data/far/far_part16.json
5. Load: docs/data/far/far_part19.json
6. Store in memory (cached)
7. Ready to search instantly
```

### Component 7: `client.py` (The Test Driver)

**What it does:**
- Connects to the server for testing
- Uses stdio mode (for development)
- Lets developers test tools before they go to production

**Usage:**
```bash
python -m usaspending_mcp.client
# Opens interactive menu to test tools
```

---

## Following a Request Through the System

Let's trace a real request from start to finish.

### Example: "Search for space contracts"

```
┌─────────────────────────────────────────────────────────────┐
│ STEP 1: REQUEST ARRIVES                                     │
│ User: "Search for federal awards about space"              │
│ Tool: search_federal_awards                                 │
│ Parameters: query="space", max_results=5                   │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ STEP 2: RATE LIMITING                                       │
│ Check: Do we have tokens available?                         │
│ Status: ✓ Yes, we have 45 tokens left (out of 60)          │
│ Action: Consume 1 token, continue                          │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ STEP 3: VALIDATION                                          │
│ Check: Is "space" a valid query?                           │
│ Check: Is 5 a valid max_results value?                     │
│ Status: ✓ Both valid                                        │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ STEP 4: BUILD API REQUEST                                   │
│ URL: https://api.usaspending.gov/api/v2/awards/search/    │
│ Headers: {"timeout": 30}                                   │
│ Body: {"filters": {"keywords": ["space"]}, "limit": 5}     │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ STEP 5: MAKE API CALL WITH RETRY                           │
│                                                              │
│ Attempt 1: GET → Response: 200 OK ✓                        │
│ → No retries needed!                                        │
│                                                              │
│ Parsing response...                                         │
│ Found 5 awards:                                             │
│   1. SpaceX - $500M                                         │
│   2. Blue Origin - $250M                                    │
│   3. NASA - $1B                                             │
│   4. Orbital Sciences - $150M                               │
│   5. Sierra Space - $75M                                    │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ STEP 6: FORMAT RESULTS                                      │
│                                                              │
│ **Federal Awards - Space**                                  │
│                                                              │
│ 1. SpaceX                                                   │
│    Award ID: 12345                                          │
│    Amount: $500,000,000                                     │
│    Link: https://usaspending.gov/award/12345               │
│                                                              │
│ 2. Blue Origin                                              │
│    Award ID: 12346                                          │
│    Amount: $250,000,000                                     │
│    Link: https://usaspending.gov/award/12346               │
│    ...                                                      │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ STEP 7: LOGGING                                             │
│                                                              │
│ Log entry written:                                          │
│ {                                                           │
│   "timestamp": "2024-11-13T14:32:16.234Z",                │
│   "tool": "search_federal_awards",                          │
│   "query": "space",                                         │
│   "results": 5,                                             │
│   "execution_time_ms": 845,                                 │
│   "status": "success"                                       │
│ }                                                           │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ STEP 8: SEND RESPONSE                                       │
│                                                              │
│ TextContent {                                               │
│   "type": "text",                                           │
│   "text": "**Federal Awards - Space** ..."                 │
│ }                                                           │
│                                                              │
│ Response sent back through MCP Protocol                    │
│ to Claude or user interface                                │
└─────────────────────────────────────────────────────────────┘
```

**Total time:** ~0.8-1.0 seconds

---

## Getting Started with Development

### Prerequisites

You'll need:
- **Python 3.10+** (programming language)
- **pip** (package manager)
- **Git** (version control)
- A terminal/command line

### Setup Steps

#### Step 1: Clone the Repository
```bash
git clone <repository-url>
cd usaspending-mcp
```

#### Step 2: Create a Virtual Environment
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

**Why a virtual environment?**
- Keeps project dependencies separate
- Doesn't interfere with your system Python
- Like a sandbox just for this project

#### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

**What gets installed:**
- `fastmcp` - The MCP server framework
- `httpx` - For making HTTP requests
- `uvicorn` - The web server
- `tenacity` - For retry logic
- `python-json-logger` - For structured logging

#### Step 4: Run the Server

**Option A: HTTP mode (recommended for learning)**
```bash
./start_mcp_server.sh
# Server runs on http://127.0.0.1:3002/mcp
```

**Option B: Stdio mode (for testing)**
```bash
PYTHONPATH=src ./.venv/bin/python -m usaspending_mcp.server --stdio
```

#### Step 5: Test a Tool

**Using the test client:**
```bash
PYTHONPATH=src ./.venv/bin/python -m usaspending_mcp.client
# Interactive menu appears
# Choose a tool to test
```

---

## Understanding the Code

### File Structure (After 2024 Refactoring)

```
usaspending-mcp/
├── src/usaspending_mcp/
│   ├── server.py           ← Main file (199 lines - just setup & coordination)
│   ├── client.py           ← Test client
│   ├── tools/
│   │   ├── __init__.py     ← Tool registration coordinator
│   │   ├── helpers.py      ← Shared utilities (720 lines)
│   │   ├── awards.py       ← Award discovery tools (1,296 lines, 6 tools)
│   │   ├── spending.py     ← Spending analysis tools (1,165 lines, 8 tools)
│   │   ├── classifications.py ← NAICS/PSC tools (1,385 lines, 5 tools)
│   │   ├── profiles.py     ← Profile tools (673 lines, 4 tools)
│   │   ├── conversations.py ← Conversation tools (337 lines, 4 tools)
│   │   └── far.py          ← FAR regulation tools (5 tools)
│   ├── loaders/
│   │   └── far.py          ← Load FAR data
│   └── utils/
│       ├── rate_limit.py   ← Token bucket
│       ├── retry.py        ← Retry logic
│       ├── logging.py      ← Structured logging
│       ├── conversation_logging.py ← Conversation tracking
│       ├── search_analytics.py  ← Track searches
│       ├── query_context.py ← Query refinement
│       ├── result_aggregation.py ← Result grouping
│       ├── relevance_scoring.py ← Smart ranking
│       └── far.py          ← FAR database
│
├── docs/
│   ├── data/far/           ← FAR regulation JSON files
│   ├── guides/             ← Documentation
│   └── archived/           ← This guide and JUNIOR_DEVELOPER_GUIDE.md
│
├── tests/                  ← Unit tests
├── REFACTORING_*.md        ← Guides on the 2024 refactoring
├── requirements.txt        ← Dependencies
└── pyproject.toml          ← Project config
```

### Reading the Main File: `server.py` (Now Much Cleaner!)

The refactored server.py is only **199 lines** and is organized like this:

```python
# ═══════════════════════════════════════════
# SECTION 1: IMPORTS
# ═══════════════════════════════════════════
import asyncio
from fastmcp import FastMCP
from utils.rate_limit import initialize_rate_limiter
# ... more imports

# ═══════════════════════════════════════════
# SECTION 2: SETUP (Logging, Rate Limiting, etc.)
# ═══════════════════════════════════════════
app = FastMCP(name="usaspending-server")
rate_limiter = initialize_rate_limiter(60)  # 60 req/min
http_client = httpx.AsyncClient(timeout=30.0)

# ═══════════════════════════════════════════
# SECTION 3: REGISTER ALL TOOL MODULES
# ═══════════════════════════════════════════
from usaspending_mcp.tools import register_all_tools

register_all_tools(
    app, http_client, rate_limiter, BASE_URL, logger,
    AWARD_TYPE_MAP, TOPTIER_AGENCY_MAP, SUBTIER_AGENCY_MAP
)
# Now all 27 tools from 6 modules are registered!

# ═══════════════════════════════════════════
# SECTION 4: SERVER STARTUP/SHUTDOWN
# ═══════════════════════════════════════════
async def run_stdio():
    await app.run_stdio_async()

def run_server():
    uvicorn.run(app.http_app(), host="127.0.0.1", port=3002)

if __name__ == "__main__":
    # ... decide between HTTP or stdio mode
```

**Much simpler!** All the tool logic is now in focused modules.

### Reading Tool Modules (e.g., `tools/awards.py`)

Here's how each tool module is structured:

```python
"""
Award search and details tools.
...
"""

def register_tools(
    app, http_client, rate_limiter, base_url, logger_instance,
    award_type_map, toptier_agency_map, subtier_agency_map
) -> None:
    """
    Register all award tools.

    These parameters are available to all nested tool functions
    through CLOSURES (explained below).
    """

    @app.tool(name="get_award_by_id")
    async def get_award_by_id(award_id: str) -> TextContent:
        # Can use: http_client, rate_limiter, base_url, etc.
        await rate_limiter.wait_if_needed()
        # ... rest of tool code

    @app.tool(name="search_federal_awards")
    async def search_federal_awards(query: str, max_results: int = 5):
        # Can also use http_client, rate_limiter, etc.
        parser = QueryParser(query, award_type_map, toptier_agency_map, subtier_agency_map)
        # ... rest of tool code
```

**Key pattern:** Each tool module has ONE `register_tools()` function that:
1. Receives all shared dependencies as parameters
2. Defines all tools for that category
3. Each tool can access the parameters via Python **closures**

### Anatomy of a Tool (Modular Architecture)

In the refactored architecture, tools live in module files like `tools/awards.py`. Here's how they're structured:

**File: `tools/awards.py`**

```python
"""
Award search and details tools.

This module contains 6 award-related tools that help find and analyze
federal award contracts, grants, and other spending.
"""

def register_tools(
    app,                      # FastMCP app (pass-through parameter)
    http_client,              # Async HTTP client for API calls
    rate_limiter,             # Rate limiter to respect API limits
    base_url,                 # Base URL for USASpending.gov API
    logger_instance,          # Logger for recording events
    award_type_map,           # Mapping of award types (contract, grant, etc.)
    toptier_agency_map,       # Mapping of agency names for normalization
    subtier_agency_map        # Mapping of sub-agency names
) -> None:
    """
    Register all award tools with FastMCP.

    The key pattern here: ALL nested tool functions can ACCESS these parameters
    through CLOSURES (explained below). They don't need to be passed explicitly.
    """

    @app.tool(
        name="search_federal_awards",
        description="Search for federal awards by keyword, agency, recipient, etc."
    )
    async def search_federal_awards(
        query: str,
        max_results: int = 10,
        agency_name: str = None,
    ) -> TextContent:
        """
        Search for federal awards.

        This function can use http_client, rate_limiter, logger_instance, etc.
        without them being passed in - they're captured via closure!
        """

        # Step 1: Check rate limit
        await rate_limiter.wait_if_needed("default")

        # Step 2: Validate inputs
        if not query or len(query.strip()) == 0:
            return [TextContent(type="text", text="Error: Query cannot be empty")]

        # Step 3: Build API request
        params = {
            "filters": {"keywords": [query]},
            "limit": min(max_results, 100)
        }

        # Step 4: Make API call
        try:
            response = await http_client.get(
                f"{base_url}/awards/search/",
                params=params
            )
            response.raise_for_status()
        except Exception as e:
            logger_instance.error(f"API call failed: {e}")
            return [TextContent(type="text", text=f"Error: {str(e)}")]

        # Step 5: Format results
        output = f"# Federal Awards - {query}\n\n"
        results = response.json().get("results", [])

        for award in results[:max_results]:
            output += f"**{award['recipient']['name']}**\n"
            output += f"- Award ID: {award['id']}\n"
            output += f"- Amount: ${award['amount']:,.0f}\n\n"

        # Step 6: Log the search
        logger_instance.info(f"Tool: search_federal_awards | Query: {query}")

        # Step 7: Return response
        return [TextContent(type="text", text=output)]

    # Other tool definitions follow the same pattern...
```

**Key Pattern Explanation: Closures**

The magic is in how the tool function accesses parameters like `http_client` and `rate_limiter`. Here's the flow:

```
┌─────────────────────────────────────┐
│ server.py                           │
│  awards.register_tools(             │
│    app, http_client,                │
│    rate_limiter, ...                │
│  )                                  │
└──────────────┬──────────────────────┘
               │ (parameters passed)
               ▼
┌──────────────────────────────────┐
│ register_tools() function        │
│  - Receives all parameters       │
│  - Defines nested tools          │
└──────────────────────────────────┘
               │
               ▼
      ┌────────────────┐
      │ Tool function  │
      │ Can ACCESS:    │
      │ - http_client  │← Captured from outer scope
      │ - rate_limiter │← Captured from outer scope
      │ - logger       │← Captured from outer scope
      │ (via closure!) │
      └────────────────┘
```

This is called a **closure** - a nested function that remembers variables from its outer scope.

### Key Python Concepts Used

#### 1. **async/await** (Asynchronous Programming)
```python
async def search_federal_awards(query: str):
    # await means "wait for this to finish"
    response = await http_client.get(url)
    # While we wait, other requests can be processed!
```

**Why?** Makes the server handle multiple requests at the same time.

#### 2. **Decorators** (Functions that modify functions)
```python
@app.tool(name="search_federal_awards")
# This decorator tells FastMCP: "This function is a tool!"

@make_api_call_with_retry
# This decorator wraps our function with retry logic
```

#### 3. **Type Hints** (Declaring data types)
```python
def search_federal_awards(
    query: str,          # query MUST be a string
    max_results: int = 10  # max_results should be an integer
) -> TextContent:        # Returns TextContent
```

**Why?** Helps catch bugs and makes code easier to understand.

#### 4. **Context Managers** (with statement)
```python
async with http_client.get(url) as response:
    # Automatically cleans up resources
    data = await response.json()
```

#### 5. **List Comprehensions** (Compact list creation)
```python
# Instead of:
results = []
for award in response.json()["results"]:
    if award["amount"] > 1000000:
        results.append(award)

# We can write:
results = [a for a in response.json()["results"] if a["amount"] > 1000000]
```

#### 6. **Closures** (Nested functions remembering outer scope) ⭐ IMPORTANT FOR MODULAR ARCHITECTURE
```python
def register_tools(app, http_client, rate_limiter):
    """Outer function - receives dependencies"""

    @app.tool(name="search_federal_awards")
    async def search_federal_awards(query: str):
        """Inner function - can use http_client and rate_limiter!"""
        await rate_limiter.wait_if_needed()  # Accessing rate_limiter from outer scope
        response = await http_client.get(url)  # Accessing http_client from outer scope
        return response.json()

# The inner function "closes over" (remembers) the parameters from the outer function
# This is how tool functions access shared dependencies without passing them explicitly!
```

**Why Closures Matter in This Project:**
- Tool functions need access to `http_client`, `rate_limiter`, `logger`, etc.
- Instead of passing them to every tool function, we pass them to `register_tools()`
- All nested tool functions automatically have access to them via closure
- This keeps the tool function signatures clean: `search_federal_awards(query: str)` instead of `search_federal_awards(query, http_client, rate_limiter, logger, ...)`

---

## Advanced Concepts

### Dependency Injection via Closures (How Modular Architecture Works)

**The Problem:**
All tools need access to the same objects (http_client, rate_limiter, logger), but we don't want to pass them to every tool function.

**The Solution:**
Use closures to "inject" dependencies automatically.

**Step-by-Step Flow:**

```
Step 1: server.py creates shared objects
┌─────────────────────────────────┐
│ server.py                       │
│ app = FastMCP()                 │
│ http_client = AsyncClient()     │
│ rate_limiter = RateLimiter()    │
│ logger = get_logger()           │
└────────┬────────────────────────┘
         │
Step 2: Pass them to register_all_tools
         │
         ▼
┌────────────────────────────────────────────┐
│ register_all_tools(app, http_client, ...) │
│  │                                         │
│  ├─→ awards.register_tools(...)           │
│  │   └─→ All 6 award tools get access     │
│  │       to http_client, etc via closure  │
│  │                                        │
│  ├─→ spending.register_tools(...)         │
│  │   └─→ All 8 spending tools get access  │
│  │       to http_client, etc via closure  │
│  │                                        │
│  └─→ classifications.register_tools(...) │
│      └─→ All 5 classification tools ...   │
└────────────────────────────────────────────┘

Step 3: Tools in each module access dependencies via closure
         ▼
     ┌─────────────────┐
     │ Tool Function   │
     │ async def       │
     │ search_awards() │
     │ {               │
     │ Can use:        │
     │ http_client ←──┘ (from outer scope)
     │ rate_limiter←─┘ (from outer scope)
     │ logger ←──────┘ (from outer scope)
     │ }               │
     └─────────────────┘
```

**Code Example:**

```python
# tools/awards.py
def register_tools(app, http_client, rate_limiter, logger):
    # These parameters are "captured" by closures below

    @app.tool(name="get_award_by_id")
    async def get_award_by_id(award_id: str):
        # This function remembers http_client and rate_limiter
        # even though they're not passed in!
        await rate_limiter.wait_if_needed()

        response = await http_client.get(
            f"https://api.usaspending.gov/api/v2/awards/{award_id}/"
        )

        return [TextContent(...)]

    @app.tool(name="search_federal_awards")
    async def search_federal_awards(query: str, max_results: int = 10):
        # This function ALSO remembers http_client and rate_limiter
        await rate_limiter.wait_if_needed()

        response = await http_client.get(...)

        return [TextContent(...)]
```

**Why This Pattern is Powerful:**

1. **Cleaner tool signatures** - No need to pass dependencies to every tool
2. **Centralized initialization** - All shared objects created once in server.py
3. **Consistency** - All tools use same http_client and rate_limiter
4. **Testability** - Can mock dependencies easily by passing test versions to register_tools()
5. **Maintainability** - Change a dependency once in server.py affects all tools

**Alternative (NOT Used Here):**
```python
# This would be messier:
@app.tool(name="search_federal_awards")
async def search_federal_awards(
    query: str,
    max_results: int = 10,
    http_client=None,      # ← Ugly!
    rate_limiter=None,     # ← Ugly!
    logger=None            # ← Ugly!
):
    # Tool signature is cluttered
```

### Rate Limiting Deep Dive

**Token Bucket Algorithm:**
```
Think of a bucket with holes in it.

┌─────────────────┐
│  60 tokens      │  ← Maximum capacity
│                 │
│  LEAK: 1 token  │  ← Every 1 second, a token "leaks out"
└─────────────────┘

When you make a request:
  - Need 1 token? Consume it and proceed
  - No tokens? Wait for one to leak out
  - Want to make 10 requests? Wait 10 seconds

Advantage: Smooths out traffic spikes
```

**Code example:**
```python
rate_limiter = RateLimiter(capacity=60, refill_rate=60)
# capacity=60: Max 60 tokens
# refill_rate=60: Add 60 tokens per 60 seconds (1 per second)

await rate_limiter.wait_if_needed("user_123")
# Will wait until a token is available
```

### Retry Logic with Exponential Backoff

**Problem:** API is sometimes busy or network is unstable

**Solution:** Try again, waiting longer each time

```
Request 1: GET /awards/search → TIMEOUT ✗
           Wait 1 second

Request 2: GET /awards/search → SERVER ERROR 500 ✗
           Wait 2 seconds

Request 3: GET /awards/search → SUCCESS! 200 ✓
           Return data
```

**Exponential backoff calculation:**
```
Wait time = base_delay * (multiplier ^ attempt_number)

Attempt 0: 1 second
Attempt 1: 2 seconds
Attempt 2: 4 seconds

Max wait: 10 seconds
```

**Why exponential backoff?**
- Don't hammer the server immediately
- Give server time to recover
- Reduces cascading failures

### Structured Logging for Analytics

**Problem:** Logs are just text, hard to analyze

**Solution:** Log as JSON (structured data)

```json
{
  "timestamp": "2024-11-13T14:32:16.234Z",
  "level": "INFO",
  "logger": "usaspending_mcp.server",
  "tool": "search_federal_awards",
  "query": "space",
  "results_count": 5,
  "execution_time_ms": 845,
  "status": "success"
}
```

**Why JSON?**
- Computers can parse it easily
- Tools can aggregate and analyze logs
- Can answer questions like:
  - "What are the most popular searches?"
  - "Which tools are slowest?"
  - "How many errors happened today?"

### Dual Transport Modes

**HTTP Mode:** For production
```
Claude Desktop
    ↓ (HTTP request)
Port 3002
    ↓
FastMCP
    ↓
Tool execution
```

**Stdio Mode:** For development/testing
```
Test Client
    ↓ (JSON-RPC over stdin/stdout)
FastMCP
    ↓
Tool execution
```

**Key difference in logging:**
- HTTP mode: Logs as JSON (for aggregation)
- Stdio mode: Logs as plain text (avoids breaking MCP protocol)

---

## The 27 Tools Explained (Organized by Module)

The refactored system organizes 27 tools across 6 focused modules. Each module file contains related tools that work together.

### Module 1: `tools/awards.py` (Award Discovery - 6 tools)

**Purpose:** Find and analyze federal award contracts, grants, loans, and insurance

1. **search_federal_awards** - Search by keyword, agency, recipient
2. **get_award_by_id** - Retrieve specific award details
3. **get_award_details** - Get comprehensive award information
4. **get_recipient_details** - Look up award history for a recipient
5. **get_vendor_by_uei** - Search vendors by Unique Entity ID
6. **get_subaward_data** - Get subaward and subcontract information

**Example Questions These Answer:**
- "Find all NASA contracts in Texas"
- "What contracts did Acme Corp receive?"
- "Get details on award #12345"

### Module 2: `tools/spending.py` (Spending Analysis - 8 tools)

**Purpose:** Analyze spending patterns, trends, and comparisons

1. **analyze_federal_spending** - Get spending overview by agency/type
2. **get_spending_trends** - See historical spending trends
3. **get_spending_by_state** - Break down spending geographically
4. **compare_states** - Compare spending metrics across states
5. **emergency_spending_tracker** - Track emergency and disaster funding
6. **spending_efficiency_metrics** - Calculate efficiency ratios
7. **get_disaster_funding** - Get disaster relief funding data
8. **get_budget_functions** - Get spending by budget function codes

**Example Questions These Answer:**
- "How much did the government spend on space in 2023?"
- "Which states got the most defense spending?"
- "Show me emergency spending trends"

### Module 3: `tools/classifications.py` (Classification Analysis - 5 tools)

**Purpose:** Analyze spending by industry, product type, and budget category

1. **get_top_naics_breakdown** - Top NAICS (industry) classifications by spending
2. **get_naics_psc_info** - Information about NAICS and PSC codes
3. **get_naics_trends** - Industry trends and year-over-year growth
4. **get_object_class_analysis** - Spending by budget categories
5. **get_field_documentation** - Documentation for USASpending API fields

**Example Questions These Answer:**
- "What industries got the most federal contracts?"
- "Show IT services spending trends"
- "Which object classes had the biggest budget?"

### Module 4: `tools/profiles.py` (Profile Tools - 4 tools)

**Purpose:** Get detailed profiles of agencies and vendors

1. **get_agency_profile** - Comprehensive profile for a federal agency
2. **get_vendor_profile** - Detailed profile for a vendor/contractor
3. **get_top_vendors_by_contract_count** - Top vendors by number of contracts (not dollars)
4. **analyze_small_business** - Small business set-asides and spending

**Example Questions These Answer:**
- "Show me DoD's spending profile"
- "What's the profile for Lockheed Martin?"
- "Which small businesses got the most contracts?"

### Module 5: `tools/conversations.py` (Conversation Management - 4 tools)

**Purpose:** Track and analyze conversation history and user behavior

1. **get_conversation** - Retrieve complete conversation history by ID
2. **list_conversations** - List all conversations for a user with pagination
3. **get_conversation_summary** - Get statistics and summary for a conversation
4. **get_tool_usage_stats** - Get tool usage patterns and statistics

**Example Questions These Answer:**
- "Show me all tools I've used today"
- "Which tools are most popular?"
- "Show statistics for conversation #123"

**Why Conversation Tools Matter:**
- Understand how users interact with the system
- Track which tools are most valuable
- Analyze conversation patterns and trends
- Support user analytics and system improvement

### Module 6: `tools/far.py` (FAR Regulations - 5 tools)

**Purpose:** Search and analyze Federal Acquisition Regulation requirements

1. **search_far_regulations** - Keyword search across FAR Parts 14, 15, 16, 19
2. **get_far_section** - Direct lookup by section number
3. **get_far_topic_sections** - Find sections by topic
4. **get_far_analytics_report** - Generate analytics on FAR section usage
5. **check_far_compliance** - Check FAR compliance requirements

**Example Questions These Answer:**
- "What's FAR 15.403-1?"
- "Show me rules about small business set-asides"
- "Is this acquisition compliant with FAR?"

### Summary: 27 Tools Across 6 Modules

```
tools/awards.py           → 6 tools  → 1,296 lines
tools/spending.py         → 8 tools  → 1,165 lines
tools/classifications.py  → 5 tools  → 1,385 lines
tools/profiles.py         → 4 tools  →   673 lines
tools/conversations.py    → 4 tools  →   337 lines
tools/far.py              → 5 tools  → (in main server)
                          ──────────
Total                     27 tools
```

---

## Common Development Tasks

### Task 1: Adding a New Tool (Modular Approach)

**Step 1: Decide which module the tool belongs to**

- Award-related? → Add to `tools/awards.py`
- Spending analysis? → Add to `tools/spending.py`
- Classification/NAICS/PSC? → Add to `tools/classifications.py`
- Vendor/agency profile? → Add to `tools/profiles.py`
- FAR regulation? → Add to `tools/far.py`
- New category? → Create `tools/new_category.py`

**Step 2: Add the tool inside the register_tools() function**

Example: Adding a new spending tool to `tools/spending.py`

```python
def register_tools(
    app, http_client, rate_limiter, base_url, logger_instance,
    award_type_map, toptier_agency_map, subtier_agency_map
) -> None:
    """Register all spending analysis tools"""

    # Existing tools here...

    # NEW TOOL: Add your new tool here
    @app.tool(
        name="analyze_inflation_adjusted_spending",
        description="Analyze federal spending adjusted for inflation"
    )
    async def analyze_inflation_adjusted_spending(
        agency_name: str,
        start_year: int = 2000,
        end_year: int = 2024
    ) -> TextContent:
        """
        Analyze spending trends adjusted for inflation.

        The rate_limiter, http_client, and logger_instance parameters
        are available via closure from the outer register_tools() scope.
        """

        # Step 1: Rate limit
        await rate_limiter.wait_if_needed("default")

        # Step 2: Validate inputs
        if not agency_name or not agency_name.strip():
            return [TextContent(type="text", text="Error: agency_name required")]

        # Step 3: Build API request
        params = {
            "filters": {"agency_name": agency_name},
            "group_by": "fiscal_year"
        }

        # Step 4: Make API call
        try:
            response = await http_client.get(
                f"{base_url}/spending/spending_over_time/",
                params=params
            )
            response.raise_for_status()
        except Exception as e:
            logger_instance.error(f"API error: {e}")
            return [TextContent(type="text", text=f"Error: {str(e)}")]

        # Step 5: Parse response
        data = response.json()
        results = data.get("results", [])

        # Step 6: Format output
        output = f"# Inflation-Adjusted Spending: {agency_name}\n\n"
        for item in results:
            output += f"**{item['fiscal_year']}**: ${item['amount']:,.0f}\n"

        # Step 7: Log the tool execution
        logger_instance.info(
            f"Tool: analyze_inflation_adjusted_spending | "
            f"Agency: {agency_name} | Years: {start_year}-{end_year}"
        )

        # Step 8: Return response
        return [TextContent(type="text", text=output)]
```

**Step 3: No changes needed to server.py!**

The `register_all_tools()` function in `tools/__init__.py` already calls `spending.register_tools()`, so your new tool is automatically registered.

**Step 4: Test the tool**

```bash
# Restart the server
./start_mcp_server.sh

# Or use the test client
PYTHONPATH=src ./.venv/bin/python -m usaspending_mcp.client
# Your new tool should appear in the menu!
```

**Key Points About Modular Tool Addition:**
- No need to touch `server.py` - it stays clean!
- Tool is automatically available once defined in register_tools()
- Can use http_client, rate_limiter, logger via closure
- All tools in the same module can share helper functions defined above them

### Task 2: Running Tests

```bash
# All tests
pytest

# Specific test file
pytest tests/unit/test_tools.py

# Single test
pytest tests/unit/test_tools.py::test_search_federal_awards -v

# With coverage
pytest --cov=src/usaspending_mcp --cov-report=html
```

### Task 3: Code Quality

```bash
# Format code (black)
black src/ tests/

# Sort imports (isort)
isort src/ tests/

# Check for problems (flake8)
flake8 src/ tests/

# Type checking (mypy)
mypy src/
```

---

## Troubleshooting

### "ModuleNotFoundError: No module named 'usaspending_mcp'"

**Solution:**
```bash
# Make sure you're in the project directory
cd usaspending-mcp

# Activate virtual environment
source .venv/bin/activate

# Install the package in development mode
pip install -e ".[dev]"
```

### "Port 3002 is already in use"

**Solution:**
```bash
# Kill the process using that port
lsof -i :3002  # Shows what's using port 3002
kill -9 <PID>  # Kill that process

# Or use a different port
python server_manager.py stop
```

### "API requests are failing"

**Check:**
1. Internet connection working?
2. Is api.usaspending.gov online? (Test in browser)
3. Are you being rate limited? (Check logs)
4. Is the timeout too short? (Currently 30 seconds)

### "JSON logging isn't working in stdio mode"

**This is intentional!** The system automatically disables JSON logging in stdio mode because JSON mixes with the MCP protocol.

---

## Key Takeaways for Students

1. **APIs are everywhere** - This project talks to another API (USASpending.gov) to get data

2. **Resilience matters** - The system retries failed requests and rate limits to be a good citizen

3. **Logging is essential** - Understanding what your code is doing is critical in production

4. **Abstraction layers help** - FastMCP hides the complexity of the MCP protocol

5. **Asynchronous code is powerful** - The system handles many requests concurrently

6. **Data formatting matters** - The same data can be presented in different ways

7. **Testing is necessary** - The project has unit tests to catch bugs early

8. **Performance monitoring** - The system tracks metrics to find bottlenecks

---

## Next Steps for Learning

### Beginner Level
1. Run the server and play with a few tools
2. Read the log files to understand what's happening
3. Try adding print statements to a tool to trace execution
4. Modify a tool's description

### Intermediate Level
1. Add a new tool to analyze spending data differently
2. Write unit tests for a tool
3. Add better error handling to a tool
4. Modify the rate limiter settings
5. Explore how conversation management tools track user behavior
6. Analyze tool usage patterns from conversation logs

### Advanced Level
1. Add a new transport mode (besides HTTP and stdio)
2. Implement caching for frequently-called tools
3. Add performance monitoring
4. Integrate a new data source (not just USASpending)

---

## Resources

**In the repository:**
- `docs/guides/QUICKSTART.md` - Get started quickly
- `docs/dev/ARCHITECTURE_GUIDE.md` - Deep architecture dive
- `docs/dev/TESTING_GUIDE.md` - How testing works
- `docs/guides/CONVERSATION_LOGGING_GUIDE.md` - Understanding conversation tracking and analytics
- `docs/API_RESOURCES.md` - USASpending API reference

**External Resources:**
- [FastMCP Documentation](https://github.com/jlouis/fastmcp)
- [MCP Protocol Spec](https://spec.modelcontextprotocol.io)
- [USASpending.gov API Docs](https://api.usaspending.gov/)
- [Python async/await Guide](https://docs.python.org/3/library/asyncio.html)
- [FastMCP Examples](https://github.com/anthropics/mcp-server-fastmcp)

---

## Conclusion

The USASpending MCP Server is a great example of a **production-ready system** that:
- Handles real-world challenges (failures, slow networks)
- Is observable (logging, analytics)
- Is well-organized (modular components)
- Has clear responsibilities (separation of concerns)
- Is testable (unit tests)

Use this guide to explore the codebase, ask questions, and start contributing! Happy coding!
