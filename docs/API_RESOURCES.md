# USASpending API Resources & References

## Official Documentation

### API Endpoint Documentation
- **USASpending API Docs:** https://api.usaspending.gov/
- **API Endpoints List:** https://api.usaspending.gov/docs/endpoints
- **Federal Spending Guide:** https://www.usaspending.gov/data/Federal-Spending-Guide.pdf

### GitHub Repository
- **Main Repository:** https://github.com/fedspendingtransparency/usaspending-api
- **API Contracts (V2):** https://github.com/fedspendingtransparency/usaspending-api/tree/master/usaspending_api/api_contracts/contracts/v2

## Critical Reference Documentation

### Data Dictionary & Field Definitions ⭐ MOST VALUABLE RESOURCE
- **Data Dictionary Endpoint:** https://github.com/fedspendingtransparency/usaspending-api/blob/master/usaspending_api/api_contracts/contracts/v2/references/data_dictionary.md
  - **Why It's Critical:** Master reference for **ALL** federal spending data fields and their valid values
  - **Use When:** You need technical details about a field, its valid codes, or how to filter by it
  - **Covers:**
    - Award types (A, B, C, D, 02-11, IDV_A-E)
    - Set-aside type codes (SDVOSBC, WOSB, 8A, HZC, etc.)
    - Agency classification codes
    - Business type indicators
    - Contract type classifications
    - All other procurement data fields
  - **Structure:** Each field includes definition, valid values, source documents, and relationships to other fields
  - **Usage Pattern:** Need to understand any federal contracting field or code? Start here!
  - **Examples:**
    - Finding award type codes → Search for "Award Type"
    - Understanding set-asides → Search for "TypeSetAside"
    - Finding business classification codes → Search for relevant business type field
    - Understanding any data element → Search the data dictionary

### Glossary of Federal Contracting Terms ⭐ COMPLEMENTARY RESOURCE
- **Glossary (GitHub):** https://github.com/fedspendingtransparency/usaspending-api/blob/master/usaspending_api/api_contracts/contracts/v2/references/glossary.md
- **Glossary (Live Endpoint):** https://api.usaspending.gov/api/v2/references/glossary/
  - **Why It's Important:** Explains the **meaning and concepts** behind the terms used in federal spending data
  - **Use When:** You need to understand what a term means in the federal contracting context
  - **Covers:**
    - Federal procurement terminology
    - Small business program definitions
    - Contract types and their meanings
    - Set-aside program explanations
    - Award and funding concept definitions
    - FAR (Federal Acquisition Regulation) related terms
  - **Relationship to Data Dictionary:**
    - Data Dictionary = WHAT (field names and valid codes)
    - Glossary = WHY & MEANING (concept definitions and explanations)
  - **Usage Pattern:** Don't understand what a procurement term means? Check the glossary!
  - **Examples:**
    - What is an SDVOSB? → Glossary explains the Service Disabled Veteran Owned Small Business program
    - What does "set-aside" mean? → Glossary defines the concept
    - What is a "competitive" vs "sole source" award? → Glossary explains the difference
    - Understanding any federal contracting concept → Search the glossary

### Award Types Reference ⭐ SPECIALIZED REFERENCE
- **Award Types (GitHub):** https://github.com/fedspendingtransparency/usaspending-api/blob/master/usaspending_api/api_contracts/contracts/v2/references/award_types.md
- **Award Types (Live Endpoint):** https://api.usaspending.gov/api/v2/references/award_types/
  - **Why It's Important:** Comprehensive reference for all federal award type codes and their meanings
  - **Use When:** You need to filter by or understand award types (contracts, grants, loans, etc.)
  - **Covers:**
    - Contract type codes (A, B, C, D and variations)
    - Grant type codes (02, 03, 04, 05, etc.)
    - Loan type codes (07, 08, 09, etc.)
    - Insurance/Other type codes (10, 11, etc.)
    - IDV (Indefinite Delivery Vehicle) types
    - Detailed descriptions of each award type
    - Award type characteristics and definitions
  - **Critical for:**
    - Filtering API queries by award_type_codes
    - Understanding the difference between contract types
    - Distinguishing between procurement awards and financial assistance
  - **Usage Pattern:** Need to filter by award type? Start here to understand codes!
  - **Examples:**
    - What's the difference between A, B, C, D contracts? → Award Types explains
    - What codes represent grants? → Award Types lists them (02-05, etc.)
    - What's an IDV? → Award Types explains Indefinite Delivery Vehicles
    - Understanding any award type code → Search the Award Types reference

### Top-Tier Agencies Reference ⭐ SPECIALIZED REFERENCE
- **Top-Tier Agencies (Live Endpoint):** https://api.usaspending.gov/api/v2/references/toptier_agencies/
  - **Why It's Important:** Complete list of all top-tier federal agencies with codes and official names
  - **Use When:** You need to filter by agency, build agency dropdown lists, or understand agency hierarchies
  - **Critical Information Provided:**
    - Agency names (official full names)
    - Agency codes
    - Agency abbreviations
    - Relationships between agencies
    - Agency organizational structure
  - **Critical for:**
    - Filtering API queries by awarding_agency_name
    - Building agency selection interfaces
    - Understanding federal agency structure
    - Mapping agency names to API format
  - **Usage Pattern:** Need to filter by agency? Get the exact agency name from here!
  - **Examples:**
    - What's the exact name for GSA in the API? → Top-Tier Agencies lists it
    - Getting all top-tier agencies for a dropdown? → Top-Tier Agencies has them all
    - Understanding if an agency is top-tier or sub-tier? → This reference clarifies it
    - Building agency filtering UI? → Use Top-Tier Agencies for authoritative list
  - **Note:** Complements TOPTIER_AGENCY_MAP in server.py (which provides shortcuts like "gsa" → "General Services Administration")

### NAICS Codes Reference ⭐ SPECIALIZED REFERENCE
- **NAICS (GitHub):** https://github.com/fedspendingtransparency/usaspending-api/blob/master/usaspending_api/api_contracts/contracts/v2/references/naics.md
- **NAICS (Live Endpoint):** https://api.usaspending.gov/api/v2/references/naics/
  - **Why It's Important:** Complete reference for North American Industry Classification System codes used in federal contracting
  - **Use When:** You need to understand industry classifications, filter by business sector, or build industry selector UIs
  - **Covers:**
    - NAICS codes and descriptions (all industries)
    - Industry classification hierarchy
    - Small business size standards by industry
    - How NAICS relates to contractor classification
  - **Critical for:**
    - Understanding what industry a contractor operates in
    - Filtering contracts by industry sector
    - Building industry selection interfaces
    - Industry-based spending analysis
  - **Usage Pattern:** Need to understand contractor industry or filter by sector? Start with NAICS!
  - **Examples:**
    - What industry is NAICS code 541511? → NAICS explains it
    - Getting all software-related industries? → NAICS lists them with hierarchies
    - Understanding small business size standards? → NAICS links to SBA standards
    - Building industry dropdown? → NAICS provides authoritative list
  - **Related:** Size standards are tied to NAICS codes; check SBA.gov for specific thresholds

### PSC Codes Reference ⭐ SPECIALIZED REFERENCE
- **PSC (GitHub):** https://github.com/fedspendingtransparency/usaspending-api/blob/master/usaspending_api/api_contracts/contracts/v2/references/filter_tree/psc.md
- **PSC (Live Endpoint):** https://api.usaspending.gov/api/v2/references/psc/
  - **Why It's Important:** Complete reference for Product/Service Codes used in federal contracting
  - **Use When:** You need to understand what products or services are being procured, or filter by product/service type
  - **Covers:**
    - Product/Service Code (PSC) definitions
    - Product and service categories
    - Hierarchical classification of goods and services
    - How PSC relates to contract descriptions
  - **Critical for:**
    - Understanding what goods/services are being purchased
    - Filtering contracts by product/service type
    - Building product/service selection interfaces
    - Service/product category-based spending analysis
  - **Usage Pattern:** Need to understand what products/services a contract covers? Check PSC!
  - **Examples:**
    - What's PSC code C for? → PSC explains it's "Clothing, Individual Equipment, and Insignia"
    - Finding all IT-related services? → PSC has hierarchical IT categories
    - Building product/service filter UI? → PSC provides authoritative hierarchical list
    - Understanding contract purpose? → PSC codes help classify procurement type
  - **Note:** PSC is more specific than NAICS; NAICS classifies the contractor's industry, PSC classifies what's being bought

### Spending By Award Endpoint Documentation
- **Search Endpoint:** https://github.com/fedspendingtransparency/usaspending-api/blob/master/usaspending_api/api_contracts/contracts/v2/search/spending_by_award.md
  - **Purpose:** Main endpoint for searching federal awards with advanced filtering
  - **Key Filters:** type_set_aside, award_type_codes, time_period, agencies, award_amount, etc.
  - **API Path:** POST `/api/v2/search/spending_by_award/`

## Data Sources

### Excel Workbooks
- **Data Dictionary Crosswalk:** https://files.usaspending.gov/docs/Data_Dictionary_Crosswalk.xlsx
  - Contains mapping between field names, FPDS codes, and data elements
  - Updated regularly with new fields and definitions

### Real-World Data
- **USASpending.gov Interface:** https://www.usaspending.gov/
  - Live federal spending database
  - Good for validating queries and understanding data structure
  - Public search interface useful for testing filter combinations

## Key Discoveries

### Set-Aside Type Codes (26+ types)
**Location:** Data Dictionary → TypeSetAside field
**Critical for:** Filtering contracts by small business programs, veteran-owned businesses, women-owned businesses, etc.

**Common Codes:**
- `SDVOSBC` = Service Disabled Veteran Owned Small Business (Competed)
- `SDVOSBS` = SDVOSB (Sole Source)
- `WOSB` = Women Owned Small Business
- `EDWOSB` = Economically Disadvantaged WOSB
- `8A` = 8(a) Business Development Program
- `HZC` = HUBZone Set-Aside (Competed)
- `HZS` = HUBZone (Sole Source)
- See `/docs/reference/set-asides.json` for complete list

### API Filter Structure
**Location:** spending_by_award.md
**Critical Learning:** API accepts `type_set_aside` as array filter:
```json
{
  "filters": {
    "type_set_aside": ["SDVOSBC", "SDVOSBS"]
  }
}
```

## How to Find New Fields/Codes

### Starting Point: Data Dictionary (Always First!)
The Data Dictionary is the **master reference** for understanding federal contracting data:
1. **Any field question?** → Check Data Dictionary first
2. **Need valid codes for a filter?** → Data Dictionary has them
3. **Understanding a data element?** → Data Dictionary defines it
4. **Looking for field relationships?** → Data Dictionary shows them

### Research Process for Adding New API Features
1. **Check Glossary First (if unfamiliar):** Understand what the concepts mean in federal contracting context
2. **Check Specialized References (if applicable):**
   - Award Types → For contract, grant, loan, IDV filtering and understanding
   - Top-Tier Agencies → For agency filtering and understanding agency structure
   - Set-Asides → For small business program filtering (already in set-asides.json)
   - NAICS Codes → For industry classification and filtering
   - PSC Codes → For product/service classification and filtering
3. **Check Data Dictionary:** Search for relevant field names and understand valid values
4. **Check spending_by_award.md:** See what filters are supported in the API
5. **Look for TypeScript/Python Enums:** GitHub repo may have enum definitions in code
6. **Test via USASpending Interface:** Use the web UI to test filter combinations before implementing
7. **Consult FAR Documentation:** For procurement regulations and business program definitions

**Tip:** Glossary + Specialized References (Award Types/Agencies/Set-Asides/NAICS/PSC) + Data Dictionary together give you complete understanding for proper integration.

## Useful References for Common Tasks

### Understanding Federal Contracting Concepts
→ **Glossary:** https://api.usaspending.gov/api/v2/references/glossary/
→ What is SDVOSB? What's the difference between competitive and sole source? Check here!

### Finding ANY Field Definition or Valid Codes
→ **Data Dictionary:** https://github.com/fedspendingtransparency/usaspending-api/blob/master/usaspending_api/api_contracts/contracts/v2/references/data_dictionary.md
→ Data Dictionary contains authoritative definitions and valid values for all procurement fields
→ Use after understanding the concepts via the Glossary

### Finding Set-Aside Codes
→ Use: Data Dictionary
→ Search for: `TypeSetAside` field
→ Contains: All 26+ set-aside type codes (SDVOSBC, WOSB, 8A, HZC, etc.)

### Understanding Award Types (Contracts, Grants, Loans, etc.)
→ **Award Types Reference:** https://api.usaspending.gov/api/v2/references/award_types/
→ Specialized reference for all award type codes and their meanings
→ Or Data Dictionary: Search for `Award Type` field
→ Contains: All valid award type codes (A, B, C, D, 02-11, IDV_A-E, etc.)

### Finding Agency Names & Codes
→ **Top-Tier Agencies Reference:** https://api.usaspending.gov/api/v2/references/toptier_agencies/
→ Authoritative list of all federal agencies with official names and codes
→ Use when filtering by agency or building agency selection interfaces
→ Note: Server.py has TOPTIER_AGENCY_MAP with shortcuts (e.g., "gsa" → "General Services Administration")

### Finding Business Classification Codes
→ Use: Data Dictionary
→ Search for: Fields like "8(a) Program Participant", "Women Owned Business", "Veteran Owned Business", etc.
→ Contains: Boolean indicators and other business type classifications

### Finding NAICS & PSC Codes
→ **NAICS:** Use Data Dictionary for field definition, then `/api/v2/references/naics/` endpoint for lookup
→ **PSC:** Use Data Dictionary for field definition, then `/api/v2/references/psc/` endpoint for lookup
→ **Direct Resources:**
  - NAICS: https://www.census.gov/naics/
  - PSC: https://www.acquisition.gov/

## Notes for Future Development

### General-Purpose Development Resources - Reference Hierarchy

**Reference Hierarchy (Best to Most Specialized):**

**Level 1: Glossary** - Conceptual Understanding
- **What does this term mean in federal contracting?** → Check Glossary
- **How do procurement programs work?** → Glossary explains business programs, set-asides, etc.
- **What's the difference between X and Y?** → Glossary clarifies distinctions

**Level 2: Specialized References** - Domain-Specific Details
- **Award Types Reference** - For filtering and understanding contract/grant/loan types
- **Top-Tier Agencies Reference** - For agency filtering and understanding agency structure
- **Set-Asides Reference** - For small business program classifications (in project: `/docs/reference/set-asides.json`)
- **NAICS Codes Reference** - For understanding contractor industry classifications and industry-based filtering
- **PSC Codes Reference** - For understanding what products/services are being procured and product/service-based filtering
- Use when you need detailed information about a specific domain

**Level 3: Data Dictionary** - Technical Implementation Details
- **Adding a new filter?** → Check Data Dictionary for valid field names and values
- **Want to expose new fields?** → Data Dictionary documents all available fields
- **Supporting a new business classification?** → Data Dictionary has all business type definitions
- **Need to understand procurement codes?** → Data Dictionary is the source

**Benefit:** Understanding concepts (Glossary) → Understanding domain details (Specialized Refs) → Technical implementation (Data Dictionary) = Complete, correct implementation.

**Pro Tip:** Always start at the appropriate level based on your knowledge:
- New to federal contracting? → Start with Glossary
- Adding award type filtering? → Check Award Types Reference, then Data Dictionary
- Adding agency filtering? → Check Top-Tier Agencies Reference (or use TOPTIER_AGENCY_MAP in server.py)
- Adding industry-based filtering? → Check NAICS Codes Reference for industry classifications
- Adding product/service filtering? → Check PSC Codes Reference for procurement categories
- Need comprehensive technical details? → Data Dictionary is your source
- Building filtering UI? → Use relevant Specialized References for authoritative lists

### Best Practices
- **Data Dictionary is Authoritative:** When uncertain about field values or names, check the data dictionary first
- **API Contracts are Version Controlled:** The GitHub contracts directory documents expected request/response structures
- **Regular Updates:** USASpending data is updated regularly; refer to the main website for update schedules
- **Rate Limiting:** The API has rate limits; implement proper retry logic and caching
- **Field Availability:** Not all fields are returned by default; you must explicitly request fields in the API payload
- **Centralize References:** Add new API reference links and discoveries to this file for team knowledge sharing

## Related Documentation in This Project

- `/docs/reference/set-asides.json` - Complete set-aside type reference with descriptions
- `/docs/reference/api-mappings.json` - API field mappings and shortcuts
- `/docs/reference/tools-catalog.json` - MCP tool definitions and capabilities
- `/src/usaspending_mcp/server.py` - Implementation of all tools with detailed comments

