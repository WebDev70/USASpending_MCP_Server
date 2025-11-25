"""
Helper utilities for USASpending MCP tools.

WHAT'S IN THIS FILE?
This module contains shared helper functions and classes that multiple
tools need. Instead of duplicating code in every tool file, we keep it
here in one place.

Think of this like a "toolkit" that all the tools (like drill, hammer, saw)
share. Instead of each tool having its own hammer, they all use the same
one from the toolkit.

WHAT WE SHARE:
1. QueryParser - Parses advanced search queries
2. URL generators - Create links to USASpending.gov
3. Currency formatter - Format money values nicely
4. API request handler - Make requests to the USASpending API
"""

import logging
import re
from typing import Optional

import httpx

# Get the logger for this module
logger = logging.getLogger(__name__)


class QueryParser:
    """
    Parse advanced search queries with support for filters and operators.

    WHAT DOES THIS DO?
    Users type questions like: "contracts from dod worth 1M-5M"
    This class breaks that down into searchable parts:
    - Award type: contracts
    - Agency: Department of Defense
    - Amount range: $1M - $5M

    HOW USERS CAN FILTER:
    Users can type filters in their searches:
    - type:grant → Search for grants
    - type:contract → Search for contracts
    - amount:1M-5M → Dollar range
    - agency:dod → Department of Defense
    - subagency:navy → Navy (under DoD)
    - scope:domestic → US-only contracts
    - recipient:acme → Company named ACME

    BOOLEAN OPERATORS:
    - AND → All keywords must match (strict search)
    - NOT → Exclude this word from results
    - "quoted phrase" → Search for exact phrase

    EXAMPLES:
    - "software AND navy" → Software contracts from Navy (all keywords required)
    - "defense NOT missile" → Defense contracts but exclude missile projects
    - "type:grant state:california" → California grants only
    """

    def __init__(self, query: str, award_type_map: dict, toptier_map: dict, subtier_map: dict):
        """
        Initialize the query parser.

        Args:
            query: The user's search query (e.g., "contracts from dod")
            award_type_map: Dictionary mapping award names to codes (from constants.py)
            toptier_map: Dictionary mapping agency names to official names (from constants.py)
            subtier_map: Dictionary mapping sub-agency names to tuples (from constants.py)
        """
        # Store the original query so we can debug if something goes wrong
        self.original_query = query

        # Lists to store extracted keywords and exclude words
        self.keywords = []  # Words to INCLUDE in search
        self.exclude_keywords = []  # Words to EXCLUDE from search

        # Should ALL keywords be present (AND) or any (OR)?
        # Default is OR (more results but looser matching)
        self.require_all = False

        # Award type filter (what kind of award)
        # Default to contracts (A, B, C, D codes)
        self.award_types = ["A", "B", "C", "D"]

        # Amount filters (what price range)
        self.min_amount = None  # Minimum dollar amount
        self.max_amount = None  # Maximum dollar amount

        # Place of performance filter (US or international?)
        # domestic = US only, foreign = international
        self.place_of_performance_scope = None

        # Specific filters from the user
        self.recipient_name = None  # Specific company name
        self.toptier_agency = None  # Big agency like DoD
        self.subtier_agency = None  # Sub-agency like Navy

        # Store the mapping dictionaries so we can use them
        self.award_type_map = award_type_map
        self.toptier_map = toptier_map
        self.subtier_map = subtier_map

        # Now parse the query
        self.parse()

    def parse(self):
        """
        Parse the query string into components.

        HOW IT WORKS:
        1. Extract filters (like "type:grant")
        2. Extract quoted phrases (like "exact phrase")
        3. Check for boolean operators (AND, NOT)
        4. Extract remaining keywords
        5. Remove common "stop words" that don't help search
           (like "the", "a", "for", "find")
        """
        # Convert to lowercase so "DOD" and "dod" are treated the same
        query = self.original_query.lower()

        # Step 1: Extract special filters like "type:grant" or "amount:1M-5M"
        self._parse_filters(query)

        # Step 2: Remove the filter syntax so we don't try to parse it as keywords
        # Example: "type:grant software" → "software"
        query = re.sub(r"\w+:[\w\-$M]+", "", query)

        # Step 3: Extract quoted phrases (exact matches)
        # Example: "software development" means search for those words together
        quoted_phrases = re.findall(r'"([^"]+)"', query)
        for phrase in quoted_phrases:
            if phrase.strip():  # Make sure it's not empty
                self.keywords.append(phrase.strip())

        # Remove the quotes from the query
        # Example: 'find "exact phrase" here' → 'find  here'
        query = re.sub(r'"[^"]+"', "", query)

        # Step 4: Check for AND operator (all keywords required)
        # Default is OR (any keyword is fine)
        if " AND " in query.upper():
            self.require_all = True
            # Remove the AND so it doesn't get treated as a keyword
            query = re.sub(r"\sAND\s", " ", query, flags=re.IGNORECASE)

        # Step 5: Extract NOT keywords (exclusions)
        # Example: "defense NOT missile" → exclude "missile"
        not_keywords = re.findall(r"(?:^|\s)NOT\s+(\w+)", query, re.IGNORECASE)
        for word in not_keywords:
            # Don't exclude common words - they're probably not meant to be NOT keywords
            if word not in {"find", "show", "me", "get", "search", "for", "the"}:
                self.exclude_keywords.append(word)

        # Remove the NOT keywords so they don't get treated as regular keywords
        query = re.sub(r"\bNOT\s+\w+", "", query, flags=re.IGNORECASE)

        # Step 6: Extract remaining keywords (ignore stop words)
        # Stop words are common words that don't help search
        # Example: "find software for the navy" → keywords: "software", "navy"
        stop_words = {
            "find",
            "show",
            "me",
            "get",
            "search",
            "for",
            "the",
            "and",
            "or",
            "in",
            "is",
            "a",
            "an",
        }
        remaining_words = [
            word for word in query.split()
            if word and word not in stop_words and word.isalpha()
        ]
        self.keywords.extend(remaining_words)

        # Remove duplicate keywords but keep them in order
        # dict.fromkeys() keeps order while removing duplicates
        self.keywords = list(dict.fromkeys(self.keywords))

    def _parse_filters(self, query: str):
        """
        Extract special filters from the query.

        Supported filters:
        - type:contract or type:grant → Award type
        - amount:1M-5M → Dollar range
        - scope:domestic or scope:foreign → US or international
        - recipient:companyname → Specific company
        - agency:dod or agency:navy → Specific agency
        - subagency:disa → Specific sub-agency

        Example queries:
        - "type:grant state:california amount:100K-1M"
        - "contracts from agency:navy"
        - "software with amount:1M-10M"
        """
        # ============ AWARD TYPE FILTER ============
        # Example: "type:grant" or "type:contract"
        type_match = re.search(r"type:(\w+)", query)
        if type_match:
            type_name = type_match.group(1).lower()
            # Look up the award type codes (like "grant" → ["02", "03", "04", "05"])
            if type_name in self.award_type_map:
                self.award_types = self.award_type_map[type_name]

        # ============ AMOUNT RANGE FILTER ============
        # Example: "amount:1M-5M" or "amount:100K-500K"
        amount_match = re.search(r"amount:(\d+[KMB]?)-(\d+[KMB]?)", query, re.IGNORECASE)
        if amount_match:
            # Parse the minimum and maximum amounts
            self.min_amount = self._parse_amount(amount_match.group(1))
            self.max_amount = self._parse_amount(amount_match.group(2))

        # ============ PLACE OF PERFORMANCE SCOPE ============
        # Example: "scope:domestic" (US only) or "scope:foreign" (international)
        scope_match = re.search(r"scope:(\w+)", query)
        if scope_match:
            scope_value = scope_match.group(1).lower()
            if scope_value in ["domestic", "foreign"]:
                self.place_of_performance_scope = scope_value

        # ============ RECIPIENT (COMPANY NAME) FILTER ============
        # Example: "recipient:acme" or recipient:"Acme Corporation"
        recipient_match = re.search(r'recipient:"([^"]+)"', query)
        if recipient_match:
            self.recipient_name = recipient_match.group(1)
        else:
            # Also try without quotes: "recipient:acme"
            recipient_match = re.search(r"recipient:(\w+)", query)
            if recipient_match:
                self.recipient_name = recipient_match.group(1)

        # ============ TOP-TIER AGENCY FILTER ============
        # Example: "agency:dod" or agency:"Department of Defense"
        agency_match = re.search(r'agency:"([^"]+)"', query)
        if agency_match:
            agency_input = agency_match.group(1).lower()
            # Look up the official agency name
            self.toptier_agency = self.toptier_map.get(agency_input, agency_input)
        else:
            # Try without quotes: "agency:dod"
            agency_match = re.search(r"agency:(\w+)", query)
            if agency_match:
                agency_input = agency_match.group(1).lower()
                self.toptier_agency = self.toptier_map.get(agency_input, agency_input)

        # ============ SUB-TIER AGENCY FILTER ============
        # Example: "subagency:disa" or subagency:"Defense Information Systems Agency"
        subagency_match = re.search(r'subagency:"([^"]+)"', query)
        if subagency_match:
            subagency_input = subagency_match.group(1).lower()
            if subagency_input in self.subtier_map:
                # Get both parent agency and official subtier name
                parent_agency, subtier_name = self.subtier_map[subagency_input]
                self.toptier_agency = parent_agency
                self.subtier_agency = subtier_name
        else:
            # Try without quotes: "subagency:disa"
            subagency_match = re.search(r"subagency:(\w+)", query)
            if subagency_match:
                subagency_input = subagency_match.group(1).lower()
                if subagency_input in self.subtier_map:
                    parent_agency, subtier_name = self.subtier_map[subagency_input]
                    self.toptier_agency = parent_agency
                    self.subtier_agency = subtier_name

    def _parse_amount(self, amount_str: str) -> Optional[float]:
        """
        Convert amount string like '1M' or '500K' to numeric value.

        EXAMPLES:
        - "1M" → 1,000,000
        - "500K" → 500,000
        - "1B" → 1,000,000,000
        - "100" → 100 (no suffix means just dollars)

        Args:
            amount_str: The amount string to parse (e.g., "1M")

        Returns:
            The numeric dollar value, or None if parsing failed
        """
        amount_str = amount_str.upper().strip()

        # Dictionary of multipliers (K=thousand, M=million, B=billion)
        multipliers = {"K": 1_000, "M": 1_000_000, "B": 1_000_000_000}

        # Check if the amount ends with a multiplier suffix
        for suffix, multiplier in multipliers.items():
            if amount_str.endswith(suffix):
                try:
                    # Remove the suffix and multiply
                    # Example: "1M" → "1" → 1 * 1,000,000 = 1,000,000
                    return float(amount_str[:-1]) * multiplier
                except ValueError:
                    # If we can't parse the number, return None
                    return None

        # No suffix, just try to parse as a plain number
        try:
            return float(amount_str)
        except ValueError:
            return None

    def get_keywords_string(self) -> str:
        """
        Get keywords formatted as a space-separated string for the API.

        If there are no keywords, return "*" (wildcard = all results).

        Returns:
            A string of keywords like "software development" or "*"
        """
        if not self.keywords:
            # No keywords means "match everything"
            return "*"
        # Join keywords with spaces
        return " ".join(self.keywords)


# ============ URL GENERATION HELPERS ============
def generate_award_url(internal_id: str) -> str:
    """
    Generate a direct link to an award on USASpending.gov.

    This lets users click through to the official website to see full details.

    Args:
        internal_id: The award's internal ID from USASpending

    Returns:
        The full URL to the award on USASpending.gov
    """
    if internal_id:
        return f"https://www.usaspending.gov/award/{internal_id}"
    return ""


def generate_recipient_url(recipient_hash: str) -> str:
    """
    Generate a direct link to a recipient/company profile on USASpending.gov.

    This shows all awards received by a company.

    Args:
        recipient_hash: The company's hash identifier from USASpending

    Returns:
        The full URL to the company's profile
    """
    if recipient_hash:
        return f"https://www.usaspending.gov/recipient/{recipient_hash}/latest"
    return ""


def generate_agency_url(agency_name: str, fiscal_year: str = "2025") -> str:
    """
    Generate a direct link to an agency profile on USASpending.gov.

    This shows all spending by a specific agency.

    Args:
        agency_name: The official agency name (e.g., "Department of Defense")
        fiscal_year: The fiscal year to show (default: 2025)

    Returns:
        The full URL to the agency's profile
    """
    if agency_name:
        # Convert to URL format: "Department of Defense" → "department-of-defense"
        agency_slug = agency_name.lower().replace(" ", "-").replace(".", "").replace("&", "and")
        return f"https://www.usaspending.gov/agency/{agency_slug}?fy={fiscal_year}"
    return ""


# ============ CURRENCY FORMATTER ============
def format_currency(amount: float) -> str:
    """
    Format a dollar amount in human-readable form.

    EXAMPLES:
    - 1,234,567,890 → "$1.23B"
    - 1,234,567 → "$1.23M"
    - 1,234 → "$1.23K"
    - 123 → "$123.00"

    This makes big numbers easier to understand. "$1.23B" is much clearer
    than "$1,234,000,000".

    Args:
        amount: The dollar amount to format

    Returns:
        A nicely formatted string like "$1.23M"
    """
    # Check from largest to smallest unit
    if amount >= 1_000_000_000:
        # Billions
        return f"${amount/1_000_000_000:.2f}B"
    elif amount >= 1_000_000:
        # Millions
        return f"${amount/1_000_000:.2f}M"
    elif amount >= 1_000:
        # Thousands
        return f"${amount/1_000:.2f}K"
    else:
        # Just dollars
        return f"${amount:.2f}"


# ============ API REQUEST HANDLER ============
async def make_api_request(
    client: httpx.AsyncClient,
    endpoint: str,
    base_url: str,
    params: dict = None,
    method: str = "GET",
    json_data: dict = None,
) -> dict:
    """
    Make a request to the USASpending API with error handling.

    This handles the common details of making an API call:
    - Building the full URL
    - Making the request
    - Checking for errors
    - Logging problems
    - Parsing the response

    WHY HAVE THIS FUNCTION?
    Every tool needs to make API calls. Instead of each tool repeating
    the same error-handling code, we do it once here.

    Args:
        client: The httpx HTTP client to use
        endpoint: The API endpoint (e.g., "search/spending_by_award")
        base_url: The base URL (e.g., "https://api.usaspending.gov/api/v2")
        params: Query parameters (for GET requests)
        method: HTTP method (GET or POST)
        json_data: JSON body data (for POST requests)

    Returns:
        A dictionary with either:
        - The API response data (if successful)
        - An error dict with "error" key (if failed)
    """
    # Build the full URL by combining base and endpoint
    url = f"{base_url}/{endpoint}"

    try:
        # Make the actual HTTP request
        if method == "POST":
            response = await client.post(url, json=json_data)
        else:
            response = await client.get(url, params=params)

        # Check if the response has an error status code (4xx, 5xx)
        if response.status_code >= 400:
            try:
                # Try to parse the error response as JSON
                error_detail = response.json()
                logger.error(f"API error ({response.status_code}): {error_detail}")
                return {"error": f"API Error {response.status_code}: {error_detail}"}
            except Exception as e:
                # If we can't parse JSON, just log the status code
                logger.error(f"API error ({response.status_code}): {str(e)}")
                return {"error": f"API Error {response.status_code}: {str(e)}"}

        # Success! Parse and return the JSON response
        return response.json()

    except Exception as e:
        # Network error or other problem
        logger.error(f"API request error: {str(e)}")
        return {"error": f"API request error: {str(e)}"}
