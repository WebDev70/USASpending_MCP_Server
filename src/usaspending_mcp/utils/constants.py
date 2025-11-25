"""
Constants for USASpending MCP Server.

WHAT ARE CONSTANTS?
Constants are values that never change while the program is running.
Instead of typing the same value over and over in different places,
we define it once here and reference it everywhere.

Think of constants like a dictionary of official names:
- If someone types "dod", we know they mean "Department of Defense"
- If someone types "nasa", we know they mean "National Aeronautics and Space Administration"

WHY USE CONSTANTS?
1. Avoid Typos: One place to define the official name
2. Easy to Update: Change it once, used everywhere
3. Readable Code: Names are clearer than abbreviations
4. Less Repetition: DRY (Don't Repeat Yourself) principle

THIS FILE CONTAINS:
- AWARD_TYPE_MAP: Maps simple names to official federal award type codes
- TOPTIER_AGENCY_MAP: Maps many variations of agency names to official names
- SUBTIER_AGENCY_MAP: Maps specific sub-divisions within departments
"""

# ============ AWARD TYPE MAPPING ============
# WHAT IS THIS?
# Federal awards fall into different categories (contracts, grants, loans, etc.)
# Each category has official codes used by the USASpending API
# This dictionary lets users type "grant" and we convert it to the official codes
#
# HOW IT WORKS:
# If user searches for "grants", we look up AWARD_TYPE_MAP["grant"]
# and get ["02", "03", "04", "05"]
# These official codes are sent to the USASpending.gov API
#
# THE CODES:
# Contracts: A, B, C, D
# Grants: 02, 03, 04, 05
# Loans: 07, 08, 09
# Insurance: 10, 11
AWARD_TYPE_MAP = {
    "contract": ["A", "B", "C", "D"],
    "grant": ["02", "03", "04", "05"],
    "loan": ["07", "08", "09"],
    "insurance": ["10", "11"],
}

# ============ TOP-TIER AGENCY MAPPING ============
# WHAT IS THIS?
# A "top-tier agency" is a major federal department like Defense or Energy
# Users might type different variations: "dod", "defense", "pentagon"
# This mapping converts all variations to the official name: "Department of Defense"
#
# WHY VARIATIONS?
# Different people know different names:
# - Some know the abbreviation: "dod"
# - Some know the full name: "defense department"
# - Some know the slang: "pentagon"
# Our job is to understand all of them!
#
# HOW IT WORKS:
# User types: "Find contracts from dod"
# We look up: TOPTIER_AGENCY_MAP.get("dod")
# We get: "Department of Defense"
# We send that to the API
#
# EXAMPLE AGENCIES:
# - Department of Defense (DoD, pentagon, military)
# - Department of Veterans Affairs (VA, veterans)
# - NASA (space administration, aeronautics)
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

# ============ SUB-TIER AGENCY MAPPING ============
# WHAT IS A SUB-TIER AGENCY?
# Some departments are so big they have smaller divisions inside them
# Examples:
# - Department of Defense has: Navy, Army, Air Force, Marine Corps, etc.
# - Department of Homeland Security has: Coast Guard, TSA, Border Protection, etc.
#
# WHY IS THIS IMPORTANT?
# Sometimes a user wants contracts from just the Navy, not all of Defense
# User might say: "navy", "usn", "department navy"
# We need to understand all these variations!
#
# HOW THE DATA IS STORED:
# Each sub-tier agency is stored as: (parent_agency, official_subtier_name)
# Example: "navy" -> ("Department of Defense", "Department of the Navy")
# This helps us know both who the parent is AND the official sub-tier name
#
# REAL WORLD ANALOGY:
# Think of a school district:
# - Top-tier: School District (like Department of Defense)
# - Sub-tier: Individual schools (like Navy, Army, Air Force)
#
# Sub-tier agency mapping (normalized to API format) - COMPREHENSIVE
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
    "acf": ("Department of Health and Human Services", "Administration for Children and Families"),
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
