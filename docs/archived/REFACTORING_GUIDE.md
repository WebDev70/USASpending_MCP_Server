# Server.py Refactoring Guide

## The Problem

**server.py** is currently **4,515 lines** of code with **28 MCP tools** all crammed into one file.

### Why This Is a Problem:
- ❌ Hard to find specific tools
- ❌ Hard to modify without breaking others
- ❌ Hard to test individual tools
- ❌ Hard to understand the structure
- ❌ Hard for multiple developers to work simultaneously
- ❌ Goes against professional best practices

### Industry Standards:
- **Ideal**: 200-400 lines per file
- **Acceptable**: Up to 500 lines
- **Too Long**: 1000+ lines (our current state: 4,515!)

---

## The Solution: Modular Tool Architecture

### New Structure

```
src/usaspending_mcp/
├── server.py                    # CLEANED UP: 100-150 lines (just app init)
│
├── tools/
│   ├── __init__.py              # Registers all tool modules
│   ├── helpers.py              # ✅ DONE - QueryParser, URL generators, etc.
│   ├── awards.py               # TEMPLATE PROVIDED - Award search/details
│   ├── spending.py             # TEMPLATE PROVIDED - Spending analysis
│   ├── classifications.py      # TEMPLATE PROVIDED - NAICS, PSC, object class
│   ├── profiles.py             # TEMPLATE PROVIDED - Vendor/agency profiles
│   └── conversations.py        # TEMPLATE PROVIDED - Conversation management
│
└── Far tools remain in:
    ├── tools/far.py            # Already separate ✓
    └── loaders/far.py          # Already separate ✓
```

### New server.py (Clean!)

```python
"""USASpending MCP Server - Minimal initialization only."""

import sys
from fastmcp import FastMCP
from usaspending_mcp.tools import register_all_tools

# Detect stdio mode
is_stdio_mode = len(sys.argv) > 1 and sys.argv[1] == "--stdio"

# Setup logging
from usaspending_mcp.utils.logging import setup_structured_logging, get_logger
setup_structured_logging(log_level="INFO", json_output=not is_stdio_mode)
logger = get_logger("server")

# Create app
app = FastMCP(name="usaspending-server")

# Register all tool modules
register_all_tools(app)

# Run server (existing code)
if is_stdio_mode:
    # stdio mode for testing
    ...
else:
    # HTTP mode for Claude Desktop
    ...
```

---

## Refactoring Pattern

### Step 1: Create a Tool Module File

Create `tools/awards.py`:

```python
"""
Award search and details tools.

This module contains tools for finding and retrieving federal awards.

TOOLS IN THIS FILE:
- get_award_by_id: Look up specific award by Award ID
- search_federal_awards: Advanced search with filters
- get_award_details: Get complete award information
- get_subaward_data: Get subaward/subcontract data
- get_recipient_details: Get vendor/recipient information
- get_vendor_by_uei: Search vendors by ID
"""

import logging
import httpx
from fastmcp import FastMCP
from mcp.types import TextContent
from usaspending_mcp.utils.logging import log_tool_execution
from usaspending_mcp.tools.helpers import (
    QueryParser,
    format_currency,
    generate_award_url,
    generate_recipient_url,
    generate_agency_url,
)

logger = logging.getLogger(__name__)


def register_tools(
    app: FastMCP,
    http_client: httpx.AsyncClient,
    rate_limiter,
    base_url: str,
    logger_instance,
    award_type_map: dict,
    toptier_agency_map: dict,
    subtier_agency_map: dict,
):
    """
    Register all award tools with the FastMCP app.

    This pattern allows tools to be registered from separate modules
    while still having access to shared dependencies like http_client.

    Args:
        app: FastMCP application instance
        http_client: Shared HTTP client
        rate_limiter: Shared rate limiter
        base_url: USASpending API base URL
        logger_instance: Logger instance
        award_type_map: Award type mappings
        toptier_agency_map: Agency name mappings
        subtier_agency_map: Sub-agency mappings
    """

    @app.tool(
        name="get_award_by_id",
        description="Get a specific federal award by its exact Award ID."
    )
    @log_tool_execution
    async def get_award_by_id(award_id: str) -> list[TextContent]:
        """
        Get a specific award by Award ID.

        This function is now moved to awards.py and receives
        dependencies (http_client, etc.) as captured variables
        from the register_tools() function.
        """
        # Implementation here (moved from server.py)
        ...

    @app.tool(
        name="search_federal_awards",
        description="Search federal spending data from USASpending.gov..."
    )
    @log_tool_execution
    async def search_federal_awards(...) -> list[TextContent]:
        """Implementation here"""
        ...
```

### Step 2: Create tools/__init__.py

```python
"""
Tool registration module.

This file coordinates registration of all tool modules with the main app.
It's the "switchboard" that tells the FastMCP app which tools are available.
"""

from fastmcp import FastMCP
import httpx


def register_all_tools(
    app: FastMCP,
    http_client: httpx.AsyncClient,
    rate_limiter,
    base_url: str,
    logger_instance,
    award_type_map: dict,
    toptier_agency_map: dict,
    subtier_agency_map: dict,
):
    """
    Register all tool modules.

    This is called once during app initialization to register
    every tool available in the system.
    """
    from usaspending_mcp.tools import awards, spending, classifications, profiles, conversations
    from usaspending_mcp.tools import far

    # Register each tool module
    awards.register_tools(app, http_client, rate_limiter, base_url, logger_instance, ...)
    spending.register_tools(app, http_client, rate_limiter, base_url, logger_instance, ...)
    classifications.register_tools(app, http_client, rate_limiter, base_url, logger_instance, ...)
    profiles.register_tools(app, http_client, rate_limiter, base_url, logger_instance, ...)
    conversations.register_tools(app, http_client, rate_limiter, base_url, logger_instance, ...)
    far.register_far_tools(app)
```

---

## Tool Files to Create

### 1. tools/awards.py (6 tools)
- `get_award_by_id`
- `search_federal_awards`
- `get_award_details`
- `get_subaward_data`
- `get_recipient_details`
- `get_vendor_by_uei`

**Status**: Template provided above

### 2. tools/spending.py (8 tools)
- `analyze_federal_spending`
- `get_spending_by_state`
- `get_spending_trends`
- `compare_states`
- `emergency_spending_tracker`
- `spending_efficiency_metrics`
- `get_disaster_funding`
- `get_budget_functions`

**Template**:
```python
"""Spending analysis and trends tools."""

def register_tools(app, http_client, rate_limiter, ...):
    @app.tool(name="analyze_federal_spending", ...)
    async def analyze_federal_spending(...): ...

    @app.tool(name="get_spending_trends", ...)
    async def get_spending_trends(...): ...
    # ... 6 more tools
```

### 3. tools/classifications.py (5 tools)
- `get_top_naics_breakdown`
- `get_naics_psc_info`
- `get_naics_trends`
- `get_object_class_analysis`
- `get_field_documentation`

**Template**: Same pattern as above

### 4. tools/profiles.py (4 tools)
- `get_vendor_profile`
- `get_agency_profile`
- `get_top_vendors_by_contract_count`
- `analyze_small_business`

### 5. tools/conversations.py (4 tools)
- `get_conversation`
- `list_conversations`
- `get_conversation_summary`
- `get_tool_usage_stats`

---

## Step-by-Step Extraction Process

### For Each Tool:

1. **Find the tool in server.py**
   ```bash
   grep -n "async def get_award_by_id" server.py
   ```

2. **Copy the complete tool** (including @app.tool decorator and function)

3. **Add imports** needed for that specific tool at the top of the file

4. **Update references**:
   - `http_client` → captured from `register_tools()` closure
   - `rate_limiter` → captured from `register_tools()` closure
   - `logger` → captured from `register_tools()` closure
   - Agency maps → passed as parameters to `register_tools()`

5. **Remove from server.py** after verification

6. **Test** the tool still works

---

## Important Dependencies Each Tool Needs

Every tool file needs:
```python
from fastmcp import FastMCP
from mcp.types import TextContent
from usaspending_mcp.utils.logging import log_tool_execution
from usaspending_mcp.tools.helpers import (
    QueryParser,
    format_currency,
    generate_award_url,
    generate_recipient_url,
    generate_agency_url,
    make_api_request,
)
```

---

## Benefits of This Refactoring

### For Code Quality
✅ Each file ~300-500 lines (professional standard)
✅ Clear separation of concerns
✅ Easier to test individual tools
✅ Easier to modify without breaking others
✅ Better code organization

### For Development
✅ Multiple developers can work on different tools
✅ Easier to add new tools
✅ Easier to remove tools
✅ Easier to understand the codebase

### For Learning
✅ Students see professional code organization
✅ Learn modular design patterns
✅ Understand dependency injection
✅ Practice code refactoring

---

## Timeline for Completion

- **Phase 1**: Extract one tool completely as example (1 hour)
- **Phase 2**: Extract remaining tools following pattern (3-4 hours)
- **Phase 3**: Clean up server.py (30 minutes)
- **Phase 4**: Test all tools still work (30 minutes)
- **Total**: ~6 hours of work

---

## How to Run During Refactoring

The server will still work the same way:
```bash
# HTTP mode
./start_mcp_server.sh

# Stdio mode
PYTHONPATH=src python -m usaspending_mcp.server --stdio
```

The internal organization changes, but external interface stays the same.

---

## Checklist

- [ ] helpers.py created (✅ DONE)
- [ ] awards.py created with register_tools()
- [ ] spending.py created with register_tools()
- [ ] classifications.py created with register_tools()
- [ ] profiles.py created with register_tools()
- [ ] conversations.py created with register_tools()
- [ ] tools/__init__.py updated
- [ ] server.py cleaned up
- [ ] All tools tested and working
- [ ] Added comments to new files
- [ ] Removed redundant code from server.py

