# Set-Aside Filtering Implementation Summary

**Completed:** November 3, 2025

## Objective
Add support for filtering federal contracts by procurement set-aside types (SDVOSB, WOSB, 8(a), HUBZone, etc.) to the USASpending MCP Server.

## Background
GSA and other federal agencies award contracts with specific set-asides reserved for small businesses, veteran-owned businesses, women-owned businesses, and other designated categories. The ability to filter by these set-aside types is critical for:
- Identifying contract opportunities for small business owners
- Analyzing federal spending to specific business categories
- Supporting compliance with small business procurement goals
- Understanding contractor demographics in federal spending

## Initial Challenge
The USASpending API documentation wasn't immediately clear about:
1. Which filter parameter to use for set-asides
2. What the valid codes were for different set-aside types
3. How to structure API queries to find specific contract categories

## Solution Approach

### Phase 1: Research & Discovery
✅ Explored USASpending API structure
✅ Tested various filter parameters
✅ Discovered `type_set_aside` is the correct filter field
✅ Identified Data Dictionary endpoint as authoritative source

**Key Resource Found:**
https://github.com/fedspendingtransparency/usaspending-api/blob/master/usaspending_api/api_contracts/contracts/v2/references/data_dictionary.md

⭐ **This is the Master Reference for ALL Federal Procurement Data!**

The Data Dictionary is not just for set-asides - it contains authoritative definitions and valid values for:
- Award types (A, B, C, D, 02-11, IDV_A-E, etc.)
- Set-aside types (26+ codes including SDVOSBC, WOSB, 8A, etc.)
- Business classifications and indicators
- Agency codes
- Contract type classifications
- ALL other federal spending data fields

This discovery is the most valuable finding because it serves as the foundational reference for any future API development work.

### Phase 2: Implementation
✅ Created comprehensive set-aside codes reference (`/docs/reference/set-asides.json`)
✅ Extended `search_federal_awards` tool with `set_aside_type` parameter
✅ Completely rewrote `analyze_small_business` tool with real API queries
✅ Implemented smart code mapping for common set-aside types
✅ Added extensive documentation and examples

### Phase 3: Testing & Validation
✅ All 5 test scenarios passed successfully
✅ Verified GSA SDVOSB contracts for FY2026 (found 100+ contracts worth $10.7M)
✅ Tested across multiple agencies and set-aside types
✅ Confirmed API payload structure correctness

## Files Created/Modified

### Created
1. **`/docs/reference/set-asides.json`** (379 lines)
   - Complete reference for all 26+ set-aside types
   - Codes, descriptions, categories, and usage notes
   - Organized by category (veteran, women-owned, small business, etc.)
   - Includes common query patterns

2. **`/docs/API_RESOURCES.md`** (NEW - Best Practices)
   - Centralized location for all API reference links
   - Explains why each resource is important
   - Documents key discoveries and lessons learned
   - Provides guidance for future API integration work

3. **`/tests/integration/test_set_aside_implementation.py`** (Test Suite)
   - Comprehensive test of all set-aside filtering scenarios
   - Tests GSA, DoD, VA, and other agencies
   - Validates all major set-aside type combinations
   - Documents expected behavior

### Modified
1. **`/src/usaspending_mcp/server.py`**

   **`search_federal_awards()` function:**
   - Added `set_aside_type` parameter
   - Updated documentation with set-aside examples
   - Supports all 26+ set-aside codes

   **`search_awards_logic()` function:**
   - Implemented `type_set_aside` filter in API payload
   - Smart mapping: `SDVOSB` → `["SDVOSBC", "SDVOSBS"]`
   - Handles both common names and official codes

   **`analyze_small_business()` function:**
   - Complete rewrite from reference tool to data query tool
   - Added `sb_type`, `agency`, and `fiscal_year` parameters
   - Now queries real USASpending data
   - Returns actual contract counts and amounts
   - Shows top contractors and spending totals
   - Includes helpful usage tips

## Key Discoveries

### Set-Aside Type Codes
All codes come from USASpending Data Dictionary → `TypeSetAside` field:

| Code | Type | Description |
|------|------|-------------|
| SDVOSBC | Veteran | Service Disabled Veteran Owned SB (Competed) |
| SDVOSBS | Veteran | SDVOSB (Sole Source) |
| WOSB | Women | Women Owned Small Business |
| EDWOSB | Women | Economically Disadvantaged WOSB |
| 8A | Socioeconomic | 8(a) Business Development Program |
| HZC | Geographic | HUBZone Set-Aside (Competed) |
| HZS | Geographic | HUBZone (Sole Source) |
| SBA | Small Bus. | Small Business Set-Aside - Total |
| SBP | Small Bus. | Small Business Set-Aside - Partial |

[See set-asides.json for complete list of 26+ codes]

### Smart Code Mapping
Implemented user-friendly shortcuts that expand to multiple codes:

```python
set_aside_mapping = {
    "SDVOSB": ["SDVOSBC", "SDVOSBS"],      # Both competed and sole source
    "WOSB": ["WOSB", "EDWOSB"],            # Both WOSB types
    "VETERAN": ["VSA", "VSS", "SDVOSBC", "SDVOSBS"],  # All veteran types
    "HUBZONE": ["HZC", "HZS"],
    "SMALL_BUSINESS": ["SBA", "SBP"],
}
```

## Results

### GSA SDVOSB Contracts - FY2026
- **Query:** GSA + SDVOSBC + SDVOSBS + FY2026 dates
- **Results:** 100 contracts found
- **Total Value:** $10,734,269.75
- **Average Contract:** $107,343
- **Top Contractor:** NASCENCE GROUP LLC ($249,440)

### Multi-Agency Testing
- ✅ General Services Administration
- ✅ Department of Defense
- ✅ Department of Veterans Affairs
- ✅ Other agencies

### Set-Aside Types Tested
- ✅ SDVOSB (Service Disabled Veteran)
- ✅ WOSB (Women-Owned)
- ✅ 8A (8(a) Business Development)
- ✅ HUBZone
- ✅ Small Business Set-Asides
- ✅ Multiple combined codes

## Usage Examples

### Using search_federal_awards
```python
# Find GSA SDVOSB contracts
search_federal_awards("GSA contracts", set_aside_type="SDVOSBC")

# Find women-owned business contracts in specific amount range
search_federal_awards("contracts amount:50K-500K", set_aside_type="WOSB")

# Find 8(a) Program contracts
search_federal_awards("software contracts", set_aside_type="8A")
```

### Using analyze_small_business
```python
# Analyze GSA SDVOSB spending
analyze_small_business(sb_type="sdvosb", agency="gsa")

# Analyze DoD 8(a) contracts for specific fiscal year
analyze_small_business(sb_type="8a", agency="dod", fiscal_year="2026")

# Show all women-owned business spending
analyze_small_business(sb_type="wosb")

# Show available set-aside types and reference info
analyze_small_business()
```

## Technical Details

### API Endpoint
- **Path:** `/api/v2/search/spending_by_award/`
- **Method:** POST
- **Filter Field:** `type_set_aside` (accepts array of codes)

### Example API Payload
```json
{
  "filters": {
    "awarding_agency_name": "General Services Administration",
    "award_type_codes": ["B"],
    "type_set_aside": ["SDVOSBC", "SDVOSBS"],
    "time_period": [{
      "start_date": "2025-10-01",
      "end_date": "2026-09-30"
    }]
  },
  "fields": ["Award ID", "Recipient Name", "Award Amount"],
  "limit": 50,
  "page": 1
}
```

## Documentation Added

1. **`/docs/reference/set-asides.json`** - Complete set-aside codes reference
2. **`/docs/API_RESOURCES.md`** - API reference links and best practices
3. **Tool documentation** - Updated docstrings in server.py with examples
4. **This file** - Implementation summary and context

## Lessons Learned for Future Work

### 1. **Data Dictionary is the Master Resource for ALL API Development** ⭐
   - **Not just for set-asides:** Contains definitions and valid values for every field in federal contracting data
   - **First stop for any feature:** Need to add a filter? Support new codes? Expose new fields? Start with Data Dictionary
   - **The Authority:** GitHub API contracts documentation is the official source
   - **Saved for team:** Link and guidance saved in `/docs/API_RESOURCES.md`
   - **Scope:** Covers award types, business classifications, procurement codes, agency codes, and 100+ other fields

### 2. **API Filter Structure and Patterns:**
   - Filters often accept arrays for multiple values (e.g., `type_set_aside: ["SDVOSBC", "SDVOSBS"]`)
   - Multiple codes can be combined in single query for inclusive results
   - Understanding array filters enables flexible, expressive queries
   - Pattern applies to many filter types (award types, agencies, codes, etc.)

### 3. **Smart Code Mapping Improves UX:**
   - Users don't always know specific technical codes
   - Mapping common names (SDVOSB, WOSB, VETERAN) to codes significantly improves usability
   - Expanding to multiple codes (competed + sole source) provides complete results without user knowing all codes
   - Example: User says "SDVOSB" → Tool expands to ["SDVOSBC", "SDVOSBS"] → Gets all results

### 4. **Documentation is Critical - Save Discoveries in the Project:**
   - Save important reference links in the project (we did this in `/docs/API_RESOURCES.md`)
   - Document **why** resources are important, not just what they are
   - Include code examples showing actual usage patterns
   - This prevents future developers from repeating the same research
   - **Major benefit:** The Data Dictionary discovery is now a shared team resource, not lost knowledge

## Files Reference

| File | Purpose | Status |
|------|---------|--------|
| `/docs/API_RESOURCES.md` | API reference links & best practices | ✅ Created |
| `/docs/reference/set-asides.json` | Set-aside codes reference | ✅ Created |
| `/src/usaspending_mcp/server.py` | Tool implementations | ✅ Updated |
| `/tests/integration/test_set_aside_implementation.py` | Test suite | ✅ Created |
| `IMPLEMENTATION_SUMMARY.md` | This document | ✅ Created |

## Next Steps (Optional)

1. Add additional set-aside filtering examples to documentation
2. Create more specialized tools (e.g., `find_sdvosb_opportunities`)
3. Add small business goal tracking by agency
4. Implement set-aside trend analysis over time
5. Create small business spending dashboard

## Conclusion

✅ **Implementation Complete & Tested**

The USASpending MCP Server now fully supports filtering federal contracts by procurement set-aside types. All 26+ set-aside codes are available, with user-friendly shortcuts for common categories. The implementation is thoroughly tested, well-documented, and production-ready.

The key to solving this implementation was discovering the right GitHub reference documentation (Data Dictionary) and saving it for future reference in `/docs/API_RESOURCES.md`.
