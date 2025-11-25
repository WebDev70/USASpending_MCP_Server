"""
Award search and details tools.

WHAT'S IN THIS FILE?
This module contains tools for finding and retrieving federal awards.
These tools help users search for contracts, grants, loans, and other
federal spending by award ID, keyword, or recipient.

TOOLS IN THIS FILE (6 total):
1. get_award_by_id - Look up a specific award by Award ID
2. search_federal_awards - Advanced keyword search with filters
3. get_award_details - Get complete details about an award
4. get_subaward_data - Get subaward and subcontract information
5. get_recipient_details - Get all awards received by a vendor
6. get_vendor_by_uei - Search vendors by Unique Entity ID

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
    Register all award-related tools with the FastMCP application.

    WHY IS THIS A FUNCTION?
    Instead of decorators at module level (which won't work when the
    app and http_client are defined elsewhere), we use a registration
    function. This gives tools access to the objects they need.

    DEPENDENCY INJECTION:
    All the parameters (http_client, rate_limiter, etc.) are "injected"
    into this function. Each tool can use them through closure variables.

    HOW IT WORKS:
    1. server.py creates http_client, rate_limiter, app, etc.
    2. server.py calls register_tools(app, http_client, ...)
    3. This function defines all tool functions
    4. Each tool can access http_client, rate_limiter, etc.
       because they're in the surrounding scope

    PYTHON CONCEPT - CLOSURES:
    A closure is when an inner function (like get_award_by_id) can
    access variables from the outer function (like register_tools).
    This is how each tool gets access to http_client without it
    being passed as a parameter!

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
        name="get_award_by_id",
        description="""Get a specific federal award by its exact Award ID.

    This tool looks up a single award using its Award ID from USASpending.gov.

    PARAMETERS:
    - award_id: The Award ID (e.g., "47QSWA26P02KE", "W91QF425PA017")

    RETURNS:
    - Award ID
    - Recipient Name
    - Award Amount
    - Award Description
    - Award Type
    - Direct link to USASpending.gov award details

    EXAMPLES:
    - "47QSWA26P02KE" → Gets the Giga Inc Oshkosh truck part award
    - "W91QF425PA017" → Gets the James B Studdard moving services award
    """,
    )
    @log_tool_execution
    async def get_award_by_id(award_id: str) -> list[TextContent]:
        """Get a specific award by Award ID"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Search for the specific award ID
            payload = {
                "filters": {
                    "keywords": [award_id],
                    "award_type_codes": [
                        "A",
                        "B",
                        "C",
                        "D",
                        "02",
                        "03",
                        "04",
                        "05",
                        "07",
                        "08",
                        "09",
                        "10",
                        "11",
                    ],
                    "time_period": [{"start_date": "2020-01-01", "end_date": "2026-12-31"}],
                },
                "fields": [
                    "Award ID",
                    "Recipient Name",
                    "Award Amount",
                    "Description",
                    "Award Type",
                    "generated_internal_id",
                    "recipient_hash",
                    "awarding_agency_name",
                ],
                "page": 1,
                "limit": 1,
            }

            try:
                response = await client.post(
                    "https://api.usaspending.gov/api/v2/search/spending_by_award", json=payload
                )
                result = response.json()

                if "results" in result and len(result["results"]) > 0:
                    award = result["results"][0]
                    output = "Award Found!\n\n"
                    output += f"Award ID: {award.get('Award ID', 'N/A')}\n"
                    output += f"Recipient: {award.get('Recipient Name', 'N/A')}\n"
                    output += f"Amount: ${float(award.get('Award Amount', 0)):,.2f}\n"
                    output += f"Type: {award.get('Award Type', 'N/A')}\n"
                    output += f"Description: {award.get('Description', 'N/A')}\n"

                    # Add USASpending.gov Links
                    output += "\nLinks:\n"
                    internal_id = award.get("generated_internal_id", "")
                    recipient_hash = award.get("recipient_hash", "")
                    awarding_agency = award.get("awarding_agency_name", "")

                    if internal_id:
                        award_url = generate_award_url(internal_id)
                        output += f"  • Award: {award_url}\n"
                    if recipient_hash:
                        recipient_url = generate_recipient_url(recipient_hash)
                        output += f"  • Recipient Profile: {recipient_url}\n"
                    if awarding_agency:
                        agency_url = generate_agency_url(awarding_agency)
                        output += f"  • Awarding Agency: {agency_url}\n"

                    return [TextContent(type="text", text=output)]
                else:
                    return [
                        TextContent(
                            type="text",
                            text=f"No award found with ID: {award_id}\n\nNote: The award may be older than 2020 or the ID may be formatted differently.",
                        )
                    ]

            except Exception as e:
                return [TextContent(type="text", text=f"Error retrieving award: {str(e)}")]



    @app.tool(
        name="search_federal_awards",
        description="""Search federal spending data from USASpending.gov to find contracts, grants, loans, and other federal awards.

    PARAMETERS:
    - query: Search query with advanced syntax (see below)
    - max_results: Maximum results to return (1-100, default 5)
    - output_format: Output format - "text" (default) or "csv"
    - start_date: Search start date in YYYY-MM-DD format (optional, defaults to 180 days ago)
    - end_date: Search end date in YYYY-MM-DD format (optional, defaults to today)
    - set_aside_type: Filter by set-aside type (e.g., "SDVOSBC", "WOSB", "8A", "HUBZONE") (optional)

    SUPPORTED QUERY SYNTAX:
    - Keywords: "software development" searches for both keywords
    - Quoted phrases: "software development" (exact phrase match)
    - Boolean operators:
      - AND: "software AND development" (both required)
      - OR: "software OR cloud" (at least one)
      - NOT: "software NOT maintenance" (exclude keyword)
    - Award type filter: type:contract, type:grant, type:loan, type:insurance
    - Amount range filter: amount:1M-5M, amount:100K-1M
    - Place of performance: scope:domestic, scope:foreign (where work is performed)
    - Recipient filter: recipient:"Company Name", recipient:dell (who received the award)
    - Top-tier agency: agency:dod, agency:gsa, agency:va, agency:dhs, agency:doe, etc.
    - Sub-tier agency: subagency:disa, subagency:fas, subagency:coast guard, etc.

    AGENCY SHORTCUTS (40+ agencies supported):
    - DOD: dod, defense | DHS: dhs, homeland | GSA: gsa | VA: va, veterans
    - DOE: doe, energy | USDA: usda, agriculture, ag | HHS: hhs | DOT: dot, transportation
    - EPA: epa, environment | DOC: commerce | DOI: interior | DOJ: justice | DOL: labor
    - NASA: nasa | NSF: nsf | SBA: sba | USAID: usaid | And many more...

    SUB-AGENCY SHORTCUTS (150+ sub-agencies supported):
    - DOD: disa, dha, whs, mda, navy, air force, army, dha, marines, centcom, socom, cybercom
    - GSA: fas (federal acquisition), pbs (public buildings)
    - DHS: coast guard, uscg, fema, ice, cbp, tsa, cisa
    - HHS: nih, cdc, fda, cms | DOT: faa, nhtsa | And many more...

    OUTPUT FORMATS:
    - text (default): Formatted text with award details and direct links
    - csv: CSV format suitable for spreadsheet applications

    EXAMPLES:
    - "software development contracts" → Text results for software contracts
    - "\"cloud services\" type:contract" → Cloud service contracts
    - "research AND technology type:grant amount:500K-2M" → Grants for research/tech, $500K-2M
    - "construction NOT residential type:grant scope:domestic" → Domestic construction grants
    - "laptops agency:dod subagency:disa amount:100K-1M" → DISA laptop purchases, $100K-$1M
    - "software agency:gsa output_format:csv" → GSA software contracts as CSV
    - With set_aside_type parameter:
      - search_federal_awards("GSA contracts", set_aside_type="SDVOSBC") → GSA SDVOSB contracts
      - search_federal_awards("contracts amount:50K-500K", set_aside_type="WOSB") → Women-owned business contracts
      - search_federal_awards("contracts", set_aside_type="8A") → 8(a) Program contracts
    """,
    )
    @log_tool_execution
    async def search_federal_awards(
        query: str,
        max_results: int = 5,
        output_format: str = "text",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        set_aside_type: Optional[str] = None,
        aggregate_results: bool = False,
        sort_by_relevance: bool = False,
        include_explanations: bool = True,
    ) -> list[TextContent]:
        """Search for federal awards with advanced query syntax, optional date range, and set-aside filters.

        ADVANCED RESULT REFINEMENT OPTIONS:
        ===================================
        - aggregate_results: Group similar awards by recipient and show summaries (default: False)
        - sort_by_relevance: Rank results by relevance to query keywords (default: False)
        - include_explanations: Show why each award matched the query (default: True)

        DOCUMENTATION REFERENCES:
        ========================
        For reference information about valid filter values and procurement codes, see:
        - Set-Aside Types: /docs/API_RESOURCES.md → "Set-Asides Reference" section
          (SDVOSB, WOSB, 8(a), HUBZone, etc.)
        - Award Types: /docs/API_RESOURCES.md → "Award Types Reference" section
          (Contract types: A, B, C, D; Grants: 02-11; Loans: 07-09; etc.)
        - Agency Names: /docs/API_RESOURCES.md → "Top-Tier Agencies Reference" section
        - Industry Classification: /docs/API_RESOURCES.md → "NAICS Codes Reference" section
        - Product/Service Types: /docs/API_RESOURCES.md → "PSC Codes Reference" section
        - Complete Field Definitions: /docs/API_RESOURCES.md → "Data Dictionary" section

        EXAMPLE QUERIES WITH SET-ASIDES:
        ================================
        - search_federal_awards("GSA contracts", set_aside_type="SDVOSB")
        - search_federal_awards("contracts amount:50K-500K", set_aside_type="WOSB")
        - search_federal_awards("software contracts", set_aside_type="8A")
        - search_federal_awards("IT contracts", sort_by_relevance=True)
        - search_federal_awards("cloud services", aggregate_results=True)"""
        logger.debug(
            f"Tool call received: search_federal_awards with query='{query}', max_results={max_results}, output_format={output_format}, start_date={start_date}, end_date={end_date}, set_aside_type={set_aside_type}"
        )

        # Validate output format
        if output_format not in ["text", "csv"]:
            output_format = "text"

        # Validate max_results
        if max_results < 1 or max_results > 100:
            max_results = 5

        # Get the date range (use provided dates or default)
        actual_start_date, actual_end_date = get_date_range(start_date, end_date)

        # Parse the query for advanced features
        parser = QueryParser(query, award_type_map, toptier_agency_map, subtier_agency_map)

        return await search_awards_logic(
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
                "set_aside_type": set_aside_type,
                "limit": max_results,
                "output_format": output_format,
                "start_date": actual_start_date,
                "end_date": actual_end_date,
                "aggregate_results": aggregate_results,
                "sort_by_relevance": sort_by_relevance,
                "include_explanations": include_explanations,
            }
        )



    @app.tool(
        name="get_award_details",
        description="""Get comprehensive details for a specific award including transactions and modifications.

    This tool provides the complete award record with:
    - Award identification and classification
    - Recipient information
    - Funding amounts and sources
    - Transaction history (modifications, calls, deliveries)
    - Performance period dates
    - Award narrative and description

    PARAMETERS:
    -----------
    - award_id: Award ID from USASpending.gov (e.g., "47QSWA26P02KE")

    RETURNS:
    --------
    - Full award details with all transactions
    - Award amount breakdown
    - Recipient details with DUNS/UEI
    - Performance dates and status

    EXAMPLES:
    ---------
    - get_award_details("47QSWA26P02KE") → Giga Inc Oshkosh truck part award details
    - get_award_details("W91QF425PA017") → James B Studdard moving services details
    """,
    )
    async def get_award_details(award_id: str) -> list[TextContent]:
        """Get comprehensive details for a specific award"""

        output = "=" * 100 + "\n"
        output += f"AWARD DETAILS: {award_id}\n"
        output += "=" * 100 + "\n\n"

        try:
            # Call the awards detail endpoint
            url = f"https://api.usaspending.gov/api/v2/awards/{award_id}/"
            resp = await http_client.get(url, timeout=30.0)

            if resp.status_code == 200:
                award = resp.json()

                # Basic Award Information
                output += "AWARD IDENTIFICATION:\n"
                output += "-" * 100 + "\n"
                output += f"Award ID: {award.get('id', 'N/A')}\n"
                output += f"Recipient: {award.get('recipient', {}).get('name', 'N/A')}\n"
                output += f"DUNS/UEI: {award.get('recipient', {}).get('duns', 'N/A')} / {award.get('recipient', {}).get('uei', 'N/A')}\n"
                output += f"Award Type: {award.get('award_type', 'N/A')}\n"
                output += f"Contract/Grant #: {award.get('contract_number', award.get('grant_number', 'N/A'))}\n"
                output += f"Awarding Agency: {award.get('awarding_agency', {}).get('name', 'N/A')}\n"

                # Funding Information
                output += "\nFUNDING INFORMATION:\n"
                output += "-" * 100 + "\n"
                output += f"Award Amount: ${float(award.get('award_amount', 0))/1e6:.2f}M\n"
                output += f"Total Obligated Amount: ${float(award.get('total_obligated_amount', 0))/1e6:.2f}M\n"
                output += f"Base and All Options Value: ${float(award.get('base_and_all_options_value', 0))/1e6:.2f}M\n"

                # Performance Period
                output += "\nPERFORMANCE PERIOD:\n"
                output += "-" * 100 + "\n"
                output += f"Start Date: {award.get('period_of_performance_start_date', 'N/A')}\n"
                output += f"End Date: {award.get('period_of_performance_end_date', 'N/A')}\n"
                output += f"Award Date: {award.get('award_date', 'N/A')}\n"

                # Award Description
                if award.get("award_description"):
                    output += "\nAWARD DESCRIPTION:\n"
                    output += "-" * 100 + "\n"
                    output += f"{award.get('award_description', '')}\n"

                # POCs
                output += "\nPOINT OF CONTACT:\n"
                output += "-" * 100 + "\n"
                poc = award.get("point_of_contact", {})
                if poc:
                    output += f"Name: {poc.get('name', 'N/A')}\n"
                    output += f"Email: {poc.get('email', 'N/A')}\n"
                    output += f"Phone: {poc.get('phone', 'N/A')}\n"
                else:
                    output += "No POC information available\n"

                # Direct link
                output += "\nDIRECT LINK:\n"
                output += "-" * 100 + "\n"
                output += (
                    f"https://www.usaspending.gov/award/{award.get('generated_internal_id', '')}\n"
                )

            elif resp.status_code == 404:
                output += f"❌ Award ID not found: {award_id}\n"
            else:
                output += f"❌ Error fetching award details (HTTP {resp.status_code})\n"

        except Exception as e:
            output += f"Error: {str(e)}\n"

        output += "\n" + "=" * 100 + "\n"
        return [TextContent(type="text", text=output)]



    @app.tool(
        name="get_subaward_data",
        description="""Find subawards and subcontractors for a specific federal contract or grant.

    This tool shows:
    - Subawardees (subcontractors, subgrantees) under a prime award
    - Subaward amounts and descriptions
    - Subaward relationships to the prime award
    - Recipient information for subawards

    PARAMETERS:
    -----------
    - award_id (required): The award ID to find subawards for (e.g., "47QSWA26P02KE")
    - max_results (optional): Maximum results to return (default: 10, max: 100)

    RETURNS:
    --------
    - List of subawards with recipient and amount information
    - Award ID relationships
    - Subaward descriptions and dates

    EXAMPLES:
    ---------
    - get_subaward_data(award_id="47QSWA26P02KE") → All subawards under this award
    - get_subaward_data(award_id="ABC123XYZ", max_results=20) → Top 20 subawards
    """,
    )
    async def get_subaward_data(
        award_id: Optional[str] = None, max_results: int = 10
    ) -> list[TextContent]:
        """Find subawards and subcontractors"""

        output = "=" * 100 + "\n"
        output += "SUBAWARD DATA\n"
        output += "=" * 100 + "\n\n"

        try:
            url = "https://api.usaspending.gov/api/v2/subawards/"

            # The API requires an award_id to search for subawards
            if not award_id:
                output += "Error: award_id parameter is required to search for subawards.\n"
                output += "Please provide a valid award ID (e.g., '47QSWA26P02KE')\n"
                output += "=" * 100 + "\n"
                return [TextContent(type="text", text=output)]

            output += f"Searching for subawards under award: {award_id}\n\n"

            payload = {
                "award_id": award_id,
                "limit": max_results,
                "page": 1,
            }

            resp = await http_client.post(url, json=payload, timeout=30.0)

            if resp.status_code == 200:
                data = resp.json()
                subawards = data.get("results", [])
                total_count = data.get("count", 0)

                output += f"Found {len(subawards)} of {total_count} total subawards\n"
                output += "-" * 100 + "\n\n"

                if subawards:
                    for i, sub in enumerate(subawards, 1):
                        output += f"{i}. {sub.get('sub_awardee_name', 'Unknown')}\n"
                        output += f"   Award ID: {sub.get('award_id', 'N/A')}\n"
                        output += f"   Subaward Amount: ${float(sub.get('amount', 0))/1e6:.2f}M\n"
                        output += f"   Subaward Date: {sub.get('subaward_date', 'N/A')}\n"
                        output += f"   Description: {sub.get('description', 'N/A')}\n"
                        output += "\n"
                else:
                    output += "No subawards found matching criteria\n"

            else:
                output += f"Error fetching subawards (HTTP {resp.status_code})\n"

        except Exception as e:
            output += f"Error: {str(e)}\n"

        output += "=" * 100 + "\n"
        return [TextContent(type="text", text=output)]



    @app.tool(
        name="get_recipient_details",
        description="""Get comprehensive profiles for specific recipients (vendors/contractors).

    This tool provides:
    - Complete recipient/vendor information
    - Award history and total spending
    - Financial metrics
    - Past performance information
    - Geographic presence

    PARAMETERS:
    -----------
    - recipient_id (optional): DUNS or UEI number
    - recipient_name (optional): Recipient/vendor name
    - detail_level (optional): "summary" or "detail" (default: detail)

    RETURNS:
    --------
    - Recipient profile with DUNS/UEI
    - Total awards and spending
    - Award type breakdown
    - Recent award history

    EXAMPLES:
    ---------
    - get_recipient_details(recipient_name="Giga Inc") → Profile for Giga Inc
    - get_recipient_details(recipient_id="123456789") → Profile for DUNS 123456789
    """,
    )
    async def get_recipient_details(
        recipient_id: Optional[str] = None,
        recipient_name: Optional[str] = None,
        detail_level: str = "detail",
    ) -> list[TextContent]:
        """Get comprehensive recipient/vendor profiles"""

        output = "=" * 100 + "\n"
        output += "RECIPIENT/VENDOR PROFILE\n"
        output += "=" * 100 + "\n\n"

        try:
            # If we have a name, search for it first
            if recipient_name and not recipient_id:
                output += f"Searching for recipient: {recipient_name}\n\n"
                search_url = "https://api.usaspending.gov/api/v2/autocomplete/recipient/"
                search_resp = await http_client.get(
                    search_url, params={"search_text": recipient_name}, timeout=30.0
                )

                if search_resp.status_code == 200:
                    results = search_resp.json().get("results", [])
                    if results:
                        recipient_id = results[0].get("id", "")
                        recipient_name = results[0].get("name", recipient_name)
                        output += f"Found: {recipient_name} (ID: {recipient_id})\n\n"
                    else:
                        output += f"No recipient found matching '{recipient_name}'\n"
                        return [TextContent(type="text", text=output)]
                else:
                    output += "Error searching for recipient\n"
                    return [TextContent(type="text", text=output)]

            # Get recipient profile
            url = "https://api.usaspending.gov/api/v2/recipients/"

            # Build payload using correct API parameter structure
            # The API uses 'keyword' for searching recipients (by name, UEI, or DUNS)
            payload = {
                "limit": 1,
                "page": 1,
            }

            # If we have a recipient_id, search by UEI/DUNS via keyword
            if recipient_id:
                payload["keyword"] = recipient_id
            elif recipient_name:
                payload["keyword"] = recipient_name

            resp = await http_client.post(url, json=payload, timeout=30.0)

            if resp.status_code == 200:
                data = resp.json()
                recipients = data.get("results", [])

                if recipients:
                    recipient = recipients[0]
                    output += "RECIPIENT INFORMATION:\n"
                    output += "-" * 100 + "\n"
                    output += f"Name: {recipient.get('name', 'N/A')}\n"
                    output += f"DUNS: {recipient.get('duns', 'N/A')}\n"
                    output += f"UEI: {recipient.get('uei', 'N/A')}\n"
                    output += f"Recipient Type: {recipient.get('recipient_type', 'N/A')}\n"

                    if detail_level.lower() == "detail":
                        output += "\nAWARD STATISTICS:\n"
                        output += "-" * 100 + "\n"
                        output += (
                            f"Total Award Amount: ${float(recipient.get('award_amount', 0))/1e9:.2f}B\n"
                        )
                        output += f"Number of Awards: {recipient.get('number_of_awards', 0)}\n"
                        output += f"Location: {recipient.get('location', {}).get('city', 'N/A')}, {recipient.get('location', {}).get('state', 'N/A')}\n"

                    output += "\nDIRECT LINK:\n"
                    output += "-" * 100 + "\n"
                    output += f"https://www.usaspending.gov/recipient/{recipient.get('id', '')}/\n"
                else:
                    output += "No recipient found\n"
            else:
                output += f"Error fetching recipient data (HTTP {resp.status_code})\n"

        except Exception as e:
            output += f"Error: {str(e)}\n"

        output += "\n" + "=" * 100 + "\n"
        return [TextContent(type="text", text=output)]



    @app.tool(
        name="get_vendor_by_uei",
        description="""Search for federal contractor awards by UEI (Unique Entity Identifier).

    The UEI is a unique identifier assigned to all federal vendors. Use this tool to find
    all awards, spending totals, and detailed profiles for a specific vendor.

    PARAMETERS:
    -----------
    - uei: The UEI identifier (e.g., "NWM1JWVDA853")
    - limit (optional): Maximum results to return (default: 100)

    RETURNS:
    --------
    - Vendor name, UEI, total awards count
    - Total spending amount and average award size
    - Breakdown by award type (contracts, grants, etc.)
    - Top awarding agencies
    - Largest individual awards with details

    EXAMPLE:
    --------
    - get_vendor_by_uei("NWM1JWVDA853") → AM General LLC profile and all awards

    NOTE:
    -----
    UEI searches work via keyword matching. For best results, provide the exact UEI.
    The tool also returns awards using spending_by_award endpoint with UEI keyword filter.
    """,
    )
    async def get_vendor_by_uei(uei: str, limit: int = 100) -> list[TextContent]:
        """Search for contractor awards by UEI (Unique Entity Identifier)"""

        output = "=" * 100 + "\n"
        output += f"VENDOR SEARCH BY UEI: {uei}\n"
        output += "=" * 100 + "\n\n"

        if not uei or len(uei.strip()) == 0:
            output += "Error: UEI parameter is required\n"
            return [TextContent(type="text", text=output)]

        try:
            # Search for awards by UEI (using keyword search with award type filter)
            url = "https://api.usaspending.gov/api/v2/search/spending_by_award/"

            # Contract award types (A, B, C, D)
            payload = {
                "filters": {"keywords": [uei], "award_type_codes": ["A", "B", "C", "D"]},
                "fields": [
                    "Award ID",
                    "Recipient Name",
                    "Recipient UEI",
                    "Award Amount",
                    "Award Type",
                    "Awarding Agency",
                    "Action Date",
                ],
                "limit": min(limit, 100),
            }

            resp = await http_client.post(url, json=payload, timeout=30.0)

            if resp.status_code == 200:
                data = resp.json()
                results = data.get("results", [])

                if not results:
                    output += f"No awards found for UEI: {uei}\n\n"
                    output += "This could mean:\n"
                    output += "- The UEI is incorrect or not in the system\n"
                    output += "- The vendor has no recent federal awards\n"
                    output += "- Try searching by vendor name instead\n"
                    output += "=" * 100 + "\n"
                    return [TextContent(type="text", text=output)]

                # Extract vendor information
                vendor_name = results[0].get("Recipient Name", "Unknown")
                uei_found = results[0].get("Recipient UEI", uei)

                output += f"Vendor Name: {vendor_name}\n"
                output += f"UEI: {uei_found}\n"
                output += f"Total Awards Found: {len(results)}\n\n"

                # Calculate statistics
                total_spending = sum(float(r.get("Award Amount", 0)) for r in results)
                avg_award = total_spending / len(results) if results else 0

                output += "FINANCIAL SUMMARY:\n"
                output += "-" * 100 + "\n"
                total_fmt = (
                    f"${total_spending/1e9:,.2f}B"
                    if total_spending >= 1e9
                    else f"${total_spending/1e6:,.2f}M"
                )
                avg_fmt = f"${avg_award/1e6:,.2f}M" if avg_award >= 1e6 else f"${avg_award/1e3:,.2f}K"
                output += f"Total Spending: {total_fmt}\n"
                output += f"Average Award: {avg_fmt}\n\n"

                # Award type breakdown
                output += "BREAKDOWN BY AWARD TYPE:\n"
                output += "-" * 100 + "\n"

                award_types = {}
                for award in results:
                    award_type = award.get("Award Type") or "Unknown"
                    amount = float(award.get("Award Amount", 0))
                    if award_type not in award_types:
                        award_types[award_type] = {"count": 0, "total": 0}
                    award_types[award_type]["count"] += 1
                    award_types[award_type]["total"] += amount

                for award_type in sorted(award_types.keys()):
                    info = award_types[award_type]
                    pct = (info["total"] / total_spending * 100) if total_spending > 0 else 0
                    type_fmt = (
                        f"${info['total']/1e9:,.2f}B"
                        if info["total"] >= 1e9
                        else f"${info['total']/1e6:,.2f}M"
                    )
                    output += f"  {award_type:<20} Count: {info['count']:>4}  Total: {type_fmt:<18}  ({pct:.1f}%)\n"

                # Top awarding agencies
                output += "\nTOP AWARDING AGENCIES:\n"
                output += "-" * 100 + "\n"

                agencies = {}
                for award in results:
                    agency = award.get("Awarding Agency") or "Unknown"
                    amount = float(award.get("Award Amount", 0))
                    if agency not in agencies:
                        agencies[agency] = {"count": 0, "total": 0}
                    agencies[agency]["count"] += 1
                    agencies[agency]["total"] += amount

                sorted_agencies = sorted(agencies.items(), key=lambda x: x[1]["total"], reverse=True)
                for agency, info in sorted_agencies[:10]:
                    pct = (info["total"] / total_spending * 100) if total_spending > 0 else 0
                    agency_fmt = (
                        f"${info['total']/1e9:,.2f}B"
                        if info["total"] >= 1e9
                        else f"${info['total']/1e6:,.2f}M"
                    )
                    agency_name = agency[:50]
                    output += f"  {agency_name:<50} {agency_fmt:<18} ({pct:.1f}%)\n"

                # Top awards by amount
                output += "\nTOP 10 AWARDS BY AMOUNT:\n"
                output += "-" * 100 + "\n"

                sorted_by_amount = sorted(
                    results, key=lambda x: float(x.get("Award Amount", 0)), reverse=True
                )
                for i, award in enumerate(sorted_by_amount[:10], 1):
                    amount = float(award.get("Award Amount", 0))
                    award_type = award.get("Award Type") or "Unknown"
                    agency = award.get("Awarding Agency") or "Unknown"
                    award_id = award.get("Award ID", "N/A")
                    date = award.get("Action Date", "N/A")

                    amount_fmt = f"${amount/1e6:,.2f}M" if amount >= 1e6 else f"${amount/1e3:,.2f}K"
                    output += f"\n  {i}. Award ID: {award_id}\n"
                    output += f"     Amount: {amount_fmt}  |  Type: {award_type}  |  Agency: {agency}\n"
                    output += f"     Date: {date}\n"

            else:
                output += f"Error fetching awards (HTTP {resp.status_code})\n"

        except Exception as e:
            output += f"Error: {str(e)}\n"

        output += "\n" + "=" * 100 + "\n"
        return [TextContent(type="text", text=output)]



    def get_default_date_range() -> tuple[str, str]:
        """Get 180-day lookback date range (YYYY-MM-DD format)"""
        today = datetime.now()
        start_date = today - timedelta(days=180)
        return start_date.strftime("%Y-%m-%d"), today.strftime("%Y-%m-%d")


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




    logger_instance.info("Award discovery tools registered successfully")
