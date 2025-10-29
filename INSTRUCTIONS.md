# USASpending MCP Server - Complete Instructions & Documentation

## Table of Contents

1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [Running the Server](#running-the-server)
4. [Tool Reference](#tool-reference)
5. [Query Syntax & Filtering](#query-syntax--filtering)
6. [Use Cases & Examples](#use-cases--examples)
7. [Advanced Features](#advanced-features)
8. [Technology Stack](#technology-stack)
9. [API Reference](#api-reference)
10. [Troubleshooting](#troubleshooting)

---

## Overview

The USASpending MCP Server is a comprehensive federal spending analysis tool that connects to the USASpending.gov API to provide detailed insights into U.S. federal government contracts, grants, and spending patterns.

### What This Server Does

This MCP (Model Context Protocol) server provides **14 powerful tools** that enable you to:

- **Search and analyze** federal contracts and grants across all U.S. agencies
- **Track spending trends** by fiscal year, agency, state, and contractor
- **Identify top contractors** and vendors across different sectors
- **Analyze budget allocations** by function, object class, and industry
- **Compare geographic spending** across states and territories
- **Monitor emergency spending** for disaster relief and crisis response
- **Evaluate procurement efficiency** and market concentration metrics
- **Research small business** and disadvantaged enterprise contracts

### Key Features

✓ **14 Comprehensive Tools** - From basic search to advanced analytics
✓ **Real-time Data** - Direct connection to USASpending.gov API v2
✓ **Advanced Filtering** - Agency, state, amount ranges, award types, and more
✓ **CSV Export** - Export results with complete data fields
✓ **Multi-agency Support** - 40+ toptier and 150+ subtier federal agencies
✓ **Dynamic Date Ranges** - Automatic 180-day rolling lookback
✓ **Pagination Support** - Handle large result sets efficiently
✓ **Direct Links** - URLs to full award details on USASpending.gov
✓ **Async Processing** - Non-blocking API calls for better performance
✓ **Comprehensive Error Handling** - Graceful failure modes with user-friendly messages

### Perfect For

- **Federal Analysts** - Track agency spending and budget allocation
- **Contractors & Vendors** - Find procurement opportunities and competitor activity
- **Researchers** - Analyze federal spending patterns and trends
- **Journalists** - Investigate government contracts and spending stories
- **Policy Makers** - Understand federal expenditures by sector and region
- **Consultants** - Provide data-driven insights to clients
- **Small Businesses** - Monitor opportunities in your industry or region

---

## Quick Start

### Fastest Way to Test

Run this single command to test the server immediately:

```bash
cd /Users/ronaldblakejr/Documents/MCP_Server/usaspending-mcp
./test_mcp_client.sh
```

This will:
1. Start the MCP server automatically
2. Launch the test client
3. List all available tools
4. Prompt you to enter a search query (e.g., "software contracts for DOD")
5. Show you the results
6. Exit cleanly

### Example First Query

```
Enter keyword: software contracts
Enter results limit: 10
```

The server will return the top 10 software contracts from federal agencies.

---

## Running the Server

### Option 1: Quick Test (Recommended)

**Best for**: Testing, development, quick validation

```bash
./test_mcp_client.sh
```

**What happens**:
- Server starts in stdio mode
- Test client connects
- Tool list displays
- You enter a search query
- Results appear
- Server shuts down cleanly

**Duration**: 2-3 minutes per test

---

### Option 2: Claude Desktop Integration (HTTP Server)

**Best for**: Using with Claude Desktop AI, long-running sessions

#### Step 1: Start the Server

```bash
./start_mcp_server.sh
```

The server will start on `http://localhost:3002/mcp`

Keep this terminal window open while you use Claude Desktop.

#### Step 2: Configure Claude Desktop (One-time Setup)

**On macOS:**
```bash
# Edit Claude Desktop config
nano ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

**On Windows:**
```
%APPDATA%\Claude\claude_desktop_config.json
```

**Add this configuration**:
```json
{
  "mcpServers": {
    "usaspending": {
      "url": "http://localhost:3002/mcp"
    }
  }
}
```

#### Step 3: Restart Claude Desktop

Close and reopen Claude Desktop. You should now see the USASpending tools available.

#### Step 4: Start Using It

Ask Claude any question about federal spending:
```
"Find the top 10 DOD contracts"
"What's the largest contract GSA has made?"
"Compare spending between California and Texas"
"Show me emergency spending for hurricane relief"
```

#### Step 5: Stop the Server

Press `Ctrl+C` in the server terminal when done.

---

### Option 3: Manual Testing (Advanced)

**Best for**: Developers, custom testing, debugging

#### Setup (One-time)

```bash
# Navigate to project directory
cd /Users/ronaldblakejr/Documents/MCP_Server/usaspending-mcp

# Activate virtual environment (if using one)
source .venv/bin/activate

# Install dependencies (if needed)
pip install -r requirements.txt
```

#### Run Server and Client

**Terminal 1 (Server)**:
```bash
python mcp_server.py
```

**Terminal 2 (Client)**:
```bash
python mcp_client.py
```

Then follow the prompts to enter queries.

---

### Running Specific Tools Directly

If you want to test a specific tool programmatically:

```python
import asyncio
import sys
sys.path.insert(0, '/Users/ronaldblakejr/Documents/MCP_Server/usaspending-mcp')

from mcp_server import get_spending_by_state

async def test():
    result = await get_spending_by_state(state="California", top_n=10)
    print(result[0].text)

asyncio.run(test())
```

---

## Tool Reference

### Overview: 14 Total Tools

Your server includes **14 comprehensive tools** organized into three categories:

**Original Tools (4)**: Core search and analysis
**Phase 1 Enhancement (4)**: Geographic and temporal analysis
**Phase 2 Enhancement (2)**: Agency and budget analysis
**Phase 3 Enhancement (4)**: Advanced analytics and comparisons

---

## ORIGINAL TOOLS

### 1. **search_federal_awards** 🔍

**Purpose**: Search and filter federal contracts and grants with advanced query capabilities

**Description**:
This is the primary search tool that allows you to find federal awards across all agencies. It supports powerful filtering including keywords, specific agencies, award amount ranges, award types, place of performance, recipient names, and boolean search operators.

**Function Signature**:
```python
async def search_federal_awards(keywords: str, results: int = 10, agency: str = "",
                                amount: str = "", award_type: str = "",
                                recipient: str = "", scope: str = "") -> list[TextContent]
```

**Parameters**:

| Parameter | Type | Optional | Description | Example |
|-----------|------|----------|-------------|---------|
| keywords | string | No | Main search terms | "software development" |
| results | int | Yes (default: 10) | Number of results (1-100) | 25 |
| agency | string | Yes | Filter by agency code | "dod" or "gsa" |
| amount | string | Yes | Dollar range filter | "100K-1M" or "$500K-5M" |
| award_type | string | Yes | Type of award | "contract" or "grant" |
| recipient | string | Yes | Specific contractor/recipient | "Microsoft" |
| scope | string | Yes | Place of performance | "domestic" or "international" |

**Query Syntax Examples**:

```
"software development"
→ Basic keyword search

"software AND contracts"
→ Boolean AND (both terms required)

"software OR IT"
→ Boolean OR (either term acceptable)

"contracts NOT grants"
→ Boolean NOT (exclude grants)

"software agency:dod amount:100K-1M"
→ Software contracts for DOD valued $100K to $1M

"laptops recipient:Dell scope:domestic"
→ Laptop contracts to Dell in domestic locations

"construction type:contract award_type:contract"
→ Construction contracts only

"research NOT development agency:nsf amount:500K-10M"
→ Research awards (no development) from NSF, $500K-$10M
```

**Output Includes**:
- Award ID and recipient name
- Award amount (formatted as $X.XXB, $X.XXM, or $X.XXK)
- Award type (Contract, Grant, Loan, etc.)
- Brief description
- Direct link to award details on USASpending.gov
- Pagination information

**Use Cases**:
- Find contracts in your industry
- Research competitor contract activity
- Identify procurement opportunities
- Analyze agency spending patterns
- Track specific vendor activity

---

### 2. **analyze_federal_spending** 📊

**Purpose**: Generate comprehensive statistical analysis and insights from spending data

**Description**:
This tool processes search results and generates detailed analytics including spending distribution across award size ranges, top recipient analysis, concentration metrics, and key insights about the federal spending landscape.

**Function Signature**:
```python
async def analyze_federal_spending(keywords: str, agency: str = "",
                                   amount: str = "", award_type: str = "") -> list[TextContent]
```

**Parameters**:

| Parameter | Type | Optional | Description | Example |
|-----------|------|----------|-------------|---------|
| keywords | string | No | Search terms to analyze | "IT services" |
| agency | string | Yes | Limit analysis to agency | "dod" |
| amount | string | Yes | Dollar range filter | "1M-50M" |
| award_type | string | Yes | Award type filter | "contract" |

**Analytics Provided**:

The tool calculates and displays:

1. **Spending Summary**
   - Total spending across all results
   - Number of awards analyzed
   - Minimum, maximum, and median award amounts
   - Average award size

2. **Spending Distribution**
   - Breakdown by size ranges:
     - Under $100K
     - $100K - $1M
     - $1M - $10M
     - $10M - $50M
     - $50M - $100M
     - $100M - $500M
     - Over $500M
   - Visual representation with Unicode bars

3. **Award Type Breakdown**
   - Percentage of contracts vs. grants vs. other types
   - Count by award type

4. **Top Recipients**
   - Top 5 contractors/recipients
   - Their total spending
   - Number of awards each received
   - Concentration metrics

5. **Key Insights**
   - Largest single award
   - Market concentration (HHI-style index)
   - Spending patterns and trends

**Output Example**:
```
FEDERAL SPENDING ANALYTICS
═══════════════════════════════════════════════════════════════

SPENDING SUMMARY
─────────────────────────────────────────────────────────────
Total Spending:        $2.45B
Number of Awards:      1,247
Average Award Size:    $1.96M
Median Award Size:     $890K
Min Award:             $5,000
Max Award:             $425M

SPENDING DISTRIBUTION BY RANGE
─────────────────────────────────────────────────────────────
< $100K          ███████        12.4%  (155 awards)
$100K - $1M      █████████████  34.8%  (434 awards)
$1M - $10M       ██████████     28.7%  (358 awards)
$10M - $50M      ████████       15.2%  (189 awards)
$50M - $100M     ███            6.8%   (85 awards)
$100M - $500M    ██             2.1%   (26 awards)
> $500M          ░              0.0%   (0 awards)

TOP 5 RECIPIENTS
─────────────────────────────────────────────────────────────
1. Microsoft Corporation          $450.2M (18 awards)
2. Dell Technologies              $320.5M (25 awards)
3. Booz Allen Hamilton             $285.3M (12 awards)
4. Lockheed Martin                 $195.7M (8 awards)
5. General Dynamics                $165.2M (11 awards)
```

**Use Cases**:
- Understand spending distribution in your sector
- Identify market leaders and concentration
- Analyze budget allocation patterns
- Research industry spending trends
- Support business proposals with data

---

### 3. **get_naics_psc_info** 📋

**Purpose**: Look up and understand NAICS and PSC classification codes

**Description**:
NAICS (North American Industry Classification System) codes identify industries, while PSC (Product/Service Code) codes identify what's being purchased. This tool helps you understand what these codes mean and find related codes.

**Function Signature**:
```python
async def get_naics_psc_info(search_term: str, code_type: str = "both") -> list[TextContent]
```

**Parameters**:

| Parameter | Type | Optional | Description | Example |
|-----------|------|----------|-------------|---------|
| search_term | string | No | Industry/service name or code | "software" or "5112" |
| code_type | string | Yes (default: "both") | "naics", "psc", or "both" | "naics" |

**NAICS Codes (Industry Classification)**:

NAICS codes are 6-digit codes that classify industries:

```
NAICS Code Structure: XX-XXX
├─ First 2 digits: Sector (11 = Agriculture, 31 = Manufacturing, etc.)
├─ Next 2 digits: Industry group
└─ Last 2 digits: Specific industry

Examples:
• 5112 = Software Publishers
• 3341 = Computer and Peripheral Equipment Manufacturing
• 5415 = Computer Systems Design and Related Services
• 5416 = Management, Scientific, and Technical Consulting Services
```

**PSC Codes (Product/Service Code)**:

PSC codes are 4-character codes identifying what's being purchased:

```
PSC Code Structure: X-XXX
├─ First character: Service or Supply class
└─ Next 3 digits: Specific product/service

Examples:
• J002 = Computer and Automatic Data Processing Equipment
• R700 = Management and Professional Services
• D300 = Construction Services
• B200 = Vehicle, Motor Vehicle, Trailers, and Cycles
```

**Search Examples**:

```
"software"           → Find NAICS codes related to software
"5112"               → Look up code 5112 (Software Publishers)
"J002"               → Look up code J002 (Computer Equipment)
"management code_type:psc" → Find PSC codes for management services
```

**Output Includes**:
- Code value and full description
- Industry/sector classification
- Related codes and sub-categories
- Federal spending patterns for each code

**Use Cases**:
- Understand what NAICS/PSC codes your company falls under
- Find related industry codes
- Research spending in specific product/service categories
- Decode classification codes in federal contracts

---

### 4. **get_top_naics_breakdown** 📈

**Purpose**: Analyze the top NAICS (industry) codes and their federal contract distribution

**Description**:
This tool identifies which industries receive the most federal contracts and grants, showing the top 5 NAICS codes, how many awards each received, and which federal agencies and contractors dominate each industry.

**Function Signature**:
```python
async def get_top_naics_breakdown() -> list[TextContent]
```

**Parameters**: None - provides a comprehensive government-wide analysis

**Information Provided**:

1. **Top 5 NAICS Codes by Award Count**
   - Code number and description
   - Number of awards
   - Percentage of total federal awards
   - Combined representation

2. **For Each Top Code**:
   - **Top Awarding Agencies**: Which federal departments buy in this sector
   - **Top Contractors**: Which companies receive the most contracts
   - **Contract Values**: Typical award amounts
   - **Products/Services**: What's typically purchased

3. **Cross-Cutting Analysis**:
   - Top contractors across all categories
   - Primary federal agencies
   - Market concentration metrics
   - Key spending insights

**Example Output**:
```
TOP 5 NAICS CODES - FEDERAL AWARDS
═════════════════════════════════════════════════════════════

Rank    Code   Industry Description                      Awards    %
─────────────────────────────────────────────────────────────────
  1      33     Manufacturing (Machinery, Equipment)       279    20.3%
  2      32     Manufacturing (Chemical, Pharma)          139    10.1%
  3      31     Manufacturing (Food, Beverage)            136     9.9%
  4      42     Wholesale Trade                            72     5.2%
  5      44     Retail Trade                               68     4.9%

Manufacturing (31-33) Combined: 554 awards (40.3% of total)

NAICS 33 - TOP CONTRACTORS:
1. Graybar Electric Company, Inc.
   Specialty: Electrical distribution & supplies
   Awards: $656.44K (sample)

2. Y Hata & Company Limited
   Specialty: Aerospace/manufacturing supplies
   Awards: $80.00K (sample)

PRIMARY AWARDING AGENCIES:
• Department of Defense (50+ awards)
• General Services Administration
• National Aeronautics and Space Administration
```

**Use Cases**:
- Understand which industries get the most federal spending
- Find your industry's market size and competitors
- Identify dominant agencies in your sector
- Research industry-specific procurement trends
- Analyze market concentration

---

## PHASE 1 ENHANCEMENT TOOLS

### 5. **get_spending_by_state** 🗺️

**Purpose**: Analyze federal spending by state and territory

**Description**:
This tool breaks down federal spending by geographic location, showing you how much each state and territory receives in federal contracts and grants, along with average award sizes and top contractors by state.

**Function Signature**:
```python
async def get_spending_by_state(state: str = "", top_n: int = 10) -> list[TextContent]
```

**Parameters**:

| Parameter | Type | Optional | Description | Example |
|-----------|------|----------|-------------|---------|
| state | string | Yes | Specific state name or "all" | "California" or "Texas" |
| top_n | int | Yes (default: 10) | Number of top states to show | 5 or 20 |

**State Name Format**:
Use full state names or two-letter abbreviations:
```
Full Name:  California, Texas, New York
Abbreviation: CA, TX, NY
Special: "all" shows all states/territories
```

**Query Examples**:

```
get_spending_by_state()
→ Top 10 states by spending (default)

get_spending_by_state(state="California")
→ Detailed California spending analysis

get_spending_by_state(state="all", top_n=50)
→ All 50 states ranked by spending

get_spending_by_state(state="NY", top_n=5)
→ New York's top 5 contractors
```

**Output Includes**:

1. **State Rankings** (if no specific state selected):
   ```
   Rank   State             Total Spending    Award Count   Avg Award
   ────────────────────────────────────────────────────────
   1      California        $245.2B           45,230        $5.42M
   2      Texas             $198.5B           38,120        $5.21M
   3      New York          $156.3B           29,450        $5.31M
   ...
   ```

2. **State-Specific Analysis** (if state selected):
   ```
   California Federal Spending Analysis
   ═════════════════════════════════════

   Total Spending:        $245.2B
   Number of Awards:      45,230
   Average Award:         $5.42M
   Median Award:          $2.15M

   TOP 10 CONTRACTORS:
   1. Lockheed Martin Corporation      $32.5B  (285 awards)
   2. Boeing Company                   $28.3B  (156 awards)
   3. Microsoft Corporation            $18.2B  (420 awards)
   ...

   TOP FEDERAL AGENCIES:
   1. Department of Defense            $145.2B (25,890 awards)
   2. General Services Administration  $45.3B  (8,230 awards)
   ...

   Link to Full State Profile on USASpending.gov:
   https://www.usaspending.gov/search/
   ```

**Geographic Coverage**:
- 50 states
- District of Columbia
- U.S. territories (Puerto Rico, Guam, Virgin Islands, etc.)
- International locations for certain contracts

**Use Cases**:
- Understand federal spending in your state
- Compare your state to others
- Find top contractors in your region
- Research agency presence by state
- Analyze regional economic impact of federal spending
- Identify growth opportunities in your area

---

### 6. **get_spending_trends** 📊

**Purpose**: Analyze federal spending trends over time by fiscal year or calendar year

**Description**:
This tool shows how federal spending has changed over time, displaying spending totals, award counts, and year-over-year percentage changes. You can view trends for all agencies combined or filter by specific agencies.

**Function Signature**:
```python
async def get_spending_trends(period: str = "fiscal_year", agency: str = "",
                              award_type: str = "") -> list[TextContent]
```

**Parameters**:

| Parameter | Type | Optional | Description | Example |
|-----------|------|----------|-------------|---------|
| period | string | Yes (default: "fiscal_year") | "fiscal_year" or "calendar_year" | "fiscal_year" |
| agency | string | Yes | Filter by specific agency | "dod" or "gsa" |
| award_type | string | Yes | Filter by award type | "contract" or "grant" |

**Supported Agency Codes**:

```
dod      → Department of Defense
gsa      → General Services Administration
hhs      → Department of Health and Human Services
va       → Department of Veterans Affairs
dhs      → Department of Homeland Security
doe      → Department of Energy
nasa     → National Aeronautics and Space Administration
```

**Fiscal Year vs Calendar Year**:

```
Fiscal Year:
FY2024 = October 1, 2023 → September 30, 2024
FY2025 = October 1, 2024 → September 30, 2025

Calendar Year:
CY2024 = January 1, 2024 → December 31, 2024
CY2025 = January 1, 2025 → December 31, 2025
```

**Query Examples**:

```
get_spending_trends()
→ Federal spending trends by fiscal year (all agencies)

get_spending_trends(agency="dod")
→ DOD spending trends by fiscal year

get_spending_trends(agency="gsa", period="calendar_year")
→ GSA spending by calendar year

get_spending_trends(period="fiscal_year", agency="hhs")
→ HHS spending trends by fiscal year
```

**Output Includes**:

```
FEDERAL SPENDING TRENDS - FISCAL YEAR
═════════════════════════════════════════════════════════════

Fiscal Year      Total Spending        Award Count    YoY Change
──────────────────────────────────────────────────────────────
FY2023           $621.2B               1,245,000      —
FY2024           $648.7B               1,289,000      +4.4%
FY2025           $675.3B               1,325,000      +4.1%

Key Insights:
• Consistent 4% annual growth
• Award volume increasing with spending
• Average award size relatively stable at ~$525K
```

**Trending Metrics**:
- Total spending by period
- Number of awards/contracts
- Year-over-year percentage change
- Growth rate trends
- Average award sizes

**Historical Data**:
Typically shows the last 5-10 fiscal years, allowing you to see long-term trends and patterns.

**Use Cases**:
- Track agency spending changes over time
- Identify growth areas and declining programs
- Plan contractor bidding strategies
- Analyze budget trends
- Support policy research
- Forecast future spending
- Understand seasonal patterns (with calendar year option)

---

### 7. **get_budget_functions** 💰

**Purpose**: Analyze federal spending by budget function (what money is spent on)

**Description**:
Federal agencies categorize their spending by budget function (what they spend money on). This tool breaks down spending by these functions: Personnel, Operations, Supplies, Equipment, R&D, Facilities, Grants, etc.

**Function Signature**:
```python
async def get_budget_functions(agency: str = "", detailed: bool = False) -> list[TextContent]
```

**Parameters**:

| Parameter | Type | Optional | Description | Example |
|-----------|------|----------|-------------|---------|
| agency | string | Yes | Specific agency code | "dod" or "hhs" |
| detailed | bool | Yes (default: False) | Show detailed breakdown | True |

**Budget Function Categories**:

```
Personnel & Compensation
├─ Salaries and wages
├─ Benefits (health, retirement)
└─ Personnel management
→ Typical: 30-40% of total spending

Operations & Maintenance
├─ Facility operations
├─ Equipment maintenance
├─ Utilities and services
└─ Day-to-day operations
→ Typical: 20-30% of total spending

Supplies & Materials
├─ Office supplies
├─ Equipment and parts
├─ Raw materials
└─ Consumables
→ Typical: 10-20% of total spending

Research & Development
├─ Basic research
├─ Applied research
├─ Product development
└─ Testing and evaluation
→ Typical: 5-15% of total spending

Capital & Infrastructure
├─ Buildings and facilities
├─ Major equipment
├─ Technology systems
└─ Infrastructure improvements
→ Typical: 5-15% of total spending

Grants & Subsidies
├─ Direct grants to recipients
├─ Formula grants to states
├─ Loans and loan guarantees
└─ Aid programs
→ Typical: 5-30% of total spending
```

**Query Examples**:

```
get_budget_functions()
→ Government-wide budget function breakdown

get_budget_functions(agency="dod", detailed=False)
→ DOD budget functions (summary)

get_budget_functions(agency="hhs", detailed=True)
→ HHS budget functions (detailed with agency breakouts)

get_budget_functions(agency="gsa")
→ GSA budget function analysis
```

**Output Includes**:

```
GSA BUDGET FUNCTION BREAKDOWN
═════════════════════════════════════════════════════════════

Function                    Spending        % of Total    Awards
─────────────────────────────────────────────────────────────
Personnel & Salaries        $12.3B          20.1%        2,450
Operations & Maintenance    $15.2B          24.8%        3,120
Supplies & Materials        $10.8B          17.6%        5,680
Professional Services       $14.5B          23.7%        1,890
Equipment & Technology      $6.2B           10.1%        820
Research & Development      $2.1B           3.4%         340
Other                       $0.2B           0.3%         50

Top Spending Categories:
1. Operations & Maintenance ($15.2B) - Federal building leases, utilities
2. Professional Services ($14.5B) - Consulting, management contracts
3. Personnel ($12.3B) - Federal employee compensation
```

**Agency-Specific Insights**:

The detailed version shows which specific agencies within the department have different spending patterns, revealing budget priorities.

**Use Cases**:
- Understand agency spending allocation
- Identify procurement opportunities by function
- Analyze budget priorities
- Compare spending categories across agencies
- Research specific types of spending
- Support budget impact analysis
- Understand where agencies focus their resources

---

### 8. **get_vendor_profile** 🏢

**Purpose**: Get comprehensive information about federal contractors and vendors

**Description**:
This tool provides detailed profiles for vendors who contract with the federal government, including their identification numbers, recent contracts, company information, and their relationship with federal agencies.

**Function Signature**:
```python
async def get_vendor_profile(vendor_name: str, show_contracts: bool = False) -> list[TextContent]
```

**Parameters**:

| Parameter | Type | Optional | Description | Example |
|-----------|------|----------|-------------|---------|
| vendor_name | string | No | Company or vendor name | "Microsoft" or "Booz Allen" |
| show_contracts | bool | Yes (default: False) | Show recent contracts | True |

**Vendor Identification Numbers**:

```
DUNS Number (Data Universal Numbering System)
├─ 9-digit identifier assigned by Dun & Bradstreet
├─ Used for federal contracting
└─ Example: 001234567

UEI (Unique Entity ID)
├─ Newer 12-character identifier (replacing DUNS)
├─ Includes registration information
└─ Example: ABCD12EF3G4H
```

**Query Examples**:

```
get_vendor_profile vendor_name:"Microsoft Corporation"
→ Microsoft's federal contractor profile

get_vendor_profile vendor_name:"Booz Allen Hamilton" show_contracts:true
→ Booz Allen with recent contracts

get_vendor_profile vendor_name:"Dell"
→ Dell Technologies contractor information

get_vendor_profile vendor_name:"Lockheed Martin" show_contracts:true
→ Lockheed Martin with contract details
```

**Output Includes**:

```
CONTRACTOR PROFILE
═════════════════════════════════════════════════════════════

Vendor Name:              Microsoft Corporation
DUNS Number:              001043373
UEI:                      PFVQQE5PGLJ5
Recipient Level:          Prime Contractor

COMPANY INFORMATION
─────────────────────────────────────────────────────────────
Entity Type:              Large Business
Primary Industry:         Software (NAICS 5112)
Headquarters:             Redmond, Washington
Years as Federal Contractor: 30+

FEDERAL CONTRACTING SUMMARY
─────────────────────────────────────────────────────────────
Total Federal Spending:   $2.45B (all-time)
Average Award Size:       $850K
Number of Awards:         2,880
Primary Agencies:         DOD, HHS, GSA, NASA

TOP AGENCIES CONTRACTING WITH THIS VENDOR
─────────────────────────────────────────────────────────────
1. Department of Defense          $980.2M  (1,245 awards)
2. Department of Health & Human   $620.5M   (450 awards)
3. General Services Admin         $450.3M   (680 awards)

RECENT CONTRACTS (if show_contracts=true)
─────────────────────────────────────────────────────────────
[Contract details with award IDs, amounts, dates, descriptions]

Links to Additional Information:
├─ Full Profile on USASpending.gov
├─ Company Website
└─ SAM.gov Registration
```

**Information Available**:
- Legal business name
- DUNS and UEI identifiers
- Business classification (small business, minority-owned, etc.)
- Industry codes (NAICS, PSC)
- Primary location and contact info
- Federal contract history
- Total spending received
- Top contracting agencies
- Recent award details
- Direct links to detailed information

**Use Cases**:
- Research potential competitors
- Understand vendor relationships with agencies
- Find contact information for partnerships
- Analyze competitor contract activity
- Identify market leaders in your sector
- Verify vendor credentials
- Research acquisition targets or partners
- Track vendor performance and activity

---

## PHASE 2 ENHANCEMENT TOOLS

### 9. **get_agency_profile** 🏛️

**Purpose**: Get comprehensive federal agency spending overview and top contractors

**Description**:
This tool provides a complete profile of a federal agency's spending patterns, including total spending amount, number of contracts, top contractors, and links to additional information.

**Function Signature**:
```python
async def get_agency_profile(agency: str, detail_level: str = "detail") -> list[TextContent]
```

**Parameters**:

| Parameter | Type | Optional | Description | Example |
|-----------|------|----------|-------------|---------|
| agency | string | No | Agency code (required) | "dod" or "gsa" |
| detail_level | string | Yes (default: "detail") | "summary", "detail", or "full" | "full" |

**Detail Levels**:

```
summary    → Quick overview (total spending, award count)
detail     → Standard profile with top contractors
full       → Complete analysis with budget breakdown
```

**Supported Agencies**:

```
Major Agencies:
dod       → Department of Defense
gsa       → General Services Administration
hhs       → Department of Health and Human Services
va        → Department of Veterans Affairs
dhs       → Department of Homeland Security
doe       → Department of Energy
nasa      → National Aeronautics and Space Administration
nsf       → National Science Foundation

Additional Agencies:
doj       → Department of Justice
dot       → Department of Transportation
usda      → Department of Agriculture
interior  → Department of the Interior
state     → Department of State
treasury  → Department of Treasury
epa       → Environmental Protection Agency
fcc       → Federal Communications Commission
... and 30+ more
```

**Query Examples**:

```
get_agency_profile agency:dod
→ DOD spending summary and top contractors

get_agency_profile agency:gsa detail_level:full
→ Complete GSA spending analysis

get_agency_profile agency:hhs detail_level:summary
→ Quick HHS overview

get_agency_profile agency:nasa
→ NASA spending profile and contracts
```

**Output Includes**:

```
FEDERAL AGENCY PROFILE
═════════════════════════════════════════════════════════════

Agency:                   Department of Defense
Organization Level:       Toptier Agency
Fiscal Year 2024 Data:

SPENDING OVERVIEW
─────────────────────────────────────────────────────────────
Total Spending:           $425.3B
Total Awards:             145,230
Average Award Size:       $2.93M
Median Award Size:        $1.2M

AWARD TYPE BREAKDOWN
─────────────────────────────────────────────────────────────
Contracts:               78.5%  ($333.8B)
Grants:                  12.3%  ($52.4B)
Loans:                   6.2%   ($26.4B)
Other:                   2.9%   ($12.3B)

TOP 20 CONTRACTORS
─────────────────────────────────────────────────────────────
Rank  Contractor                    Total Spending    Awards
───────────────────────────────────────────────────────────
1     Lockheed Martin Corp          $45.2B           285
2     Boeing Defense               $38.5B           156
3     Raytheon Technologies         $32.1B           234
... (through rank 20)

GEOGRAPHIC DISTRIBUTION
─────────────────────────────────────────────────────────────
California:              $95.2B  (35 contractors)
Texas:                   $72.3B  (28 contractors)
Virginia:                $58.4B  (42 contractors)
... (additional states)

FULL AGENCY PROFILE
─────────────────────────────────────────────────────────────
Link: https://www.usaspending.gov/agency/[agency_id]/
```

**Information Included**:
- Total spending amount and trends
- Number and types of awards
- Top 10-20 contractors
- Budget allocation by category
- Geographic distribution
- Subtier agencies and components
- Contact information
- Links to detailed profiles

**Detail Level Differences**:

| Aspect | Summary | Detail | Full |
|--------|---------|--------|------|
| Basic Stats | ✓ | ✓ | ✓ |
| Top Contractors | — | ✓ | ✓ |
| Budget Breakdown | — | — | ✓ |
| Geographic Data | — | — | ✓ |

**Use Cases**:
- Research federal agency budget and spending
- Identify primary contractors for an agency
- Understand agency procurement priorities
- Analyze agency spending trends
- Find agency contact information
- Support policy research
- Business development for federal contractors
- Analyze agency budget allocation

---

### 10. **get_object_class_analysis** 📊

**Purpose**: Analyze spending by object class (type of expenditure)

**Description**:
Object Class is a federal accounting system that categorizes spending by what's being bought: Personnel, Contractual Services, Supplies, Equipment, etc. This tool breaks down federal spending by these categories.

**Function Signature**:
```python
async def get_object_class_analysis(agency: str = "", fiscal_year: str = "") -> list[TextContent]
```

**Parameters**:

| Parameter | Type | Optional | Description | Example |
|-----------|------|----------|-------------|---------|
| agency | string | Yes | Limit to specific agency | "dod" |
| fiscal_year | str | Yes | Specific fiscal year | "2024" |

**Object Class Categories**:

```
Personnel Compensation (10)
├─ Full-time permanent salaries
├─ Part-time and temporary wages
├─ Military personnel costs
└─ Other personnel compensation

Contractual Services (20)
├─ Contract research and development
├─ Management support services
├─ Consulting services
└─ Professional services

Supplies (30)
├─ Office supplies
├─ Materials and parts
├─ Clothing and textiles
└─ Food and fuel

Equipment (40)
├─ Vehicles and transportation
├─ Machinery and tools
├─ Technology and software
└─ Other equipment

Grants & Subsidies (41-49)
├─ Direct financial assistance
├─ Formula grants
├─ Loan guarantees
└─ Aid programs

Other (50+)
├─ Travel and transportation
├─ Utilities and rent
├─ Insurance and indemnities
└─ Miscellaneous
```

**Query Examples**:

```
get_object_class_analysis()
→ Government-wide object class breakdown

get_object_class_analysis agency:dod
→ DOD spending by object class

get_object_class_analysis agency:hhs fiscal_year:2024
→ HHS FY2024 object class analysis

get_object_class_analysis fiscal_year:2025
→ Government-wide FY2025 breakdown
```

**Output Includes**:

```
OBJECT CLASS ANALYSIS - DOD
═════════════════════════════════════════════════════════════

Object Class            Spending        % of Total    Count
─────────────────────────────────────────────────────────
Personnel Compensation  $98.2B          23.1%        1,234,000
Contractual Services    $145.3B         34.2%        45,230
Supplies & Materials    $52.1B          12.3%        23,450
Equipment               $85.2B          20.1%        8,230
Grants & Subsidies      $28.5B          6.7%        2,340
Travel & Other          $15.4B          3.6%        1,120

KEY INSIGHTS
─────────────────────────────────────────────────────────────
• Contractual Services dominate at 34.2% of spending
• Personnel compensation is significant at 23.1%
• Equipment spending reflects military modernization
• Supplies spending reflects operational needs

Trends:
├─ Contractual services growing 3.2% annually
├─ Personnel compensation growing 2.1% annually
└─ Equipment spending growing 5.8% annually
```

**Information Included**:
- Spending total by object class
- Percentage of total budget
- Number of expenditures
- Year-over-year trends
- Agency-specific insights
- Growth rates by category

**Use Cases**:
- Understand federal budget composition
- Analyze agency spending priorities
- Identify growth areas in federal spending
- Research specific types of federal expenditures
- Compare spending patterns across agencies
- Support budget impact analysis
- Understand procurement vs. personnel spending ratios

---

## PHASE 3 ENHANCEMENT TOOLS

### 11. **compare_states** ⚖️

**Purpose**: Side-by-side comparison of federal spending across multiple states

**Description**:
This tool allows you to compare how much federal spending goes to different states, showing totals, per-capita amounts, average award sizes, and top contractors by state.

**Function Signature**:
```python
async def compare_states(states: str, metric: str = "total") -> list[TextContent]
```

**Parameters**:

| Parameter | Type | Optional | Description | Example |
|-----------|------|----------|-------------|---------|
| states | string | No | States to compare (comma-separated) | "California,Texas,New York" |
| metric | string | Yes (default: "total") | "total", "percapita", or "awards" | "percapita" |

**Metric Options**:

```
total      → Total spending amount (dollars)
percapita  → Spending per person (dollars per capita)
awards     → Number of awards (award count)
```

**Query Examples**:

```
compare_states states:"California,Texas,Florida"
→ Compare total spending for CA, TX, FL

compare_states states:"California,Texas,New York" metric:percapita
→ Per-capita spending comparison

compare_states states:"CA,TX,NY,PA,IL,OH" metric:awards
→ Compare by number of awards

compare_states states:"Washington,Oregon,California" metric:total
→ Compare West Coast spending
```

**Output Includes**:

```
STATE SPENDING COMPARISON
═════════════════════════════════════════════════════════════

Comparing: California, Texas, New York (Total Spending)

State           Spending        Awards    Avg Award    Per-Capita
──────────────────────────────────────────────────────────────
California      $245.2B         45,230    $5.42M       $6,187
Texas           $198.5B         38,120    $5.21M       $6,524
New York        $156.3B         29,450    $5.31M       $8,015

ANALYSIS
─────────────────────────────────────────────────────────────
Highest Spending:       California ($245.2B)
Highest Per-Capita:     New York ($8,015 per person)
Most Awards:            California (45,230)
Largest Avg Award:      California ($5.42M)

TOP CONTRACTORS - CALIFORNIA
1. Lockheed Martin          $32.5B
2. Boeing                   $28.3B
3. Microsoft                $18.2B

TOP CONTRACTORS - TEXAS
1. Bell Helicopter          $24.2B
2. General Dynamics         $19.5B
3. Raytheon                 $15.3B

TOP CONTRACTORS - NEW YORK
1. Goldman Sachs            $12.5B
2. JPMorgan Chase           $11.8B
3. Citigroup                $9.3B
```

**Comparison Options**:

**Total Spending**: Raw dollar amounts awarded to each state

**Per-Capita Spending**: Spending divided by state population
- Shows federal investment intensity
- Accounts for population differences
- Useful for policy analysis

**Award Count**: Number of contracts/grants
- Shows procurement activity
- Different from spending (many small vs few large)
- Indicates agency engagement level

**Information Included**:
- Spending totals or per-capita amounts
- Number of awards in each state
- Average award size
- Top contractors per state
- Top agencies per state
- Geographic distribution analysis
- Ranking and comparison metrics

**Use Cases**:
- Compare federal investment across states
- Analyze regional economic impact
- Research regional contractor concentration
- Understand geographic spending disparities
- Support economic development analysis
- Compare your state to peer states
- Analyze political economy of federal spending
- Research regional industrial policies

---

### 12. **analyze_small_business** 🏪

**Purpose**: Analyze federal spending on small business and disadvantaged business enterprises

**Description**:
The federal government reserves a percentage of contracts for small businesses and companies owned by minorities, women, veterans, and disadvantaged groups. This tool analyzes spending on these special contracting categories.

**Function Signature**:
```python
async def analyze_small_business(sb_type: str = "", agency: str = "") -> list[TextContent]
```

**Parameters**:

| Parameter | Type | Optional | Description | Example |
|-----------|------|----------|-------------|---------|
| sb_type | string | Yes | Type: "dbe", "wob", "mbe", "sdvosb", "huas" | "dbe" |
| agency | string | Yes | Limit to agency | "dod" |

**Small Business Categories**:

```
SB   = Small Business (general)
      └─ Businesses with fewer than 500-1,500 employees
         (size varies by industry)

DBE  = Disadvantaged Business Enterprise
      └─ Minority-owned or economically disadvantaged
         └─ Set-aside: 5% of federal contracts

WOB  = Women-Owned Business
      └─ At least 51% owned/controlled by women
      └─ Set-aside: 5% of federal contracts

MBE  = Minority-Owned Business
      └─ At least 51% owned by minorities
         (African American, Hispanic, Asian, Native American)
      └─ Often combined with other categories

SDVOSB = Service-Disabled Veteran-Owned Small Business
       └─ Owned by veteran with service-connected disability
       └─ Set-aside: 3% of federal contracts

HUAS = Historically Underutilized Business Zones
     └─ Located in economically distressed areas
     └─ Small business set-asides in certain zones
```

**Query Examples**:

```
analyze_small_business()
→ Overall small business spending (all types)

analyze_small_business sb_type:dbe
→ Disadvantaged business enterprise spending

analyze_small_business sb_type:wob agency:dod
→ Women-owned businesses contracting with DOD

analyze_small_business sb_type:sdvosb
→ Service-disabled veteran-owned businesses

analyze_small_business sb_type:mbe agency:gsa
→ Minority-owned businesses with GSA
```

**Output Includes**:

```
SMALL BUSINESS & DBE SPENDING ANALYSIS
═════════════════════════════════════════════════════════════

SPENDING BY CATEGORY
─────────────────────────────────────────────────────────────
Small Business (All)      $125.3B   45.2%  (89,230 awards)
├─ Disadvantaged (DBE)    $28.5B    10.3%  (12,450 awards)
├─ Women-Owned (WOB)      $22.1B    8.0%   (9,870 awards)
├─ Minority-Owned (MBE)   $32.4B    11.7%  (18,230 awards)
├─ Vet-Owned (SDVOSB)     $18.2B    6.6%   (8,120 awards)
└─ Other SB               $24.1B    8.7%   (40,560 awards)

Large Business           $150.3B   54.8%  (45,230 awards)

FEDERAL AGENCY BREAKDOWN
─────────────────────────────────────────────────────────────
Agency              SB Spending    % of Agency Total    Awards
────────────────────────────────────────────────────────
Department of Defense    $48.2B      31.2%            28,450
General Services Admin   $32.5B      56.8%            18,230
Department of Commerce   $15.3B      42.1%            9,120
...

TOP SMALL BUSINESSES (All Types Combined)
─────────────────────────────────────────────────────────────
1. XYZ Technology Solutions (DBE, WOB)    $1.2B  (450 awards)
2. ABC Consulting (MBE)                   $950M  (380 awards)
3. DEF Manufacturing (SDVOSB)              $785M  (320 awards)

PERFORMANCE METRICS
─────────────────────────────────────────────────────────────
Federal Target for SB Set-Asides:  23% of all contracts
Actual SB Spending:                 22.8% of contracts
Performance vs Target:              99.1% (slightly below)

Women-Owned Targets:                5% of contracts
Actual WOB Spending:                4.2% of contracts
Performance vs Target:              84% (below target)

Growth Rate (YoY):                  +3.2% for SB spending
```

**Information Included**:
- Total spending by business category
- Percentage of overall federal spending
- Number of awards by category
- Top small businesses in each category
- Agency-specific breakdowns
- Performance vs. federal targets
- Growth trends
- Award size distribution

**Federal Goals**:
The government has specific targets for small business spending:
- Small Business overall: 23% of contracts
- Disadvantaged Business (DBE): 5% of contracts
- Women-Owned Business (WOB): 5% of contracts
- Service-Disabled Veteran: 3% of contracts

**Use Cases**:
- Small business owners: Find federal contracting opportunities
- Researchers: Analyze small business federal participation
- Policy makers: Monitor small business set-aside goals
- Investors: Identify small business success stories
- Large contractors: Find small business partners for subcontracting
- Economic development: Assess small business federal engagement
- Support minority/women/veteran-owned business development

---

### 13. **emergency_spending_tracker** 🚨

**Purpose**: Track federal spending for disaster relief, emergency response, and crisis management

**Description**:
When disasters occur (hurricanes, earthquakes, floods, pandemics, etc.), the federal government appropriates emergency spending. This tool tracks this spending across different disaster types and regions.

**Function Signature**:
```python
async def emergency_spending_tracker(disaster_type: str = "", state: str = "",
                                     year: str = "") -> list[TextContent]
```

**Parameters**:

| Parameter | Type | Optional | Description | Example |
|-----------|------|----------|-------------|---------|
| disaster_type | string | Yes | Type of disaster | "hurricane", "earthquake", "covid", "flood" |
| state | string | Yes | Affected state | "Florida", "Texas", "Louisiana" |
| year | string | Yes | Year of disaster | "2024", "2023" |

**Disaster Types Tracked**:

```
hurricane       → Hurricane damage and relief
earthquake      → Earthquake response and recovery
flood           → Flood damage and recovery
tornado         → Tornado damage and cleanup
wildfire        → Wildfire suppression and recovery
pandemic/covid  → COVID-19 and pandemic response
drought         → Drought relief and assistance
snow            → Winter storm and snow damage
other           → Other declared disasters
```

**Query Examples**:

```
emergency_spending_tracker()
→ All emergency spending (current/recent)

emergency_spending_tracker disaster_type:hurricane
→ All hurricane relief spending

emergency_spending_tracker disaster_type:hurricane state:Florida
→ Hurricane relief specific to Florida

emergency_spending_tracker disaster_type:covid
→ COVID-19 pandemic spending

emergency_spending_tracker disaster_type:flood state:Louisiana year:2024
→ 2024 Louisiana flood relief spending

emergency_spending_tracker state:Texas
→ All emergency spending in Texas
```

**Output Includes**:

```
EMERGENCY SPENDING TRACKER
═════════════════════════════════════════════════════════════

RECENT EMERGENCY DECLARATIONS & SPENDING
─────────────────────────────────────────────────────────────
Event: Hurricane Helene (2024)
Affected States: Florida, Georgia, North Carolina, Tennessee
Declaration Date: September 26, 2024
Total Spending Approved: $8.2B

Event: California Wildfires (2024)
Affected Areas: Northern California
Declaration Date: July 15, 2024
Total Spending Approved: $2.5B

COVID-19 PANDEMIC RESPONSE (2020-2024)
─────────────────────────────────────────────────────────────
Total Pandemic Spending: $5.2 Trillion (all programs)
Healthcare Response: $1.8B
Vaccine Distribution: $12.3B
Economic Stimulus: $3.8B (direct payments, unemployment)
Business Relief (PPP): $800B
Education Support: $195B

SPENDING BY FEDERAL AGENCY
─────────────────────────────────────────────────────────────
FEMA (Federal Emergency Management Agency)
├─ Disaster Relief:        $3.2B
├─ Housing Assistance:     $1.5B
└─ Infrastructure Repair:  $2.1B

Department of Health & Human Services
├─ Emergency Medical:      $850M
├─ Vaccines & Treatment:   $1.2B
└─ Mental Health Support:  $340M

Department of Defense
├─ Resource Provision:     $450M
├─ Personnel Support:      $220M
└─ Equipment:              $180M

STATE-BY-STATE EMERGENCY SPENDING
─────────────────────────────────────────────────────────────
Florida:        $2.4B (Hurricanes, wildfires)
Texas:          $1.8B (Winter storms, flooding)
Louisiana:      $1.5B (Flood recovery)
California:     $1.2B (Wildfire suppression)
...

RECENT CONTRACTING FOR EMERGENCY RESPONSE
─────────────────────────────────────────────────────────────
Contractor                    Award Amount    Services
──────────────────────────────────────────────
Bechtel Infrastructure        $245.3M        Debris removal, reconstruction
Aecom Technical Services      $189.2M        Environmental assessment
Fluor Corporation             $156.4M        Construction management
...
```

**Information Included**:
- Recent disaster declarations
- Emergency spending totals by event
- Spending by federal agency
- Contractor awarded emergency contracts
- State-by-state breakdown
- Recovery timelines
- Spending by category (relief, reconstruction, medical, etc.)
- Links to emergency declarations

**Agencies Managing Emergency Spending**:
- **FEMA** - Federal Emergency Management Agency (primary)
- **HHS** - Health and Human Services (pandemic, medical)
- **DOD** - Department of Defense (resource provision)
- **DOI** - Department of Interior (natural disasters)
- **EPA** - Environmental Protection Agency (environmental response)
- **USDA** - Agriculture (agricultural disasters)

**Use Cases**:
- Disaster recovery analysis
- Emergency contracting research
- Policy impact assessment
- Business opportunity identification for emergency services
- Federal spending transparency
- Crisis response planning
- Contractor performance analysis
- Emergency management research

---

### 14. **spending_efficiency_metrics** 📈

**Purpose**: Analyze federal procurement efficiency and market concentration

**Description**:
This tool examines how efficiently the federal government spends money, measuring factors like vendor concentration (too many contracts to one company?), competition levels, contract size distribution, and market health indicators.

**Function Signature**:
```python
async def spending_efficiency_metrics(agency: str = "", sector: str = "") -> list[TextContent]
```

**Parameters**:

| Parameter | Type | Optional | Description | Example |
|-----------|------|----------|-------------|---------|
| agency | string | Yes | Specific agency | "dod" |
| sector | string | Yes | Industry sector | "manufacturing" or "IT services" |

**Efficiency Metrics Calculated**:

```
Herfindahl-Hirschman Index (HHI)
├─ Measures market concentration
├─ Higher = more concentrated (less competition)
├─ Lower = more competitive (more vendors)
└─ Range: 0-10,000
    • 0-1,500 = Competitive
    • 1,500-2,500 = Moderate concentration
    • 2,500+ = High concentration

Vendor Concentration
├─ % spending with top 5 vendors
├─ % spending with top 10 vendors
├─ Number of unique vendors
└─ Vendor distribution

Contract Size Distribution
├─ Average contract size
├─ Median contract size
├─ Range of contract sizes
└─ Distribution percentiles

Competition Indicators
├─ Number of bidders per contract
├─ Sole-source vs. competitive contracts
├─ Set-aside contracts (SB, DBE, etc.)
└─ Competition rates by sector
```

**Query Examples**:

```
spending_efficiency_metrics()
→ Government-wide efficiency analysis

spending_efficiency_metrics agency:dod
→ DOD procurement efficiency

spending_efficiency_metrics sector:manufacturing
→ Federal manufacturing procurement analysis

spending_efficiency_metrics agency:gsa sector:IT
→ GSA's IT services procurement efficiency
```

**Output Includes**:

```
PROCUREMENT EFFICIENCY METRICS
═════════════════════════════════════════════════════════════

OVERALL MARKET HEALTH
─────────────────────────────────────────────────────────────
Total Spending Analyzed:   $425.3B
Total Contracts:           145,230
Total Unique Vendors:      28,450
Average Contract Size:     $2.93M

VENDOR CONCENTRATION ANALYSIS
─────────────────────────────────────────────────────────────
Top 5 Vendors Control:    28.3% of spending
Top 10 Vendors Control:   42.1% of spending
Top 100 Vendors Control:  68.5% of spending

Herfindahl-Hirschman Index (HHI): 2,340
Assessment: MODERATE CONCENTRATION
Interpretation: Reasonable competition, but room for improvement

Vendor Distribution:
├─ Single vendor (10-20%): 12.3% of contracts (sole source)
├─ 2-5 vendors:            31.2% of contracts
├─ 6-20 vendors:           42.1% of contracts
└─ 20+ vendors:            14.4% of contracts (very competitive)

TOP 10 VENDORS & MARKET SHARE
─────────────────────────────────────────────────────────────
Rank  Vendor                     Spending     Market Share   Contracts
───────────────────────────────────────────────────────────────
1     Lockheed Martin            $45.2B       10.6%         285
2     Boeing Defense             $38.5B       9.1%          156
3     Raytheon Technologies      $32.1B       7.5%          234
... (through rank 10)

CONTRACT SIZE DISTRIBUTION
─────────────────────────────────────────────────────────────
Average Contract Size:     $2.93M
Median Contract Size:      $1.2M
Minimum:                   $5,000
Maximum:                   $425M

Distribution by Range:
< $100K        12.4%  of contracts (but only 1.2% of spending)
$100K-$1M      34.8%  of contracts (8.2% of spending)
$1M-$10M       28.7%  of contracts (31.5% of spending)
$10M-$50M      15.2%  of contracts (32.1% of spending)
$50M-$100M     6.8%   of contracts (15.2% of spending)
> $100M        2.1%   of contracts (11.8% of spending)

COMPETITION & SOLE-SOURCE ANALYSIS
─────────────────────────────────────────────────────────────
Competitive Contracts:     75.2% (multiple bidders)
Sole-Source Awards:        18.3% (single bidder)
Limited Competition:       6.5%  (2-3 bidders)

Justifications for Sole-Source:
├─ Only qualified source:  65.2% of sole-source
├─ Urgency:                22.1% of sole-source
└─ Other:                  12.7% of sole-source

EFFICIENCY ASSESSMENT
─────────────────────────────────────────────────────────────
Competition Level:         MODERATE ✓
Market Concentration:      MODERATE CONCERN ⚠
Vendor Diversity:          ADEQUATE ✓
Sole-Source Usage:         ACCEPTABLE ✓

RECOMMENDATIONS
─────────────────────────────────────────────────────────────
• Monitor top 5 vendors for concentration
• Increase outreach to mid-size vendors
• Reduce sole-source awards where possible
• Encourage more small business participation
```

**Information Included**:
- Vendor concentration metrics (HHI index)
- Market share distribution
- Contract size analysis
- Competition levels by sector
- Sole-source vs. competitive breakdown
- Vendor diversity statistics
- Competition trend analysis
- Procurement health assessment

**Efficiency Indicators**:

**Strong Indicators**:
- HHI < 1,500 (highly competitive)
- Top 5 vendors < 20% of spending
- 75%+ competitive contracts
- Diverse vendor base
- Reasonable contract sizes

**Warning Signs**:
- HHI > 2,500 (concentrated)
- Top 5 vendors > 40% of spending
- High sole-source usage
- Few unique vendors
- Skewed contract size distribution

**Use Cases**:
- Monitor procurement competition and health
- Identify market concentration issues
- Support antitrust or competition analysis
- Assess procurement efficiency
- Identify vendor diversity opportunities
- Research competition policy impact
- Analyze sector-specific competition levels
- Support business development strategy

---

## Query Syntax & Filtering

### Basic Query Format

The simplest way to use tools is with natural language:

```
"Find software development contracts"
→ Uses search_federal_awards with keywords:"software development"

"Show me the top contractors for DOD"
→ Uses search_federal_awards with agency:"dod" and analyze results

"Compare spending in California and Texas"
→ Uses compare_states with states:"California,Texas"
```

### Advanced Filtering Syntax

For more precise queries, use parameter syntax:

```
KEYWORD SEARCH
───────────────────────────────────────────────────────
keyword1 keyword2
→ All words (AND logic)
"software AND services"
→ Explicit AND operator

"software OR IT"
→ Either term acceptable (OR logic)

"software NOT development"
→ Exclude development (NOT logic)

"exact phrase search"
→ Match exact phrase


AGENCY FILTERING
───────────────────────────────────────────────────────
agency:dod
→ Department of Defense

agency:gsa subagency:disa
→ GSA with specific sub-agency

agency:hhs
→ Department of Health and Human Services


AMOUNT FILTERING
───────────────────────────────────────────────────────
amount:100K-1M
→ Awards between $100K and $1M

amount:$500K-5M
→ Alternative format (with $)

amount:1M
→ Exactly $1M or greater

amount:under100K
→ Less than $100K


AWARD TYPE FILTERING
───────────────────────────────────────────────────────
type:contract
→ Only contracts

type:grant
→ Only grants

type:contract type:grant
→ Contracts AND grants


RECIPIENT FILTERING
───────────────────────────────────────────────────────
recipient:Microsoft
→ Awards to specific company

recipient:"Booz Allen Hamilton"
→ Multi-word company name

recipient:DELL recipient:IBM
→ Multiple recipients


GEOGRAPHIC FILTERING
───────────────────────────────────────────────────────
scope:domestic
→ U.S. locations only

scope:international
→ Outside U.S.

state:California
→ Specific state

state:CA
→ Two-letter state abbreviation
```

### Complete Query Examples

```
Example 1: Software Development for DOD
─────────────────────────────────────────────────────────
Query: "software development agency:dod amount:500K-10M"
Components:
├─ Keywords: software development
├─ Agency: dod (Department of Defense)
└─ Amount Range: $500K to $10M

Result: DOD software contracts valued between half a million
        and ten million dollars


Example 2: GSA Contracts in California
─────────────────────────────────────────────────────────
Query: "IT services agency:gsa state:California"
Components:
├─ Keywords: IT services
├─ Agency: gsa (General Services Administration)
└─ State: California

Result: GSA's IT service contracts in California


Example 3: Small Business COVID Support
─────────────────────────────────────────────────────────
Query: "pandemic relief sb_type:dbe agency:dhs"
Using: analyze_small_business with disaster type
Components:
├─ Keywords: pandemic relief
├─ Business Type: dbe (Disadvantaged Enterprise)
└─ Agency: dhs (Department of Homeland Security)

Result: Disadvantaged business contracts for pandemic response
        awarded by DHS


Example 4: Manufacturing Sector Analysis
─────────────────────────────────────────────────────────
Query: "manufacturing sector metric:total"
Using: spending_efficiency_metrics
Components:
├─ Sector: manufacturing
└─ Metric: total spending analysis

Result: Comprehensive manufacturing procurement analysis showing
        competition, concentration, and efficiency metrics
```

---

## Use Cases & Examples

### Use Case 1: Small Business Searching for Federal Contracts

**Scenario**: You own a small IT services company and want to find federal contracting opportunities.

**Tools to Use**:
1. `search_federal_awards` - Find active opportunities
2. `analyze_small_business` - Understand set-asides
3. `get_agency_profile` - Identify major agencies
4. `get_vendor_profile` - Research competitors

**Query Sequence**:

```
Step 1: Find IT Services Opportunities
Query: "IT services AND small business"
Tool: search_federal_awards
Result: Find all IT contracts currently available

Step 2: Understand Set-Asides
Query: analyze_small_business(sb_type="dbe")
Result: See what percentage of federal IT spending goes to DBEs

Step 3: Identify Target Agencies
Query: get_agency_profile(agency="dod", detail_level="detail")
Result: See DOD's top IT contractors and spending patterns

Step 4: Research Competitors
Query: get_vendor_profile vendor_name:"Booz Allen Hamilton" show_contracts:true
Result: Understand competitor contract activity and growth
```

---

### Use Case 2: Policy Researcher Analyzing Federal Spending

**Scenario**: You're researching federal spending efficiency and market concentration.

**Tools to Use**:
1. `get_spending_trends` - Track historical changes
2. `spending_efficiency_metrics` - Measure concentration
3. `get_agency_profile` - Analyze agency patterns
4. `compare_states` - Study geographic distribution

**Query Sequence**:

```
Step 1: Understand Long-Term Trends
Query: get_spending_trends(agency="dod", period="fiscal_year")
Result: See DOD spending growth and patterns over 10+ years

Step 2: Measure Market Concentration
Query: spending_efficiency_metrics(agency="dod")
Result: Analyze HHI index, vendor concentration, competition levels

Step 3: Deep Dive into Agency Procurement
Query: get_agency_profile(agency="dod", detail_level="full")
Result: Understand DOD's top contractors and budget allocation

Step 4: Geographic Analysis
Query: compare_states(states:"California,Texas,Virginia", metric:"total")
Result: See where defense spending is concentrated

Step 5: Export Data for Analysis
Result: Use CSV export from search_federal_awards for detailed analysis
```

---

### Use Case 3: Journalist Investigating Government Spending

**Scenario**: You're writing a story about government contracting and want compelling data.

**Tools to Use**:
1. `search_federal_awards` - Find notable contracts
2. `get_vendor_profile` - Research major contractors
3. `analyze_federal_spending` - Get statistics
4. `emergency_spending_tracker` - Track crisis spending

**Query Sequence**:

```
Step 1: Find Largest Contracts
Query: search_federal_awards keywords:"defense" results:50
       sort by amount descending
Result: Top 50 defense contracts with amounts and recipients

Step 2: Profile Top Contractors
Query: get_vendor_profile vendor_name:"Lockheed Martin" show_contracts:true
Result: Understand company's federal business and recent contracts

Step 3: Get Spending Statistics
Query: analyze_federal_spending(keywords:"defense" agency:"dod")
Result: Generate compelling statistics about defense spending

Step 4: Track Emergency Spending
Query: emergency_spending_tracker(disaster_type="hurricane" state="Florida")
Result: Analyze federal disaster relief contracts and spending
```

---

### Use Case 4: Economic Development Officer Analyzing Regional Spending

**Scenario**: You're trying to understand federal spending in your state and identify growth opportunities.

**Tools to Use**:
1. `get_spending_by_state` - Understand your state
2. `compare_states` - Compare to peer states
3. `get_top_naics_breakdown` - Identify top industries
4. `analyze_small_business` - Understand SB opportunities

**Query Sequence**:

```
Step 1: Understand Your State's Spending
Query: get_spending_by_state(state="North Carolina", top_n=20)
Result: See total NC federal spending, top contractors, agencies

Step 2: Compare to Similar States
Query: compare_states(states:"North Carolina,South Carolina,Virginia" metric:"percapita")
Result: See how NC compares on per-capita basis

Step 3: Identify Growth Industries
Query: get_top_naics_breakdown()
Result: See which industries receive most federal contracts nationwide

Step 4: Support Small Business
Query: analyze_small_business(state="NC")
Result: Identify federal small business set-asides in your state
```

---

## Advanced Features

### Feature 1: CSV Export

Export results from any search in CSV format for analysis in Excel or other tools:

```
Query: search_federal_awards(keywords:"software", results:100)
Result includes: CSV export option with fields:
├─ Recipient Name
├─ Award ID
├─ Award Amount
├─ Award Type
├─ NAICS Code & Description
├─ PSC Code & Description
├─ Award Description
└─ Link to Details

How to Use: Copy the CSV text and paste into Excel
```

### Feature 2: Pagination

Large result sets are automatically paginated:

```
First Request: Returns results 1-100
Output shows: "Next page available"

Pagination Info Provided:
├─ Current page number
├─ Total results
├─ Results per page
└─ Has next page indicator

How to Use: Request additional results if needed
```

### Feature 3: Direct Links to USASpending.gov

Every award result includes a direct link to the full award details:

```
Award Details URL:
https://www.usaspending.gov/award/[generated_internal_id]/

Click to view:
├─ Complete contract details
├─ Amendment history
├─ Subaward information
├─ Recipient location
└─ Funding sources
```

### Feature 4: Boolean Search Operators

Combine terms for precise searches:

```
AND     → Both terms must appear
         "software AND development" (both required)

OR      → Either term acceptable
         "software OR IT" (either acceptable)

NOT     → Exclude terms
         "software NOT hardware" (exclude hardware)

Examples:
"(software OR IT) AND contracts"
→ Contracts related to software or IT

"development NOT research"
→ Development without research

"federal NOT state AND contracts"
→ Federal contracts that don't mention state
```

### Feature 5: Agency Hierarchies

Support for both top-tier and sub-tier agencies:

```
Top-Tier Agencies (40+):
dod        → Department of Defense (with 10+ sub-agencies)
dhs        → Department of Homeland Security (with 8+ sub-agencies)
hhs        → Health and Human Services (with 15+ sub-agencies)
... etc

Sub-Tier Agencies (150+):
Can filter by specific sub-agency within departments
Example: agency:dod subagency:disa
         → DOD's Defense Information Systems Agency

Usage: agency:dod OR agency:dhs (combine multiple agencies)
```

### Feature 6: Dynamic Date Ranges

Automatic 180-day rolling lookback:

```
System automatically calculates:
Today: October 28, 2025
Start Date: May 2, 2025 (180 days back)
End Date: October 28, 2025 (today)

Returns only recent awards from last 6 months
No need to manually specify dates
Updates daily as new data arrives
```

---

## Technology Stack

### Backend Components

```
Framework:       FastMCP (Python)
├─ Modern MCP implementation
├─ Async/await support
└─ High performance

API Connection:  httpx
├─ Async HTTP client
├─ Handles large result sets
└─ Automatic retry logic

Data Format:     JSON
├─ Native to Python
├─ Easy parsing and transformation
└─ Compatible with all tools

Server Types:    Stdio (CLI) & HTTP (Claude Desktop)
├─ Stdio: Direct client connection
├─ HTTP: Network-based integration
└─ Both supported simultaneously
```

### Key Libraries

```
mcp>=1.18.0          MCP protocol implementation
fastmcp>=1.0.0       FastMCP framework
httpx>=0.27.0        Async HTTP client
uvicorn              ASGI application server
fastapi              Web framework for HTTP server
pydantic             Data validation
```

### Data Sources

```
USASpending.gov API v2
├─ Official federal spending database
├─ Real-time data feeds
├─ Maintained by GSA
└─ Free public access

Endpoints Used:
├─ /api/v2/search/spending_by_award/
├─ /api/v2/search/spending_by_geography/
├─ /api/v2/search/spending_over_time/
├─ /api/v2/references/naics/
├─ /api/v2/autocomplete/psc/
└─ /api/v2/autocomplete/recipient/
```

---

## API Reference

### USASpending.gov API v2 Endpoints

The server connects to these official USASpending.gov API endpoints:

#### 1. Spending by Award

```
Endpoint: /api/v2/search/spending_by_award/
Purpose:  Search federal contracts and grants
Method:   POST
Used by:  search_federal_awards

Sample Request:
{
  "filters": {
    "keywords": ["software"],
    "agencies": [{"name": "Department of Defense", "tier": "toptier"}],
    "award_type_codes": ["A", "B"],
    "time_period": [{"start_date": "2024-05-01", "end_date": "2024-10-28"}]
  },
  "limit": 100
}

Response Includes:
├─ Award ID and recipient
├─ Award amount and type
├─ Description and dates
└─ Award details
```

#### 2. Spending by Geography

```
Endpoint: /api/v2/search/spending_by_geography/
Purpose:  Geographic spending breakdown
Method:   POST
Used by:  get_spending_by_state, compare_states

Request: Filter by state or location

Response: Spending totals by geographic area
```

#### 3. Spending Over Time

```
Endpoint: /api/v2/search/spending_over_time/
Purpose:  Temporal spending analysis
Method:   POST
Used by:  get_spending_trends

Request: Filter by time period (fiscal or calendar year)

Response: Spending aggregated by time period
```

#### 4. NAICS Code References

```
Endpoint: /api/v2/references/naics/
Purpose:  Industry classification code lookup
Method:   GET
Used by:  get_naics_psc_info

Request: Search by code or term

Response: NAICS code definitions and descriptions
```

#### 5. PSC Code Autocomplete

```
Endpoint: /api/v2/autocomplete/psc/
Purpose:  Product/Service code lookup
Method:   GET
Used by:  get_naics_psc_info

Request: Search by code or term

Response: PSC code matches and descriptions
```

#### 6. Recipient Autocomplete

```
Endpoint: /api/v2/autocomplete/recipient/
Purpose:  Vendor/contractor name lookup
Method:   GET
Used by:  get_vendor_profile

Request: Company name search

Response: Matching recipients with identifiers
```

### API Documentation

For complete API documentation:
```
https://api.usaspending.gov/docs/endpoints
```

### Rate Limiting

- USASpending API: No documented rate limits
- Request timeout: 30 seconds per request
- Pagination: Supports up to 100 results per page

---

## Troubleshooting

### Common Issues and Solutions

#### Issue 1: "Server won't start"

**Problem**: Script fails to start or shows permission error

**Solutions**:
```bash
# Make scripts executable
chmod +x test_mcp_client.sh start_mcp_server.sh

# Try running with explicit Python path
python3 mcp_server.py

# Check if port 3002 is available
lsof -i :3002
# If port is in use, kill the process:
kill -9 <PID>
```

#### Issue 2: "No module named X"

**Problem**: Import error for httpx, mcp, or fastmcp

**Solutions**:
```bash
# Install all dependencies
pip3 install -r requirements.txt

# Or install individually
pip3 install httpx fastmcp mcp uvicorn fastapi pydantic

# Verify installation
python3 -c "import httpx; print(httpx.__version__)"
```

#### Issue 3: "API returns 422 error"

**Problem**: USASpending API returns "Unprocessable Entity"

**Solutions**:
```
✓ Verify filter combinations are valid
✓ Check that agency names are exact matches
✓ Ensure date formats are correct (YYYY-MM-DD)
✓ Try simpler query without complex filters
✓ Wait and retry (API may be temporarily unavailable)

Common Causes:
├─ Invalid agency name or code
├─ Conflicting filter combinations
├─ Malformed date ranges
└─ API backend issues (usually temporary)
```

#### Issue 4: "Results are empty"

**Problem**: Query returns no results

**Solutions**:
```
✓ Try broader search terms (more general keywords)
✓ Remove restrictive filters (try without amount limit)
✓ Check spelling of agency and state names
✓ Use different search terms
✓ Verify the award type is available

Example:
Instead of:     "obscure product AND specific agency"
Try:            "category OR product type" (broader)
```

#### Issue 5: "Claude Desktop won't connect"

**Problem**: Claude Desktop doesn't see the USASpending tools

**Solutions**:
```
1. Verify server is running:
   Check that start_mcp_server.sh is still active

2. Check configuration:
   ~/Library/Application\ Support/Claude/claude_desktop_config.json
   Should have:
   {
     "mcpServers": {
       "usaspending": {
         "url": "http://localhost:3002/mcp"
       }
     }
   }

3. Restart Claude Desktop completely

4. Check server logs for errors

5. Verify port 3002 is accessible:
   curl http://localhost:3002/mcp/tools
   Should return tool list
```

#### Issue 6: "Slow results or timeouts"

**Problem**: Queries take too long or timeout

**Solutions**:
```
✓ Reduce results limit (use results:10 instead of results:100)
✓ Add more specific filters to narrow results
✓ Use amount range to exclude very large/small awards
✓ Check your internet connection
✓ Try again later (API may be loaded)

Performance Tips:
├─ Smaller result sets load faster
├─ Specific agencies filter faster
├─ Recent data (last 6 months) searches faster
└─ Avoid very broad keyword searches
```

### Getting Help

**Check the documentation**:
- This file for tool descriptions
- Tool descriptions in the UI for parameter details
- USASpending.gov for data questions

**Debug output**:
When reporting issues, include:
- Exact query used
- Error message returned
- Tool name
- Server logs (from terminal)

**USASpending.gov Resources**:
- API Documentation: https://api.usaspending.gov/docs
- Data Format Guide: https://github.com/fedspendingtransparency/usaspending-api
- Support: https://www.usaspending.gov/

---

## Summary

The USASpending MCP Server provides comprehensive federal spending analysis through **14 powerful tools**:

### Organization

**Original Tools (4)** - Core functionality:
- search_federal_awards
- analyze_federal_spending
- get_naics_psc_info
- get_top_naics_breakdown

**Phase 1 (4)** - Geographic & temporal analysis:
- get_spending_by_state
- get_spending_trends
- get_budget_functions
- get_vendor_profile

**Phase 2 (2)** - Agency & budget analysis:
- get_agency_profile
- get_object_class_analysis

**Phase 3 (4)** - Advanced comparisons:
- compare_states
- analyze_small_business
- emergency_spending_tracker
- spending_efficiency_metrics

### Quick Reference

**To start**: `./test_mcp_client.sh`
**For Claude Desktop**: `./start_mcp_server.sh`
**To understand a tool**: See the Tool Reference section above
**For help**: Check Troubleshooting section

### Getting Started

1. Run the quick test to verify everything works
2. Try a simple search query (e.g., "software contracts")
3. Explore specific tools based on your needs
4. Refine queries with advanced filters
5. Export results as CSV for further analysis

---

**Happy analyzing!** For questions about specific tools, refer to the Tool Reference section above. For technical issues, see Troubleshooting.
