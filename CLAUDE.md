# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**USASpending MCP Server**: A FastMCP server that provides access to USASpending.gov federal spending data and FAR (Federal Acquisition Regulation) lookup tools through the Model Context Protocol (MCP).

- **Type**: MCP Server
- **Language**: Python 3.10+
- **Transport Modes**: stdio (testing) and HTTP (Claude Desktop)
- **Key Framework**: FastMCP
- **Primary API**: USASpending.gov API v2

## Common Development Commands

### Setup & Installation
```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install with dev dependencies
pip install -e ".[dev]"
```

### Running the Server
```bash
# HTTP mode (Claude Desktop)
./start_mcp_server.sh
# Starts on http://127.0.0.1:3002/mcp

# Stdio mode (testing/debugging)
PYTHONPATH=src ./.venv/bin/python -m usaspending_mcp.server --stdio
```

### Testing
```bash
# Run all tests
pytest

# Run specific test file
pytest tests/unit/test_tools.py

# Run single test
pytest tests/unit/test_tools.py::TestTools::test_search_federal_awards

# Run with coverage
pytest --cov=src/usaspending_mcp --cov-report=html

# Run integration tests (require network)
pytest -m integration

# Run without slow tests
pytest -m "not slow"
```

### Testing the Server
```bash
# Use the test client script
./tests/scripts/test_mcp_client.sh

# Or run directly
PYTHONPATH=src ./.venv/bin/python -m usaspending_mcp.client

# View interactive test menu
./tests/scripts/run_tests.sh
```

### Code Quality
```bash
# Format with black
black src/ tests/

# Sort imports with isort
isort src/ tests/

# Lint with flake8
flake8 src/ tests/

# Type checking with mypy
mypy src/
```

### Manage Server (HTTP mode)
```bash
# Start server (uses server_manager.py)
./start_mcp_server.sh

# Stop specific server
./.venv/bin/python server_manager.py stop <port>

# Stop all servers on default port
./.venv/bin/python server_manager.py stop
```

### Docker Deployment
```bash
# Build Docker image
docker build -t usaspending-mcp .

# Run with Docker Compose
docker-compose up

# Run standalone container
docker run -p 3002:3002 usaspending-mcp
```

For detailed Docker deployment instructions, see `DOCKER_GUIDE.md`

## Architecture Overview

### Core Components

**1. Server (`src/usaspending_mcp/server.py`)** - REFACTORED 2024!
- FastMCP application initialization (now only 199 lines, was 4,515!)
- Imports tool modules and coordinates registration
- USASpending.gov API integration
- Dual transport support (stdio/HTTP with uvicorn)
- Rate limiting and retry logic applied globally
- Award type and agency mappings

**2. Tools Module (`src/usaspending_mcp/tools/`)** - MODULAR ARCHITECTURE
- **__init__.py**: Coordinates registration of all tool modules via `register_all_tools()`
- **helpers.py**: Shared utilities (QueryParser, formatters, URL generators)
- **awards.py**: Award discovery tools (6 tools)
  - `search_federal_awards` - Search by keyword, agency, recipient
  - `get_award_by_id` - Retrieve specific award
  - `get_award_details` - Comprehensive award information
  - `get_recipient_details` - Award history for recipient
  - `get_vendor_by_uei` - Search vendors by UEI
  - `get_subaward_data` - Subaward and subcontract information
- **spending.py**: Spending analysis tools (8 tools)
  - `analyze_federal_spending` - Spending overview by agency/type
  - `get_spending_trends` - Historical spending trends
  - `get_spending_by_state` - Geographic spending breakdown
  - `compare_states` - Compare spending metrics
  - `emergency_spending_tracker` - Emergency/disaster funding
  - `spending_efficiency_metrics` - Efficiency calculations
  - `get_disaster_funding` - Disaster relief funding data
  - `get_budget_functions` - Spending by budget function
- **classifications.py**: Classification analysis tools (5 tools)
  - `get_top_naics_breakdown` - Top NAICS classifications
  - `get_naics_psc_info` - NAICS/PSC code information
  - `get_naics_trends` - Industry trends and growth
  - `get_object_class_analysis` - Budget category analysis
  - `get_field_documentation` - USASpending.gov field documentation
- **profiles.py**: Vendor and agency profile tools (4 tools)
  - `get_agency_profile` - Federal agency profile
  - `get_vendor_profile` - Vendor/contractor profile
  - `get_top_vendors_by_contract_count` - Top vendors by contract count
  - `analyze_small_business` - Small business set-asides analysis
- **conversations.py**: Conversation management tools (4 tools)
  - `get_conversation` - Retrieve conversation history
  - `list_conversations` - List user conversations with pagination
  - `get_conversation_summary` - Conversation statistics and summary
  - `get_tool_usage_stats` - Tool usage patterns and statistics
- **far.py**: FAR (Federal Acquisition Regulation) tools (5 tools)
  - `search_far_regulations` - Keyword search across FAR Parts 14, 15, 16, 19
  - `get_far_section` - Direct lookup by section number
  - `get_far_topic_sections` - Find sections by topic
  - `get_far_analytics_report` - Generate analytics on FAR section usage
  - `check_far_compliance` - Check compliance requirements for acquisitions

**3. Loaders (`src/usaspending_mcp/loaders/`)**
- **far.py**: Loads FAR JSON data from `docs/data/far/` into memory during initialization

**4. Utilities (`src/usaspending_mcp/utils/`)**
- **retry.py**: Exponential backoff retry logic using tenacity library
  - Retries on transient failures (TimeoutException, ConnectError, ReadError)
  - Retries on 408, 429, 500, 502, 503, 504 status codes
- **rate_limit.py**: Token bucket rate limiter
  - Default: 60 requests/minute
  - Async-safe, shared across stdio/HTTP transports
- **logging.py**: Structured JSON logging utilities
  - JSON output for HTTP mode only (disabled in stdio mode to avoid MCP protocol conflicts)
  - Includes search analytics and tool execution logging
- **conversation_logging.py**: Conversation management and analytics
  - Tracks conversation history and metadata
  - Provides statistics and tool usage analytics
  - Enables conversation retrieval and analysis
- **search_analytics.py**: Tracks and analyzes search patterns
- **far.py**: FAR database utilities
  - Loads FAR data from JSON files
  - Provides search and lookup operations with caching
- **query_context.py**: Query refinement and conversation-aware filtering
  - Extracts filter patterns from conversation history
  - Suggests progressive refinements for large result sets (>50 results)
  - Tracks user preferences and query patterns
- **result_aggregation.py**: Result summarization and explanation
  - Aggregates similar awards by recipient or industry classification (NAICS)
  - Generates match explanations showing why results matched the query
  - Provides recipient-based and industry-based summaries
- **relevance_scoring.py**: Intelligent result ranking
  - Scores awards based on keyword match quality and field placement
  - Weights recipient matches higher than partial matches
  - Integrates conversation context for relevance boosting
  - Provides confidence scores (0-100) for each result
- **constants.py**: Centralized constants for the application
  - Award type mappings (contracts, grants, loans, insurance)
  - Top-tier agency mappings for normalization

**5. Configuration (`src/usaspending_mcp/config.py`)**
- **ServerConfig**: Centralized configuration management
  - Server settings: port, host, log level
  - API settings: timeout, base URL
  - Rate limiting: requests per minute
  - FAR settings: data path
  - Environment variable support with validation

**6. Client (`src/usaspending_mcp/client.py`)**
- MCP protocol client for testing/debugging
- stdio transport implementation
- Interactive query interface

### Data Flow

1. **MCP Tool Call** → Server receives request via stdio or HTTP
2. **Rate Limiting Check** → Global rate limiter validates request
3. **Retry Loop** → Decorated API call with exponential backoff
4. **USASpending API** → Fetch federal spending data
5. **Query Refinement** (optional) → Apply intelligence to results:
   - **Relevance Scoring**: Score awards by keyword match quality
   - **Result Aggregation**: Group similar awards by recipient/industry
   - **Explanations**: Show why each result matched the query
   - **Progressive Filtering**: Suggest refinements for large result sets (>50 results)
6. **Response Formatting** → Format results with currency notation and descriptions
7. **Logging** → Structured logging of tool execution and searches
8. **Return to Client** → TextContent response via MCP protocol

### Key Architectural Decisions

- **FastMCP over manual MCP**: Simplifies tool registration and protocol handling
- **Global Rate Limiter**: Shared across all tools to prevent API overload
- **Conditional JSON Logging**: Disabled in stdio mode to avoid protocol interference
- **FAR Data as JSON Files**: Enables offline regulation lookup without API calls
- **Modular Tool Registration**: FAR tools registered separately via `register_far_tools()`
- **Agency/Award Type Mappings**: Comprehensive normalization for API filtering
- **Query Refinement as Optional Features**: `aggregate_results`, `sort_by_relevance`, `include_explanations` parameters on `search_federal_awards` are all opt-in for backwards compatibility
- **Conversation-Aware Filtering**: Leverages existing ConversationLogger to extract context without requiring new data storage
- **Progressive Enhancement**: Query refinement features degrade gracefully; if analysis fails, standard results are returned

## Project Structure (After 2024 Refactoring)

```
src/usaspending_mcp/
├── server.py              # FastMCP app initialization (199 lines, was 4,515!)
├── client.py              # MCP client for testing
├── config.py              # Server configuration management
├── __init__.py            # Package exports
├── __main__.py            # Entry point
├── tools/                 # MODULAR TOOL ARCHITECTURE
│   ├── __init__.py        # register_all_tools() coordinator
│   ├── helpers.py         # Shared utilities (QueryParser, formatters)
│   ├── awards.py          # Award discovery tools (6 tools)
│   ├── spending.py        # Spending analysis tools (8 tools)
│   ├── classifications.py # NAICS/PSC analysis tools (5 tools)
│   ├── profiles.py        # Vendor/agency profile tools (4 tools)
│   ├── conversations.py   # Conversation management tools (4 tools)
│   └── far.py             # FAR regulation tools (5 tools)
├── loaders/
│   ├── __init__.py
│   └── far.py             # FAR data loading
└── utils/
    ├── __init__.py
    ├── constants.py       # Centralized constants and mappings
    ├── retry.py           # Retry logic with exponential backoff
    ├── rate_limit.py      # Token bucket rate limiter
    ├── logging.py         # Structured logging
    ├── conversation_logging.py # Conversation tracking and analytics
    ├── search_analytics.py # Search pattern tracking
    ├── far.py             # FAR database utilities
    ├── query_context.py   # Query refinement and progressive filtering
    ├── result_aggregation.py # Result grouping and explanations
    └── relevance_scoring.py # Intelligent result ranking and scoring

docs/
├── DOCUMENTATION_ROADMAP.md          # Learning paths by role
├── API_RESOURCES.md                  # API reference data
├── IMPLEMENTATION_SUMMARY.md         # Recent implementations and features
├── guides/
│   ├── QUICKSTART.md
│   ├── STRUCTURED_LOGGING_GUIDE.md
│   ├── CONVERSATION_LOGGING_GUIDE.md # Conversation tracking and analytics
│   ├── RATE_LIMITING_AND_RETRY_GUIDE.md
│   ├── FAR_ANALYTICS_GUIDE.md
│   ├── MULTI_TOOL_ANALYTICS_ARCHITECTURE.md
│   ├── MCP_BEST_PRACTICES_REVIEW.md
│   └── FUTURE_RECOMMENDATIONS.md
├── dev/
│   ├── ARCHITECTURE_GUIDE.md
│   ├── TESTING_GUIDE.md
│   ├── SERVER_MANAGER_GUIDE.md
│   └── PRODUCTION_MONITORING_GUIDE.md
├── reference/              # API mappings, field dictionary, etc.
└── data/
    └── far/                # FAR JSON data files (Parts 14, 15, 16, 19)

tests/
├── conftest.py             # Pytest fixtures and config
├── unit/
│   ├── test_tools.py
│   ├── test_utils_retry.py
│   ├── test_utils_logging.py
│   ├── test_utils_rate_limit.py
│   ├── test_query_context.py # Tests for query context analysis
│   ├── test_aggregation.py # Tests for result aggregation
│   └── test_relevance_scoring.py # Tests for relevance scoring
└── integration/

Docker/
├── Dockerfile              # Production-ready multi-stage build
├── docker-compose.yml      # Container orchestration
├── docker-entrypoint.sh    # Entry point script
└── .dockerignore            # Build optimization

pyproject.toml                 # Modern Python project config (build, dependencies, tools)
pytest.ini                     # Pytest configuration
requirements.txt               # Direct dependencies
IMPLEMENTATION_SUMMARY.md      # Summary of recent implementations
DOCKER_GUIDE.md               # Docker deployment guide
CHANGELOG.md                  # Project changelog
start_mcp_server.sh            # Script to start MCP server in HTTP mode
server_manager.py              # Manage running server instances
```

## Available Tools - 27 Tools Organized by 6 Modules

### Module 1: Award Discovery Tools (6 tools - `tools/awards.py`)

- `search_federal_awards` - Search federal awards by agency, recipient, time period, and other filters
  - **Advanced Features**: `aggregate_results` (group by recipient), `sort_by_relevance` (intelligent ranking), `include_explanations` (show match reasons)
- `get_award_by_id` - Retrieve detailed information about a specific award
- `get_award_details` - Get comprehensive award details including modifications and attachments
- `get_recipient_details` - Look up award history for a specific recipient
- `get_vendor_by_uei` - Search vendors by Unique Entity ID (UEI)
- `get_subaward_data` - Get subaward and subcontract information

### Module 2: Spending Analysis Tools (8 tools - `tools/spending.py`)

- `analyze_federal_spending` - Analyze spending patterns and trends
- `get_spending_trends` - Get historical spending trends by agency or category
- `get_spending_by_state` - Break down federal spending by state
- `compare_states` - Compare spending metrics across multiple states
- `emergency_spending_tracker` - Track emergency and disaster funding
- `spending_efficiency_metrics` - Calculate spending efficiency metrics and ratios
- `get_disaster_funding` - Get disaster and emergency relief funding data
- `get_budget_functions` - Get spending breakdown by budget function codes

### Module 3: Classification & Breakdown Analysis (5 tools - `tools/classifications.py`)

- `get_top_naics_breakdown` - Get top NAICS (industry) classifications by spending
- `get_naics_psc_info` - Get information about NAICS and PSC codes
- `get_naics_trends` - Track NAICS industry trends and year-over-year growth by sector
- `get_object_class_analysis` - Analyze spending by object class (budget categories)
- `get_field_documentation` - Get documentation for USASpending.gov API fields

### Module 4: Vendor & Agency Profile Tools (4 tools - `tools/profiles.py`)

- `get_agency_profile` - Get comprehensive profile for a federal agency
- `get_vendor_profile` - Get detailed profile for a vendor or contractor
- `get_top_vendors_by_contract_count` - Get top vendors ranked by number of contracts awarded (not dollar value)
- `analyze_small_business` - Analyze small business set-asides and spending

### FAR (Federal Acquisition Regulation) Tools (5 tools)

The server provides tools for searching and analyzing federal acquisition regulations:

- `search_far_regulations` - Keyword search across FAR Parts 14, 15, 16, 19
- `get_far_section` - Direct lookup of FAR section by number
- `get_far_topic_sections` - Find FAR sections by topic
- `get_far_analytics_report` - Generate analytics on FAR section usage and patterns
- `check_far_compliance` - Check FAR compliance requirements for specific acquisition scenarios

### Conversation Management Tools (4 tools)

The server provides tools for tracking and analyzing conversation history:

- `get_conversation` - Retrieve complete conversation history by conversation ID
- `list_conversations` - List all conversations for a user with pagination support
- `get_conversation_summary` - Get statistics and summary information for a specific conversation
- `get_tool_usage_stats` - Get tool usage patterns and statistics for a user across all conversations

All tools return results via the MCP protocol with automatic rate limiting and retry logic applied. For detailed information about conversation tracking, see `docs/guides/CONVERSATION_LOGGING_GUIDE.md`

## Important Implementation Details

### Adding New Tools (Modular Approach)

In the refactored architecture, tools are defined inside a `register_tools()` function in the appropriate module file (e.g., `tools/spending.py`):

```python
def register_tools(
    app, http_client, rate_limiter, base_url, logger_instance,
    award_type_map, toptier_agency_map, subtier_agency_map
) -> None:
    """Register all spending analysis tools"""

    @app.tool(
        name="tool_name",
        description="Tool description with parameters and returns"
    )
    async def tool_function(param1: str, param2: int = 5) -> TextContent:
        # Can access http_client, rate_limiter, logger_instance via closure!
        await rate_limiter.wait_if_needed("default")
        response = await http_client.get(f"{base_url}/endpoint", params={})
        return TextContent(type="text", text=result)
```

**Key Points:**
- Tools are defined INSIDE `register_tools()` function
- Tool functions access shared dependencies (http_client, rate_limiter, logger) via closure
- No need to modify server.py or tools/__init__.py
- Tool is automatically registered by existing registration flow

Tools are automatically rate-limited and retry logic can be applied via `@make_api_call_with_retry` decorator.

### Rate Limiting

The global rate limiter is initialized on server startup:
```python
rate_limiter = initialize_rate_limiter(requests_per_minute=60)
```

To apply rate limiting to tool calls, wrap API calls with the rate limiter:
```python
await rate_limiter.acquire()
response = await http_client.get(url)
```

### API Integration

The server queries USASpending.gov API v2:
- **Base URL**: `https://api.usaspending.gov/api/v2`
- **No API key required**
- **Retry Policy**: 3 attempts with exponential backoff
- **Timeout**: 30 seconds per request

### FAR Data

FAR data is loaded once during initialization from JSON files in `docs/data/far/`:
- FAR Part 14 (Sealed Bidding)
- FAR Part 15 (Competitive Procedures)
- FAR Part 16 (Types of Contracts)
- FAR Part 19 (Small Business Programs)

Each part contains sections with regulatory text that can be searched or looked up directly.

### Logging

Structured logging is configured with:
- **JSON output** in HTTP mode (facilitates log aggregation)
- **Console output** in stdio mode (avoids MCP protocol conflicts)
- **Log level**: INFO by default, can be configured via environment

Search logs and tool execution logs are tracked separately and can feed analytics.

### Query Refinement Features

The `search_federal_awards` tool includes advanced result refinement capabilities:

**Progressive Filtering Suggestions**
- Automatically suggests refinement filters when result set exceeds 50 awards
- Suggests filtering by: set-aside type, award type, state, fiscal year, amount range
- Example: `search_federal_awards("IT contracts")` → Returns suggestions if >50 results found

**Result Aggregation**
- Groups similar awards by recipient or industry classification (NAICS)
- Shows aggregate summaries: "15 awards to Acme Corp ($50M total)"
- Use with `aggregate_results=True` parameter

**Match Explanations**
- Shows why each award matched the query
- Indicates which fields matched (recipient name, description, NAICS, PSC)
- Includes confidence scores (0-100) for each match
- Enabled by default with `include_explanations=True`

**Intelligent Ranking**
- Scores awards based on keyword match quality and field importance
- Exact keyword matches weighted higher than partial matches
- Recipient name matches weighted higher than description matches
- Use with `sort_by_relevance=True` parameter

**Conversation Context Awareness**
- Analyzes previous queries in the conversation
- Remembers user preferences and filter patterns
- Uses conversation history to boost relevance of contextually relevant results
- Automatic—leverages existing ConversationLogger

## Testing Strategy

### Test Organization
- **Unit tests** (`tests/unit/`): Test individual functions in isolation
- **Integration tests** (`tests/integration/`): Test against actual API
- **Test fixtures** in `conftest.py`: Shared test data and mocks

### Running Tests

```bash
# All tests
pytest

# By category
pytest -m unit
pytest -m integration
pytest -m critical

# With coverage report
pytest --cov=src/usaspending_mcp --cov-report=term-missing

# Single test
pytest tests/unit/test_tools.py::test_search_federal_awards -v
```

## Git Workflow

- **Main branch**: Production-ready code
- **Recent commits**: Performance improvements, bug fixes, documentation updates
- **Untracked files**: GEMINI.md (can be ignored)

## Common Pitfalls

1. **JSON logging in stdio mode**: Breaks MCP protocol. The server automatically disables JSON logging when `--stdio` is passed.
2. **Rate limiting**: Global limiter applies to all tools. High-concurrency scenarios may need adjustment.
3. **Virtual environment**: Always ensure `.venv` is activated when running commands.
4. **Port conflicts**: When running HTTP server, ensure port 3002 is available or use `server_manager.py` for automatic cleanup.
5. **Docker binding issues**: The `docker-entrypoint.sh` script handles 0.0.0.0 binding for Docker containers. See `DOCKER_GUIDE.md` for details.
6. **Untracked files**: `Dockerfile`, `docker-compose.yml`, `DOCKER_GUIDE.md`, and `CONVERSATION_LOGGING_GUIDE.md` are part of the project but untracked in git.
7. **Query Refinement graceful degradation**: If conversation context extraction fails, standard results are returned. Query refinement features are wrapped in try/except and don't break the search tool.

## Documentation Resources

For deep dives, refer to:

**Getting Started**
- **Learning Paths**: `docs/DOCUMENTATION_ROADMAP.md`
- **Quick Start**: `docs/guides/QUICKSTART.md`
- **API Reference**: `docs/API_RESOURCES.md`

**Development Guides**
- **Architecture**: `docs/dev/ARCHITECTURE_GUIDE.md`
- **Testing**: `docs/dev/TESTING_GUIDE.md`
- **Server Management**: `docs/dev/SERVER_MANAGER_GUIDE.md`
- **Production Monitoring**: `docs/dev/PRODUCTION_MONITORING_GUIDE.md`

**Implementation Guides**
- **Logging**: `docs/guides/STRUCTURED_LOGGING_GUIDE.md`
- **Conversation Tracking**: `docs/guides/CONVERSATION_LOGGING_GUIDE.md`
- **Rate Limiting**: `docs/guides/RATE_LIMITING_AND_RETRY_GUIDE.md`
- **FAR Analytics**: `docs/guides/FAR_ANALYTICS_GUIDE.md`
- **Multi-Tool Analytics**: `docs/guides/MULTI_TOOL_ANALYTICS_ARCHITECTURE.md`
- **MCP Best Practices**: `docs/guides/MCP_BEST_PRACTICES_REVIEW.md`

**Deployment & Operations**
- **Docker Deployment**: `DOCKER_GUIDE.md` - Complete Docker setup and deployment instructions
- **Changelog**: `CHANGELOG.md` - Project version history and recent improvements

**Project Overview**
- **Implementation Summary**: `IMPLEMENTATION_SUMMARY.md` - Set-aside filtering and recent feature implementations
