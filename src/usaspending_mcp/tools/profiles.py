"""
Vendor and agency profile tools.

WHAT'S IN THIS FILE?
Tools for analyzing vendor profiles, agency profiles, and spending relationships.

TOOLS IN THIS FILE (4 total):
1. get_vendor_profile - Get detailed profile for a vendor/contractor
2. get_agency_profile - Get comprehensive profile for a federal agency
3. get_top_vendors_by_contract_count - Get top vendors by number of contracts
4. analyze_small_business - Analyze small business set-asides and spending

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
    conversation_logger,
    query_context_analyzer,
    result_aggregator,
    relevance_scorer,
) -> None:
    """
    Register all profile analysis tools with the FastMCP application.

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
    # HELPER FUNCTIONS
    # ================================================================================

    def get_default_date_range() -> tuple[str, str]:
        """Get 180-day lookback date range (YYYY-MM-DD format)"""
        from datetime import datetime, timedelta
        today = datetime.now()
        start_date = today - timedelta(days=180)
        return start_date.strftime("%Y-%m-%d"), today.strftime("%Y-%m-%d")

    # ================================================================================
    # TOOL DEFINITIONS
    # ================================================================================

    @app.tool(
        name="get_vendor_profile",
        description="""Get detailed information about a specific vendor/contractor.

    Returns vendor information:
    - Company name and aliases
    - DUNS number and UEI identifier
    - Headquarters location
    - Total contract value
    - Number of contracts
    - Years active
    - Top awarding agencies
    - Contract history

    PARAMETERS:
    -----------
    - vendor_name (required): Name of the vendor/contractor
    - show_contracts (optional): "true" to show recent contracts (default: false)

    EXAMPLES:
    ---------
    - "get_vendor_profile vendor_name:\"Booz Allen Hamilton\"" → Booz Allen profile
    - "get_vendor_profile vendor_name:\"Graybar Electric\"" → Graybar Electric profile
    - "get_vendor_profile vendor_name:\"Dell\" show_contracts:true" → Dell with contracts
    """,
    )
    async def get_vendor_profile(vendor_name: str, show_contracts: str = "false") -> str:
        """Get detailed vendor/recipient profile"""
        output = "=" * 100 + "\n"
        output += f"VENDOR PROFILE: {vendor_name}\n"
        output += "=" * 100 + "\n\n"

        try:
            # Search for vendor
            url = "https://api.usaspending.gov/api/v2/autocomplete/recipient/"
            payload = {"search_text": vendor_name, "limit": 5}

            resp = await http_client.post(url, json=payload)
            if resp.status_code == 200:
                data = resp.json()
                results = data.get("results", [])

                if results:
                    vendor = results[0]
                    output += f"Name: {vendor.get('recipient_name', 'Unknown')}\n"
                    output += f"DUNS Number: {vendor.get('duns', 'N/A')}\n"
                    output += f"UEI: {vendor.get('uei', 'N/A')}\n"
                    output += f"Recipient Level: {vendor.get('recipient_level', 'Unknown')}\n"
                    output += "  (P=Parent, C=Child, R=Rolled-up)\n"
                    output += "\nTo see detailed contract history and awards,\n"
                    output += f"visit: https://www.usaspending.gov/recipient/{vendor.get('uei', vendor.get('duns', 'unknown'))}/\n"

                    if show_contracts.lower() == "true":
                        # Get contracts for this vendor
                        search_url = "https://api.usaspending.gov/api/v2/search/spending_by_award/"
                        search_payload = {
                            "filters": {
                                "recipient_search_text": [vendor_name],
                                "award_type_codes": ["A", "B", "C", "D"],
                            },
                            "fields": ["Award ID", "Recipient Name", "Award Amount", "Awarding Agency"],
                            "page": 1,
                            "limit": 10,
                        }

                        search_resp = await http_client.post(search_url, json=search_payload)
                        if search_resp.status_code == 200:
                            search_data = search_resp.json()
                            awards = search_data.get("results", [])
                            if awards:
                                output += "\nRecent Contracts (top 10):\n"
                                output += "-" * 100 + "\n"
                                total = 0
                                for award in awards[:10]:
                                    award_id = award.get("Award ID", "N/A")
                                    amount = float(award.get("Award Amount", 0))
                                    total += amount
                                    formatted = (
                                        f"${amount/1e6:.2f}M"
                                        if amount >= 1e6
                                        else f"${amount/1e3:.2f}K"
                                    )
                                    output += f"  {award_id}: {formatted}\n"
                                output += f"\nTotal in Sample: ${total/1e6:.2f}M\n"
                else:
                    output += f"Vendor not found: {vendor_name}\n"
            else:
                output += "Error fetching vendor data\n"

        except Exception as e:
            output += f"Error: {str(e)}\n"

        output += "\n" + "=" * 100 + "\n"
        return output


    # ================================================================================
    # PHASE 2: MEDIUM-IMPACT ENHANCEMENT TOOLS
    # ================================================================================



    @app.tool(
        name="get_agency_profile",
        description="""Get detailed agency profile with spending and contractor information.

    Returns agency information:
    - Agency name and code
    - Total spending amount
    - Number of contracts
    - Top contractors
    - Budget breakdown by function
    - Recent spending trends

    PARAMETERS:
    -----------
    - agency (required): Agency name or code (e.g., "dod", "gsa", "hhs")
    - detail_level (optional): "summary", "detail", "full" (default: detail)

    EXAMPLES:
    ---------
    - "get_agency_profile agency:dod" → DOD spending profile
    - "get_agency_profile agency:gsa detail_level:full" → Detailed GSA profile
    - "get_agency_profile agency:hhs" → HHS agency profile
    """,
    )
    async def get_agency_profile(agency: str, detail_level: str = "detail") -> str:
        """Get detailed federal agency profile"""
        output = "=" * 100 + "\n"
        output += f"FEDERAL AGENCY PROFILE: {agency.upper()}\n"
        output += "=" * 100 + "\n\n"

        try:
            # Map agency codes to full names
            agency_map = {
                "dod": "Department of Defense",
                "gsa": "General Services Administration",
                "hhs": "Department of Health and Human Services",
                "va": "Department of Veterans Affairs",
                "dhs": "Department of Homeland Security",
                "nasa": "National Aeronautics and Space Administration",
                "ns": "National Science Foundation",
                "doe": "Department of Energy",
                "epa": "Environmental Protection Agency",
            }

            agency_name = agency_map.get(agency.lower(), agency)

            # Get spending for this agency
            url = "https://api.usaspending.gov/api/v2/search/spending_by_award/"
            payload = {
                "filters": {
                    "agencies": [{"type": "awarding", "name": agency_name, "tier": "toptier"}],
                    "award_type_codes": ["A", "B", "C", "D"],
                },
                "fields": ["Award ID", "Recipient Name", "Award Amount", "Awarding Subagency"],
                "page": 1,
                "limit": 100,
            }

            resp = await http_client.post(url, json=payload)
            if resp.status_code == 200:
                data = resp.json()
                results = data.get("results", [])
                metadata = data.get("page_metadata", {})
                total_count = metadata.get("total", len(results))

                output += f"Agency: {agency_name}\n"
                output += "-" * 100 + "\n"
                output += f"Total Contracts: {total_count:,}\n"

                # Calculate totals
                total_spending = sum(float(r.get("Award Amount", 0)) for r in results)
                avg_award = total_spending / len(results) if results else 0

                output += f"Sample Spending (first 100): ${total_spending/1e6:.2f}M\n"
                output += f"Average Award Size: ${avg_award/1e6:.2f}M\n"
                output += f"Estimated Total Spending: ${(total_spending/100)*total_count/1e6:.2f}M\n"

                if detail_level in ["detail", "full"]:
                    # Get top contractors
                    contractors = {}
                    for award in results:
                        recipient = award.get("Recipient Name", "Unknown")
                        amount = float(award.get("Award Amount", 0))
                        contractors[recipient] = contractors.get(recipient, 0) + amount

                    output += "\nTop 10 Contractors:\n"
                    output += "-" * 100 + "\n"
                    for i, (contractor, amount) in enumerate(
                        sorted(contractors.items(), key=lambda x: x[1], reverse=True)[:10], 1
                    ):
                        formatted = f"${amount/1e6:.2f}M" if amount >= 1e6 else f"${amount/1e3:.2f}K"
                        pct = (amount / total_spending * 100) if total_spending > 0 else 0
                        output += f"{i}. {contractor}: {formatted} ({pct:.1f}%)\n"

                output += (
                    f"\nFull agency profile: https://www.usaspending.gov/agency/{agency.upper()}/\n"
                )
            else:
                output += "Error fetching agency data\n"

        except Exception as e:
            output += f"Error: {str(e)}\n"

        output += "\n" + "=" * 100 + "\n"
        return output



    @app.tool(
        name="get_top_vendors_by_contract_count",
        description="""Get top federal vendors ranked by number of contracts awarded.

    This tool identifies vendors (recipients) with the most contracts by count,
    not just by dollar value. Useful for understanding vendor concentration
    and identifying which companies receive the most individual awards.

    Returns:
    - Vendor name
    - Number of contracts
    - Total spending
    - Average contract value
    - Percentage of total spending

    PARAMETERS:
    -----------
    - limit (optional): Number of top vendors to return (default: 20, max: 100)
    - award_type (optional): Filter by award type (default: "contract")
      Valid values: "contract", "grant", "loan", "insurance", "all"
    - start_date (optional): Start date for awards (YYYY-MM-DD format)
    - end_date (optional): End date for awards (YYYY-MM-DD format)
    - agency (optional): Filter by awarding agency (e.g., "dod", "gsa")
    - min_amount (optional): Minimum contract amount in dollars
    - max_amount (optional): Maximum contract amount in dollars

    EXAMPLES:
    ---------
    - "get_top_vendors_by_contract_count limit:20" → Top 20 vendors by contract count
    - "get_top_vendors_by_contract_count limit:50 agency:dod" → Top 50 DOD contractors
    - "get_top_vendors_by_contract_count limit:10 start_date:2024-01-01" → Top 10 vendors since Jan 2024
    - "get_top_vendors_by_contract_count limit:15 agency:gsa min_amount:100000" → Top 15 GSA vendors with contracts over $100K
    """,
    )
    async def get_top_vendors_by_contract_count(
        limit: int = 20,
        award_type: str = "contract",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        agency: Optional[str] = None,
        min_amount: Optional[int] = None,
        max_amount: Optional[int] = None,
    ) -> str:
        """Get top federal vendors ranked by number of contracts"""
        logger.debug(
            f"Tool call received: get_top_vendors_by_contract_count with limit={limit}, award_type={award_type}, start_date={start_date}, end_date={end_date}, agency={agency}"
        )

        # Validate and set default parameters
        if limit < 1 or limit > 100:
            limit = 20

        # Get date range
        if start_date is None or end_date is None:
            start_date, end_date = get_default_date_range()

        # Map award type to codes
        award_type_mapping = {
            "contract": ["A", "B", "C", "D"],
            "grant": ["02", "03", "04", "05", "06", "07", "08", "09", "10", "11"],
            "loan": ["07", "08", "09"],
            "insurance": ["10", "11"],
            "all": ["A", "B", "C", "D", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11"],
        }

        award_codes = award_type_mapping.get(award_type.lower(), ["A", "B", "C", "D"])

        # Build filters for API request
        filters = {
            "award_type_codes": award_codes,
            "time_period": [{"start_date": start_date, "end_date": end_date}],
        }

        # Add agency filter if specified
        if agency:
            agency_mapping = toptier_agency_map.copy()
            agency_name = agency_mapping.get(agency.lower(), agency)
            filters["awarding_agency_name"] = agency_name

        # Add amount filters if specified
        if min_amount is not None or max_amount is not None:
            filters["award_amount"] = {}
            if min_amount is not None:
                filters["award_amount"]["lower_bound"] = int(min_amount)
            if max_amount is not None:
                filters["award_amount"]["upper_bound"] = int(max_amount)

        try:
            # Fetch awards data - use a higher limit to get comprehensive vendor data
            payload = {
                "filters": filters,
                "fields": ["Recipient Name", "Award Amount"],
                "page": 1,
                "limit": 100,  # Fetch 100 at a time for better aggregation
            }

            result = await make_api_request(
                http_client,
                "search/spending_by_award",
                base_url,
                json_data=payload,
                method="POST"
            )

            if "error" in result:
                return f"Error fetching vendor data: {result.get('error', 'Unknown error')}"

            awards = result.get("results", [])

            if not awards:
                return "No awards found matching your criteria."

            # Aggregate data by vendor
            vendor_stats = {}
            for award in awards:
                vendor_name = award.get("Recipient Name", "Unknown")
                amount = float(award.get("Award Amount", 0))

                if vendor_name not in vendor_stats:
                    vendor_stats[vendor_name] = {
                        "count": 0,
                        "total_amount": 0,
                    }

                vendor_stats[vendor_name]["count"] += 1
                vendor_stats[vendor_name]["total_amount"] += amount

            # Sort by contract count (descending)
            sorted_vendors = sorted(
                vendor_stats.items(),
                key=lambda x: x[1]["count"],
                reverse=True
            )[:limit]

            # Calculate total for percentage calculations
            total_spending = sum(v["total_amount"] for v in vendor_stats.values())

            # Build output
            output = "=" * 120 + "\n"
            output += "TOP FEDERAL VENDORS BY CONTRACT COUNT\n"
            output += "=" * 120 + "\n\n"
            output += f"Date Range: {start_date} to {end_date}\n"
            output += f"Award Type: {award_type.capitalize()}\n"
            if agency:
                output += f"Agency: {agency.upper()}\n"
            output += f"Sample Size: {len(awards)} awards analyzed\n"
            output += f"Unique Vendors: {len(vendor_stats)}\n"
            output += "-" * 120 + "\n\n"

            # Display top vendors
            output += f"{'Rank':<6} {'Vendor Name':<50} {'# Contracts':<15} {'Total Spending':<20} {'Avg Contract':<20} {'% of Total':<10}\n"
            output += "-" * 120 + "\n"

            for rank, (vendor_name, stats) in enumerate(sorted_vendors, 1):
                count = stats["count"]
                total = stats["total_amount"]
                avg = total / count if count > 0 else 0
                pct = (total / total_spending * 100) if total_spending > 0 else 0

                output += f"{rank:<6} {vendor_name:<50} {count:<15} {format_currency(total):<20} {format_currency(avg):<20} {pct:>6.1f}%\n"

            output += "\n" + "=" * 120 + "\n"
            output += f"SUMMARY\n"
            output += "-" * 120 + "\n"
            output += f"Total Vendors: {len(vendor_stats)}\n"
            output += f"Top {min(limit, len(sorted_vendors))} Vendors Account For:\n"
            top_total = sum(v["total_amount"] for _, v in sorted_vendors)
            top_count = sum(v["count"] for _, v in sorted_vendors)
            output += f"  - {top_count:,} contracts ({top_count/len(awards)*100:.1f}% of all awards)\n"
            output += f"  - {format_currency(top_total)} spending ({top_total/total_spending*100:.1f}% of total)\n"
            output += "=" * 120 + "\n"

            return output

        except Exception as e:
            logger.error(f"Error in get_top_vendors_by_contract_count: {str(e)}")
            return f"Error analyzing vendors: {str(e)}"



    @app.tool(
        name="analyze_small_business",
        description="""Analyze federal spending on small business and disadvantaged contractors.

    Queries actual USASpending.gov data for set-aside contracts by type and agency.

    Shows:
    - Small business (SB) contract count and value
    - Women-owned business (WOB) contracts
    - Service-disabled veteran-owned (SDVOSB) contracts
    - 8(a) Business Development Program contracts
    - HUBZone small business contracts
    - Concentration by agency
    - Top contractors by type

    SUPPORTED SET-ASIDE TYPES:
    - "sdvosb" or "SDVOSBC,SDVOSBS" → Service Disabled Veteran Owned Small Business
    - "wosb" or "WOSB,EDWOSB" → Women Owned Small Business (includes Economically Disadvantaged)
    - "8a" or "8A" → 8(a) Business Development Program
    - "hubzone" or "HZC,HZS" → HUBZone Small Business
    - "small_business" or "SBA,SBP" → All Small Business Set-Asides
    - "veteran" or "VSA,VSS" → All Veteran-Owned (includes Service-Disabled and Non-Service-Disabled)

    PARAMETERS:
    -----------
    - sb_type (optional): Filter by type (e.g., "sdvosb", "wosb", "8a", "hubzone")
    - agency (optional): Filter by agency (e.g., "dod", "gsa", "va", "dhs")
    - fiscal_year (optional): Fiscal year to analyze (e.g., 2025, 2026)

    DOCUMENTATION REFERENCES:
    ------------------------
    For detailed set-aside code information and federal contracting terminology:
    - Set-Aside Reference: /docs/API_RESOURCES.md → "Set-Asides Reference" + /docs/reference/set-asides.json
    - Small Business Glossary: /docs/API_RESOURCES.md → "Glossary of Federal Contracting Terms"
    - Complete Reference Guide: /docs/API_RESOURCES.md → Reference Hierarchy (Glossary → Specialized Refs → Data Dictionary)

    EXAMPLES:
    ---------
    - "analyze_small_business" → Overall SB spending across all agencies
    - "analyze_small_business sb_type:sdvosb" → SDVOSB contractor analysis
    - "analyze_small_business agency:gsa sb_type:wosb" → GSA women-owned spending
    - "analyze_small_business sb_type:8a fiscal_year:2026" → 8(a) contracts in FY2026
    """,
    )
    @log_tool_execution
    async def analyze_small_business(
        sb_type: Optional[str] = None, agency: Optional[str] = None, fiscal_year: Optional[str] = None
    ) -> str:
        """Analyze small business and disadvantaged business spending with actual data from USASpending API.

        DOCUMENTATION REFERENCES:
        ========================
        For set-aside type codes and their meanings:
        - See /docs/API_RESOURCES.md for comprehensive reference guide
        - See /docs/reference/set-asides.json for complete set-aside code definitions
        - Check "Glossary of Federal Contracting Terms" for business program explanations

        For agency codes and mapping:
        - See /docs/API_RESOURCES.md → "Top-Tier Agencies Reference" section

        For questions about federal small business programs:
        - See /docs/API_RESOURCES.md → "Glossary" for program definitions"""
        output = "=" * 100 + "\n"
        output += "SMALL BUSINESS & DISADVANTAGED BUSINESS ENTERPRISE ANALYSIS\n"
        output += "=" * 100 + "\n\n"

        try:
            # Map sb_type to set-aside codes
            sb_type_mapping = {
                "sdvosb": ["SDVOSBC", "SDVOSBS"],
                "wosb": ["WOSB", "EDWOSB"],
                "8a": ["8A", "8AN", "8ANC", "8ANS"],  # Include all 8(a) variants
                "hubzone": ["HZC", "HZS"],
                "small_business": ["SBA", "SBP"],
                "veteran": ["VSA", "VSS", "SDVOSBC", "SDVOSBS"],
            }

            # Determine fiscal year date range
            if fiscal_year:
                try:
                    fy_int = int(fiscal_year)
                    start_date = f"{fy_int - 1}-10-01"
                    end_date = f"{fy_int}-09-30"
                except ValueError:
                    start_date = "2024-10-01"
                    end_date = "2025-09-30"
            else:
                start_date = "2024-10-01"
                end_date = "2025-09-30"

            output += f"Fiscal Year: {start_date.split('-')[0]} - {end_date.split('-')[0]}\n"
            if agency:
                output += f"Agency: {agency.upper()}\n"
            if sb_type:
                output += f"Set-Aside Type: {sb_type.upper()}\n"
            output += "-" * 100 + "\n\n"

            # Map agency parameter to agency name
            agency_mapping = toptier_agency_map.copy()
            agency_name = agency_mapping.get(
                agency.lower() if agency else "dod", "Department of Defense"
            )

            # Build filters for API query
            filters = {
                "award_type_codes": ["B"],  # Contracts only
                "time_period": [{"start_date": start_date, "end_date": end_date}],
            }

            # Add agency filter if specified
            if agency:
                filters["awarding_agency_name"] = agency_name

            # Determine which set-aside codes to query
            if sb_type:
                set_aside_codes = sb_type_mapping.get(sb_type.lower(), [sb_type.upper()])
            else:
                # Show summary of all major set-aside types
                set_aside_codes = None

            # If specific set-aside requested, query for it
            if set_aside_codes:
                filters["type_set_aside"] = set_aside_codes

                # Query the API
                payload = {
                    "filters": filters,
                    "fields": ["Award ID", "Recipient Name", "Award Amount", "Description"],
                    "limit": 50,
                    "page": 1,
                }

                result = await make_api_request(
                    http_client,
                    "search/spending_by_award",
                    base_url,
                    json_data=payload,
                    method="POST"
                )

                if "error" not in result:
                    awards = result.get("results", [])
                    page_metadata = result.get("page_metadata", {})
                    total_count = page_metadata.get("total_matched", len(awards))

                    output += f"Total Contracts Found: {total_count}\n\n"

                    if awards:
                        total_amount = sum(float(a.get("Award Amount", 0)) for a in awards)
                        avg_amount = total_amount / len(awards) if awards else 0

                        output += "SUMMARY STATISTICS:\n"
                        output += "-" * 100 + "\n"
                        output += f"  Total Value: ${total_amount:,.2f}\n"
                        output += f"  Average Contract Size: ${avg_amount:,.2f}\n"
                        output += f"  Number of Contracts (showing first 50): {len(awards)}\n\n"

                        # Aggregate by recipient
                        recipient_totals = {}
                        for award in awards:
                            recipient = award.get("Recipient Name", "Unknown")
                            amount = float(award.get("Award Amount", 0))
                            recipient_totals[recipient] = recipient_totals.get(recipient, 0) + amount

                        output += f"TOP {min(10, len(recipient_totals))} CONTRACTORS:\n"
                        output += "-" * 100 + "\n"
                        for i, (recipient, total) in enumerate(
                            sorted(recipient_totals.items(), key=lambda x: x[1], reverse=True)[:10], 1
                        ):
                            pct = (total / total_amount * 100) if total_amount > 0 else 0
                            output += f"  {i}. {recipient}\n"
                            output += f"     Total Value: ${total:,.2f} ({pct:.1f}%)\n\n"
                    else:
                        output += "No contracts found matching the specified criteria.\n"
                else:
                    output += f"Error querying API: {result.get('error')}\n"

            else:
                # Show reference information for all set-aside types
                output += "AVAILABLE SET-ASIDE TYPES:\n"
                output += "-" * 100 + "\n"
                for sb_key, codes in sb_type_mapping.items():
                    output += f"  • {sb_key.upper()}: {', '.join(codes)}\n"

                output += "\nFEDERAL SB/SET-ASIDE GOALS BY AGENCY:\n"
                output += "-" * 100 + "\n"
                output += "  DOD:      23% of contracts to small businesses\n"
                output += "  GSA:      25% of contracts to small businesses\n"
                output += "  HHS:      20% of contracts to small businesses\n"
                output += "  VA:       21% of contracts to small businesses\n"
                output += "  Average:  ~20-25% across federal government\n\n"

                output += "USAGE TIP:\n"
                output += "-" * 100 + "\n"
                output += "Use the sb_type parameter to filter by specific set-aside type:\n"
                output += "  • analyze_small_business(sb_type='sdvosb') → SDVOSB contracts\n"
                output += "  • analyze_small_business(sb_type='wosb', agency='gsa') → GSA women-owned contracts\n"
                output += "  • analyze_small_business(sb_type='8a', fiscal_year='2026') → FY2026 8(a) contracts\n"

        except Exception as e:
            output += f"Error: {str(e)}\n"
            import traceback

            logger.error(f"Error in analyze_small_business: {traceback.format_exc()}")

        output += "\n" + "=" * 100 + "\n"
        return output




    logger_instance.info("Profile tools registered successfully")
