# FAR Analytics Guide

## Overview

The FAR (Federal Acquisition Regulation) tools in this MCP server include built-in search analytics that track user interactions, search patterns, and tool usage. This guide explains how to use and interpret FAR analytics reports.

## Quick Start

### Viewing Analytics Reports

The `get_far_analytics_report` tool generates searchable analytics from FAR tool usage. Available report types:

```
- summary:       Overall analytics summary with trending topics, failed searches, and cross-part analysis
- trending:      Most popular FAR search terms ranked by frequency
- zero_results:  Searches that found no results (identifies topic mapping gaps)
- cross_part:    Searches that match content across multiple FAR parts
```

### Example Usage

Get the overall analytics summary:
```bash
get_far_analytics_report("summary")
```

View trending search terms:
```bash
get_far_analytics_report("trending")
```

Identify searches that returned no results (useful for improving topic mappings):
```bash
get_far_analytics_report("zero_results")
```

See searches that work across multiple FAR parts:
```bash
get_far_analytics_report("cross_part")
```

## How Analytics Are Collected

### Logged Events

Every FAR tool call automatically logs analytics data:

#### search_far_regulations
- **Logged When**: User searches for FAR sections by keyword
- **Data Captured**:
  - Search keyword
  - Number of results returned
  - Optional FAR part filter (14, 15, 16, or 19)
  - Timestamp
  - Search success (results > 0)

#### get_far_section
- **Logged When**: User retrieves a specific FAR section
- **Data Captured**:
  - Section number searched
  - Search success (1 if found, 0 if not)
  - Timestamp

#### get_far_topic_sections
- **Logged When**: User looks up sections by procurement topic
- **Data Captured**:
  - Topic searched
  - Number of relevant sections found
  - Optional part filter
  - Timestamp

#### check_far_compliance
- **Logged When**: User checks FAR compliance for a contracting method
- **Data Captured**:
  - Contracting method checked
  - Number of relevant sections returned
  - Timestamp

## Understanding Analytics Reports

### Summary Report

The summary report provides a high-level overview of FAR tool usage:

```
TRENDING TOPICS (Top 10)
  small business: 45 searches (89% success rate)
  negotiation: 38 searches (92% success rate)
  best value: 32 searches (97% success rate)

ZERO-RESULT SEARCHES (Gaps in topic mappings)
  "contract modifications": 5 times
  "change order procedures": 3 times
  "value engineering": 2 times

CROSS-PART TOPICS (Multi-part searches)
  "documentation requirements": 8 times
  "cost analysis": 6 times

OVERALL STATISTICS
  Total Searches: 245
  Avg Results/Search: 4.2
  Zero-Result Rate: 8.2%
```

**What This Tells You:**
- **Trending Topics**: Shows which FAR subjects are most frequently consulted
- **Success Rate**: High success rate means topic mappings are effective; low rate indicates potential gaps
- **Zero-Result Searches**: Identifies searches that return no results—these suggest missing or incomplete topic mappings
- **Cross-Part Topics**: Shows which topics naturally span multiple FAR parts

### Trending Report

Ranked list of most-searched FAR topics:

```
Keyword                        Searches    Success Rate    Failures
small business                 45          89%             5
negotiation                    38          92%             3
best value                     32          97%             1
sealed bidding                 28          86%             4
source selection               19          95%             1
```

**Usage**: Use this to understand what procurement professionals are most interested in learning about from the FAR.

### Zero-Result Report

Searches that return no results, useful for identifying improvements:

```
Keyword                              Occurrences
contract modifications               5
change order procedures              3
value engineering                    2
protest procedures                   2
```

**Action Items**: If a zero-result search appears frequently, consider:
1. Adding the topic to the topic mappings in `usaspending_mcp/utils/far.py`
2. Improving section titles or content indexing
3. Creating new synthetic sections for that topic

### Cross-Part Report

Searches without a specific part filter that return results from multiple parts:

```
Keyword                              Search Count
documentation requirements           8
cost analysis                        6
socioeconomic program                5
award mechanisms                     4
```

**Insight**: These topics naturally span multiple FAR parts, indicating they're complex procurement concepts that don't fit neatly into a single part.

## Analytics Data Storage

### File Location

Analytics are stored in JSONL (JSON Lines) format:
```
/tmp/mcp_analytics/far_analytics.jsonl
```

Each line is a complete JSON record of a search event.

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

**Field Descriptions:**
- **timestamp**: ISO 8601 timestamp in UTC
- **tool**: Tool name ("far")
- **keyword**: Search term or section number
- **search_type**: Type of search ("keyword", "topic", "section", "compliance")
- **results_count**: Number of results returned
- **part**: Optional FAR part filter (null = no filter)
- **user_id**: User identifier (default: "anonymous")
- **success**: Boolean indicating if search returned results

## Using Analytics Programmatically

### Initialize FAR Analytics

```python
from usaspending_mcp.utils.search_analytics import initialize_analytics, get_analytics

# Initialize analytics for FAR tool
analytics = initialize_analytics("far")

# Or get existing instance
analytics = get_analytics("far")
```

### Log a Search

```python
# Log a keyword search for "best value" with 5 results, no part filter
analytics.log_search(
    keyword="best value",
    results_count=5,
    filter_value=None,
    search_type="keyword"
)

# Log a part-filtered search for "sealed bidding" in Part 14
analytics.log_search(
    keyword="sealed bidding",
    results_count=3,
    filter_value="14",
    search_type="keyword"
)
```

### Get Analytics Data

```python
# Get top 20 trending topics
trending = analytics.get_trending_topics(limit=20)
for topic in trending:
    print(f"{topic['keyword']}: {topic['searches']} searches, "
          f"{topic['success_rate']*100:.0f}% success rate")

# Get searches with zero results
zero_results = analytics.get_zero_result_searches()
for item in zero_results:
    print(f"'{item['keyword']}' returned no results {item['count']} times")

# Get searches across multiple FAR parts
cross_part = analytics.get_cross_filter_searches(min_count=3)
for item in cross_part:
    print(f"'{item['keyword']}' appears in multiple parts ({item['count']} times)")
```

### Generate Full Report

```python
report = analytics.generate_report()

# Report includes:
# - trending_topics: Top 10 by frequency
# - zero_result_searches: All searches with 0 results
# - cross_filter_topics: Searches spanning multiple parts
# - summary: Statistics like total searches, average results per search, zero-result %
```

## Improving FAR Topic Mappings

The analytics system helps identify gaps in topic mappings. Here's how to improve them:

### 1. Identify Zero-Result Searches

```bash
get_far_analytics_report("zero_results")
```

### 2. Analyze the Searches

Look at the "Keyword" column. Common issues:
- **Typos or informal language**: "contract mods" vs "contract modifications"
- **Missing topics**: Procurement concepts not yet mapped to FAR parts
- **Synonym issues**: Different users may use different terms for the same concept

### 3. Add to Topic Mappings

Edit `src/usaspending_mcp/utils/far.py` in the `_build_topics_index()` method:

```python
def _build_topics_index(self):
    """Build a topics index from section titles and content."""
    topics_map = {
        "sealed bidding": "14",
        "value engineering": "16",        # NEW: Add missing topic
        "change order": "16",              # NEW: Add synonym
        # ... rest of topics
    }
```

### 4. Test the Improvement

Perform the search again to verify it now returns results:
```bash
search_far_regulations("value engineering")
```

### 5. Review the Analytics Report

After some time, run the report again to confirm the topic mapping improved:
```bash
get_far_analytics_report("trending")
```

## Performance Considerations

### Analytics Impact

- **Minimal**: Analytics logging adds <1ms per search
- **Storage**: ~500 bytes per search event (200 searches ≈ 100KB)
- **Cleanup**: Delete `/tmp/mcp_analytics/far_analytics.jsonl` to reset analytics

### Large-Scale Usage

For production deployments with thousands of searches:

1. **Archival**: Periodically archive old analytics to separate files
2. **Aggregation**: Pre-compute monthly reports from raw JSONL
3. **Retention Policy**: Delete records older than 90 days

Example cleanup:
```bash
# Remove analytics file (loses all data—backup first!)
rm /tmp/mcp_analytics/far_analytics.jsonl

# Or keep only recent searches (delete records from > 90 days ago)
```

## Best Practices

### For Tool Users

1. **Be Specific**: More specific searches return more relevant results
   - ✓ "best value source selection"
   - ✗ "far"

2. **Use Part Filters**: If you know the relevant FAR part, include it
   - Faster results
   - Cleaner analytics data for your domain

3. **Check Topic Lookup**: For common procurement concepts, try topic lookup first
   - `get_far_topic_sections("source selection")`
   - More complete results than keyword search

### For Analytics Interpretation

1. **Look for Trends**: If zero-result searches increase, investigate why
2. **Monitor Success Rates**: Topic success rates should be >90%
3. **Use Cross-Part Data**: Understand which topics naturally span parts
4. **Set Improvement Goals**: "Reduce zero-result rate from 8% to 5%"

## Troubleshooting

### No Analytics Showing

**Problem**: `get_far_analytics_report()` shows "No search data available yet"

**Solution**: The analytics file hasn't been created yet. Perform a few searches to generate data.

### Zero-Result Rate Too High

**Problem**: More than 15% of searches return no results

**Solution**:
1. Run `get_far_analytics_report("zero_results")` to see what's missing
2. Add topics to `_build_topics_index()` in `far.py`
3. Improve section content indexing by expanding section titles

### Analytics File Growing Too Large

**Problem**: `/tmp/mcp_analytics/far_analytics.jsonl` is very large

**Solution**: Archive old data or delete the file to start fresh:
```bash
# Backup current analytics
cp /tmp/mcp_analytics/far_analytics.jsonl ~/far_analytics_backup.jsonl

# Delete to reset
rm /tmp/mcp_analytics/far_analytics.jsonl
```

## Integration with Other Tools

This analytics framework is configurable to support multiple tools. See [MULTI_TOOL_ANALYTICS_ARCHITECTURE.md](MULTI_TOOL_ANALYTICS_ARCHITECTURE.md) for information about:
- Using the same analytics system for USASpending searches
- Adding analytics to new tools
- Viewing analytics for all tools at once

## Summary

FAR Analytics provides:
- **Visibility** into what users are searching for
- **Quality Metrics** to measure search effectiveness
- **Improvement Data** to identify topic mapping gaps
- **Usage Patterns** to understand procurement information needs

Regular review of analytics reports helps ensure the FAR tool remains relevant and effective for users.
