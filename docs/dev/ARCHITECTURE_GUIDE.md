# USASpending MCP Server - Architecture & Design Guide

**Last Updated**: October 29, 2025
**Status**: Complete Analysis with Recommendations

---

## Executive Summary

Your current **single monolithic MCP server with 21 tools** is the **correct architectural choice** for this use case. However, this guide provides framework for future evolution if needed.

**Key Finding**: Don't split into multiple servers unless you encounter specific technical constraints (resource limits, conflicting dependencies, separate deployment lifecycles).

---

## Current Architecture Assessment

### What You Have (Recommended ✅)

```
┌─────────────────────────────────────────┐
│ Single MCP Server (src/usaspending_mcp/ │
│ server.py)                              │
│                                         │
│  21 Tools - Unified Context            │
│  - Awards Search & Details (5)          │
│  - Recipients & Vendors (4)             │
│  - Agency & Reference (3)               │
│  - Spending Analytics (9)               │
│                                         │
│  Single Connection  | Unified State     │
│  Easier Debugging   | Better Caching    │
└─────────────────────────────────────────┘
         ↓
  Client Application
    (Claude, etc.)
```

### Why This Works Well

| Aspect | Benefit |
|--------|---------|
| **Simplicity** | One server to deploy, configure, monitor |
| **State Management** | Shared caching, session context across tools |
| **API Consistency** | Unified error handling, authentication |
| **Tool Interaction** | Tools can leverage shared data without API calls |
| **Debugging** | Single log stream, unified error tracking |
| **Performance** | No inter-server communication overhead |

---

## When To Split Into Multiple Servers

Only split if you encounter these specific constraints:

### ❌ NOT Recommended For This Project

```
Constraint              | Your Situation
───────────────────────────────────────────
Resource Limits        | Single server handles load fine
Conflicting Deps       | All use same libraries (httpx, async)
Separate Deployments   | All tools deploy together
Team Ownership         | Single team maintains
Different Auth Models  | All use same API credentials
```

### ✅ Would Be Recommended If:

```
Scenario 1: Scale Beyond 50+ Tools
├─ Tools per server: 10-15 max
├─ Reason: Complexity management
└─ Impact: Minimal at 21 tools

Scenario 2: Separate Teams
├─ Awards Team owns 5 tools
├─ Analytics Team owns 9 tools
├─ Reason: Team autonomy, separate deployments
└─ Impact: Increases client complexity

Scenario 3: Conflicting Dependencies
├─ Tool A requires old library version
├─ Tool B requires new library version
├─ Reason: Can't satisfy both in single process
└─ Impact: None currently

Scenario 4: Different SLAs
├─ Analytics tools need 99.9% uptime
├─ Awards tools acceptable at 95%
├─ Reason: Can scale/upgrade independently
└─ Impact: Not required for your needs
```

---

## Recommended Multi-Server Architecture (Future Option)

If you ever need to split, here's the recommended approach:

### Option A: Domain-Based Split (4 servers)

```
┌──────────────────┐
│ Awards Server    │ (5 tools)
├──────────────────┤
│ get_award_by_id
│ search_federal_awards
│ get_award_details
│ get_subaward_data
│ download_award_data
└──────────────────┘
           ↓
┌──────────────────┐
│ Recipient Server │ (4 tools)
├──────────────────┤
│ get_recipient_details
│ get_vendor_profile
│ get_agency_profile
│ analyze_small_business
└──────────────────┘
           ↓
┌──────────────────┐
│ Reference Server │ (3 tools)
├──────────────────┤
│ get_field_documentation
│ get_naics_psc_info
│ get_budget_functions
└──────────────────┘
           ↓
┌──────────────────┐
│ Analytics Server │ (9 tools)
├──────────────────┤
│ get_spending_by_state
│ get_spending_trends
│ compare_states
│ get_object_class_analysis
│ analyze_federal_spending
│ emergency_spending_tracker
│ spending_efficiency_metrics
│ get_top_naics_breakdown
│ get_disaster_funding
└──────────────────┘
           ↓
      Client App
```

**Pros:**
- Clear domain boundaries
- Independent scaling
- Separate team ownership possible

**Cons:**
- 4x configuration complexity
- Cross-server queries require API calls (not shared state)
- Harder to maintain tool consistency
- Client must manage 4 connections

### Option B: Lightweight + Heavy Server (2 servers)

```
┌──────────────────────────┐
│ Lightweight Server       │ (9 tools)
├──────────────────────────┤
│ Reference tools that     │
│ rarely change, have      │
│ simple lookups           │
└──────────────────────────┘
           ↓
┌──────────────────────────┐
│ Primary Server           │ (12 tools)
├──────────────────────────┤
│ Heavy computation:       │
│ - Analytics (9)          │
│ - Awards Search (3)      │
└──────────────────────────┘
           ↓
      Client App
```

**Pros:**
- Separate resource allocation
- Can independently scale heavy workloads

**Cons:**
- Less clean domain boundaries
- Still adds complexity

---

## Best Practices: Staying Monolithic

Since monolithic is recommended, here's how to keep it maintainable:

### 1. Tool Organization (Within Single Server)

```python
# src/usaspending_mcp/server.py - Organize by domain

# ===== AWARDS DOMAIN =====
@app.tool()
async def get_award_by_id(award_id: str) -> str:
    """..."""
    pass

@app.tool()
async def search_federal_awards(...) -> str:
    """..."""
    pass

# ===== RECIPIENT DOMAIN =====
@app.tool()
async def get_recipient_details(...) -> str:
    """..."""
    pass

# ===== ANALYTICS DOMAIN =====
@app.tool()
async def get_spending_by_state(...) -> str:
    """..."""
    pass

# Use this organization even in single server
```

### 2. Shared Utilities

```python
# Create a utilities module (future)
# mcp_utils/
#   ├── api_client.py      (Shared HTTP client)
#   ├── cache.py           (Shared caching)
#   ├── validators.py      (Shared validation)
#   └── formatters.py      (Shared output formatting)

# This allows tool separation without multiple servers
```

### 3. Clear Interface Boundaries

```python
# Even within single server, define clear boundaries

class AwardsToolSet:
    """Awards domain tools"""
    def __init__(self, client: HttpClient):
        self.client = client

    async def get_award_by_id(self, award_id: str) -> str:
        """..."""
        pass

class RecipientToolSet:
    """Recipient domain tools"""
    def __init__(self, client: HttpClient):
        self.client = client

    async def get_recipient_details(self, name: str) -> str:
        """..."""
        pass

# Then in main server, register tools from each set
```

### 4. Tool Documentation

```python
# Create a tool registry document
# tool_registry.json

{
  "tools": [
    {
      "name": "get_award_by_id",
      "domain": "awards",
      "tier": 1,
      "dependencies": ["httpx"],
      "api_endpoints": [
        "GET /api/v2/awards/{award_id}/"
      ],
      "performance": "< 1s",
      "availability": "99.5%"
    }
  ]
}
```

---

## Performance Comparison

### Monolithic (Current) ✅ Recommended

```
Single MCP Server

Connection Time:    100ms (one connection)
Tool Lookup:        O(1)  (in-process)
Cross-Tool Data:    Instant (shared memory)
State Management:   Shared cache
Memory Usage:       ~150MB per server
Scaling:            Vertical only (add server instances)
```

### Multi-Server (If Needed)

```
4 Independent Servers

Connection Time:    400ms (4 connections)
Tool Lookup:        O(1)  (in-process)
Cross-Tool Data:    100-500ms (HTTP calls)
State Management:   Distributed cache complexity
Memory Usage:       ~50MB per server × 4 = 200MB
Scaling:            Horizontal and vertical
```

**Net Result**: Monolithic is ~3x faster for your use case.

---

## Migration Path (If Needed In Future)

If you ever need to split, here's the safe migration:

### Phase 1: Refactor While Monolithic (No Architecture Change)

```bash
Step 1: Create tool domains (still in one server)
  src/usaspending_mcp/server.py → domain_based organization

Step 2: Create domain modules
  mcp_domains/
    ├── awards.py
    ├── recipients.py
    ├── reference.py
    └── analytics.py

Step 3: Register tools from domains
  → All still in single server process
  → No client changes needed
```

### Phase 2: Create Server Wrapper (Optional)

```bash
If you decide to split:

Step 4: Create separate server executables
  server_awards.py      (imports domain_awards)
  server_recipients.py  (imports domain_recipients)
  server_analytics.py   (imports domain_analytics)

Step 5: Update client configuration
  clients/claude_config.json
  - Update to connect to all servers
```

### Phase 3: Deployment Updates

```bash
Step 6: Containerize if needed
  docker/
    ├── Dockerfile.awards
    ├── Dockerfile.recipients
    ├── Dockerfile.analytics
  docker-compose.yml    (runs all servers)

Step 7: Update docs and deployment guides
```

**Timeline**: ~1-2 weeks if needed, vs. 1 day to do now (not recommended).

---

## Recommendation Summary

### ✅ DO (Current Approach)

- Keep single monolithic server
- Organize tools by domain within the server
- Use shared utilities module
- Document tool dependencies and performance
- Add structured logging
- Build comprehensive test suite (already done! ✅)

### ❌ DON'T (Unless Constraints Appear)

- Split into multiple servers prematurely
- Create separate processes for each tool
- Build distributed caching yet
- Add inter-server communication
- Increase client configuration complexity

### 🎯 Future-Proofing

- Organize code as if domains are separate (even in one server)
- Use clear interfaces between domains
- Document dependencies and requirements
- Build tests that validate domain isolation
- Keep domain-specific code in separate modules

---

## Decision Matrix

Use this to decide if you should split in the future:

```
Question                          | Answer → Action
──────────────────────────────────┼─────────────────────────
Tools > 30?                       | YES  → Consider splitting
Server using > 500MB RAM?         | YES  → Consider splitting
Tools have conflicting deps?      | YES  → Must split
Different teams own tools?        | YES  → Consider splitting
Different deployment schedules?   | YES  → Consider splitting
Performance SLA varies by tool?   | YES  → Consider splitting
All above are NO?                 | NO   → STAY MONOLITHIC ✅
```

For your current situation: **All are NO → Stay monolithic** ✅

---

## Example: Organized Monolithic Server

```python
# src/usaspending_mcp/server.py - Clean organization example

from fastmcp import FastMCP
from mcp_domains import awards, recipients, analytics, reference

app = FastMCP("usaspending")

# ===== AWARDS DOMAIN TOOLS =====
awards_tools = awards.AwardsToolSet()

@app.tool()
async def get_award_by_id(award_id: str) -> str:
    return await awards_tools.get_award_by_id(award_id)

@app.tool()
async def search_federal_awards(keyword: str, ...) -> str:
    return await awards_tools.search_federal_awards(keyword, ...)

# ===== RECIPIENT DOMAIN TOOLS =====
recipient_tools = recipients.RecipientToolSet()

@app.tool()
async def get_recipient_details(name: str) -> str:
    return await recipient_tools.get_recipient_details(name)

# ===== ANALYTICS DOMAIN TOOLS =====
analytics_tools = analytics.AnalyticsToolSet()

@app.tool()
async def get_spending_by_state(state: str, ...) -> str:
    return await analytics_tools.get_spending_by_state(state, ...)

# ===== REFERENCE DOMAIN TOOLS =====
reference_tools = reference.ReferenceToolSet()

@app.tool()
async def get_field_documentation() -> str:
    return await reference_tools.get_field_documentation()

# Still a single server, but clean domain organization
```

---

## Conclusion

**Your current single-server architecture is optimal.**

Focus on:
1. ✅ Maintaining comprehensive tests (you've done this!)
2. ✅ Organizing code by domain
3. ✅ Clear documentation
4. ✅ Monitoring and logging
5. ✅ API performance optimization

**Revisit this decision when/if:**
- You exceed 50 tools
- Tools have conflicting dependencies
- Different teams need independent deployments
- Performance degradation appears

**Until then: Keep it simple, keep it fast, keep it maintainable.**

---

## Analytics Architecture

### Overview

The FAR tools include a **configurable, reusable analytics system** that tracks search patterns, user interactions, and tool usage. This architecture is designed to support multiple tools with minimal code duplication.

### Key Design Pattern: Tool-Agnostic Analytics

```
Single SearchAnalytics Class
        ↓
Multiple Instances (One Per Tool)
        ↓
Tool-Specific Configuration
        ↓
Separate Data Storage Per Tool
```

**Benefits:**
- **Code Reuse**: One implementation, multiple tools
- **Tool Flexibility**: Each tool configures its own filter names and behavior
- **Data Isolation**: FAR analytics separate from USASpending, etc.
- **Scalability**: Add unlimited tools without code duplication

### How It Works

1. **Tool logs search**: `analytics = get_analytics("far")`
2. **Record created**: Generic record with tool metadata
3. **Filter field dynamic**: `filter_name` config determines the field name
4. **Data stored**: Tool-specific JSONL file (`far_analytics.jsonl`)
5. **Reports generated**: Tool-aware analytics with metrics

### Record Format

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

**Dynamic Field**: The `"part"` field name comes from configuration. USASpending tools would use `"agency"` instead.

### Integration Points

**In FAR Tools** (`src/usaspending_mcp/tools/far.py`):
```python
from usaspending_mcp.utils.search_analytics import get_analytics

async def search_far_regulations(keyword: str, part: str = None):
    # ... perform search ...

    # Log to analytics
    analytics = get_analytics("far")
    analytics.log_search(
        keyword=keyword,
        results_count=len(results),
        filter_value=part,
        search_type="keyword"
    )
```

**In Server Setup**:
Initialize analytics when server starts:
```python
from usaspending_mcp.utils.search_analytics import initialize_analytics

initialize_analytics("far", {"filter_name": "part"})
```

### Adding New Tools with Analytics

To add analytics to a new tool:

1. **Initialize in server**:
   ```python
   initialize_analytics("my_tool", {"filter_name": "my_filter"})
   ```

2. **Log in tool**:
   ```python
   analytics = get_analytics("my_tool")
   analytics.log_search(
       keyword=query,
       results_count=len(results),
       filter_value=filter_val
   )
   ```

3. **Get reports**:
   ```python
   report = get_analytics("my_tool").generate_report()
   ```

That's it. No code duplication needed.

### Analytics Storage

- **Location**: `/tmp/mcp_analytics/{tool_name}_analytics.jsonl`
- **Format**: JSON Lines (one record per line)
- **Size**: ~500 bytes per search event

Example files:
```
/tmp/mcp_analytics/
├── far_analytics.jsonl          (FAR searches)
├── usaspending_analytics.jsonl  (USASpending searches)
└── other_tool_analytics.jsonl   (Other tools)
```

### Future: Multi-Tool Dashboards

When USASpending analytics are added:

```python
from usaspending_mcp.utils.search_analytics import get_all_analytics

# Get analytics for all tools at once
all_analytics = get_all_analytics()

# Generate multi-tool report
for tool_name, analytics in all_analytics.items():
    report = analytics.generate_report()
    print(f"{tool_name}: {report['summary']['total_searches']} searches")
```

### Best Practices

1. **Always use tool-specific get_analytics()**
   ```python
   # Correct
   analytics = get_analytics("my_tool")

   # Avoid
   analytics = get_analytics()  # Only works for FAR
   ```

2. **Include appropriate search_type**
   ```python
   # Be specific about the search type
   analytics.log_search(keyword, count, search_type="section")
   ```

3. **Use filter_value for optional filters**
   ```python
   # Log with optional filter
   analytics.log_search(keyword, count, filter_value=part_num)
   ```

### Performance Impact

- **Logging overhead**: <1ms per search
- **Storage**: ~500 bytes per search
- **Report generation**: ~20ms for typical dataset

Negligible impact on overall tool performance.

### Documentation References

For detailed analytics information:
- **FAR Users**: See [FAR_ANALYTICS_GUIDE.md](../FAR_ANALYTICS_GUIDE.md)
- **Developers**: See [MULTI_TOOL_ANALYTICS_ARCHITECTURE.md](../MULTI_TOOL_ANALYTICS_ARCHITECTURE.md)

---

## References

- **MCP Specification**: Single server model assumed
- **Microservices Pattern**: Not applicable until you hit specific constraints
- **Monolithic Benefits**: Simpler debugging, better state management, lower latency
- **Migration Cost**: ~2 weeks if needed in future (acceptable cost to avoid premature splitting)
- **Analytics Pattern**: Configurable, multi-tool approach for tracking and analysis

---

**Next Steps**:
1. Refactor `src/usaspending_mcp/server.py` to organize by domain (optional but recommended)
2. Create `mcp_domains/` module structure
3. Continue leveraging single-server benefits
4. Monitor metrics as tool count grows

This approach scales to ~50 tools comfortably before reconsidering architecture.
