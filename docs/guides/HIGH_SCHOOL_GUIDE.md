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
- Can handle **32 different tools** to analyze federal spending

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

### Component 1: `server.py` (The Headquarters)

This is the **main file** where everything happens.

**What it does:**
- Defines 27 different tools for analyzing federal spending
- Sets up the FastMCP app
- Initializes the rate limiter
- Creates the HTTP client
- Handles all tool definitions

**Analogy:** This is like the CEO's office - it makes all the big decisions and coordinates the whole company.

**Some tools it provides:**
```python
@app.tool(name="search_federal_awards")
async def search_federal_awards(query: str, max_results: int = 10) -> TextContent:
    """Search for federal awards"""
    # Make API call
    # Format results
    # Return to user
```

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

### File Structure

```
usaspending-mcp/
├── src/usaspending_mcp/
│   ├── server.py           ← Main file (32 tools)
│   ├── client.py           ← Test client
│   ├── tools/
│   │   └── far.py          ← FAR regulation tools
│   ├── loaders/
│   │   └── far.py          ← Load FAR data
│   └── utils/
│       ├── rate_limit.py   ← Token bucket
│       ├── retry.py        ← Retry logic
│       ├── logging.py      ← Structured logging
│       ├── search_analytics.py  ← Track searches
│       └── far.py          ← FAR database
│
├── docs/
│   ├── data/far/           ← FAR regulation JSON files
│   └── guides/             ← Documentation
│
├── tests/                  ← Unit tests
├── requirements.txt        ← Dependencies
└── pyproject.toml          ← Project config
```

### Reading the Main File: `server.py`

The main file is organized like this:

```python
# ═══════════════════════════════════════════
# SECTION 1: IMPORTS
# ═══════════════════════════════════════════
import asyncio
from fastmcp import FastMCP
from utils.rate_limit import initialize_rate_limiter
# ... more imports

# ═══════════════════════════════════════════
# SECTION 2: INITIALIZATION
# ═══════════════════════════════════════════
app = FastMCP(name="usaspending-server")
rate_limiter = initialize_rate_limiter(60)  # 60 req/min
http_client = httpx.AsyncClient(timeout=30.0)

# ═══════════════════════════════════════════
# SECTION 3: HELPER FUNCTIONS
# ═══════════════════════════════════════════
def format_currency(value):
    """Convert 500000000 to $500M"""
    # ... code

# ═══════════════════════════════════════════
# SECTION 4: TOOL DEFINITIONS (27 tools)
# ═══════════════════════════════════════════
@app.tool(name="search_federal_awards")
async def search_federal_awards(query: str, max_results: int = 10):
    # ... tool code

# ═══════════════════════════════════════════
# SECTION 5: STARTUP & SHUTDOWN
# ═══════════════════════════════════════════
async def startup():
    # ... setup code

def run_server():
    # ... start HTTP server
```

### Anatomy of a Tool

Here's what a tool looks like:

```python
@app.tool(
    name="search_federal_awards",
    description="Search for federal awards by keyword, agency, recipient, etc."
)
async def search_federal_awards(
    query: str,                    # What to search for
    max_results: int = 10,         # How many results to return
    agency_name: str = None,       # Optional: filter by agency
) -> TextContent:
    """
    This is the function that runs when someone calls this tool.

    Args:
        query: The search term (e.g., "space contracts")
        max_results: Number of results (default 10)
        agency_name: Filter by specific agency (optional)

    Returns:
        TextContent: Formatted text response for the user
    """

    # Step 1: Check rate limit
    await rate_limiter.wait_if_needed("default")

    # Step 2: Validate inputs
    if not query or len(query.strip()) == 0:
        return TextContent(type="text", text="Error: Query cannot be empty")

    # Step 3: Build API request
    params = {
        "filters": {"keywords": [query]},
        "limit": min(max_results, 100)  # Cap at 100
    }

    # Step 4: Make API call with retry
    try:
        response = await make_api_request(
            "awards/search/",
            params
        )
    except Exception as e:
        return TextContent(type="text", text=f"Error: {str(e)}")

    # Step 5: Format results
    output = f"# Federal Awards - {query}\n\n"

    results = response.json().get("results", [])
    for award in results[:max_results]:
        output += f"**{award['recipient']['name']}**\n"
        output += f"- Award ID: {award['id']}\n"
        output += f"- Amount: {format_currency(award['amount'])}\n"
        output += f"- Link: {generate_award_url(award['id'])}\n\n"

    # Step 6: Log the search
    logger.info(f"Tool: search_federal_awards | Query: {query} | Results: {len(results)}")

    # Step 7: Return response
    return [TextContent(type="text", text=output)]
```

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

---

## Advanced Concepts

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

## The 32 Tools Explained

### Federal Spending Tools (27 tools)

These are grouped by what they help you analyze:

#### Award Discovery (5 tools)
- Find specific awards
- Look up recipients
- Get details about contracts

#### Spending Analysis (7 tools)
- Understand spending patterns
- See trends over time
- Compare different areas

#### Classification Analysis (4 tools)
- Analyze by industry type (NAICS)
- Analyze by product/service type (PSC)
- Analyze by budget category (Object Class)
- Analyze by function (Budget Functions)

#### Specialized Tools (4 tools)
- Small business analysis
- Subaward/subcontract tracking
- Disaster funding tracking
- Data export

#### Information Tools (2 tools)
- Get agency profiles
- Get vendor profiles
- Get field documentation

### FAR Regulation Tools (5 tools)

These search federal acquisition rules:

1. **search_far_regulations** - Search across all 4 parts
2. **get_far_section** - Look up specific section
3. **get_far_topic_sections** - Find by topic
4. **get_far_analytics_report** - See usage patterns
5. **check_far_compliance** - Check if something follows rules

---

## Common Development Tasks

### Task 1: Adding a New Tool

To add a new tool, you add it to `server.py`:

```python
@app.tool(
    name="my_new_tool",
    description="What this tool does"
)
async def my_new_tool(param1: str) -> TextContent:
    # Step 1: Rate limit
    await rate_limiter.wait_if_needed("default")

    # Step 2: Call API
    response = await make_api_request("endpoint/", params)

    # Step 3: Format results
    output = "Formatted response"

    # Step 4: Log
    logger.info(f"my_new_tool called with {param1}")

    # Step 5: Return
    return [TextContent(type="text", text=output)]
```

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
