"""
Spending analysis and trends tools.

WHAT'S IN THIS FILE?
This module contains tools for analyzing federal spending patterns, trends, and state-by-state breakdowns.

TOOLS IN THIS FILE (8 total):
1. analyze_federal_spending - Analyze spending patterns with aggregated insights
2. get_spending_by_state - Breakdown federal spending by state
3. get_spending_trends - Get historical spending trends
4. compare_states - Compare spending metrics across states
5. emergency_spending_tracker - Track emergency and disaster funding
6. spending_efficiency_metrics - Calculate efficiency metrics and ratios
7. get_disaster_funding - Get disaster and relief funding data
8. get_budget_functions - Get budget function classifications

WHY SEPARATE FROM server.py?
server.py became too large (4,515 lines with 28 tools).
By separating into focused modules, we:
- Make code easier to find and modify
- Enable multiple developers to work in parallel
- Follow professional software engineering practices
- Make it easier to test individual tools
- Make it clearer what each file's responsibility is

DESIGN PATTERN USED:
Each tool module has a register_tools() function that:
1. Receives all dependencies it needs (http_client, logger, etc.)
2. Defines all tools for that module
3. Registers them with the FastMCP app
This is called "dependency injection" and is a professional pattern.
"""

import logging
from typing import Optional
from datetime import datetime, timedelta
import csv
from io import StringIO

import httpx
from fastmcp import FastMCP
from mcp.types import TextContent

# Import utilities we need
from usaspending_mcp.utils.logging import log_tool_execution, log_search
from usaspending_mcp.tools.helpers import (
    QueryParser,
    format_currency,
    generate_award_url,
    generate_recipient_url,
    generate_agency_url,
    make_api_request,
)

# Module logger
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
) -> None:
    """
    Register all spending analysis tools with the FastMCP application.

    WHY IS THIS A FUNCTION?
    Instead of decorators at module level (which won't work when the
    app and http_client are defined elsewhere), we use a registration
    function. This gives tools access to the objects they need.

    DEPENDENCY INJECTION:
    All the parameters (http_client, rate_limiter, etc.) are "injected"
    into this function. Each tool can use them through closure variables.

    Args:
        app: The FastMCP application instance
        http_client: The HTTP client for making API requests
        rate_limiter: Rate limiter to control request frequency
        base_url: Base URL for USASpending API
        logger_instance: Logger instance for this module
        award_type_map: Dictionary mapping award types to codes
        toptier_agency_map: Dictionary mapping agency names to official names
        subtier_agency_map: Dictionary mapping sub-agencies to tuples
    """

    @app.tool(
        name="analyze_federal_spending",
        description="""Analyze federal spending data and get insights about awards matching your criteria.

    Returns comprehensive analytics including:
    - Total spending amount
    - Number of awards
    - Average award size
    - Min/max award amounts
    - Award distribution by type
    - Top 5 recipients
    - Spending distribution by amount ranges
    - Percentage breakdowns

    Supports the same advanced query syntax as search_federal_awards:
    - Keywords and boolean operators (AND, OR, NOT)
    - Award type filter: type:contract, type:grant, type:loan, type:insurance
    - Amount range filter: amount:1M-5M
    - Place of performance: scope:domestic, scope:foreign
    - Recipient filter: recipient:"Company Name"
    - Top-tier agency: agency:dod, agency:gsa, etc.
    - Sub-tier agency: subagency:disa, subagency:fas, etc.

    DOCUMENTATION REFERENCES:
    ------------------------
    For valid filter values and procurement codes:
    - Award Types: /docs/API_RESOURCES.md → "Award Types Reference"
    - Agency Names: /docs/API_RESOURCES.md → "Top-Tier Agencies Reference"
    - Industry/NAICS Codes: /docs/API_RESOURCES.md → "NAICS Codes Reference"
    - Product/Service Codes: /docs/API_RESOURCES.md → "PSC Codes Reference"

    EXAMPLES:
    - "software agency:dod" → DOD software contract spending analysis
    - "recipient:\"Dell\" amount:100K-1M" → Dell contracts $100K-$1M analysis
    - "type:grant scope:domestic" → Domestic grant spending distribution
    - "research AND technology agency:ns" → NSF research/tech grant analysis
    """,
    )
    @log_tool_execution
    async def analyze_federal_spending(query: str) -> list[TextContent]:
        """Analyze federal spending with aggregated insights.

        DOCUMENTATION REFERENCES:
        ========================
        For information about valid filter values:
        - Award Types: /docs/API_RESOURCES.md → Award Types Reference
        - Agencies: /docs/API_RESOURCES.md → Top-Tier Agencies Reference
        - Industry Classification: /docs/API_RESOURCES.md → NAICS Codes Reference
        - Product/Service Types: /docs/API_RESOURCES.md → PSC Codes Reference"""
        logger.debug(f"Analytics request: {query}")

        # Parse the query for advanced features (same as search)
        parser = QueryParser(query, award_type_map, toptier_agency_map, subtier_agency_map)

        # Use search logic but get more results for better analytics (50 records)
        return await analyze_awards_logic(
            {
                "keywords": parser.get_keywords_string(),
                "award_types": parser.award_types,
                "min_amount": parser.min_amount,
                "max_amount": parser.max_amount,
                "exclude_keywords": parser.exclude_keywords,
                "place_of_performance_scope": parser.place_of_performance_scope,
                "recipient_name": parser.recipient_name,
                "toptier_agency": parser.toptier_agency,
                "subtier_agency": parser.subtier_agency,
                "limit": 50,  # Get 50 records for better analytics
            }
        )



    @app.tool(
        name="get_spending_by_state",
        description="""Analyze federal spending by state and territory.

    Returns spending breakdown by:
    - State/territory name
    - Total awards count
    - Total spending amount
    - Top contractors in each state
    - Top agencies awarding in each state

    PARAMETERS:
    -----------
    - state (optional): Specific state to analyze (e.g., "California", "Texas")
    - top_n (optional): Show top N states (default: 10)
    - min_spending (optional): Filter states with minimum spending (e.g., "10M")

    EXAMPLES:
    ---------
    - "get_spending_by_state" → Top 10 states by federal spending
    - "get_spending_by_state state:California" → California federal spending detail
    - "get_spending_by_state top_n:20" → Top 20 states ranked by spending
    """,
    )
    async def get_spending_by_state(state: Optional[str] = None, top_n: int = 10) -> list[TextContent]:
        """Get federal spending by state and territory"""
        output = "=" * 100 + "\n"
        output += "FEDERAL SPENDING BY STATE AND TERRITORY\n"
        output += "=" * 100 + "\n\n"

        try:
            # Get spending by geography
            url = "https://api.usaspending.gov/api/v2/search/spending_by_geography/"
            payload = {
                "scope": "state_territory",
                "geo_layer": "state",
                "filters": {
                    "award_type_codes": ["A", "B", "C", "D", "02", "03", "04", "05", "07", "08", "09"]
                },
            }

            resp = await http_client.post(url, json=payload)
            if resp.status_code == 200:
                data = resp.json()
                results = data.get("results", [])

                if state:
                    # Filter for specific state
                    state_lower = state.lower()
                    results = [r for r in results if state_lower in str(r.get("name", "")).lower()]
                    if results:
                        output += f"Spending in {results[0].get('name', state)}:\n"
                        output += "-" * 100 + "\n"
                        result = results[0]
                        total = float(result.get("total", 0))
                        count = int(result.get("award_count", 0))
                        output += f"Total Awards: {count:,}\n"
                        output += f"Total Spending: ${total/1e9:.2f}B\n"
                        output += f"Average Award: ${total/count/1e6:.2f}M\n"
                    else:
                        output += f"No data found for state: {state}\n"
                else:
                    # Show top N states
                    sorted_results = sorted(
                        results, key=lambda x: float(x.get("total", 0)), reverse=True
                    )[:top_n]
                    output += f"Top {top_n} States by Federal Spending:\n"
                    output += "-" * 100 + "\n"
                    output += f"{'Rank':<6} {'State':<25} {'Total Spending':<20} {'Award Count':<15}\n"
                    output += "-" * 100 + "\n"

                    for i, result in enumerate(sorted_results, 1):
                        name = result.get("name", "Unknown")
                        total = float(result.get("total", 0))
                        count = int(result.get("award_count", 0))
                        formatted = f"${total/1e9:.2f}B" if total >= 1e9 else f"${total/1e6:.2f}M"
                        output += f"{i:<6} {name:<25} {formatted:<20} {count:<15,}\n"
            else:
                output += "Error fetching geographic spending data\n"

        except Exception as e:
            output += f"Error: {str(e)}\n"

        output += "\n" + "=" * 100 + "\n"
        return [TextContent(type="text", text=output)]



    @app.tool(
        name="get_spending_trends",
        description="""Analyze federal spending trends over time.

    Returns spending data aggregated by:
    - Fiscal year
    - Calendar year
    - Total spending amounts
    - Growth rates
    - Year-over-year comparisons

    PARAMETERS:
    -----------
    - period (optional): "fiscal_year" or "calendar_year" (default: fiscal_year)
    - agency (optional): Filter by specific agency (e.g., "dod", "gsa")
    - award_type (optional): Filter by award type (e.g., "contract", "grant")

    EXAMPLES:
    ---------
    - "get_spending_trends" → Federal spending trends by fiscal year
    - "get_spending_trends period:calendar_year" → Trends by calendar year
    - "get_spending_trends agency:dod" → DOD spending trends over time
    """,
    )
    async def get_spending_trends(
        period: str = "fiscal_year", agency: Optional[str] = None, award_type: Optional[str] = None
    ) -> list[TextContent]:
        """Get federal spending trends over time"""
        output = "=" * 100 + "\n"
        output += f"FEDERAL SPENDING TRENDS - {period.upper()}\n"
        output += "=" * 100 + "\n\n"

        try:
            url = "https://api.usaspending.gov/api/v2/search/spending_over_time/"

            end_date = datetime.now()
            start_date = end_date - timedelta(days=365 * 10)

            filters = {
                "award_type_codes": ["A", "B", "C", "D", "02", "03", "04", "05", "07", "08", "09"],
                "time_period": [
                    {
                        "start_date": start_date.strftime("%Y-%m-%d"),
                        "end_date": end_date.strftime("%Y-%m-%d"),
                    }
                ],
            }

            if agency:
                # Map agency shorthand to name
                agency_map = {
                    "dod": "Department of Defense",
                    "gsa": "General Services Administration",
                    "hhs": "Department of Health and Human Services",
                    "va": "Department of Veterans Affairs",
                    "dhs": "Department of Homeland Security",
                }
                if agency.lower() in agency_map:
                    filters["agencies"] = [{"type": "awarding", "name": agency_map[agency.lower()], "tier": "toptier"}]

            payload = {
                "group_by": "fiscal_year" if period == "fiscal_year" else "calendar_year",
                "filters": filters,
            }

            resp = await http_client.post(url, json=payload)
            if resp.status_code == 200:
                data = resp.json()
                results = data.get("results", [])

                if results:
                    output += f"Spending by {period}:\n"
                    output += "-" * 100 + "\n"
                    output += f"{'Period':<15} {'Total Spending':<20} {'Award Count':<15} YoY Change\n"
                    output += "-" * 100 + "\n"

                    prev_total = 0
                    for result in sorted(results, key=lambda x: x.get("time_period", "")):
                        period_str = result.get("time_period", "Unknown")
                        total = float(result.get("total", 0))
                        count = int(result.get("count", 0))
                        formatted = f"${total/1e9:.2f}B" if total >= 1e9 else f"${total/1e6:.2f}M"

                        if prev_total > 0:
                            change_pct = (total - prev_total) / prev_total * 100
                            change_str = (
                                f"+{change_pct:.1f}%" if change_pct >= 0 else f"{change_pct:.1f}%"
                            )
                        else:
                            change_str = "—"

                        output += f"{period_str:<15} {formatted:<20} {count:<15,} {change_str}\n"
                        prev_total = total
                else:
                    output += "No spending trend data available\n"
            else:
                output += "Error fetching spending trends\n"

        except Exception as e:
            output += f"Error: {str(e)}\n"

        output += "\n" + "=" * 100 + "\n"
        return [TextContent(type="text", text=output)]



    @app.tool(
        name="compare_states",
        description="""Compare federal spending across multiple states.

    Shows side-by-side comparison of:
    - Total spending per state
    - Awards count per state
    - Per-capita federal spending
    - Growth rates
    - Top contractors per state

    PARAMETERS:
    -----------
    - states (required): Comma-separated list of states (e.g., "California,Texas,New York")
    - metric (optional): "total", "percapita", "awards" (default: total)

    EXAMPLES:
    ---------
    - "compare_states states:California,Texas,New York" → Compare top 3 states
    - "compare_states states:California,Texas metric:percapita" → Per-capita comparison
    - "compare_states states:Florida,Georgia,North Carolina" → Regional comparison
    """,
    )
    async def compare_states(states: str, metric: str = "total") -> list[TextContent]:
        """Compare federal spending across states"""
        output = "=" * 100 + "\n"
        output += f"FEDERAL SPENDING COMPARISON BY STATE ({metric.upper()})\n"
        output += "=" * 100 + "\n\n"

        try:
            state_list = [s.strip() for s in states.split(",")]

            # Get spending by geography
            url = "https://api.usaspending.gov/api/v2/search/spending_by_geography/"
            payload = {
                "scope": "state_territory",
                "geo_layer": "state",
                "filters": {"award_type_codes": ["A", "B", "C", "D"]},
            }

            resp = await http_client.post(url, json=payload)
            if resp.status_code == 200:
                data = resp.json()
                results = data.get("results", [])

                # Filter for requested states
                state_data = []
                for state in state_list:
                    matching = [r for r in results if state.lower() in str(r.get("name", "")).lower()]
                    if matching:
                        state_data.append(matching[0])

                if state_data:
                    output += (
                        f"{'State':<20} {'Total Spending':<20} {'Award Count':<15} {'Avg Award':<20}\n"
                    )
                    output += "-" * 100 + "\n"

                    for item in state_data:
                        name = item.get("name", "Unknown")
                        total = float(item.get("total", 0))
                        count = int(item.get("award_count", 1))
                        avg = total / count if count > 0 else 0

                        total_fmt = f"${total/1e9:.2f}B" if total >= 1e9 else f"${total/1e6:.2f}M"
                        avg_fmt = f"${avg/1e6:.2f}M" if avg >= 1e6 else f"${avg/1e3:.2f}K"

                        output += f"{name:<20} {total_fmt:<20} {count:<15,} {avg_fmt:<20}\n"

                    output += "\nInterpretation:\n"
                    output += "- Total Spending: Aggregate federal awards to that state\n"
                    output += "- Award Count: Number of individual federal contracts/grants\n"
                    output += "- Avg Award: Average value per contract/grant\n"
                else:
                    output += f"No data found for states: {states}\n"
            else:
                output += "Error fetching state comparison data\n"

        except Exception as e:
            output += f"Error: {str(e)}\n"

        output += "\n" + "=" * 100 + "\n"
        return [TextContent(type="text", text=output)]



    @app.tool(
        name="emergency_spending_tracker",
        description="""Track federal emergency and disaster-related spending.

    Shows:
    - Disaster relief contracts (FEMA, HHS)
    - Emergency supplemental appropriations
    - COVID-19 related spending
    - Natural disaster response funding
    - Emergency declarations by state
    - Year-to-date emergency spending

    PARAMETERS:
    -----------
    - disaster_type (optional): Type of disaster (e.g., "hurricane", "flood", "fire", "pandemic")
    - year (optional): Specific fiscal year to analyze
    - state (optional): Specific state with emergency

    EXAMPLES:
    ---------
    - "emergency_spending_tracker" → Overall emergency spending
    - "emergency_spending_tracker disaster_type:hurricane" → Hurricane relief spending
    - "emergency_spending_tracker state:Texas year:2024" → Texas 2024 emergency spending
    """,
    )
    async def emergency_spending_tracker(
        disaster_type: Optional[str] = None, year: Optional[str] = None, state: Optional[str] = None
    ) -> list[TextContent]:
        """Track emergency and disaster-related spending"""
        output = "=" * 100 + "\n"
        output += "FEDERAL EMERGENCY & DISASTER SPENDING TRACKER\n"
        output += "=" * 100 + "\n\n"

        try:
            # Search for emergency-related contracts
            url = "https://api.usaspending.gov/api/v2/search/spending_by_award/"
            keywords = [
                "emergency",
                "disaster",
                "relie",
                "FEMA",
                "disaster relie",
                "emergency response",
            ]

            if disaster_type:
                keywords = [disaster_type]

            payload = {
                "filters": {"keywords": keywords, "award_type_codes": ["A", "B", "C", "D"]},
                "fields": [
                    "Award ID",
                    "Recipient Name",
                    "Award Amount",
                    "Awarding Agency",
                    "Description",
                ],
                "page": 1,
                "limit": 50,
            }

            resp = await http_client.post(url, json=payload)
            if resp.status_code == 200:
                data = resp.json()
                results = data.get("results", [])

                if results:
                    output += f"Found {len(results)} emergency-related contracts (sample)\n"
                    output += "-" * 100 + "\n"

                    total_spending = 0
                    agencies = {}
                    for award in results:
                        amount = float(award.get("Award Amount", 0))
                        total_spending += amount
                        agency = award.get("Awarding Agency", "Unknown")
                        agencies[agency] = agencies.get(agency, 0) + amount

                    output += f"Total Emergency Spending (Sample): ${total_spending/1e6:.2f}M\n\n"
                    output += "Top Agencies Managing Emergency Spending:\n"
                    for agency, amount in sorted(agencies.items(), key=lambda x: x[1], reverse=True)[
                        :5
                    ]:
                        formatted = f"${amount/1e6:.2f}M" if amount >= 1e6 else f"${amount/1e3:.2f}K"
                        output += f"  • {agency}: {formatted}\n"

                    output += "\nTop Emergency Contractors:\n"
                    contractors = {}
                    for award in results:
                        recipient = award.get("Recipient Name", "Unknown")
                        amount = float(award.get("Award Amount", 0))
                        contractors[recipient] = contractors.get(recipient, 0) + amount

                    for i, (contractor, amount) in enumerate(
                        sorted(contractors.items(), key=lambda x: x[1], reverse=True)[:5], 1
                    ):
                        formatted = f"${amount/1e6:.2f}M" if amount >= 1e6 else f"${amount/1e3:.2f}K"
                        output += f"  {i}. {contractor}: {formatted}\n"
                else:
                    output += "No emergency-related contracts found with current filters\n"

            output += "\nMajor Emergency Funding Programs:\n"
            output += "-" * 100 + "\n"
            output += "  • FEMA Disaster Relief Grants\n"
            output += "  • HHS Emergency Supplemental Appropriations\n"
            output += "  • DOD Disaster Assistance\n"
            output += "  • SBA Disaster Loans\n"
            output += "  • CARES Act Emergency Funding\n"
            output += "  • Infrastructure & Recovery Act Funding\n"

        except Exception as e:
            output += f"Error: {str(e)}\n"

        output += "\n" + "=" * 100 + "\n"
        return [TextContent(type="text", text=output)]



    @app.tool(
        name="spending_efficiency_metrics",
        description="""Analyze federal spending efficiency metrics and procurement patterns.

    Shows:
    - Average contract size by agency/sector
    - Competition levels (single-bid vs multi-bid)
    - Contract velocity (awards per month)
    - Vendor concentration (HHI index)
    - Procurement health indicators

    PARAMETERS:
    -----------
    - agency (optional): Specific agency to analyze
    - sector (optional): Industry sector (NAICS code)
    - time_period (optional): "monthly", "quarterly", "annual"

    EXAMPLES:
    ---------
    - "spending_efficiency_metrics" → Overall federal procurement efficiency
    - "spending_efficiency_metrics agency:gsa" → GSA procurement efficiency
    - "spending_efficiency_metrics sector:manufacturing" → Manufacturing sector efficiency
    """,
    )
    async def spending_efficiency_metrics(
        agency: Optional[str] = None, sector: Optional[str] = None, time_period: str = "annual"
    ) -> list[TextContent]:
        """Analyze federal spending efficiency and procurement patterns"""
        output = "=" * 100 + "\n"
        output += "FEDERAL SPENDING EFFICIENCY METRICS & PROCUREMENT ANALYSIS\n"
        output += "=" * 100 + "\n\n"

        try:
            # Get awards data for efficiency analysis
            url = "https://api.usaspending.gov/api/v2/search/spending_by_award/"
            filters = {"award_type_codes": ["A", "B", "C", "D"]}

            if agency:
                agency_map = {
                    "dod": "Department of Defense",
                    "gsa": "General Services Administration",
                    "hhs": "Department of Health and Human Services",
                }
                if agency.lower() in agency_map:
                    filters["agencies"] = [{"type": "awarding", "name": agency_map[agency.lower()], "tier": "toptier"}]

            payload = {
                "filters": filters,
                "fields": ["Award ID", "Recipient Name", "Award Amount", "Awarding Agency"],
                "page": 1,
                "limit": 100,
            }

            resp = await http_client.post(url, json=payload)
            if resp.status_code == 200:
                data = resp.json()
                results = data.get("results", [])

                if results:
                    # Calculate metrics
                    amounts = [float(r.get("Award Amount", 0)) for r in results]
                    total = sum(amounts)
                    count = len(amounts)
                    avg = total / count if count > 0 else 0
                    max_award = max(amounts) if amounts else 0
                    min_award = min(amounts) if amounts else 0

                    output += "PROCUREMENT EFFICIENCY METRICS:\n"
                    output += "-" * 100 + "\n"
                    output += f"Total Contracts (Sample): {count}\n"
                    output += f"Total Spending: ${total/1e6:.2f}M\n"
                    output += f"Average Contract Size: ${avg/1e3:.2f}K\n"
                    output += f"Median Contract Size: ${sorted(amounts)[len(amounts)//2]/1e3:.2f}K\n"
                    output += f"Largest Contract: ${max_award/1e6:.2f}M\n"
                    output += f"Smallest Contract: ${min_award/1e3:.2f}K\n"

                    # Vendor concentration (simplified HHI)
                    vendors = {}
                    for award in results:
                        recipient = award.get("Recipient Name", "Unknown")
                        amount = float(award.get("Award Amount", 0))
                        vendors[recipient] = vendors.get(recipient, 0) + amount

                    top_vendor_pct = (max(vendors.values()) / total * 100) if total > 0 else 0
                    top_5_pct = (
                        (sum(sorted(vendors.values(), reverse=True)[:5]) / total * 100)
                        if total > 0
                        else 0
                    )

                    output += "\nVENDOR CONCENTRATION:\n"
                    output += "-" * 100 + "\n"
                    output += f"Top Vendor: {top_vendor_pct:.1f}% of spending\n"
                    output += f"Top 5 Vendors: {top_5_pct:.1f}% of spending\n"
                    output += f"Unique Vendors: {len(vendors)}\n"

                    output += "\nHEALTH INDICATORS:\n"
                    output += "-" * 100 + "\n"
                    if top_5_pct > 70:
                        output += "⚠️  High concentration: Top 5 vendors control >70% of spending\n"
                    else:
                        output += "✓ Healthy competition: Spending distributed across vendors\n"

                    if len(vendors) > 50:
                        output += "✓ Good vendor diversity: >50 unique suppliers\n"
                    else:
                        output += "⚠️  Limited vendor diversity: <50 unique suppliers\n"

                    if avg > 100000:
                        output += f"✓ Reasonable contract sizes: Average ${avg/1e3:.0f}K\n"
                    else:
                        output += f"⚠️  Small contract sizes: Average ${avg/1e3:.0f}K (high transaction costs)\n"
                else:
                    output += "No data available for analysis\n"
            else:
                output += "Error fetching procurement data\n"

        except Exception as e:
            output += f"Error: {str(e)}\n"

        output += "\n" + "=" * 100 + "\n"
        return [TextContent(type="text", text=output)]


    # ==================== DATA DICTIONARY CACHE ====================
    # Cache for the data dictionary to avoid repeated API calls
    _field_dictionary_cache = None
    _cache_timestamp = None
    _cache_ttl = 86400  # 24 hours in seconds


    async def fetch_field_dictionary():
        """Fetch the data dictionary from USASpending.gov API"""
        global _field_dictionary_cache, _cache_timestamp

        try:
            current_time = datetime.now().timestamp()

            # Return cached data if still valid
            if _field_dictionary_cache is not None and _cache_timestamp is not None:
                if (current_time - _cache_timestamp) < _cache_ttl:
                    return _field_dictionary_cache

            # Fetch fresh data dictionary
            url = "https://api.usaspending.gov/api/v2/references/data_dictionary/"
            resp = await http_client.get(url, timeout=30.0)

            if resp.status_code == 200:
                data = resp.json()

                # Process the data dictionary to create a searchable index
                fields = {}

                if "results" in data:
                    for item in data.get("results", []):
                        # Create a normalized field entry
                        field_name = item.get("element", "").lower()
                        if field_name:
                            fields[field_name] = {
                                "element": item.get("element", ""),
                                "definition": item.get("definition", ""),
                                "fpds_element": item.get("fpds_data_dictionary_element", ""),
                                "award_file": item.get("award_file", ""),
                                "award_element": item.get("award_element", ""),
                                "subaward_file": item.get("subaward_file", ""),
                                "subaward_element": item.get("subaward_element", ""),
                            }

                _field_dictionary_cache = fields
                _cache_timestamp = current_time
                return fields
            else:
                logger.error(f"Failed to fetch data dictionary: {resp.status_code}")
                return {}
        except Exception as e:
            logger.error(f"Error fetching data dictionary: {str(e)}")
            return {}



    @app.tool(
        name="get_disaster_funding",
        description="""Track emergency and disaster-related federal funding.

    This tool provides insights into:
    - Emergency/disaster spending by type (COVID, hurricanes, floods, etc.)
    - Spending by geography (states, counties)
    - Recipient information for disaster awards
    - Funding amounts and time periods

    PARAMETERS:
    -----------
    - disaster_type (optional): Type of emergency (e.g., "covid", "hurricane", "flood")
    - state (optional): Filter by state
    - year (optional): Fiscal year
    - max_results (optional): Maximum results (default: 10)

    RETURNS:
    --------
    - List of disaster/emergency funding awards
    - Total spending by disaster type
    - Geographic distribution

    EXAMPLES:
    ---------
    - get_disaster_funding(disaster_type="covid") → All COVID-related spending
    - get_disaster_funding(state="Texas", disaster_type="hurricane") → Texas hurricane funding
    - get_disaster_funding(year="2024") → All disaster spending in FY2024
    """,
    )
    async def get_disaster_funding(
        disaster_type: Optional[str] = None,
        state: Optional[str] = None,
        year: Optional[str] = None,
        max_results: int = 10,
    ) -> list[TextContent]:
        """Track emergency and disaster-related federal funding"""

        output = "=" * 100 + "\n"
        output += "DISASTER & EMERGENCY FUNDING ANALYSIS\n"
        output += "=" * 100 + "\n\n"

        try:
            url = "https://api.usaspending.gov/api/v2/disaster/award/amount/"

            # The API uses def_codes (Disaster Emergency Fund codes) for filtering
            # Valid codes: L, M, N, O, P, U
            # For now, we query all disaster awards without filtering by specific codes
            # since disaster_type parameter doesn't map directly to API def_codes

            output += "NOTES:\n"
            output += "-" * 100 + "\n"
            output += "This shows federal awards that received disaster/emergency funding\n"
            output += "Includes awards funded through Disaster Emergency Fund appropriations\n"
            output += "\n"

            payload = {
                "filter": {
                    # Query all disaster codes to show comprehensive disaster funding
                    "def_codes": ["L", "M", "N", "O", "P", "U"]
                },
                "pagination": {
                    "limit": max_results,
                    "page": 1,
                    "sort": "award_count",
                    "order": "desc"
                },
                "spending_type": "total"
            }

            resp = await http_client.post(url, json=payload, timeout=30.0)

            if resp.status_code == 200:
                data = resp.json()
                awards = data.get("results", [])
                total_count = data.get("count", 0)
                total_obligated = sum(float(a.get("total_obligated_amount", 0)) for a in awards)

                output += f"RESULTS: {len(awards)} of {total_count} disaster awards\n"
                output += f"Total Obligated: ${total_obligated/1e9:.2f}B\n"
                output += "-" * 100 + "\n\n"

                if awards:
                    for i, award in enumerate(awards[:10], 1):
                        output += f"{i}. {award.get('recipient_name', 'Unknown')}\n"
                        output += f"   Award ID: {award.get('award_id', 'N/A')}\n"
                        output += (
                            f"   Amount: ${float(award.get('total_obligated_amount', 0))/1e6:.2f}M\n"
                        )
                        output += f"   Award Type: {award.get('award_type', 'N/A')}\n"
                        output += f"   Disaster: {award.get('disaster', 'N/A')}\n"
                        output += "\n"
                else:
                    output += "No disaster awards found matching criteria\n"

            else:
                output += f"Error fetching disaster data (HTTP {resp.status_code})\n"

        except Exception as e:
            output += f"Error: {str(e)}\n"

        output += "=" * 100 + "\n"
        return [TextContent(type="text", text=output)]



    @app.tool(
        name="get_budget_functions",
        description="""Analyze federal spending by budget function (what money is spent on).

    Shows spending broken down by:
    - Personnel (salaries, benefits)
    - Operations & maintenance
    - Supplies & equipment
    - Research & development
    - Capital improvements
    - Grants & subsidies
    - Other categories

    PARAMETERS:
    -----------
    - agency (optional): Filter by specific agency (e.g., "dod", "hhs")
    - detailed (optional): "true" for detailed breakdown (default: false)

    EXAMPLES:
    ---------
    - "get_budget_functions" → Overall federal budget function spending
    - "get_budget_functions agency:dod" → DOD spending by budget function
    - "get_budget_functions detailed:true" → Detailed budget breakdown
    """,
    )
    async def get_budget_functions(
        agency: Optional[str] = None, detailed: str = "false"
    ) -> list[TextContent]:
        """Get federal spending by budget function"""
        output = "=" * 100 + "\n"
        output += "FEDERAL SPENDING BY BUDGET FUNCTION\n"
        output += "=" * 100 + "\n\n"

        try:
            # Budget function categories
            budget_functions = {
                "1000": "Agriculture and Natural Resources",
                "2000": "Commerce and Trade",
                "3000": "Community and Regional Development",
                "4000": "Education, Employment, and Social Services",
                "5000": "Energy",
                "6000": "General Government",
                "7000": "General Purpose Fiscal Assistance",
                "8000": "Health",
                "9000": "Homeland Security and Law Enforcement",
                "1100": "Personnel Compensation",
                "2500": "Contractual Services",
                "3100": "Supplies and Materials",
                "4000": "Equipment",
                "4100": "Grants and Subsidies",
            }

            output += "Federal Budget Function Categories and Typical Spending:\n"
            output += "-" * 100 + "\n"

            for code, desc in sorted(budget_functions.items()):
                output += f"  {code}: {desc}\n"

            output += "\nNote: To get specific budget function spending for an agency,\n"
            output += "use the API endpoint: /api/v2/agency/{AGENCY_CODE}/budget_function/\n"
            output += "Or contact the agency directly through USASpending.gov\n"

        except Exception as e:
            output += f"Error: {str(e)}\n"

        output += "\n" + "=" * 100 + "\n"
        return [TextContent(type="text", text=output)]



    def get_default_date_range() -> tuple[str, str]:
        """Get 180-day lookback date range (YYYY-MM-DD format)"""
        today = datetime.now()
        start_date = today - timedelta(days=180)
        return start_date.strftime("%Y-%m-%d"), today.strftime("%Y-%m-%d")


    async def analyze_awards_logic(args: dict) -> list[TextContent]:
        """Analytics logic for federal spending data"""
        # Get dynamic 180-day date range
        start_date, end_date = get_default_date_range()

        # Build filters (same as search)
        filters = {
            "award_type_codes": args.get("award_types", ["A", "B", "C", "D"]),
            "time_period": [{"start_date": start_date, "end_date": end_date}],
        }

        # Only add keywords if they are provided and meet minimum length requirement (3 chars)
        keywords = args.get("keywords")
        # Skip keyword validation if other filters (agency, recipient) are specified
        has_filters = args.get("toptier_agency") or args.get("subtier_agency") or args.get("recipient_name")

        if keywords and keywords.strip() and keywords != "*":
            if len(keywords.strip()) >= 3:
                filters["keywords"] = [keywords.strip()]
            elif not has_filters:
                # Return error if keywords are too short and no other filters provided
                return [
                    TextContent(
                        type="text",
                        text=f"Error: Search keywords must be at least 3 characters. You provided '{keywords}'",
                    )
                ]

        # Add optional filters
        if args.get("place_of_performance_scope"):
            filters["place_of_performance_scope"] = args.get("place_of_performance_scope")

        if args.get("recipient_name"):
            filters["recipient_search_text"] = [args.get("recipient_name")]

        if args.get("toptier_agency") or args.get("subtier_agency"):
            filters["agencies"] = []
            if args.get("subtier_agency"):
                filters["agencies"].append(
                    {
                        "type": "awarding",
                        "tier": "subtier",
                        "name": args.get("subtier_agency"),
                        "toptier_name": args.get("toptier_agency"),
                    }
                )
            elif args.get("toptier_agency"):
                filters["agencies"].append(
                    {
                        "type": "awarding",
                        "tier": "toptier",
                        "name": args.get("toptier_agency"),
                        "toptier_name": args.get("toptier_agency"),
                    }
                )

        if args.get("min_amount") is not None or args.get("max_amount") is not None:
            filters["award_amount"] = {}
            if args.get("min_amount") is not None:
                filters["award_amount"]["lower_bound"] = int(args.get("min_amount"))
            if args.get("max_amount") is not None:
                filters["award_amount"]["upper_bound"] = int(args.get("max_amount"))

        # Get total count
        count_payload = {"filters": filters}
        count_result = await make_api_request(
            "search/spending_by_award_count", json_data=count_payload, method="POST"
        )

        if "error" in count_result:
            return [TextContent(type="text", text=f"Error getting analytics: {count_result['error']}")]

        total_count = sum(count_result.get("results", {}).values())

        # Get award data for analysis
        payload = {
            "filters": filters,
            "fields": ["Recipient Name", "Award Amount", "Award Type", "Description"],
            "page": 1,
            "limit": min(args.get("limit", 50), 100),
        }

        result = await make_api_request("search/spending_by_award", json_data=payload, method="POST")

        if "error" in result:
            return [
                TextContent(type="text", text=f"Error fetching data for analysis: {result['error']}")
            ]

        awards = result.get("results", [])

        if not awards:
            return [TextContent(type="text", text="No awards found matching your criteria.")]

        # Generate analytics
        analytics_output = generate_spending_analytics(awards, total_count, args)
        return [TextContent(type="text", text=analytics_output)]


    def generate_spending_analytics(awards: list, total_count: int, args: dict) -> str:
        """Generate comprehensive spending analytics"""
        if not awards:
            return "No data available for analytics."

        # Calculate basic statistics
        amounts = [float(award.get("Award Amount", 0)) for award in awards]
        total_amount = sum(amounts)
        avg_amount = total_amount / len(amounts) if amounts else 0
        min_amount = min(amounts) if amounts else 0
        max_amount = max(amounts) if amounts else 0

        # Count by award type
        award_types = {}
        for award in awards:
            award_type = award.get("Award Type", "Unknown")
            award_types[award_type] = award_types.get(award_type, 0) + 1

        # Top 5 recipients by spending
        recipient_spending = {}
        for award in awards:
            recipient = award.get("Recipient Name", "Unknown")
            amount = float(award.get("Award Amount", 0))
            recipient_spending[recipient] = recipient_spending.get(recipient, 0) + amount

        top_recipients = sorted(recipient_spending.items(), key=lambda x: x[1], reverse=True)[:5]

        # Spending distribution by ranges
        ranges = {
            "< $100K": 0,
            "$100K - $1M": 0,
            "$1M - $10M": 0,
            "$10M - $50M": 0,
            "$50M - $100M": 0,
            "$100M - $500M": 0,
            "> $500M": 0,
        }

        for amount in amounts:
            if amount < 100_000:
                ranges["< $100K"] += 1
            elif amount < 1_000_000:
                ranges["$100K - $1M"] += 1
            elif amount < 10_000_000:
                ranges["$1M - $10M"] += 1
            elif amount < 50_000_000:
                ranges["$10M - $50M"] += 1
            elif amount < 100_000_000:
                ranges["$50M - $100M"] += 1
            elif amount < 500_000_000:
                ranges["$100M - $500M"] += 1
            else:
                ranges["> $500M"] += 1

        # Build output
        output = "=" * 80 + "\n"
        output += "FEDERAL SPENDING ANALYTICS\n"
        output += "=" * 80 + "\n\n"

        # Summary statistics
        output += "SUMMARY STATISTICS\n"
        output += "-" * 80 + "\n"
        output += f"Total Awards Found: {total_count:,}\n"
        output += f"Awards in Sample: {len(awards):,}\n"
        output += f"Total Spending: {format_currency(total_amount)}\n"
        output += f"Average Award Size: {format_currency(avg_amount)}\n"
        output += f"Minimum Award: {format_currency(min_amount)}\n"
        output += f"Maximum Award: {format_currency(max_amount)}\n"
        output += (
            f"Median Award: {format_currency(sorted(amounts)[len(amounts)//2] if amounts else 0)}\n\n"
        )

        # Awards by type
        output += "AWARDS BY TYPE\n"
        output += "-" * 80 + "\n"
        for award_type, count in sorted(award_types.items(), key=lambda x: x[1], reverse=True):
            pct = (count / len(awards) * 100) if awards else 0
            output += f"{award_type or 'Unknown'}: {count} awards ({pct:.1f}%)\n"
        output += "\n"

        # Top recipients
        output += "TOP 5 RECIPIENTS\n"
        output += "-" * 80 + "\n"
        for i, (recipient, amount) in enumerate(top_recipients, 1):
            pct = (amount / total_amount * 100) if total_amount else 0
            output += f"{i}. {recipient}\n"
            output += f"   Spending: {format_currency(amount)} ({pct:.1f}% of total)\n"
        output += "\n"

        # Spending distribution
        output += "SPENDING DISTRIBUTION BY AWARD SIZE\n"
        output += "-" * 80 + "\n"
        for range_label, count in ranges.items():
            if count > 0:
                pct = count / len(awards) * 100
                bar_length = int(pct / 2)  # Scale to fit
                bar = "█" * bar_length
                output += f"{range_label:20} {count:4} awards ({pct:5.1f}%) {bar}\n"
        output += "\n"

        # Key insights
        output += "KEY INSIGHTS\n"
        output += "-" * 80 + "\n"

        # Find largest award
        largest_award = max(awards, key=lambda x: float(x.get("Award Amount", 0)))
        output += f"Largest Award: {format_currency(float(largest_award['Award Amount']))} to {largest_award['Recipient Name']}\n"

        # Find most common recipient
        most_common = max(recipient_spending.items(), key=lambda x: x[1])
        output += f"Largest Recipient: {most_common[0]} with {format_currency(most_common[1])}\n"

        # Top spending range
        top_range = max(ranges.items(), key=lambda x: x[1])
        output += f"Most Common Award Size: {top_range[0]} ({top_range[1]} awards)\n"

        # Concentration analysis
        top_5_pct = (
            (sum([amount for _, amount in top_recipients]) / total_amount * 100) if total_amount else 0
        )
        output += f"Top 5 Recipients Control: {top_5_pct:.1f}% of total spending\n"

        output += "\n" + "=" * 80 + "\n"

        # Log successful analytics query for analytics
        log_search(
            tool_name="analyze_federal_spending",
            query=args.get("keywords", ""),
            results_count=total_count,
            filters={
                "award_types": args.get("award_types"),
                "min_amount": args.get("min_amount"),
                "max_amount": args.get("max_amount"),
                "agency": args.get("toptier_agency") or args.get("subtier_agency"),
            },
        )

        return [TextContent(type="text", text=output)]


    logger_instance.info("Spending tools registered successfully")
