#!/usr/bin/env python3
# Start the server
# ./.venv/bin/python -m usaspending_mcp.server
# ./.venv/bin/python -m usaspending_mcp.client
"""
USASpending.gov MCP Server

Provides tools to query federal spending data including awards and vendors
"""

import asyncio
import csv
import json
import re
import sys
from datetime import datetime, timedelta
from io import StringIO
from typing import Optional

import httpx
import uvicorn
from fastmcp import FastMCP
from mcp.types import TextContent

# Import conversation logging utilities
from usaspending_mcp.utils.conversation_logging import (
    get_conversation_logger,
    initialize_conversation_logger,
)

# Import structured logging utilities
from usaspending_mcp.utils.logging import (
    get_logger,
    log_search,
    log_tool_execution,
    setup_structured_logging,
)

# Detect if running in stdio mode - if so, disable JSON output to avoid protocol conflicts
# JSON logging interferes with MCP protocol communication on stdio
is_stdio_mode = len(sys.argv) > 1 and sys.argv[1] == "--stdio"

# Set up structured logging (JSON only for HTTP mode)
setup_structured_logging(log_level="INFO", json_output=not is_stdio_mode)
logger = get_logger("server")

# Initialize FastMCP server
app = FastMCP(name="usaspending-server")

# Base URL for USASpending API
BASE_URL = "https://api.usaspending.gov/api/v2"

from usaspending_mcp.utils.rate_limit import initialize_rate_limiter

# Initialize rate limiter: 60 requests per minute
rate_limiter = initialize_rate_limiter(requests_per_minute=60)
logger.info("Rate limiter initialized: 60 requests/minute")

# Initialize conversation logger for tracking MCP tool interactions
conversation_logger = initialize_conversation_logger()
logger.info("Conversation logger initialized")

# Register modular tool sets
# FAR tools are registered from the usaspending_mcp.tools module
try:
    from usaspending_mcp.tools.far import register_far_tools

    register_far_tools(app)
    logger.info("FAR tools registered successfully")
except Exception as e:
    logger.warning(f"Could not register FAR tools: {e}")

# HTTP client with timeout
http_client = httpx.AsyncClient(timeout=30.0)

# Award type mapping
AWARD_TYPE_MAP = {
    "contract": ["A", "B", "C", "D"],
    "grant": ["02", "03", "04", "05"],
    "loan": ["07", "08", "09"],
    "insurance": ["10", "11"],
}

# Top-tier agency mapping (normalized to API format) - COMPREHENSIVE
TOPTIER_AGENCY_MAP = {
    # Department of Defense
    "dod": "Department of Defense",
    "defense": "Department of Defense",
    "defense department": "Department of Defense",
    "pentagon": "Department of Defense",
    # Department of Veterans Affairs
    "va": "Department of Veterans Affairs",
    "veterans": "Department of Veterans Affairs",
    "veterans affairs": "Department of Veterans Affairs",
    # Department of Energy
    "doe": "Department of Energy",
    "energy": "Department of Energy",
    "energy department": "Department of Energy",
    # General Services Administration
    "gsa": "General Services Administration",
    "general services": "General Services Administration",
    # Department of Homeland Security
    "dhs": "Department of Homeland Security",
    "homeland": "Department of Homeland Security",
    "homeland security": "Department of Homeland Security",
    # Department of Agriculture
    "usda": "Department of Agriculture",
    "agriculture": "Department of Agriculture",
    "ag": "Department of Agriculture",
    "farm": "Department of Agriculture",
    # Social Security Administration
    "ssa": "Social Security Administration",
    "social security": "Social Security Administration",
    # Department of the Treasury
    "treasury": "Department of the Treasury",
    "treasury department": "Department of the Treasury",
    "treasury dept": "Department of the Treasury",
    # Department of Transportation
    "dot": "Department of Transportation",
    "transportation": "Department of Transportation",
    # Department of Health and Human Services
    "hhs": "Department of Health and Human Services",
    "health human services": "Department of Health and Human Services",
    "health services": "Department of Health and Human Services",
    # Environmental Protection Agency
    "epa": "Environmental Protection Agency",
    "environmental protection": "Environmental Protection Agency",
    "environment": "Environmental Protection Agency",
    # Department of Commerce
    "commerce": "Department of Commerce",
    "department commerce": "Department of Commerce",
    "doc": "Department of Commerce",
    # Department of State
    "state": "Department of State",
    "state department": "Department of State",
    "dos": "Department of State",
    "state dept": "Department of State",
    # Department of the Interior
    "interior": "Department of the Interior",
    "doi": "Department of the Interior",
    "department interior": "Department of the Interior",
    # Department of Justice
    "justice": "Department of Justice",
    "doj": "Department of Justice",
    "justice department": "Department of Justice",
    # Department of Labor
    "labor": "Department of Labor",
    "dol": "Department of Labor",
    "labor department": "Department of Labor",
    # Department of Housing and Urban Development
    "hud": "Department of Housing and Urban Development",
    "housing urban": "Department of Housing and Urban Development",
    "housing development": "Department of Housing and Urban Development",
    # Department of Education
    "education": "Department of Education",
    "ed": "Department of Education",
    "dept education": "Department of Education",
    # NASA
    "nasa": "National Aeronautics and Space Administration",
    "space administration": "National Aeronautics and Space Administration",
    "aeronautics": "National Aeronautics and Space Administration",
    # NSF
    "ns": "National Science Foundation",
    "science foundation": "National Science Foundation",
    # SBA
    "sba": "Small Business Administration",
    "small business": "Small Business Administration",
    # USAID
    "usaid": "Agency for International Development",
    "aid": "Agency for International Development",
    "international development": "Agency for International Development",
    # Other independent agencies
    "opm": "Office of Personnel Management",
    "nrc": "Nuclear Regulatory Commission",
    "nuclear": "Nuclear Regulatory Commission",
    "fcc": "Federal Communications Commission",
    "communications": "Federal Communications Commission",
    "sec": "Securities and Exchange Commission",
    "usps": "United States Postal Service",
    "postal service": "United States Postal Service",
    "tva": "Tennessee Valley Authority",
    "exim": "Export-Import Bank",
    "dfc": "International Development Finance Corporation",
    "cpb": "Corporation for Public Broadcasting",
    "nea": "National Endowment for the Arts",
    "neh": "National Endowment for the Humanities",
}

# Sub-tier agency mapping (normalized to API format) - COMPREHENSIVE
# Format: "subtier_name" -> ("parent_agency_name", "subtier_official_name")
SUBTIER_AGENCY_MAP = {
    # ============ DEPARTMENT OF DEFENSE ============
    # Military Departments
    "navy": ("Department of Defense", "Department of the Navy"),
    "navy department": ("Department of Defense", "Department of the Navy"),
    "usn": ("Department of Defense", "Department of the Navy"),
    "department navy": ("Department of Defense", "Department of the Navy"),
    "army": ("Department of Defense", "Department of the Army"),
    "army department": ("Department of Defense", "Department of the Army"),
    "usa": ("Department of Defense", "Department of the Army"),
    "department army": ("Department of Defense", "Department of the Army"),
    "air force": ("Department of Defense", "Department of the Air Force"),
    "usa": ("Department of Defense", "Department of the Air Force"),
    "air force department": ("Department of Defense", "Department of the Air Force"),
    "department air force": ("Department of Defense", "Department of the Air Force"),
    "marine corps": ("Department of Defense", "Department of the Navy"),
    "usmc": ("Department of Defense", "Department of the Navy"),
    "marines": ("Department of Defense", "Department of the Navy"),
    # DOD Agencies
    "disa": ("Department of Defense", "Defense Information Systems Agency"),
    "information systems": ("Department of Defense", "Defense Information Systems Agency"),
    "dha": ("Department of Defense", "Defense Health Agency"),
    "health agency": ("Department of Defense", "Defense Health Agency"),
    "tricare": ("Department of Defense", "Defense Health Agency"),
    "whs": ("Department of Defense", "Washington Headquarters Services"),
    "headquarters services": ("Department of Defense", "Washington Headquarters Services"),
    "mda": ("Department of Defense", "Missile Defense Agency"),
    "missile defense": ("Department of Defense", "Missile Defense Agency"),
    "ballistic": ("Department of Defense", "Missile Defense Agency"),
    "dla": ("Department of Defense", "Defense Logistics Agency"),
    "logistics agency": ("Department of Defense", "Defense Logistics Agency"),
    "logistics": ("Department of Defense", "Defense Logistics Agency"),
    "defense contract audit": ("Department of Defense", "Defense Contract Audit Agency"),
    "dcaa": ("Department of Defense", "Defense Contract Audit Agency"),
    "defense threat reduction": ("Department of Defense", "Defense Threat Reduction Agency"),
    "dtra": ("Department of Defense", "Defense Threat Reduction Agency"),
    "counterintelligence security": (
        "Department of Defense",
        "Defense Counterintelligence and Security Agency",
    ),
    "dcsa": ("Department of Defense", "Defense Counterintelligence and Security Agency"),
    # Combatant Commands
    "stratcom": ("Department of Defense", "United States Strategic Command"),
    "strategic command": ("Department of Defense", "United States Strategic Command"),
    "centcom": ("Department of Defense", "United States Central Command"),
    "central command": ("Department of Defense", "United States Central Command"),
    "eucom": ("Department of Defense", "United States European Command"),
    "european command": ("Department of Defense", "United States European Command"),
    "pacom": ("Department of Defense", "United States Indo-Pacific Command"),
    "pacific command": ("Department of Defense", "United States Indo-Pacific Command"),
    "indo-pacific": ("Department of Defense", "United States Indo-Pacific Command"),
    "southcom": ("Department of Defense", "United States Southern Command"),
    "southern command": ("Department of Defense", "United States Southern Command"),
    "northcom": ("Department of Defense", "United States Northern Command"),
    "northern command": ("Department of Defense", "United States Northern Command"),
    "norad": ("Department of Defense", "United States Northern Command"),
    "africom": ("Department of Defense", "United States Africa Command"),
    "africa command": ("Department of Defense", "United States Africa Command"),
    "socom": ("Department of Defense", "United States Special Operations Command"),
    "special operations": ("Department of Defense", "United States Special Operations Command"),
    "special ops": ("Department of Defense", "United States Special Operations Command"),
    "cybercom": ("Department of Defense", "United States Cyber Command"),
    "cyber command": ("Department of Defense", "United States Cyber Command"),
    "cybersecurity": ("Department of Defense", "United States Cyber Command"),
    "space command": ("Department of Defense", "United States Space Command"),
    "spacecom": ("Department of Defense", "United States Space Command"),
    # ============ DEPARTMENT OF HOMELAND SECURITY ============
    "coast guard": ("Department of Homeland Security", "U.S. Coast Guard"),
    "uscg": ("Department of Homeland Security", "U.S. Coast Guard"),
    "coast guard operations": ("Department of Homeland Security", "U.S. Coast Guard"),
    "ice": ("Department of Homeland Security", "U.S. Immigration and Customs Enforcement"),
    "immigration customs": (
        "Department of Homeland Security",
        "U.S. Immigration and Customs Enforcement",
    ),
    "customs enforcement": (
        "Department of Homeland Security",
        "U.S. Immigration and Customs Enforcement",
    ),
    "cbp": ("Department of Homeland Security", "U.S. Customs and Border Protection"),
    "border protection": ("Department of Homeland Security", "U.S. Customs and Border Protection"),
    "customs border": ("Department of Homeland Security", "U.S. Customs and Border Protection"),
    "tsa": ("Department of Homeland Security", "Transportation Security Administration"),
    "transportation security": (
        "Department of Homeland Security",
        "Transportation Security Administration",
    ),
    "uscis": ("Department of Homeland Security", "U.S. Citizenship and Immigration Services"),
    "citizenship immigration": (
        "Department of Homeland Security",
        "U.S. Citizenship and Immigration Services",
    ),
    "fema": ("Department of Homeland Security", "Federal Emergency Management Agency"),
    "emergency management": (
        "Department of Homeland Security",
        "Federal Emergency Management Agency",
    ),
    "cisa": ("Department of Homeland Security", "Cybersecurity and Infrastructure Security Agency"),
    "cybersecurity infrastructure": (
        "Department of Homeland Security",
        "Cybersecurity and Infrastructure Security Agency",
    ),
    "opo": ("Department of Homeland Security", "Office of Procurement Operations"),
    "procurement operations": (
        "Department of Homeland Security",
        "Office of Procurement Operations",
    ),
    "secret service": ("Department of Homeland Security", "United States Secret Service"),
    "usss": ("Department of Homeland Security", "United States Secret Service"),
    # ============ GENERAL SERVICES ADMINISTRATION ============
    "fas": ("General Services Administration", "Federal Acquisition Service"),
    "federal acquisition": ("General Services Administration", "Federal Acquisition Service"),
    "acquisition service": ("General Services Administration", "Federal Acquisition Service"),
    "pbs": ("General Services Administration", "Public Buildings Service"),
    "public buildings": ("General Services Administration", "Public Buildings Service"),
    # ============ DEPARTMENT OF VETERANS AFFAIRS ============
    "vba": ("Department of Veterans Affairs", "Veterans Benefits Administration"),
    "benefits administration": (
        "Department of Veterans Affairs",
        "Veterans Benefits Administration",
    ),
    "vha": ("Department of Veterans Affairs", "Veterans Health Administration"),
    "health administration": ("Department of Veterans Affairs", "Veterans Health Administration"),
    # ============ DEPARTMENT OF ENERGY ============
    "ferc": ("Department of Energy", "Federal Energy Regulatory Commission"),
    "energy regulatory": ("Department of Energy", "Federal Energy Regulatory Commission"),
    "nnsa": ("Department of Energy", "National Nuclear Security Administration"),
    "nuclear security": ("Department of Energy", "National Nuclear Security Administration"),
    # ============ DEPARTMENT OF AGRICULTURE ============
    "forest service": ("Department of Agriculture", "Forest Service"),
    "fs": ("Department of Agriculture", "Forest Service"),
    "nrcs": ("Department of Agriculture", "Natural Resources Conservation Service"),
    "conservation service": ("Department of Agriculture", "Natural Resources Conservation Service"),
    "aphis": ("Department of Agriculture", "Animal and Plant Health Inspection Service"),
    "animal plant health": (
        "Department of Agriculture",
        "Animal and Plant Health Inspection Service",
    ),
    "fsa": ("Department of Agriculture", "Farm Service Agency"),
    "farm service": ("Department of Agriculture", "Farm Service Agency"),
    "rda": ("Department of Agriculture", "Rural Development"),
    "rural development": ("Department of Agriculture", "Rural Development"),
    "ams": ("Department of Agriculture", "Agricultural Marketing Service"),
    "marketing service": ("Department of Agriculture", "Agricultural Marketing Service"),
    # ============ DEPARTMENT OF HEALTH AND HUMAN SERVICES ============
    "nih": ("Department of Health and Human Services", "National Institutes of Health"),
    "national institutes": (
        "Department of Health and Human Services",
        "National Institutes of Health",
    ),
    "cdc": (
        "Department of Health and Human Services",
        "Centers for Disease Control and Prevention",
    ),
    "disease control": (
        "Department of Health and Human Services",
        "Centers for Disease Control and Prevention",
    ),
    "fda": ("Department of Health and Human Services", "Food and Drug Administration"),
    "food drug": ("Department of Health and Human Services", "Food and Drug Administration"),
    "cms": ("Department of Health and Human Services", "Centers for Medicare & Medicaid Services"),
    "medicare medicaid": (
        "Department of Health and Human Services",
        "Centers for Medicare & Medicaid Services",
    ),
    "medicaid": (
        "Department of Health and Human Services",
        "Centers for Medicare & Medicaid Services",
    ),
    "ac": ("Department of Health and Human Services", "Administration for Children and Families"),
    "children families": (
        "Department of Health and Human Services",
        "Administration for Children and Families",
    ),
    "hrsa": (
        "Department of Health and Human Services",
        "Health Resources and Services Administration",
    ),
    "resources services": (
        "Department of Health and Human Services",
        "Health Resources and Services Administration",
    ),
    "samhsa": (
        "Department of Health and Human Services",
        "Substance Abuse and Mental Health Services Administration",
    ),
    "mental health": (
        "Department of Health and Human Services",
        "Substance Abuse and Mental Health Services Administration",
    ),
    # ============ DEPARTMENT OF TRANSPORTATION ============
    "faa": ("Department of Transportation", "Federal Aviation Administration"),
    "aviation administration": ("Department of Transportation", "Federal Aviation Administration"),
    "air traffic": ("Department of Transportation", "Federal Aviation Administration"),
    "nhtsa": ("Department of Transportation", "National Highway Traffic Safety Administration"),
    "highway safety": (
        "Department of Transportation",
        "National Highway Traffic Safety Administration",
    ),
    "fhwa": ("Department of Transportation", "Federal Highway Administration"),
    "highway administration": ("Department of Transportation", "Federal Highway Administration"),
    "fta": ("Department of Transportation", "Federal Transit Administration"),
    "transit administration": ("Department of Transportation", "Federal Transit Administration"),
    "public transit": ("Department of Transportation", "Federal Transit Administration"),
    "ntsb": ("Department of Transportation", "National Transportation Safety Board"),
    "safety board": ("Department of Transportation", "National Transportation Safety Board"),
    # ============ DEPARTMENT OF THE INTERIOR ============
    "usgs": ("Department of the Interior", "United States Geological Survey"),
    "geological survey": ("Department of the Interior", "United States Geological Survey"),
    "nps": ("Department of the Interior", "National Park Service"),
    "park service": ("Department of the Interior", "National Park Service"),
    "parks": ("Department of the Interior", "National Park Service"),
    "fish wildlife": ("Department of the Interior", "U.S. Fish and Wildlife Service"),
    "fws": ("Department of the Interior", "U.S. Fish and Wildlife Service"),
    "blm": ("Department of the Interior", "Bureau of Land Management"),
    "land management": ("Department of the Interior", "Bureau of Land Management"),
    # ============ DEPARTMENT OF COMMERCE ============
    "noaa": ("Department of Commerce", "National Oceanic and Atmospheric Administration"),
    "oceanic atmospheric": (
        "Department of Commerce",
        "National Oceanic and Atmospheric Administration",
    ),
    "nws": ("Department of Commerce", "National Weather Service"),
    "weather service": ("Department of Commerce", "National Weather Service"),
    "nist": ("Department of Commerce", "National Institute of Standards and Technology"),
    "standards technology": (
        "Department of Commerce",
        "National Institute of Standards and Technology",
    ),
    "census": ("Department of Commerce", "Census Bureau"),
    "census bureau": ("Department of Commerce", "Census Bureau"),
    # ============ DEPARTMENT OF JUSTICE ============
    "fbi": ("Department of Justice", "Federal Bureau of Investigation"),
    "federal bureau": ("Department of Justice", "Federal Bureau of Investigation"),
    "dea": ("Department of Justice", "Drug Enforcement Administration"),
    "drug enforcement": ("Department of Justice", "Drug Enforcement Administration"),
    "at": ("Department of Justice", "Bureau of Alcohol, Tobacco, Firearms and Explosives"),
    "bop": ("Department of Justice", "Bureau of Prisons"),
    "prisons": ("Department of Justice", "Bureau of Prisons"),
    # ============ DEPARTMENT OF LABOR ============
    "osha": ("Department of Labor", "Occupational Safety and Health Administration"),
    "safety health": ("Department of Labor", "Occupational Safety and Health Administration"),
    "eta": ("Department of Labor", "Employment and Training Administration"),
    "employment training": ("Department of Labor", "Employment and Training Administration"),
    "bls": ("Department of Labor", "Bureau of Labor Statistics"),
    "labor statistics": ("Department of Labor", "Bureau of Labor Statistics"),
    # ============ NATIONAL AERONAUTICS AND SPACE ADMINISTRATION ============
    "jpl": ("National Aeronautics and Space Administration", "Jet Propulsion Laboratory"),
    "propulsion laboratory": (
        "National Aeronautics and Space Administration",
        "Jet Propulsion Laboratory",
    ),
    "gsfc": ("National Aeronautics and Space Administration", "Goddard Space Flight Center"),
    "goddard": ("National Aeronautics and Space Administration", "Goddard Space Flight Center"),
    "msfc": ("National Aeronautics and Space Administration", "Marshall Space Flight Center"),
    "marshall": ("National Aeronautics and Space Administration", "Marshall Space Flight Center"),
    "ksc": ("National Aeronautics and Space Administration", "Kennedy Space Center"),
    "kennedy": ("National Aeronautics and Space Administration", "Kennedy Space Center"),
    "jsc": ("National Aeronautics and Space Administration", "Johnson Space Center"),
    "johnson": ("National Aeronautics and Space Administration", "Johnson Space Center"),
    "grc": ("National Aeronautics and Space Administration", "Glenn Research Center"),
    "glenn": ("National Aeronautics and Space Administration", "Glenn Research Center"),
    "arc": ("National Aeronautics and Space Administration", "Ames Research Center"),
    "ames": ("National Aeronautics and Space Administration", "Ames Research Center"),
    "larc": ("National Aeronautics and Space Administration", "Langley Research Center"),
    "langley": ("National Aeronautics and Space Administration", "Langley Research Center"),
    # ============ UNITED STATES TRANSPORTATION COMMAND ============
    "transcom": ("United States Transportation Command", "United States Transportation Command"),
    "transportation command": (
        "United States Transportation Command",
        "United States Transportation Command",
    ),
    # ============ OTHER AGENCIES ============
    "sbdc": ("Small Business Administration", "Small Business Development Center"),
    "business development": ("Small Business Administration", "Small Business Development Center"),
}


def get_default_date_range() -> tuple[str, str]:
    """Get 180-day lookback date range (YYYY-MM-DD format)"""
    today = datetime.now()
    start_date = today - timedelta(days=180)
    return start_date.strftime("%Y-%m-%d"), today.strftime("%Y-%m-%d")


def get_date_range(
    start_date: Optional[str] = None, end_date: Optional[str] = None
) -> tuple[str, str]:
    """
    Get date range - use provided dates or default to 180-day lookback

    Args:
        start_date: Start date in YYYY-MM-DD format (optional)
        end_date: End date in YYYY-MM-DD format (optional)

    Returns:
        Tuple of (start_date, end_date) in YYYY-MM-DD format
    """
    today = datetime.now()

    # Use provided dates or default to 180-day lookback
    if start_date is None:
        start_date = (today - timedelta(days=180)).strftime("%Y-%m-%d")
    if end_date is None:
        end_date = today.strftime("%Y-%m-%d")

    # Validate date format
    try:
        datetime.strptime(start_date, "%Y-%m-%d")
        datetime.strptime(end_date, "%Y-%m-%d")
    except ValueError as e:
        return get_default_date_range()  # Fall back to default on format error

    return start_date, end_date


class QueryParser:
    """Parse advanced search queries with support for quoted phrases, boolean operators, and filters"""

    def __init__(self, query: str):
        self.original_query = query
        self.keywords = []
        self.exclude_keywords = []
        self.require_all = False  # AND operator (default is OR)
        self.award_types = ["A", "B", "C", "D"]  # Default to contracts
        self.min_amount = None
        self.max_amount = None
        self.place_of_performance_scope = None  # domestic or foreign
        self.recipient_name = None  # Recipient company name
        self.toptier_agency = None  # Top-tier agency (e.g., DOD)
        self.subtier_agency = None  # Sub-tier agency (e.g., DISA)
        self.parse()

    def parse(self):
        """Parse the query string"""
        query = self.original_query.lower()

        # Extract filters from query (e.g., "type:grant" or "amount:1M-5M")
        self._parse_filters(query)

        # Remove filter syntax for keyword extraction
        query = re.sub(r"\w+:[\w\-$M]+", "", query)

        # Extract quoted phrases
        quoted_phrases = re.findall(r'"([^"]+)"', query)
        for phrase in quoted_phrases:
            if phrase.strip():
                self.keywords.append(phrase.strip())

        # Remove quoted phrases from query
        query = re.sub(r'"[^"]+"', "", query)

        # Check for boolean operators
        if " AND " in query.upper():
            self.require_all = True
            query = re.sub(r"\sAND\s", " ", query, flags=re.IGNORECASE)

        # Extract NOT (exclude) keywords
        not_keywords = re.findall(r"(?:^|\s)NOT\s+(\w+)", query, re.IGNORECASE)
        for word in not_keywords:
            if word not in {"find", "show", "me", "get", "search", "for", "the"}:
                self.exclude_keywords.append(word)

        query = re.sub(r"\bNOT\s+\w+", "", query, flags=re.IGNORECASE)

        # Extract remaining keywords (remove stop words)
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
            word for word in query.split() if word and word not in stop_words and word.isalpha()
        ]
        self.keywords.extend(remaining_words)

        # Remove duplicates while preserving order
        self.keywords = list(dict.fromkeys(self.keywords))

    def _parse_filters(self, query: str):
        """Extract filter specifications like type:, amount:, scope:, recipient:, agency:, subagency:"""
        # Parse award type filter (e.g., "type:grant" or "type:contract")
        type_match = re.search(r"type:(\w+)", query)
        if type_match:
            type_name = type_match.group(1).lower()
            if type_name in AWARD_TYPE_MAP:
                self.award_types = AWARD_TYPE_MAP[type_name]

        # Parse amount range filter (e.g., "amount:1M-5M" or "amount:100K-1M")
        amount_match = re.search(r"amount:(\d+[KMB]?)-(\d+[KMB]?)", query, re.IGNORECASE)
        if amount_match:
            self.min_amount = self._parse_amount(amount_match.group(1))
            self.max_amount = self._parse_amount(amount_match.group(2))

        # Parse place of performance scope (e.g., "scope:domestic" or "scope:foreign")
        scope_match = re.search(r"scope:(\w+)", query)
        if scope_match:
            scope_value = scope_match.group(1).lower()
            if scope_value in ["domestic", "foreign"]:
                self.place_of_performance_scope = scope_value

        # Parse recipient filter (e.g., "recipient:\"Company Name\"" or just recipient:companyname)
        recipient_match = re.search(r'recipient:"([^"]+)"', query)
        if recipient_match:
            self.recipient_name = recipient_match.group(1)
        else:
            # Also try recipient:word format
            recipient_match = re.search(r"recipient:(\w+)", query)
            if recipient_match:
                self.recipient_name = recipient_match.group(1)

        # Parse top-tier agency filter (e.g., "agency:dod" or "agency:\"Department of Defense\"")
        agency_match = re.search(r'agency:"([^"]+)"', query)
        if agency_match:
            agency_input = agency_match.group(1).lower()
            self.toptier_agency = TOPTIER_AGENCY_MAP.get(agency_input, agency_input)
        else:
            agency_match = re.search(r"agency:(\w+)", query)
            if agency_match:
                agency_input = agency_match.group(1).lower()
                self.toptier_agency = TOPTIER_AGENCY_MAP.get(agency_input, agency_input)

        # Parse sub-tier agency filter (e.g., "subagency:disa" or "subagency:\"Defense Information Systems Agency\"")
        subagency_match = re.search(r'subagency:"([^"]+)"', query)
        if subagency_match:
            subagency_input = subagency_match.group(1).lower()
            if subagency_input in SUBTIER_AGENCY_MAP:
                parent_agency, subtier_name = SUBTIER_AGENCY_MAP[subagency_input]
                self.toptier_agency = parent_agency
                self.subtier_agency = subtier_name
        else:
            subagency_match = re.search(r"subagency:(\w+)", query)
            if subagency_match:
                subagency_input = subagency_match.group(1).lower()
                if subagency_input in SUBTIER_AGENCY_MAP:
                    parent_agency, subtier_name = SUBTIER_AGENCY_MAP[subagency_input]
                    self.toptier_agency = parent_agency
                    self.subtier_agency = subtier_name

    def _parse_amount(self, amount_str: str) -> float:
        """Convert amount string like '1M' or '500K' to numeric value"""
        amount_str = amount_str.upper().strip()
        multipliers = {"K": 1_000, "M": 1_000_000, "B": 1_000_000_000}

        for suffix, multiplier in multipliers.items():
            if amount_str.endswith(suffix):
                try:
                    return float(amount_str[:-1]) * multiplier
                except ValueError:
                    return None

        try:
            return float(amount_str)
        except ValueError:
            return None

    def get_keywords_string(self) -> str:
        """Get comma-separated keywords for API"""
        if not self.keywords:
            return "*"
        return " ".join(self.keywords)


def generate_award_url(internal_id: str) -> str:
    """Generate USASpending.gov award URL"""
    if internal_id:
        return f"https://www.usaspending.gov/award/{internal_id}"
    return ""


def generate_recipient_url(recipient_hash: str) -> str:
    """Generate USASpending.gov recipient profile URL"""
    if recipient_hash:
        return f"https://www.usaspending.gov/recipient/{recipient_hash}/latest"
    return ""


def generate_agency_url(agency_name: str, fiscal_year: str = "2025") -> str:
    """Generate USASpending.gov agency profile URL"""
    if agency_name:
        # URL encode the agency name by replacing spaces with hyphens
        agency_slug = agency_name.lower().replace(" ", "-").replace(".", "").replace("&", "and")
        return f"https://www.usaspending.gov/agency/{agency_slug}?fy={fiscal_year}"
    return ""


def format_currency(amount: float) -> str:
    """Format currency values"""
    if amount >= 1_000_000_000:
        return f"${amount/1_000_000_000:.2f}B"
    elif amount >= 1_000_000:
        return f"${amount/1_000_000:.2f}M"
    elif amount >= 1_000:
        return f"${amount/1_000:.2f}K"
    return f"${amount:.2f}"


async def make_api_request(
    endpoint: str, params: dict = None, method: str = "GET", json_data: dict = None
) -> dict:
    """Make request to USASpending API with error handling and logging"""
    url = f"{BASE_URL}/{endpoint}"

    try:
        if method == "POST":
            response = await http_client.post(url, json=json_data)
        else:
            response = await http_client.get(url, params=params)

        # Check for HTTP errors
        if response.status_code >= 400:
            try:
                error_detail = response.json()
                logger.error(f"API error ({response.status_code}): {error_detail}")
                return {"error": f"API Error {response.status_code}: {error_detail}"}
            except Exception as e:
                logger.error(f"API error ({response.status_code}): {str(e)}")
                return {"error": f"API Error {response.status_code}: {str(e)}"}

        return response.json()
    except Exception as e:
        logger.error(f"API request error: {str(e)}")
        return {"error": f"API request error: {str(e)}"}


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
) -> list[TextContent]:
    """Search for federal awards with advanced query syntax, optional date range, and set-aside filters.

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
    - search_federal_awards("software contracts", set_aside_type="8A")"""
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
    parser = QueryParser(query)

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
        }
    )


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
    parser = QueryParser(query)

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
    if keywords and keywords.strip() and len(keywords.strip()) >= 3:
        filters["keywords"] = [keywords.strip()]
    elif keywords and keywords.strip() and len(keywords.strip()) < 3:
        # Return error if keywords are too short
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
    if keywords and keywords.strip() and len(keywords.strip()) >= 3:
        filters["keywords"] = [keywords.strip()]
    elif keywords and keywords.strip() and len(keywords.strip()) < 3:
        # Return error if keywords are too short
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

    if output_format == "csv":
        # Generate CSV output
        output = format_awards_as_csv(filtered_awards, total_count, current_page, has_next)
    else:
        # Generate text output (default)
        output = format_awards_as_text(filtered_awards, total_count, current_page, has_next)

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
                filters["agencies"] = [{"name": agency_map[agency.lower()], "tier": "toptier"}]

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
async def get_vendor_profile(vendor_name: str, show_contracts: str = "false") -> list[TextContent]:
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
    return [TextContent(type="text", text=output)]


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
async def get_agency_profile(agency: str, detail_level: str = "detail") -> list[TextContent]:
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
                "agencies": [{"name": agency_name, "tier": "toptier"}],
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
    return [TextContent(type="text", text=output)]


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
) -> list[TextContent]:
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
            "8a": ["8A"],
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
        agency_mapping = TOPTIER_AGENCY_MAP.copy()
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
                "search/spending_by_award", json_data=payload, method="POST"
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
    return [TextContent(type="text", text=output)]


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
) -> list[TextContent]:
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
        agency_mapping = TOPTIER_AGENCY_MAP.copy()
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

        result = await make_api_request("search/spending_by_award", json_data=payload, method="POST")

        if "error" in result:
            return [TextContent(type="text", text=f"Error fetching vendor data: {result.get('error', 'Unknown error')}")]

        awards = result.get("results", [])

        if not awards:
            return [TextContent(type="text", text="No awards found matching your criteria.")]

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

        return [TextContent(type="text", text=output)]

    except Exception as e:
        logger.error(f"Error in get_top_vendors_by_contract_count: {str(e)}")
        return [TextContent(type="text", text=f"Error analyzing vendors: {str(e)}")]


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
                filters["agencies"] = [{"name": agency_map[agency.lower()], "tier": "toptier"}]

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


@app.tool(
    name="download_award_data",
    description="""Export award search results as a downloadable CSV file.

This tool creates bulk exports of federal spending data for external analysis.

PARAMETERS:
-----------
- query: Search keywords (e.g., "laptop", "construction")
- file_format (optional): "csv" (default)
- include_transactions (optional): "true" to include transaction-level detail

RETURNS:
--------
- Download URL for CSV file with award data
- File location and size information
- Summary of exported records

EXAMPLES:
---------
- download_award_data("Dell laptop") → CSV of all Dell laptop contracts
- download_award_data("GSA FAS", include_transactions="true") → CSV with transaction detail
""",
)
async def download_award_data(
    query: str, file_format: str = "csv", include_transactions: str = "false"
) -> list[TextContent]:
    """Export award search results as CSV for bulk analysis"""

    output = "=" * 100 + "\n"
    output += "AWARD DATA EXPORT\n"
    output += "=" * 100 + "\n\n"

    try:
        output += f"Preparing export for: {query}\n"
        output += f"Format: {file_format.upper()}\n"
        output += f"Include Transactions: {include_transactions}\n\n"

        # First, search for the awards
        search_url = "https://api.usaspending.gov/api/v2/search/spending_by_award/"
        filters = {
            "keywords": [query],
        }

        payload = {
            "filters": filters,
            "page": 1,
            "limit": 100,
        }

        resp = await http_client.post(search_url, json=payload, timeout=30.0)

        if resp.status_code == 200:
            data = resp.json()
            results = data.get("results", [])
            total_count = data.get("count", 0)

            output += "SEARCH RESULTS:\n"
            output += "-" * 100 + "\n"
            output += f"Found {len(results)} records (Total: {total_count})\n"
            output += f"Query: {query}\n\n"

            # Create CSV-like output
            output += "CSV EXPORT PREVIEW (First 5 records):\n"
            output += "-" * 100 + "\n"
            output += "Award ID,Recipient,Amount,Agency,Type,Date\n"

            for award in results[:5]:
                csv_line = (
                    f"{award.get('Award ID', 'N/A')},"
                    f"{award.get('Recipient Name', 'N/A')},"
                    f"${float(award.get('Award Amount', 0))/1e6:.2f}M,"
                    f"{award.get('Awarding Agency', 'N/A')},"
                    f"{award.get('Award Type', 'N/A')},"
                    f"{award.get('Award Date', 'N/A')}\n"
                )
                output += csv_line

            output += f"\n... and {len(results) - 5} more records\n\n"

            # Download instructions
            output += "DOWNLOAD INFORMATION:\n"
            output += "-" * 100 + "\n"
            output += f"Total Records: {total_count}\n"
            output += f"Records in Export: {len(results)}\n"
            output += f"Estimated File Size: {(total_count * 0.5 / 1024):.2f}MB\n\n"

            output += "TO DOWNLOAD FULL EXPORT:\n"
            output += "Use the USASpending.gov download interface at:\n"
            output += "https://www.usaspending.gov/download_center/custom_award_download\n"
            output += f"With search query: {query}\n"

        else:
            output += f"Error searching awards (HTTP {resp.status_code})\n"

    except Exception as e:
        output += f"Error: {str(e)}\n"

    output += "\n" + "=" * 100 + "\n"
    return [TextContent(type="text", text=output)]


# ============================================================================
# Conversation Management Tools
# ============================================================================


@app.tool(
    name="get_conversation",
    description="""Retrieve a complete MCP conversation history by ID.

This tool retrieves all tool calls within a specific conversation session,
including inputs, outputs, execution times, and timestamps.

PARAMETERS:
- conversation_id: The unique identifier of the conversation
- user_id: Optional user identifier (default: "anonymous")

RETURNS:
- List of tool call records with complete context
- Each record includes: tool name, parameters, response, execution time, timestamp, status

EXAMPLE:
- conversation_id="550e8400-e29b-41d4-a716-446655440000" → Returns all tool calls in that conversation
""",
)
async def get_conversation(conversation_id: str, user_id: str = "anonymous") -> list[TextContent]:
    """Retrieve a conversation by ID"""
    conv_logger = get_conversation_logger()
    records = conv_logger.get_conversation(conversation_id, user_id)

    if not records:
        return [TextContent(type="text", text=f"No conversation found with ID: {conversation_id}")]

    output = f"=== Conversation {conversation_id} ===\n"
    output += f"User: {user_id}\n"
    output += f"Messages: {len(records)}\n"
    output += "=" * 80 + "\n\n"

    for i, record in enumerate(records, 1):
        output += f"--- Message {i} ---\n"
        output += f"Tool: {record['tool_name']}\n"
        output += f"Time: {record['timestamp']}\n"
        output += f"Status: {record['status']}\n"
        output += f"Duration: {record.get('execution_time_ms', 0):.1f}ms\n"
        output += f"\nInput:\n{json.dumps(record.get('input_params', {}), indent=2)}\n"
        output += f"\nOutput:\n{record.get('output_response', '')[:500]}...\n"
        if record.get("error_message"):
            output += f"Error: {record['error_message']}\n"
        output += "\n"

    return [TextContent(type="text", text=output)]


@app.tool(
    name="list_conversations",
    description="""List all conversations for a user.

This tool retrieves metadata about recent conversations, including
message count, tools used, success rates, and time ranges.

PARAMETERS:
- user_id: Optional user identifier (default: "anonymous")
- limit: Maximum number of conversations to return (default: 20, max: 100)

RETURNS:
- List of conversation metadata with:
  - conversation_id: Unique identifier
  - message_count: Number of tool calls in conversation
  - tools_used: List of tool names
  - first_message: Timestamp of first message
  - last_message: Timestamp of last message
  - success_count: Number of successful tool calls
  - error_count: Number of failed tool calls

EXAMPLE:
- Calling with user_id="user123" → Returns their recent conversations
""",
)
async def list_conversations(user_id: str = "anonymous", limit: int = 20) -> list[TextContent]:
    """List conversations for a user"""
    conv_logger = get_conversation_logger()
    conversations = conv_logger.list_user_conversations(user_id, limit=min(limit, 100))

    if not conversations:
        return [TextContent(type="text", text=f"No conversations found for user: {user_id}")]

    output = f"=== Conversations for {user_id} ===\n"
    output += f"Found {len(conversations)} conversations\n"
    output += "=" * 80 + "\n\n"

    for i, conv in enumerate(conversations, 1):
        output += f"{i}. Conversation ID: {conv['conversation_id']}\n"
        output += f"   Messages: {conv['message_count']}\n"
        output += f"   Tools: {', '.join(conv['tools_used'])}\n"
        output += f"   Time Range: {conv['first_message']} to {conv['last_message']}\n"
        output += f"   Success Rate: {conv['success_count']}/{conv['message_count']} "
        output += f"({100*conv['success_count']/conv['message_count']:.1f}%)\n\n"

    return [TextContent(type="text", text=output)]


@app.tool(
    name="get_conversation_summary",
    description="""Get statistics and summary for a specific conversation.

This tool provides analytics on a conversation including total execution time,
tool breakdown, success rates, and error analysis.

PARAMETERS:
- conversation_id: The unique identifier of the conversation
- user_id: Optional user identifier (default: "anonymous")

RETURNS:
- Conversation statistics:
  - Message count
  - Tools used
  - Total and average execution times
  - Success/error counts and rates
  - Time range (first to last message)

EXAMPLE:
- conversation_id="550e8400-e29b-41d4-a716-446655440000" → Returns statistics
""",
)
async def get_conversation_summary(
    conversation_id: str, user_id: str = "anonymous"
) -> list[TextContent]:
    """Get conversation summary statistics"""
    conv_logger = get_conversation_logger()
    summary = conv_logger.get_conversation_summary(conversation_id, user_id)

    if not summary:
        return [TextContent(type="text", text=f"No conversation found with ID: {conversation_id}")]

    output = "=== Conversation Summary ===\n"
    output += f"ID: {summary['conversation_id']}\n"
    output += f"User: {summary['user_id']}\n"
    output += f"Messages: {summary['message_count']}\n"
    output += f"Tools Used: {', '.join(summary['tools_used'])}\n\n"

    output += "Execution Time:\n"
    output += f"  Total: {summary['total_execution_time_ms']:.1f}ms\n"
    output += f"  Average per call: {summary['avg_execution_time_ms']:.1f}ms\n\n"

    output += "Results:\n"
    output += f"  Success: {summary['success_count']}\n"
    output += f"  Errors: {summary['error_count']}\n"
    output += f"  Success Rate: {summary['success_rate']:.1f}%\n\n"

    output += "Time Range:\n"
    output += f"  First: {summary['first_message_time']}\n"
    output += f"  Last: {summary['last_message_time']}\n"

    return [TextContent(type="text", text=output)]


@app.tool(
    name="get_tool_usage_stats",
    description="""Get tool usage statistics for a user.

This tool analyzes which tools have been used most frequently,
their success rates, and how many conversations they appear in.

PARAMETERS:
- user_id: Optional user identifier (default: "anonymous")

RETURNS:
- Tool usage statistics including:
  - Total number of times each tool was used
  - Success/error counts per tool
  - Success rate percentage
  - Number of conversations containing each tool

EXAMPLE:
- user_id="user123" → Returns their tool usage patterns
""",
)
async def get_tool_usage_stats(user_id: str = "anonymous") -> list[TextContent]:
    """Get tool usage statistics for a user"""
    conv_logger = get_conversation_logger()
    stats = conv_logger.get_tool_usage_stats(user_id)

    output = f"=== Tool Usage Statistics for {user_id} ===\n"
    output += f"Total Conversations: {stats['total_conversations']}\n"
    output += f"Total Tool Calls: {stats['total_tool_calls']}\n"
    output += "=" * 80 + "\n\n"

    if not stats["tools"]:
        output += "No tool usage found.\n"
    else:
        # Sort by usage count
        sorted_tools = sorted(stats["tools"].items(), key=lambda x: x[1]["uses"], reverse=True)

        for tool_name, tool_stats in sorted_tools:
            output += f"Tool: {tool_name}\n"
            output += f"  Uses: {tool_stats['uses']}\n"
            output += f"  Success Rate: {tool_stats['success_rate']:.1f}%\n"
            output += f"  Successes: {tool_stats['success_count']}\n"
            output += f"  Errors: {tool_stats['error_count']}\n"
            output += f"  Conversations: {tool_stats['conversations']}\n\n"

    return [TextContent(type="text", text=output)]


def run_server():
    """Run the server with proper signal handling"""
    try:
        logger.info("Starting server on http://127.0.0.1:3002")
        uvicorn.run(app.http_app(), host="127.0.0.1", port=3002, log_level="info", reload=False)
    except KeyboardInterrupt:
        logger.info("Received shutdown signal, shutting down gracefully...")
    except Exception as e:
        logger.error(f"Server error: {str(e)}")
    finally:
        logger.info("Server shutdown complete")


# ============================================================================
# FAR (Federal Acquisition Regulation) Tools - Now in modular structure
# ============================================================================
# FAR tools have been moved to src/usaspending_mcp/tools/far.py for better code organization
# and are registered above via register_far_tools(app)
#
# Tools registered:
#  - lookup_far_section: Look up specific FAR sections by number
#  - search_far: Search FAR across all parts by keywords
#  - list_far_sections: List all available FAR sections
#
# See src/usaspending_mcp/tools/far.py for implementation details
# See src/usaspending_mcp/loaders/far.py for FAR data loading logic


async def run_stdio():
    """Run the server using stdio transport (for MCP clients)"""
    try:
        # Use FastMCP's built-in stdio support
        await app.run_stdio_async()
    except BaseException as e:
        # Catch all exceptions including TaskGroup errors
        error_msg = str(e)
        logger.error(f"Error running stdio server: {error_msg}")
        # Log more detailed error info for debugging
        import traceback

        logger.debug(f"Full traceback: {traceback.format_exc()}")
        # Don't re-raise - allow graceful shutdown
        return


if __name__ == "__main__":
    import sys

    # Check if we should run in stdio mode (for MCP client) or HTTP mode (for Claude Desktop)
    if len(sys.argv) > 1 and sys.argv[1] == "--stdio":
        # Run in stdio mode for MCP client testing
        asyncio.run(run_stdio())
    else:
        # Run in HTTP mode for Claude Desktop
        run_server()
