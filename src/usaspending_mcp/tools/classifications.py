"""
NAICS, PSC, and object class analysis tools.

WHAT'S IN THIS FILE?
Tools for analyzing industry classifications (NAICS), product/service codes (PSC),
and federal budget object classes.

TOOLS IN THIS FILE (5 total):
1. get_top_naics_breakdown - Get top NAICS codes with agencies and contractors
2. get_naics_psc_info - Look up NAICS and PSC code information
3. get_naics_trends - Get NAICS industry trends and year-over-year comparisons
4. get_object_class_analysis - Analyze spending by object class
5. get_field_documentation - Get documentation for API fields

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
from usaspending_mcp.utils.logging import log_search
from usaspending_mcp.tools.helpers import (
    format_currency,
    make_api_request,
    generate_award_url,
    generate_recipient_url,
    generate_agency_url,
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
    conversation_logger,
    query_context_analyzer,
    result_aggregator,
    relevance_scorer,
) -> None:
    """
    Register all classification analysis tools with the FastMCP application.

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

    # ================================================================================
    # HELPER FUNCTIONS AND CACHING
    # ================================================================================

    # Cache for field dictionary
    _field_dictionary_cache = None
    _cache_timestamp = None
    _cache_ttl = 86400  # 24 hours in seconds

    async def fetch_field_dictionary():
        """Fetch the data dictionary from USASpending.gov API"""
        nonlocal _field_dictionary_cache, _cache_timestamp

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
                                "data_type": item.get("data_type", ""),
                            }

                _field_dictionary_cache = fields
                _cache_timestamp = current_time
                return fields

            return {}

        except Exception as e:
            logger_instance.error(f"Error fetching field dictionary: {e}")
            return {}

    def get_default_date_range() -> tuple[str, str]:
        """Get 180-day lookback date range (YYYY-MM-DD format)"""
        today = datetime.now()
        start_date = today - timedelta(days=180)
        return start_date.strftime("%Y-%m-%d"), today.strftime("%Y-%m-%d")

    # ================================================================================
    # TOOL DEFINITIONS
    # ================================================================================

    @app.tool(
        name="get_top_naics_breakdown",
        description="""Get top NAICS codes across all federal agencies with associated agencies and contractors.

    Returns detailed breakdown showing:
    - Top 3 NAICS codes by award count
    - Agencies awarding contracts in each NAICS
    - Top contractors in each NAICS category
    - Spending amounts and percentages

    This provides a comprehensive view of which agencies procure from which industries
    and which contractors dominate each sector.

    NOTE: Limited to top 3 NAICS codes to prevent timeout issues.

    DOCUMENTATION REFERENCES:
    ------------------------
    For detailed NAICS code information and industry classifications:
    - NAICS Reference: /docs/API_RESOURCES.md → "NAICS Codes Reference"
    - Data Dictionary: /docs/API_RESOURCES.md → "Data Dictionary" (for NAICS field definitions)
    - Direct Source: Census.gov/naics/
    """,
    )
    async def get_top_naics_breakdown() -> str:
        """Get top NAICS codes with agencies and contractors.

        DOCUMENTATION REFERENCES:
        ========================
        For understanding NAICS codes in results:
        - NAICS Reference: /docs/API_RESOURCES.md → NAICS Codes Reference
        - Data Dictionary: /docs/API_RESOURCES.md → Data Dictionary"""
        output = "=" * 100 + "\n"
        output += "TOP 3 NAICS CODES - FEDERAL AGENCIES & CONTRACTORS ANALYSIS\n"
        output += "=" * 100 + "\n\n"

        # Get NAICS reference data
        naics_url = "https://api.usaspending.gov/api/v2/references/naics/"
        try:
            resp = await http_client.get(naics_url)
            if resp.status_code == 200:
                data = resp.json()
                naics_list = data.get("results", [])

                # Sort by count - Reduced to top 3 to prevent client-side timeouts
                # (Each NAICS requires an additional API call, limiting to 3 keeps total under 60s)
                sorted_naics = sorted(naics_list, key=lambda x: x.get("count", 0), reverse=True)[:3]

                total_awards = sum(n.get("count", 0) for n in naics_list)

                for i, naics in enumerate(sorted_naics, 1):
                    code = naics.get("naics")
                    desc = naics.get("naics_description")
                    count = naics.get("count", 0)
                    pct = (count / total_awards * 100) if total_awards > 0 else 0

                    output += f"{i}. NAICS {code}: {desc}\n"
                    output += f"   Awards: {count:,} ({pct:.1f}% of total)\n\n"

                    # Search for contracts in this NAICS (using keywords)
                    naics_keywords = {
                        "31": "food manufacturing beverage",
                        "32": "chemical pharmaceutical manufacturing",
                        "33": "machinery equipment electronics manufacturing",
                        "42": "wholesale distribution supply",
                        "44": "retail office supplies equipment",
                    }

                    keyword = naics_keywords.get(code, code)
                    search_url = "https://api.usaspending.gov/api/v2/search/spending_by_award/"
                    # Reduced limit to 25 for faster response times
                    search_payload = {
                        "filters": {"award_type_codes": ["A", "B", "C", "D"]},
                        "fields": [
                            "Award ID",
                            "Recipient Name",
                            "Award Amount",
                            "Awarding Agency",
                            "Description",
                        ],
                        "page": 1,
                        "limit": 25,  # Reduced from 50 to prevent timeouts
                    }

                    try:
                        search_resp = await http_client.post(search_url, json=search_payload)
                        if search_resp.status_code == 200:
                            search_data = search_resp.json()
                            awards = search_data.get("results", [])

                            if awards:
                                # Aggregate agencies and contractors
                                agencies = {}
                                contractors = {}
                                total_spending = 0

                                for award in awards:
                                    agency = award.get("Awarding Agency", "Unknown")
                                    recipient = award.get("Recipient Name", "Unknown")
                                    amount = float(award.get("Award Amount", 0))

                                    total_spending += amount
                                    agencies[agency] = agencies.get(agency, 0) + 1
                                    contractors[recipient] = contractors.get(recipient, 0) + amount

                                output += "   Associated Agencies:\n"
                                for agency, count in sorted(
                                    agencies.items(), key=lambda x: x[1], reverse=True
                                )[:3]:
                                    output += f"      • {agency} ({count} awards)\n"

                                output += "   Top Contractors:\n"
                                for contractor, amount in sorted(
                                    contractors.items(), key=lambda x: x[1], reverse=True
                                )[:3]:
                                    formatted = (
                                        f"${amount/1e6:.2f}M"
                                        if amount >= 1e6
                                        else f"${amount/1e3:.2f}K"
                                    )
                                    output += f"      • {contractor}: {formatted}\n"
                            else:
                                output += "   (No sample contracts found with this NAICS keyword)\n"
                        output += "\n"
                    except Exception as e:
                        output += f"   (Error fetching contract data: {str(e)[:50]})\n\n"
            else:
                output += "Error fetching NAICS reference data\n"
        except Exception as e:
            output += f"Error: {str(e)}\n"

        output += "=" * 100 + "\n"
        return output



    @app.tool(
        name="get_naics_psc_info",
        description="""Look up NAICS (industry classification) and PSC (product/service) codes.

    NAICS - North American Industry Classification System codes identify what industry a contractor operates in.
    PSC - Product/Service codes identify what type of product or service is being procured.

    PARAMETERS:
    -----------
    - search_term (required): What to search for
      * NAICS lookup: "software", "construction", "consulting", "manufacturing"
      * PSC lookup: "information technology", "office furniture", "engineering"

    - code_type (optional): "naics" or "psc" (default: search both)

    DOCUMENTATION REFERENCES:
    ------------------------
    For comprehensive information about NAICS and PSC codes:
    - NAICS Reference: /docs/API_RESOURCES.md → "NAICS Codes Reference"
    - PSC Reference: /docs/API_RESOURCES.md → "PSC Codes Reference"
    - Data Dictionary: /docs/API_RESOURCES.md → "Data Dictionary" section
    - Direct Resources: Census.gov (NAICS), Acquisition.gov (PSC)

    EXAMPLES:
    ---------
    - "software" → Find software-related NAICS and PSC codes
    - "consulting" → Consulting industry classifications
    - "information technology psc" → IT product/service codes
    """,
    )
    async def get_naics_psc_info(search_term: str, code_type: str = "both") -> str:
        """Look up NAICS and PSC code information.

        DOCUMENTATION REFERENCES:
        ========================
        For detailed information about codes found:
        - NAICS Codes: /docs/API_RESOURCES.md → NAICS Codes Reference
        - PSC Codes: /docs/API_RESOURCES.md → PSC Codes Reference
        - Data Dictionary: /docs/API_RESOURCES.md → Data Dictionary"""
        output = f"Looking up codes for: {search_term}\n\n"
        output += "=" * 80 + "\n"

        # Get NAICS codes if requested
        if code_type.lower() in ["both", "naics"]:
            output += "NAICS CODES (Industry Classification)\n"
            output += "-" * 80 + "\n"

            naics_url = "https://api.usaspending.gov/api/v2/references/naics/"
            try:
                resp = await http_client.get(naics_url)
                if resp.status_code == 200:
                    naics_data = resp.json()
                    # Filter NAICS codes by search term
                    matches = [
                        n
                        for n in naics_data.get("results", [])
                        if search_term.lower() in n.get("naics_description", "").lower()
                    ]
                    if matches:
                        for match in matches[:10]:  # Show top 10
                            code = match.get("naics")
                            desc = match.get("naics_description")
                            count = match.get("count", 0)
                            output += f"{code:6} - {desc} ({count} awards)\n"
                    else:
                        output += f"No NAICS codes found matching '{search_term}'\n"
                else:
                    output += "Error fetching NAICS codes\n"
            except Exception as e:
                output += f"Error: {str(e)}\n"

        output += "\n"

        # Get PSC codes if requested
        if code_type.lower() in ["both", "psc"]:
            output += "PSC CODES (Product/Service Classification)\n"
            output += "-" * 80 + "\n"

            psc_url = "https://api.usaspending.gov/api/v2/autocomplete/psc/"
            try:
                psc_payload = {"search_text": search_term, "limit": 10}
                resp = await http_client.post(psc_url, json=psc_payload)
                if resp.status_code == 200:
                    psc_data = resp.json()
                    results = psc_data.get("results", [])
                    if results:
                        for match in results:
                            code = match.get("product_or_service_code")
                            desc = match.get("psc_description")
                            output += f"{code:8} - {desc}\n"
                    else:
                        output += f"No PSC codes found matching '{search_term}'\n"
                else:
                    output += "Error fetching PSC codes\n"
            except Exception as e:
                output += f"Error: {str(e)}\n"

        output += "\n" + "=" * 80 + "\n"
        return output



    @app.tool(
        name="get_naics_trends",
        description="""Get NAICS industry trends and year-over-year comparisons.

    This tool tracks how federal spending and contracting in specific industries
    (NAICS codes) has changed over time. Shows growth/decline trends and
    year-over-year comparisons for industry sectors.

    Returns:
    - NAICS code and industry name
    - Year-by-year spending totals
    - Year-over-year growth/decline percentages
    - Contract count trends
    - Average contract value trends

    PARAMETERS:
    -----------
    - naics_code (optional): Specific NAICS code to analyze (e.g., "511210")
      If not provided, shows top industries by spending
    - years (optional): Number of fiscal years to analyze (default: 3, max: 10)
    - agency (optional): Filter by awarding agency (e.g., "dod", "gsa")
    - award_type (optional): Filter by award type ("contract", "grant", "all")
    - limit (optional): Number of industries to show (default: 10)

    EXAMPLES:
    ---------
    - "get_naics_trends years:5" → Top 10 industries with 5-year trend
    - "get_naics_trends naics_code:511210" → Software publishing industry trends
    - "get_naics_trends agency:dod limit:20 years:3" → Top 20 DOD contractor industries over 3 years
    - "get_naics_trends award_type:contract years:5" → Contract trends for top industries
    """,
    )
    async def get_naics_trends(
        naics_code: Optional[str] = None,
        years: int = 3,
        agency: Optional[str] = None,
        award_type: str = "contract",
        limit: int = 10,
    ) -> str:
        """Get NAICS industry trends and year-over-year analysis"""
        logger.debug(
            f"Tool call received: get_naics_trends with naics_code={naics_code}, years={years}, agency={agency}, award_type={award_type}, limit={limit}"
        )

        # Validate parameters
        if years < 1 or years > 10:
            years = 3
        if limit < 1 or limit > 50:
            limit = 10

        # Map award type to codes
        award_type_mapping = {
            "contract": ["A", "B", "C", "D"],
            "grant": ["02", "03", "04", "05", "06", "07", "08", "09", "10", "11"],
            "all": ["A", "B", "C", "D", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11"],
        }

        award_codes = award_type_mapping.get(award_type.lower(), ["A", "B", "C", "D"])

        try:
            # Calculate date ranges for multiple fiscal years
            # Fiscal year runs Oct-Sep, so FY2024 = Oct 2023 - Sep 2024
            from datetime import datetime

            today = datetime.now()
            current_fy = today.year if today.month >= 10 else today.year - 1
            start_fy = current_fy - years + 1

            # Collect data for each fiscal year
            fiscal_year_data = {}

            for fy in range(start_fy, current_fy + 1):
                # Fiscal year date range
                fy_start = f"{fy - 1}-10-01"
                fy_end = f"{fy}-09-30"

                # Build filters
                filters = {
                    "award_type_codes": award_codes,
                    "time_period": [{"start_date": fy_start, "end_date": fy_end}],
                }

                # Add agency filter if specified
                if agency:
                    agency_mapping = toptier_agency_map.copy()
                    agency_name = agency_mapping.get(agency.lower(), agency)
                    filters["awarding_agency_name"] = agency_name

                # Fetch awards data
                # Note: USASpending API doesn't support naics_code filter directly,
                # so we'll filter results client-side if a specific NAICS is requested
                payload = {
                    "filters": filters,
                    "fields": ["NAICS Code", "NAICS Description", "Award Amount"],
                    "page": 1,
                    "limit": 100,  # Get more for better aggregation
                }

                result = await make_api_request(
                    http_client,
                    "search/spending_by_award",
                    base_url,
                    json_data=payload,
                    method="POST"
                )

                if "error" in result:
                    continue

                awards = result.get("results", [])

                # Aggregate by NAICS code
                for award in awards:
                    naics = award.get("NAICS Code", "Unknown")
                    naics_desc = award.get("NAICS Description", "Unknown")

                    # Filter by specific NAICS code if provided (client-side filtering)
                    if naics_code and naics != naics_code:
                        continue

                    amount = float(award.get("Award Amount", 0))

                    if naics not in fiscal_year_data:
                        fiscal_year_data[naics] = {
                            "description": naics_desc,
                            "years": {},
                        }

                    if fy not in fiscal_year_data[naics]["years"]:
                        fiscal_year_data[naics]["years"][fy] = {
                            "total": 0,
                            "count": 0,
                        }

                    fiscal_year_data[naics]["years"][fy]["total"] += amount
                    fiscal_year_data[naics]["years"][fy]["count"] += 1

            if not fiscal_year_data:
                return "No NAICS trend data found for the specified criteria."

            # Calculate total spending across all years for each NAICS (for sorting)
            for naics in fiscal_year_data:
                total = sum(fy["total"] for fy in fiscal_year_data[naics]["years"].values())
                fiscal_year_data[naics]["total"] = total

            # Sort by total spending (descending)
            sorted_naics = sorted(
                fiscal_year_data.items(),
                key=lambda x: x[1]["total"],
                reverse=True
            )[:limit]

            # Build output
            output = "=" * 140 + "\n"
            output += "NAICS INDUSTRY TRENDS & YEAR-OVER-YEAR ANALYSIS\n"
            output += "=" * 140 + "\n\n"
            output += f"Fiscal Years Analyzed: FY{start_fy} - FY{current_fy}\n"
            output += f"Award Type: {award_type.capitalize()}\n"
            if agency:
                output += f"Agency: {agency.upper()}\n"
            if naics_code:
                output += f"Specific NAICS: {naics_code}\n"
            output += "-" * 140 + "\n\n"

            # Display trends for each NAICS
            for rank, (naics, data) in enumerate(sorted_naics, 1):
                description = data["description"]
                years_dict = data["years"]

                output += f"{rank}. NAICS {naics}: {description}\n"
                output += "-" * 140 + "\n"
                output += f"{'Fiscal Year':<15} {'Total Spending':<20} {'# Contracts':<15} {'Avg Contract':<20} {'YoY Growth':<15}\n"
                output += "-" * 140 + "\n"

                prev_total = None
                for fy in sorted(years_dict.keys()):
                    fy_data = years_dict[fy]
                    total = fy_data["total"]
                    count = fy_data["count"]
                    avg = total / count if count > 0 else 0

                    # Calculate YoY growth
                    if prev_total is not None and prev_total > 0:
                        yoy_growth = ((total - prev_total) / prev_total) * 100
                        yoy_str = f"+{yoy_growth:.1f}%" if yoy_growth >= 0 else f"{yoy_growth:.1f}%"
                    else:
                        yoy_str = "—"

                    output += f"FY{fy:<13} {format_currency(total):<20} {count:<15} {format_currency(avg):<20} {yoy_str:<15}\n"
                    prev_total = total

                # Summary for this NAICS
                total_all_years = data["total"]
                total_contracts = sum(fy["count"] for fy in years_dict.values())
                avg_per_year = total_all_years / len(years_dict) if years_dict else 0

                output += f"\n  Summary: {format_currency(total_all_years)} total across {total_contracts:,} contracts\n"
                output += f"  Average per year: {format_currency(avg_per_year)}\n\n"

            output += "=" * 140 + "\n"
            return output

        except Exception as e:
            logger.error(f"Error in get_naics_trends: {str(e)}")
            return f"Error analyzing NAICS trends: {str(e)}"


    # ==================== TIER 1: HIGH-IMPACT ENDPOINTS ====================




    logger_instance.info("Classification tools registered successfully")
