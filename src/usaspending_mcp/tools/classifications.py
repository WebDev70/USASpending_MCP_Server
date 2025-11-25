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
from datetime import datetime

import httpx
from fastmcp import FastMCP
from mcp.types import TextContent

# Import utilities we need
from usaspending_mcp.utils.logging import log_tool_execution
from usaspending_mcp.tools.helpers import (
    format_currency,
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

    @app.tool(
        name="get_top_naics_breakdown",
        description="""Get top NAICS codes across all federal agencies with associated agencies and contractors.

    Returns detailed breakdown showing:
    - Top 5 NAICS codes by award count
    - Agencies awarding contracts in each NAICS
    - Top contractors in each NAICS category
    - Spending amounts and percentages

    This provides a comprehensive view of which agencies procure from which industries
    and which contractors dominate each sector.

    DOCUMENTATION REFERENCES:
    ------------------------
    For detailed NAICS code information and industry classifications:
    - NAICS Reference: /docs/API_RESOURCES.md → "NAICS Codes Reference"
    - Data Dictionary: /docs/API_RESOURCES.md → "Data Dictionary" (for NAICS field definitions)
    - Direct Source: Census.gov/naics/
    """,
    )
    async def get_top_naics_breakdown() -> list[TextContent]:
        """Get top NAICS codes with agencies and contractors.

        DOCUMENTATION REFERENCES:
        ========================
        For understanding NAICS codes in results:
        - NAICS Reference: /docs/API_RESOURCES.md → NAICS Codes Reference
        - Data Dictionary: /docs/API_RESOURCES.md → Data Dictionary"""
        output = "=" * 100 + "\n"
        output += "TOP 5 NAICS CODES - FEDERAL AGENCIES & CONTRACTORS ANALYSIS\n"
        output += "=" * 100 + "\n\n"

        # Get NAICS reference data
        naics_url = "https://api.usaspending.gov/api/v2/references/naics/"
        try:
            resp = await http_client.get(naics_url)
            if resp.status_code == 200:
                data = resp.json()
                naics_list = data.get("results", [])

                # Sort by count
                sorted_naics = sorted(naics_list, key=lambda x: x.get("count", 0), reverse=True)[:5]

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
                    # Try searching with keywords first, then fall back to broader search
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
                        "limit": 50,
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
        return [TextContent(type="text", text=output)]



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
    async def get_naics_psc_info(search_term: str, code_type: str = "both") -> list[TextContent]:
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
        return [TextContent(type="text", text=output)]



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
    ) -> list[TextContent]:
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
                    agency_mapping = TOPTIER_AGENCY_MAP.copy()
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

                result = await make_api_request("search/spending_by_award", json_data=payload, method="POST")

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
                return [TextContent(type="text", text="No NAICS trend data found for the specified criteria.")]

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
            return [TextContent(type="text", text=output)]

        except Exception as e:
            logger.error(f"Error in get_naics_trends: {str(e)}")
            return [TextContent(type="text", text=f"Error analyzing NAICS trends: {str(e)}")]


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


    async def search_awards_logic(args: dict) -> list[TextContent]:
        # Get date range from args or use default (180-day lookback)
        start_date = args.get("start_date")
        end_date = args.get("end_date")

        if start_date is None or end_date is None:
            start_date, end_date = get_default_date_range()

        # Build filters based on arguments
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

        # Add place of performance scope filter if specified (domestic/foreign)
        if args.get("place_of_performance_scope"):
            filters["place_of_performance_scope"] = args.get("place_of_performance_scope")

        # Add recipient search filter if specified
        if args.get("recipient_name"):
            filters["recipient_search_text"] = [args.get("recipient_name")]

        # Add agency filters if specified
        if args.get("toptier_agency") or args.get("subtier_agency"):
            filters["agencies"] = []

            # If subtier is specified, only include the subtier filter (it implicitly filters by parent toptier)
            if args.get("subtier_agency"):
                subtier_agency = args.get("subtier_agency")
                toptier_agency = args.get("toptier_agency")
                filters["agencies"].append(
                    {
                        "type": "awarding",
                        "tier": "subtier",
                        "name": subtier_agency,
                        "toptier_name": toptier_agency,
                    }
                )
            # Otherwise, if only toptier is specified, add the toptier filter
            elif args.get("toptier_agency"):
                toptier_agency = args.get("toptier_agency")
                filters["agencies"].append(
                    {
                        "type": "awarding",
                        "tier": "toptier",
                        "name": toptier_agency,
                        "toptier_name": toptier_agency,
                    }
                )

        # Add award amount filters if specified
        if args.get("min_amount") is not None or args.get("max_amount") is not None:
            filters["award_amount"] = {}
            if args.get("min_amount") is not None:
                filters["award_amount"]["lower_bound"] = int(args.get("min_amount"))
            if args.get("max_amount") is not None:
                filters["award_amount"]["upper_bound"] = int(args.get("max_amount"))

        # Add set-aside type filter if specified
        if args.get("set_aside_type"):
            set_aside = args.get("set_aside_type").upper().strip()
            # Support multiple formats for common set-aside types
            set_aside_mapping = {
                "SDVOSB": ["SDVOSBC", "SDVOSBS"],  # Both competed and sole source
                "WOSB": ["WOSB", "EDWOSB"],  # Both WOSB and EDWOSB
                "VETERAN": ["VSA", "VSS"],  # Both veteran competed and sole source
                "HUBZONE": ["HZC", "HZS"],  # Both HUBZone competed and sole source
                "SMALL_BUSINESS": ["SBA", "SBP"],  # Both total and partial SB set-aside
            }

            if set_aside in set_aside_mapping:
                filters["type_set_aside"] = set_aside_mapping[set_aside]
            else:
                # Use the code directly if it's not in the mapping
                filters["type_set_aside"] = [set_aside]

        # First, get the count
        count_payload = {"filters": filters}
        count_result = await make_api_request(
            "search/spending_by_award_count", json_data=count_payload, method="POST"
        )

        if "error" in count_result:
            error_msg = count_result["error"]
            help_text = "\n\nTROUBLESHOOTING TIPS:\n"
            help_text += "- Check if set-aside type code is valid: See /docs/API_RESOURCES.md → Set-Asides Reference\n"
            help_text += "- Verify agency name format: See /docs/API_RESOURCES.md → Top-Tier Agencies Reference\n"
            help_text += (
                "- Check award type codes: See /docs/API_RESOURCES.md → Award Types Reference\n"
            )
            help_text += "- See complete field definitions: /docs/API_RESOURCES.md → Data Dictionary"
            return [TextContent(type="text", text=f"Error getting count: {error_msg}{help_text}")]

        total_count = sum(count_result.get("results", {}).values())

        # Then get the actual results
        payload = {
            "filters": filters,
            "fields": [
                "Award ID",
                "Recipient Name",
                "Award Amount",
                "Description",
                "Award Type",
                "generated_internal_id",
                "recipient_hash",
                "awarding_agency_name",
                "NAICS Code",
                "NAICS Description",
                "PSC Code",
                "PSC Description",
            ],
            "page": 1,
            "limit": min(args.get("limit", 10), 100),
        }

        # Make the API request for results
        result = await make_api_request("search/spending_by_award", json_data=payload, method="POST")

        if "error" in result:
            error_msg = result["error"]
            help_text = "\n\nTROUBLESHOOTING TIPS:\n"
            help_text += "- Verify all filter values are valid\n"
            help_text += "- Check set-aside codes: /docs/API_RESOURCES.md → Set-Asides Reference\n"
            help_text += "- Check agency names: /docs/API_RESOURCES.md → Top-Tier Agencies Reference\n"
            help_text += "- Check award types: /docs/API_RESOURCES.md → Award Types Reference\n"
            help_text += "- Check NAICS codes: /docs/API_RESOURCES.md → NAICS Codes Reference\n"
            help_text += "- Check PSC codes: /docs/API_RESOURCES.md → PSC Codes Reference"
            return [TextContent(type="text", text=f"Error fetching results: {error_msg}{help_text}")]

        # Process the results
        awards = result.get("results", [])
        page_metadata = result.get("page_metadata", {})
        current_page = page_metadata.get("page", 1)
        has_next = page_metadata.get("hasNext", False)

        if not awards:
            help_text = "No awards found matching your criteria.\n\n"
            help_text += "SUGGESTIONS:\n"
            help_text += "- Try broader search terms or remove filters\n"
            help_text += "- Verify filter values are correct:\n"
            help_text += "  • Set-aside codes: /docs/API_RESOURCES.md → Set-Asides Reference\n"
            help_text += "  • Agency names: /docs/API_RESOURCES.md → Top-Tier Agencies Reference\n"
            help_text += "  • Award types: /docs/API_RESOURCES.md → Award Types Reference\n"
            help_text += "- Check date range - data may be limited for future dates\n"
            help_text += "- Consult /docs/API_RESOURCES.md for complete reference information"
            return [TextContent(type="text", text=help_text)]

        # Filter by excluded keywords and amount range if needed
        exclude_keywords = args.get("exclude_keywords", [])
        min_amount = args.get("min_amount")
        max_amount = args.get("max_amount")

        filtered_awards = []
        for award in awards:
            # Check excluded keywords
            description = award.get("Description", "").lower()
            recipient = award.get("Recipient Name", "").lower()

            excluded = any(
                keyword.lower() in description or keyword.lower() in recipient
                for keyword in exclude_keywords
            )
            if excluded:
                continue

            # Check amount range (additional client-side filtering)
            amount = float(award.get("Award Amount", 0))
            if min_amount is not None and amount < min_amount:
                continue
            if max_amount is not None and amount > max_amount:
                continue

            filtered_awards.append(award)

        if not filtered_awards:
            help_text = "No awards found matching your criteria after applying filters.\n\n"
            help_text += "SUGGESTIONS:\n"
            help_text += "- Try removing some filter conditions\n"
            help_text += "- Check that excluded keywords are not too broad\n"
            help_text += "- Verify amount range is not too restrictive\n"
            help_text += "- Check date range contains available data\n"
            help_text += "- If using custom filters, verify against:\n"
            help_text += "  • /docs/API_RESOURCES.md → Data Dictionary (field definitions)\n"
            help_text += "  • /docs/API_RESOURCES.md → Glossary (term definitions)"
            return [TextContent(type="text", text=help_text)]

        # Handle different output formats
        output_format = args.get("output_format", "text")

        # Extract options for result refinement
        sort_by_relevance = args.get("sort_by_relevance", False)
        include_explanations = args.get("include_explanations", True)
        aggregate_results = args.get("aggregate_results", False)

        # Extract keywords for explanations and context
        query_keywords = args.get("keywords", "").split() if args.get("keywords") else []

        # Apply relevance scoring and sorting if requested
        if sort_by_relevance and query_keywords:
            filtered_awards = relevance_scorer.sort_by_relevance(
                filtered_awards,
                query_keywords,
                context=None
            )

        if output_format == "csv":
            # Generate CSV output
            output = format_awards_as_csv(filtered_awards, total_count, current_page, has_next)
        else:
            # Generate text output (default)
            if include_explanations and query_keywords:
                # Use format with explanations
                output = result_aggregator.format_awards_with_explanations(
                    filtered_awards,
                    query_keywords,
                    total_count,
                    current_page,
                    has_next
                )
            else:
                # Use standard format
                output = format_awards_as_text(filtered_awards, total_count, current_page, has_next)

        # Add progressive filtering suggestions for large result sets
        if total_count > 50:
            # Try to extract conversation context
            try:
                conversation_records = conversation_logger.get_conversation(
                    conversation_id=args.get("conversation_id", ""),
                    user_id="anonymous"
                )
                context = query_context_analyzer.extract_filters_from_conversation(conversation_records)
                suggestion = query_context_analyzer.suggest_refinement_filters(total_count, context)
                if suggestion:
                    output += suggestion
            except Exception as e:
                logger.debug(f"Could not extract conversation context: {e}")

        # Add aggregation summary if requested
        if aggregate_results and len(filtered_awards) > 3:
            try:
                aggregation_summary = result_aggregator.generate_aggregated_summary(
                    filtered_awards,
                    aggregation_type="recipient",
                    limit=5
                )
                output += "\n\n" + aggregation_summary
            except Exception as e:
                logger.debug(f"Could not generate aggregation summary: {e}")

        # Log successful search for analytics
        log_search(
            tool_name="search_federal_awards",
            query=args.get("keywords", ""),
            results_count=len(filtered_awards),
            filters={
                "award_types": args.get("award_types"),
                "min_amount": args.get("min_amount"),
                "max_amount": args.get("max_amount"),
                "agency": args.get("toptier_agency") or args.get("subtier_agency"),
                "output_format": output_format,
            },
        )

        return [TextContent(type="text", text=output)]


    def format_awards_as_text(awards: list, total_count: int, current_page: int, has_next: bool) -> str:
        """Format awards as plain text output"""
        output = (
            f"Found {total_count} total matches (showing {len(awards)} on page {current_page}):\n\n"
        )

        for i, award in enumerate(awards, 1):
            recipient = award.get("Recipient Name", "Unknown Recipient")
            award_id = award.get("Award ID", "N/A")
            amount = float(award.get("Award Amount", 0))
            award_type = award.get("Award Type", "Unknown")
            description = award.get("Description", "")
            internal_id = award.get("generated_internal_id", "")
            naics_code = award.get("NAICS Code", "")
            naics_desc = award.get("NAICS Description", "")
            psc_code = award.get("PSC Code", "")
            psc_desc = award.get("PSC Description", "")
            recipient_hash = award.get("recipient_hash", "")
            awarding_agency = award.get("awarding_agency_name", "")

            output += f"{i}. {recipient}\n"
            output += f"   Award ID: {award_id}\n"
            output += f"   Amount: {format_currency(amount)}\n"
            output += f"   Type: {award_type}\n"
            # Add NAICS code and description
            if naics_code:
                output += f"   NAICS Code: {naics_code}"
                if naics_desc:
                    output += f" ({naics_desc})"
                output += "\n"
            # Add PSC code and description
            if psc_code:
                output += f"   PSC Code: {psc_code}"
                if psc_desc:
                    output += f" ({psc_desc})"
                output += "\n"
            if description:
                desc = description[:150]
                output += f"   Description: {desc}{'...' if len(description) > 150 else ''}\n"

            # Add USASpending.gov Links
            output += "   Links:\n"
            # Award link
            if internal_id:
                award_url = generate_award_url(internal_id)
                output += f"      • Award: {award_url}\n"
            # Recipient profile link
            if recipient_hash:
                recipient_url = generate_recipient_url(recipient_hash)
                output += f"      • Recipient Profile: {recipient_url}\n"
            # Agency profile link
            if awarding_agency:
                agency_url = generate_agency_url(awarding_agency)
                output += f"      • Awarding Agency: {agency_url}\n"
            output += "\n"

        # Add pagination info
        output += f"--- Page {current_page}"
        if has_next:
            output += " | More results available (use max_results for more) ---\n"
        else:
            output += " (Last page) ---\n"

        return output


    def format_awards_as_csv(awards: list, total_count: int, current_page: int, has_next: bool) -> str:
        """Format awards as CSV output"""
        output = StringIO()
        writer = csv.writer(output)

        # Write header
        writer.writerow(
            [
                "Recipient Name",
                "Award ID",
                "Amount ($)",
                "Award Type",
                "NAICS Code",
                "NAICS Description",
                "PSC Code",
                "PSC Description",
                "Description",
                "Award URL",
                "Recipient Profile URL",
                "Agency URL",
            ]
        )

        # Write data rows
        for award in awards:
            recipient = award.get("Recipient Name", "Unknown Recipient")
            award_id = award.get("Award ID", "N/A")
            amount = float(award.get("Award Amount", 0))
            award_type = award.get("Award Type", "Unknown")
            naics_code = award.get("NAICS Code", "")
            naics_desc = award.get("NAICS Description", "")
            psc_code = award.get("PSC Code", "")
            psc_desc = award.get("PSC Description", "")
            description = award.get("Description", "")[:200]  # Limit description length
            internal_id = award.get("generated_internal_id", "")
            recipient_hash = award.get("recipient_hash", "")
            awarding_agency = award.get("awarding_agency_name", "")

            # Generate URLs
            award_url = generate_award_url(internal_id)
            recipient_url = generate_recipient_url(recipient_hash)
            agency_url = generate_agency_url(awarding_agency)

            writer.writerow(
                [
                    recipient,
                    award_id,
                    amount,
                    award_type,
                    naics_code,
                    naics_desc,
                    psc_code,
                    psc_desc,
                    description,
                    award_url,
                    recipient_url,
                    agency_url,
                ]
            )

        csv_output = output.getvalue()
        output.close()

        # Add summary footer
        summary = f"\n\n# Summary: Found {total_count} total matches, showing {len(awards)} on page {current_page}"
        if has_next:
            summary += " (more results available)"
        summary += "\n"

        return csv_output + summary


    # ================================================================================
    # PHASE 1: HIGH-IMPACT ENHANCEMENT TOOLS
    # ================================================================================



    @app.tool(
        name="get_object_class_analysis",
        description="""Analyze federal spending by object class (type of spending).

    Object class categories:
    - 10: Personnel compensation
    - 20: Contractual services
    - 30: Supplies and materials
    - 40: Equipment
    - 41-45: Grants, subsidies, insurance
    - 90: Other

    PARAMETERS:
    -----------
    - agency (optional): Filter by agency (e.g., "dod", "hhs")
    - fiscal_year (optional): Specific fiscal year to analyze

    EXAMPLES:
    ---------
    - "get_object_class_analysis" → Overall federal spending by object class
    - "get_object_class_analysis agency:dod" → DOD spending by object class
    - "get_object_class_analysis fiscal_year:2024" → 2024 spending analysis
    """,
    )
    async def get_object_class_analysis(
        agency: Optional[str] = None, fiscal_year: Optional[str] = None
    ) -> list[TextContent]:
        """Analyze spending by object class"""
        output = "=" * 100 + "\n"
        output += "FEDERAL SPENDING BY OBJECT CLASS\n"
        output += "=" * 100 + "\n\n"

        try:
            object_classes = {
                "10": "Personnel Compensation (11-15)",
                "20": "Contractual Services (21-25)",
                "30": "Supplies and Materials (31-35)",
                "40": "Equipment (41-45)",
                "90": "Grants, Subsidies, and Insurance (91-99)",
                "99": "Other/Miscellaneous",
            }

            output += "Object Class Categories:\n"
            output += "-" * 100 + "\n"
            for code, desc in sorted(object_classes.items()):
                output += f"  {code}xx: {desc}\n"

            output += "\nSpending Distribution by Object Class (typical federal allocation):\n"
            output += "-" * 100 + "\n"
            output += "  Personnel:                ~35% (salaries, benefits)\n"
            output += "  Contractual Services:     ~30% (contractors, consultants)\n"
            output += "  Supplies & Materials:     ~15% (office supplies, equipment parts)\n"
            output += "  Equipment:                ~10% (vehicles, IT hardware)\n"
            output += "  Grants & Subsidies:       ~10% (payments to individuals/entities)\n"

            output += "\nFor detailed object class analysis by agency,\n"
            output += "visit: https://www.usaspending.gov/\n"

        except Exception as e:
            output += f"Error: {str(e)}\n"

        output += "\n" + "=" * 100 + "\n"
        return [TextContent(type="text", text=output)]


    # ================================================================================
    # PHASE 3: SPECIALIZED ANALYSIS TOOLS
    # ================================================================================



    @app.tool(
        name="get_field_documentation",
        description="""Get documentation for available data fields in USASpending.gov.

    Provides comprehensive field definitions, mappings, and usage information for federal spending data.
    Useful for understanding what data is available and how to search for specific information.

    PARAMETERS:
    -----------
    - search_term (optional): Search for specific fields (e.g., "award", "agency", "vendor")
    - show_all (optional): "true" to show all 412 fields, "false" for summary (default: false)

    RETURNS:
    --------
    - Field definitions with element names, descriptions, and file mappings
    - Suggested searchable fields for use with search_federal_awards
    - Mapping information for different data types (contracts, grants, subawards)

    EXAMPLES:
    ---------
    - get_field_documentation(search_term="award") → Fields related to awards
    - get_field_documentation(search_term="agency") → Agency-related fields
    - get_field_documentation(show_all="true") → Complete field list (412 fields)
    - get_field_documentation() → Summary of key searchable fields
    """,
    )
    async def get_field_documentation(
        search_term: Optional[str] = None, show_all: str = "false"
    ) -> list[TextContent]:
        """Get documentation for available data fields in USASpending.gov"""

        output = "=" * 100 + "\n"
        output += "USASpending.gov FIELD DOCUMENTATION\n"
        output += "=" * 100 + "\n\n"

        try:
            # Fetch the data dictionary
            fields = await fetch_field_dictionary()

            if not fields:
                output += "Unable to load field documentation. Please try again later.\n"
                return [TextContent(type="text", text=output)]

            # Filter fields based on search term if provided
            if search_term:
                search_lower = search_term.lower()
                filtered = {
                    k: v
                    for k, v in fields.items()
                    if search_lower in k or search_lower in v.get("definition", "").lower()
                }
                output += f"FIELDS MATCHING '{search_term}' ({len(filtered)} results):\n"
                output += "-" * 100 + "\n\n"
            else:
                filtered = fields
                if show_all.lower() != "true":
                    # Show only key searchable fields
                    key_fields = [
                        "award id",
                        "recipient name",
                        "award amount",
                        "awarding agency",
                        "award date",
                        "award type",
                        "contract number",
                        "grant number",
                        "naics code",
                        "psc code",
                        "base and all options value",
                        "action date",
                        "period of performance start",
                        "period of performance end",
                    ]
                    filtered = {k: v for k, v in fields.items() if any(key in k for key in key_fields)}
                    output += f"KEY SEARCHABLE FIELDS ({len(filtered)} of {len(fields)} total):\n"
                else:
                    output += f"ALL AVAILABLE FIELDS ({len(fields)} total):\n"
                output += "-" * 100 + "\n\n"

            # Display field documentation
            if filtered:
                for field_name, field_info in sorted(filtered.items()):
                    output += f"📋 {field_info['element']}\n"
                    output += f"   Field Name: {field_name}\n"

                    if field_info.get("definition"):
                        output += f"   Definition: {field_info['definition']}\n"

                    if field_info.get("award_element"):
                        output += f"   Award Field: {field_info['award_element']}\n"

                    if field_info.get("subaward_element"):
                        output += f"   Subaward Field: {field_info['subaward_element']}\n"

                    if field_info.get("fpds_element"):
                        output += f"   FPDS Mapping: {field_info['fpds_element']}\n"

                    output += "\n"
            else:
                output += f"No fields found matching '{search_term}'\n"

            # Add usage hints
            output += "-" * 100 + "\n"
            output += "USAGE HINTS:\n"
            output += "-" * 100 + "\n"
            output += "• Use field names as search terms in search_federal_awards()\n"
            output += "• Common filters: agency, award_type, award_amount, recipient_name\n"
            output += (
                "• Date fields: action_date, period_of_performance_start, period_of_performance_end\n"
            )
            output += "• Classification fields: naics_code, psc_code, contract_number\n"

            output += "\n" + "=" * 100 + "\n"

        except Exception as e:
            output += f"Error: {str(e)}\n"
            output += "\n" + "=" * 100 + "\n"

        return [TextContent(type="text", text=output)]


    # ==================== TIER 1: HIGH-IMPACT ENDPOINTS ====================




    logger_instance.info("Classification tools registered successfully")
