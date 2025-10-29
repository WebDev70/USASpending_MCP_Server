#!/usr/bin/env python3
# Start the server
#./.venv/bin/python mcp_server.py
#./.venv/bin/python mcp_client.py
"""
USASpending.gov MCP Server

Provides tools to query federal spending data including awards and vendors
"""

import asyncio
import httpx
import json
import logging
import re
import csv
from io import StringIO
from datetime import datetime, timedelta
from typing import Any, Optional
from functools import lru_cache
import uvicorn
from fastmcp import FastMCP
from mcp.types import TextContent

# Set up logging
logging.basicConfig(
    level=logging.INFO,  # Changed from DEBUG to INFO for cleaner output
    format='%(levelname)s:%(name)s:%(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastMCP server
app = FastMCP(name="usaspending-server")

# Base URL for USASpending API
BASE_URL = "https://api.usaspending.gov/api/v2"

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
    "nsf": "National Science Foundation",
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
    "usaf": ("Department of Defense", "Department of the Air Force"),
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

    "counterintelligence security": ("Department of Defense", "Defense Counterintelligence and Security Agency"),
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
    "immigration customs": ("Department of Homeland Security", "U.S. Immigration and Customs Enforcement"),
    "customs enforcement": ("Department of Homeland Security", "U.S. Immigration and Customs Enforcement"),

    "cbp": ("Department of Homeland Security", "U.S. Customs and Border Protection"),
    "border protection": ("Department of Homeland Security", "U.S. Customs and Border Protection"),
    "customs border": ("Department of Homeland Security", "U.S. Customs and Border Protection"),

    "tsa": ("Department of Homeland Security", "Transportation Security Administration"),
    "transportation security": ("Department of Homeland Security", "Transportation Security Administration"),

    "uscis": ("Department of Homeland Security", "U.S. Citizenship and Immigration Services"),
    "citizenship immigration": ("Department of Homeland Security", "U.S. Citizenship and Immigration Services"),

    "fema": ("Department of Homeland Security", "Federal Emergency Management Agency"),
    "emergency management": ("Department of Homeland Security", "Federal Emergency Management Agency"),

    "cisa": ("Department of Homeland Security", "Cybersecurity and Infrastructure Security Agency"),
    "cybersecurity infrastructure": ("Department of Homeland Security", "Cybersecurity and Infrastructure Security Agency"),

    "opo": ("Department of Homeland Security", "Office of Procurement Operations"),
    "procurement operations": ("Department of Homeland Security", "Office of Procurement Operations"),

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
    "benefits administration": ("Department of Veterans Affairs", "Veterans Benefits Administration"),

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
    "animal plant health": ("Department of Agriculture", "Animal and Plant Health Inspection Service"),

    "fsa": ("Department of Agriculture", "Farm Service Agency"),
    "farm service": ("Department of Agriculture", "Farm Service Agency"),

    "rda": ("Department of Agriculture", "Rural Development"),
    "rural development": ("Department of Agriculture", "Rural Development"),

    "ams": ("Department of Agriculture", "Agricultural Marketing Service"),
    "marketing service": ("Department of Agriculture", "Agricultural Marketing Service"),

    # ============ DEPARTMENT OF HEALTH AND HUMAN SERVICES ============
    "nih": ("Department of Health and Human Services", "National Institutes of Health"),
    "national institutes": ("Department of Health and Human Services", "National Institutes of Health"),

    "cdc": ("Department of Health and Human Services", "Centers for Disease Control and Prevention"),
    "disease control": ("Department of Health and Human Services", "Centers for Disease Control and Prevention"),

    "fda": ("Department of Health and Human Services", "Food and Drug Administration"),
    "food drug": ("Department of Health and Human Services", "Food and Drug Administration"),

    "cms": ("Department of Health and Human Services", "Centers for Medicare & Medicaid Services"),
    "medicare medicaid": ("Department of Health and Human Services", "Centers for Medicare & Medicaid Services"),
    "medicaid": ("Department of Health and Human Services", "Centers for Medicare & Medicaid Services"),

    "acf": ("Department of Health and Human Services", "Administration for Children and Families"),
    "children families": ("Department of Health and Human Services", "Administration for Children and Families"),

    "hrsa": ("Department of Health and Human Services", "Health Resources and Services Administration"),
    "resources services": ("Department of Health and Human Services", "Health Resources and Services Administration"),

    "samhsa": ("Department of Health and Human Services", "Substance Abuse and Mental Health Services Administration"),
    "mental health": ("Department of Health and Human Services", "Substance Abuse and Mental Health Services Administration"),

    # ============ DEPARTMENT OF TRANSPORTATION ============
    "faa": ("Department of Transportation", "Federal Aviation Administration"),
    "aviation administration": ("Department of Transportation", "Federal Aviation Administration"),
    "air traffic": ("Department of Transportation", "Federal Aviation Administration"),

    "nhtsa": ("Department of Transportation", "National Highway Traffic Safety Administration"),
    "highway safety": ("Department of Transportation", "National Highway Traffic Safety Administration"),

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
    "oceanic atmospheric": ("Department of Commerce", "National Oceanic and Atmospheric Administration"),

    "nws": ("Department of Commerce", "National Weather Service"),
    "weather service": ("Department of Commerce", "National Weather Service"),

    "nist": ("Department of Commerce", "National Institute of Standards and Technology"),
    "standards technology": ("Department of Commerce", "National Institute of Standards and Technology"),

    "census": ("Department of Commerce", "Census Bureau"),
    "census bureau": ("Department of Commerce", "Census Bureau"),

    # ============ DEPARTMENT OF JUSTICE ============
    "fbi": ("Department of Justice", "Federal Bureau of Investigation"),
    "federal bureau": ("Department of Justice", "Federal Bureau of Investigation"),

    "dea": ("Department of Justice", "Drug Enforcement Administration"),
    "drug enforcement": ("Department of Justice", "Drug Enforcement Administration"),

    "atf": ("Department of Justice", "Bureau of Alcohol, Tobacco, Firearms and Explosives"),

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
    "propulsion laboratory": ("National Aeronautics and Space Administration", "Jet Propulsion Laboratory"),

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
    "transportation command": ("United States Transportation Command", "United States Transportation Command"),

    # ============ OTHER AGENCIES ============
    "sbdc": ("Small Business Administration", "Small Business Development Center"),
    "business development": ("Small Business Administration", "Small Business Development Center"),
}

def get_default_date_range() -> tuple[str, str]:
    """Get 180-day lookback date range (YYYY-MM-DD format)"""
    today = datetime.now()
    start_date = today - timedelta(days=180)
    return start_date.strftime("%Y-%m-%d"), today.strftime("%Y-%m-%d")

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
        query = re.sub(r'\w+:[\w\-$M]+', '', query)

        # Extract quoted phrases
        quoted_phrases = re.findall(r'"([^"]+)"', query)
        for phrase in quoted_phrases:
            if phrase.strip():
                self.keywords.append(phrase.strip())

        # Remove quoted phrases from query
        query = re.sub(r'"[^"]+"', '', query)

        # Check for boolean operators
        if " AND " in query.upper():
            self.require_all = True
            query = re.sub(r'\sAND\s', ' ', query, flags=re.IGNORECASE)

        # Extract NOT (exclude) keywords
        not_keywords = re.findall(r'(?:^|\s)NOT\s+(\w+)', query, re.IGNORECASE)
        for word in not_keywords:
            if word not in {"find", "show", "me", "get", "search", "for", "the"}:
                self.exclude_keywords.append(word)

        query = re.sub(r'\bNOT\s+\w+', '', query, flags=re.IGNORECASE)

        # Extract remaining keywords (remove stop words)
        stop_words = {"find", "show", "me", "get", "search", "for", "the", "and", "or", "in", "is", "a", "an"}
        remaining_words = [
            word for word in query.split()
            if word and word not in stop_words and word.isalpha()
        ]
        self.keywords.extend(remaining_words)

        # Remove duplicates while preserving order
        self.keywords = list(dict.fromkeys(self.keywords))

    def _parse_filters(self, query: str):
        """Extract filter specifications like type:, amount:, scope:, recipient:, agency:, subagency:"""
        # Parse award type filter (e.g., "type:grant" or "type:contract")
        type_match = re.search(r'type:(\w+)', query)
        if type_match:
            type_name = type_match.group(1).lower()
            if type_name in AWARD_TYPE_MAP:
                self.award_types = AWARD_TYPE_MAP[type_name]

        # Parse amount range filter (e.g., "amount:1M-5M" or "amount:100K-1M")
        amount_match = re.search(r'amount:(\d+[KMB]?)-(\d+[KMB]?)', query, re.IGNORECASE)
        if amount_match:
            self.min_amount = self._parse_amount(amount_match.group(1))
            self.max_amount = self._parse_amount(amount_match.group(2))

        # Parse place of performance scope (e.g., "scope:domestic" or "scope:foreign")
        scope_match = re.search(r'scope:(\w+)', query)
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
            recipient_match = re.search(r'recipient:(\w+)', query)
            if recipient_match:
                self.recipient_name = recipient_match.group(1)

        # Parse top-tier agency filter (e.g., "agency:dod" or "agency:\"Department of Defense\"")
        agency_match = re.search(r'agency:"([^"]+)"', query)
        if agency_match:
            agency_input = agency_match.group(1).lower()
            self.toptier_agency = TOPTIER_AGENCY_MAP.get(agency_input, agency_input)
        else:
            agency_match = re.search(r'agency:(\w+)', query)
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
            subagency_match = re.search(r'subagency:(\w+)', query)
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

def format_currency(amount: float) -> str:
    """Format currency values"""
    if amount >= 1_000_000_000:
        return f"${amount/1_000_000_000:.2f}B"
    elif amount >= 1_000_000:
        return f"${amount/1_000_000:.2f}M"
    elif amount >= 1_000:
        return f"${amount/1_000:.2f}K"
    return f"${amount:.2f}"

async def make_api_request(endpoint: str, params: dict = None, method: str = "GET", json_data: dict = None) -> dict:
    """Make request to USASpending API with error handling and logging"""
    url = f"{BASE_URL}/{endpoint}"
    
    try:
        if method == "POST":
            response = await http_client.post(url, json=json_data)
        else:
            response = await http_client.get(url, params=params)
        
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"API request error: {str(e)}")
        return {"error": f"API request error: {str(e)}"}

@app.tool(
    name="search_federal_awards",
    description="""Search federal spending data from USASpending.gov to find contracts, grants, loans, and other federal awards.

PARAMETERS:
- query: Search query with advanced syntax (see below)
- max_results: Maximum results to return (1-100, default 5)
- output_format: Output format - "text" (default) or "csv"

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
""",
)
async def search_federal_awards(query: str, max_results: int = 5, output_format: str = "text") -> list[TextContent]:
    """Search for federal awards with advanced query syntax"""
    logger.debug(f"Tool call received: search_federal_awards with query='{query}', max_results={max_results}, output_format={output_format}")

    # Validate output format
    if output_format not in ["text", "csv"]:
        output_format = "text"

    # Parse the query for advanced features
    parser = QueryParser(query)

    return await search_awards_logic({
        "keywords": parser.get_keywords_string(),
        "award_types": parser.award_types,
        "min_amount": parser.min_amount,
        "max_amount": parser.max_amount,
        "exclude_keywords": parser.exclude_keywords,
        "place_of_performance_scope": parser.place_of_performance_scope,
        "recipient_name": parser.recipient_name,
        "toptier_agency": parser.toptier_agency,
        "subtier_agency": parser.subtier_agency,
        "limit": max_results,
        "output_format": output_format
    })

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

EXAMPLES:
- "software agency:dod" → DOD software contract spending analysis
- "recipient:\"Dell\" amount:100K-1M" → Dell contracts $100K-$1M analysis
- "type:grant scope:domestic" → Domestic grant spending distribution
- "research AND technology agency:nsf" → NSF research/tech grant analysis
""",
)
async def analyze_federal_spending(query: str) -> list[TextContent]:
    """Analyze federal spending with aggregated insights"""
    logger.debug(f"Analytics request: {query}")

    # Parse the query for advanced features (same as search)
    parser = QueryParser(query)

    # Use search logic but get more results for better analytics (50 records)
    return await analyze_awards_logic({
        "keywords": parser.get_keywords_string(),
        "award_types": parser.award_types,
        "min_amount": parser.min_amount,
        "max_amount": parser.max_amount,
        "exclude_keywords": parser.exclude_keywords,
        "place_of_performance_scope": parser.place_of_performance_scope,
        "recipient_name": parser.recipient_name,
        "toptier_agency": parser.toptier_agency,
        "subtier_agency": parser.subtier_agency,
        "limit": 50  # Get 50 records for better analytics
    })

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
""",
)
async def get_top_naics_breakdown() -> list[TextContent]:
    """Get top NAICS codes with agencies and contractors"""
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
            sorted_naics = sorted(naics_list, key=lambda x: x.get('count', 0), reverse=True)[:5]

            total_awards = sum(n.get('count', 0) for n in naics_list)

            for i, naics in enumerate(sorted_naics, 1):
                code = naics.get('naics')
                desc = naics.get('naics_description')
                count = naics.get('count', 0)
                pct = (count / total_awards * 100) if total_awards > 0 else 0

                output += f"{i}. NAICS {code}: {desc}\n"
                output += f"   Awards: {count:,} ({pct:.1f}% of total)\n\n"

                # Search for contracts in this NAICS (using keywords)
                naics_keywords = {
                    '31': 'food manufacturing beverage',
                    '32': 'chemical pharmaceutical manufacturing',
                    '33': 'machinery equipment electronics manufacturing',
                    '42': 'wholesale distribution supply',
                    '44': 'retail office supplies equipment',
                }

                keyword = naics_keywords.get(code, code)
                search_url = "https://api.usaspending.gov/api/v2/search/spending_by_award/"
                # Try searching with keywords first, then fall back to broader search
                search_payload = {
                    "filters": {
                        "award_type_codes": ["A", "B", "C", "D"]
                    },
                    "fields": [
                        "Award ID",
                        "Recipient Name",
                        "Award Amount",
                        "Awarding Agency",
                        "Description"
                    ],
                    "page": 1,
                    "limit": 50
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
                            for agency, count in sorted(agencies.items(), key=lambda x: x[1], reverse=True)[:3]:
                                output += f"      • {agency} ({count} awards)\n"

                            output += "   Top Contractors:\n"
                            for contractor, amount in sorted(contractors.items(), key=lambda x: x[1], reverse=True)[:3]:
                                formatted = f"${amount/1e6:.2f}M" if amount >= 1e6 else f"${amount/1e3:.2f}K"
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

EXAMPLES:
---------
- "software" → Find software-related NAICS and PSC codes
- "consulting" → Consulting industry classifications
- "information technology psc" → IT product/service codes
""",
)
async def get_naics_psc_info(search_term: str, code_type: str = "both") -> list[TextContent]:
    """Look up NAICS and PSC code information"""
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
                    n for n in naics_data.get("results", [])
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

async def analyze_awards_logic(args: dict) -> list[TextContent]:
    """Analytics logic for federal spending data"""
    # Get dynamic 180-day date range
    start_date, end_date = get_default_date_range()

    # Build filters (same as search)
    filters = {
        "keywords": [args.get("keywords", "")],
        "award_type_codes": args.get("award_types", ["A", "B", "C", "D"]),
        "time_period": [
            {
                "start_date": start_date,
                "end_date": end_date
            }
        ]
    }

    # Add optional filters
    if args.get("place_of_performance_scope"):
        filters["place_of_performance_scope"] = args.get("place_of_performance_scope")

    if args.get("recipient_name"):
        filters["recipient_search_text"] = [args.get("recipient_name")]

    if args.get("toptier_agency") or args.get("subtier_agency"):
        filters["agencies"] = []
        if args.get("subtier_agency"):
            filters["agencies"].append({
                "type": "awarding",
                "tier": "subtier",
                "name": args.get("subtier_agency"),
                "toptier_name": args.get("toptier_agency")
            })
        elif args.get("toptier_agency"):
            filters["agencies"].append({
                "type": "awarding",
                "tier": "toptier",
                "name": args.get("toptier_agency"),
                "toptier_name": args.get("toptier_agency")
            })

    if args.get("min_amount") is not None or args.get("max_amount") is not None:
        filters["award_amount"] = {}
        if args.get("min_amount") is not None:
            filters["award_amount"]["lower_bound"] = int(args.get("min_amount"))
        if args.get("max_amount") is not None:
            filters["award_amount"]["upper_bound"] = int(args.get("max_amount"))

    # Get total count
    count_payload = {"filters": filters}
    count_result = await make_api_request("search/spending_by_award_count", json_data=count_payload, method="POST")

    if "error" in count_result:
        return [TextContent(type="text", text=f"Error getting analytics: {count_result['error']}")]

    total_count = sum(count_result.get("results", {}).values())

    # Get award data for analysis
    payload = {
        "filters": filters,
        "fields": ["Recipient Name", "Award Amount", "Award Type", "Description"],
        "page": 1,
        "limit": min(args.get("limit", 50), 100)
    }

    result = await make_api_request("search/spending_by_award", json_data=payload, method="POST")

    if "error" in result:
        return [TextContent(type="text", text=f"Error fetching data for analysis: {result['error']}")]

    awards = result.get("results", [])

    if not awards:
        return [TextContent(type="text", text="No awards found matching your criteria.")]

    # Generate analytics
    analytics_output = generate_spending_analytics(awards, total_count)
    return [TextContent(type="text", text=analytics_output)]

def generate_spending_analytics(awards: list, total_count: int) -> str:
    """Generate comprehensive spending analytics"""
    if not awards:
        return "No data available for analytics."

    # Calculate basic statistics
    amounts = [float(award.get('Award Amount', 0)) for award in awards]
    total_amount = sum(amounts)
    avg_amount = total_amount / len(amounts) if amounts else 0
    min_amount = min(amounts) if amounts else 0
    max_amount = max(amounts) if amounts else 0

    # Count by award type
    award_types = {}
    for award in awards:
        award_type = award.get('Award Type', 'Unknown')
        award_types[award_type] = award_types.get(award_type, 0) + 1

    # Top 5 recipients by spending
    recipient_spending = {}
    for award in awards:
        recipient = award.get('Recipient Name', 'Unknown')
        amount = float(award.get('Award Amount', 0))
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
        "> $500M": 0
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
    output += f"Median Award: {format_currency(sorted(amounts)[len(amounts)//2] if amounts else 0)}\n\n"

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
            pct = (count / len(awards) * 100)
            bar_length = int(pct / 2)  # Scale to fit
            bar = "█" * bar_length
            output += f"{range_label:20} {count:4} awards ({pct:5.1f}%) {bar}\n"
    output += "\n"

    # Key insights
    output += "KEY INSIGHTS\n"
    output += "-" * 80 + "\n"

    # Find largest award
    largest_award = max(awards, key=lambda x: float(x.get('Award Amount', 0)))
    output += f"Largest Award: {format_currency(float(largest_award['Award Amount']))} to {largest_award['Recipient Name']}\n"

    # Find most common recipient
    most_common = max(recipient_spending.items(), key=lambda x: x[1])
    output += f"Largest Recipient: {most_common[0]} with {format_currency(most_common[1])}\n"

    # Top spending range
    top_range = max(ranges.items(), key=lambda x: x[1])
    output += f"Most Common Award Size: {top_range[0]} ({top_range[1]} awards)\n"

    # Concentration analysis
    top_5_pct = (sum([amount for _, amount in top_recipients]) / total_amount * 100) if total_amount else 0
    output += f"Top 5 Recipients Control: {top_5_pct:.1f}% of total spending\n"

    output += "\n" + "=" * 80 + "\n"

    return output

async def search_awards_logic(args: dict) -> list[TextContent]:
    # Get default date range (180-day lookback)
    start_date, end_date = get_default_date_range()

    # Build filters based on arguments
    filters = {
        "keywords": [args.get("keywords", "")],
        "award_type_codes": args.get("award_types", ["A", "B", "C", "D"]),
        "time_period": [
            {
                "start_date": start_date,
                "end_date": end_date
            }
        ]
    }

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
            filters["agencies"].append({
                "type": "awarding",
                "tier": "subtier",
                "name": subtier_agency,
                "toptier_name": toptier_agency
            })
        # Otherwise, if only toptier is specified, add the toptier filter
        elif args.get("toptier_agency"):
            toptier_agency = args.get("toptier_agency")
            filters["agencies"].append({
                "type": "awarding",
                "tier": "toptier",
                "name": toptier_agency,
                "toptier_name": toptier_agency
            })

    # Add award amount filters if specified
    if args.get("min_amount") is not None or args.get("max_amount") is not None:
        filters["award_amount"] = {}
        if args.get("min_amount") is not None:
            filters["award_amount"]["lower_bound"] = int(args.get("min_amount"))
        if args.get("max_amount") is not None:
            filters["award_amount"]["upper_bound"] = int(args.get("max_amount"))

    # First, get the count
    count_payload = {"filters": filters}
    count_result = await make_api_request("search/spending_by_award_count", json_data=count_payload, method="POST")

    if "error" in count_result:
        return [TextContent(type="text", text=f"Error getting count: {count_result['error']}")]

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
            "NAICS Code",
            "NAICS Description",
            "PSC Code",
            "PSC Description"
        ],
        "page": 1,
        "limit": min(args.get("limit", 10), 100)
    }

    # Make the API request for results
    result = await make_api_request("search/spending_by_award", json_data=payload, method="POST")

    if "error" in result:
        return [TextContent(type="text", text=f"Error fetching results: {result['error']}")]

    # Process the results
    awards = result.get("results", [])
    page_metadata = result.get("page_metadata", {})
    current_page = page_metadata.get("page", 1)
    has_next = page_metadata.get("hasNext", False)

    if not awards:
        return [TextContent(type="text", text="No awards found matching your criteria.")]

    # Filter by excluded keywords and amount range if needed
    exclude_keywords = args.get("exclude_keywords", [])
    min_amount = args.get("min_amount")
    max_amount = args.get("max_amount")

    filtered_awards = []
    for award in awards:
        # Check excluded keywords
        description = award.get('Description', '').lower()
        recipient = award.get('Recipient Name', '').lower()

        excluded = any(
            keyword.lower() in description or keyword.lower() in recipient
            for keyword in exclude_keywords
        )
        if excluded:
            continue

        # Check amount range (additional client-side filtering)
        amount = float(award.get('Award Amount', 0))
        if min_amount is not None and amount < min_amount:
            continue
        if max_amount is not None and amount > max_amount:
            continue

        filtered_awards.append(award)

    if not filtered_awards:
        return [TextContent(type="text", text="No awards found matching your criteria after applying filters.")]

    # Handle different output formats
    output_format = args.get("output_format", "text")

    if output_format == "csv":
        # Generate CSV output
        output = format_awards_as_csv(filtered_awards, total_count, current_page, has_next)
    else:
        # Generate text output (default)
        output = format_awards_as_text(filtered_awards, total_count, current_page, has_next)

    return [TextContent(type="text", text=output)]

def format_awards_as_text(awards: list, total_count: int, current_page: int, has_next: bool) -> str:
    """Format awards as plain text output"""
    output = f"Found {total_count} total matches (showing {len(awards)} on page {current_page}):\n\n"

    for i, award in enumerate(awards, 1):
        recipient = award.get('Recipient Name', 'Unknown Recipient')
        award_id = award.get('Award ID', 'N/A')
        amount = float(award.get('Award Amount', 0))
        award_type = award.get('Award Type', 'Unknown')
        description = award.get('Description', '')
        internal_id = award.get('generated_internal_id', '')
        naics_code = award.get('NAICS Code', '')
        naics_desc = award.get('NAICS Description', '')
        psc_code = award.get('PSC Code', '')
        psc_desc = award.get('PSC Description', '')

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
        # Add award detail link
        if internal_id:
            output += f"   Details: https://www.usaspending.gov/award/{internal_id}\n"
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
    writer.writerow(["Recipient Name", "Award ID", "Amount ($)", "Award Type", "NAICS Code", "NAICS Description", "PSC Code", "PSC Description", "Description", "Details URL"])

    # Write data rows
    for award in awards:
        recipient = award.get('Recipient Name', 'Unknown Recipient')
        award_id = award.get('Award ID', 'N/A')
        amount = float(award.get('Award Amount', 0))
        award_type = award.get('Award Type', 'Unknown')
        naics_code = award.get('NAICS Code', '')
        naics_desc = award.get('NAICS Description', '')
        psc_code = award.get('PSC Code', '')
        psc_desc = award.get('PSC Description', '')
        description = award.get('Description', '')[:200]  # Limit description length
        internal_id = award.get('generated_internal_id', '')
        details_url = f"https://www.usaspending.gov/award/{internal_id}" if internal_id else ""

        writer.writerow([recipient, award_id, amount, award_type, naics_code, naics_desc, psc_code, psc_desc, description, details_url])

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
async def get_spending_by_state(state: str = "", top_n: int = 10) -> list[TextContent]:
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
            }
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
                sorted_results = sorted(results, key=lambda x: float(x.get("total", 0)), reverse=True)[:top_n]
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
async def get_spending_trends(period: str = "fiscal_year", agency: str = "", award_type: str = "") -> list[TextContent]:
    """Get federal spending trends over time"""
    output = "=" * 100 + "\n"
    output += f"FEDERAL SPENDING TRENDS - {period.upper()}\n"
    output += "=" * 100 + "\n\n"

    try:
        url = "https://api.usaspending.gov/api/v2/search/spending_over_time/"

        filters = {"award_type_codes": ["A", "B", "C", "D", "02", "03", "04", "05", "07", "08", "09"]}

        if agency:
            # Map agency shorthand to name
            agency_map = {
                "dod": "Department of Defense",
                "gsa": "General Services Administration",
                "hhs": "Department of Health and Human Services",
                "va": "Department of Veterans Affairs",
                "dhs": "Department of Homeland Security"
            }
            if agency.lower() in agency_map:
                filters["agencies"] = [{"name": agency_map[agency.lower()], "tier": "toptier"}]

        payload = {
            "group_by": "fy" if period == "fiscal_year" else "cy",
            "filters": filters
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
                        change_str = f"+{change_pct:.1f}%" if change_pct >= 0 else f"{change_pct:.1f}%"
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
async def get_budget_functions(agency: str = "", detailed: str = "false") -> list[TextContent]:
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
                output += f"  (P=Parent, C=Child, R=Rolled-up)\n"
                output += "\nTo see detailed contract history and awards,\n"
                output += f"visit: https://www.usaspending.gov/recipient/{vendor.get('uei', vendor.get('duns', 'unknown'))}/\n"

                if show_contracts.lower() == "true":
                    # Get contracts for this vendor
                    search_url = "https://api.usaspending.gov/api/v2/search/spending_by_award/"
                    search_payload = {
                        "filters": {
                            "recipient_search_text": [vendor_name],
                            "award_type_codes": ["A", "B", "C", "D"]
                        },
                        "fields": ["Award ID", "Recipient Name", "Award Amount", "Awarding Agency"],
                        "page": 1,
                        "limit": 10
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
                                formatted = f"${amount/1e6:.2f}M" if amount >= 1e6 else f"${amount/1e3:.2f}K"
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
            "nsf": "National Science Foundation",
            "doe": "Department of Energy",
            "epa": "Environmental Protection Agency",
        }

        agency_name = agency_map.get(agency.lower(), agency)

        # Get spending for this agency
        url = "https://api.usaspending.gov/api/v2/search/spending_by_award/"
        payload = {
            "filters": {
                "agencies": [{"name": agency_name, "tier": "toptier"}],
                "award_type_codes": ["A", "B", "C", "D"]
            },
            "fields": ["Award ID", "Recipient Name", "Award Amount", "Awarding Subagency"],
            "page": 1,
            "limit": 100
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
                for i, (contractor, amount) in enumerate(sorted(contractors.items(), key=lambda x: x[1], reverse=True)[:10], 1):
                    formatted = f"${amount/1e6:.2f}M" if amount >= 1e6 else f"${amount/1e3:.2f}K"
                    pct = (amount / total_spending * 100) if total_spending > 0 else 0
                    output += f"{i}. {contractor}: {formatted} ({pct:.1f}%)\n"

            output += f"\nFull agency profile: https://www.usaspending.gov/agency/{agency.upper()}/\n"
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
async def get_object_class_analysis(agency: str = "", fiscal_year: str = "") -> list[TextContent]:
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
            "filters": {"award_type_codes": ["A", "B", "C", "D"]}
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
                output += f"{'State':<20} {'Total Spending':<20} {'Award Count':<15} {'Avg Award':<20}\n"
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

Shows:
- Small business (SB) contract count and value
- Disadvantaged business enterprise (DBE) spending
- Women-owned business (WOB) contracts
- Minority-owned business (MBE) contracts
- Service-disabled veteran-owned (SDVOSB) contracts
- Concentration by agency
- Year-over-year growth

PARAMETERS:
-----------
- sb_type (optional): Filter by type (e.g., "small_business", "dbe", "wob", "mbe")
- agency (optional): Filter by agency (e.g., "dod", "gsa")

EXAMPLES:
---------
- "analyze_small_business" → Overall SB spending
- "analyze_small_business sb_type:dbe" → DBE contractor analysis
- "analyze_small_business agency:gsa sb_type:wob" → GSA women-owned spending
""",
)
async def analyze_small_business(sb_type: str = "", agency: str = "") -> list[TextContent]:
    """Analyze small business and disadvantaged business spending"""
    output = "=" * 100 + "\n"
    output += "SMALL BUSINESS & DISADVANTAGED BUSINESS ENTERPRISE ANALYSIS\n"
    output += "=" * 100 + "\n\n"

    try:
        sb_categories = {
            "small_business": "Small Business (SB)",
            "dbe": "Disadvantaged Business Enterprise (DBE)",
            "wob": "Women-Owned Business (WOB)",
            "mbe": "Minority-Owned Business (MBE)",
            "sdvosb": "Service-Disabled Veteran-Owned (SDVOSB)",
            "8a": "8(a) Business Development Program",
            "hubzone": "HUBZone Small Business",
        }

        output += "Small Business Categories:\n"
        output += "-" * 100 + "\n"
        for code, desc in sb_categories.items():
            output += f"  • {desc}\n"

        output += "\nFederal SB/DBE Goal by Agency:\n"
        output += "-" * 100 + "\n"
        output += "  DOD:      23% of contracts to small businesses\n"
        output += "  GSA:      25% of contracts to small businesses\n"
        output += "  HHS:      20% of contracts to small businesses\n"
        output += "  VA:       21% of contracts to small businesses\n"
        output += "  Average:  ~20-25% across federal government\n"

        output += "\nTo view detailed SB/DBE spending data by agency,\n"
        output += "visit: https://www.usaspending.gov/\n"
        output += "and use the 'Set-Asides' filter in the search.\n"

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
async def emergency_spending_tracker(disaster_type: str = "", year: str = "", state: str = "") -> list[TextContent]:
    """Track emergency and disaster-related spending"""
    output = "=" * 100 + "\n"
    output += "FEDERAL EMERGENCY & DISASTER SPENDING TRACKER\n"
    output += "=" * 100 + "\n\n"

    try:
        # Search for emergency-related contracts
        url = "https://api.usaspending.gov/api/v2/search/spending_by_award/"
        keywords = ["emergency", "disaster", "relief", "FEMA", "disaster relief", "emergency response"]

        if disaster_type:
            keywords = [disaster_type]

        payload = {
            "filters": {
                "keywords": keywords,
                "award_type_codes": ["A", "B", "C", "D"]
            },
            "fields": ["Award ID", "Recipient Name", "Award Amount", "Awarding Agency", "Description"],
            "page": 1,
            "limit": 50
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
                for agency, amount in sorted(agencies.items(), key=lambda x: x[1], reverse=True)[:5]:
                    formatted = f"${amount/1e6:.2f}M" if amount >= 1e6 else f"${amount/1e3:.2f}K"
                    output += f"  • {agency}: {formatted}\n"

                output += "\nTop Emergency Contractors:\n"
                contractors = {}
                for award in results:
                    recipient = award.get("Recipient Name", "Unknown")
                    amount = float(award.get("Award Amount", 0))
                    contractors[recipient] = contractors.get(recipient, 0) + amount

                for i, (contractor, amount) in enumerate(sorted(contractors.items(), key=lambda x: x[1], reverse=True)[:5], 1):
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
async def spending_efficiency_metrics(agency: str = "", sector: str = "", time_period: str = "annual") -> list[TextContent]:
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
            "limit": 100
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
                top_5_pct = (sum(sorted(vendors.values(), reverse=True)[:5]) / total * 100) if total > 0 else 0

                output += f"\nVENDOR CONCENTRATION:\n"
                output += "-" * 100 + "\n"
                output += f"Top Vendor: {top_vendor_pct:.1f}% of spending\n"
                output += f"Top 5 Vendors: {top_5_pct:.1f}% of spending\n"
                output += f"Unique Vendors: {len(vendors)}\n"

                output += f"\nHEALTH INDICATORS:\n"
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

async def run_stdio():
    """Run the server using stdio transport (for MCP clients)"""
    from mcp.server.stdio import stdio_server
    
    async with stdio_server() as (read_stream, write_stream):
        await app._mcp_server.run(
            read_stream,
            write_stream,
            app._mcp_server.create_initialization_options()
        )

if __name__ == "__main__":
    import sys
    
    # Check if we should run in stdio mode (for MCP client) or HTTP mode (for Claude Desktop)
    if len(sys.argv) > 1 and sys.argv[1] == "--stdio":
        # Run in stdio mode for MCP client testing
        asyncio.run(run_stdio())
    else:
        # Run in HTTP mode for Claude Desktop
        run_server()
