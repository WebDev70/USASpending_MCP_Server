#!/usr/bin/env python3
"""
Explore USASpending API response structure to identify set-aside and recipient type fields.

This script queries the API with different payloads to understand:
1. What fields are returned in award records
2. How set-aside information is represented
3. How to filter by SDVOSB and other set-aside types
"""

import httpx
import json
from pprint import pprint

BASE_URL = "https://api.usaspending.gov/api/v2"

def explore_gsa_contracts_response():
    """
    Query GSA contracts for FY2026 and examine the response structure.
    """
    print("=" * 100)
    print("EXPLORING USASPENDING API RESPONSE STRUCTURE")
    print("=" * 100)
    print()

    # Query 1: Basic GSA contracts for FY2026 with all available fields
    print("\n1. BASIC QUERY: GSA Contracts for FY2026 (Limited Results)")
    print("-" * 100)

    payload = {
        "filters": {
            "agencies": [
                {
                    "type": "toptier",
                    "tier": "toptier",
                    "toptier_name": "General Services Administration",
                    "name": "General Services Administration"
                }
            ],
            "award_type_codes": ["B"],  # Contracts only
            "time_period": [
                {
                    "start_date": "2025-10-01",
                    "end_date": "2026-09-30"
                }
            ]
        },
        "fields": [
            "Award ID",
            "Recipient Name",
            "Award Amount",
            "Award Type",
            "Description"
        ],
        "limit": 3,  # Get just a few to examine structure
        "page": 1
    }

    try:
        response = httpx.post(
            f"{BASE_URL}/search/spending_by_award/",
            json=payload,
            timeout=30
        )

        if response.status_code != 200:
            print(f"✗ Error Status {response.status_code}")
            print(f"Response: {response.text[:500]}")
            print("\nFY2026 data may not be available yet. Proceeding to FY2025 query...")
        else:
            response.raise_for_status()
            data = response.json()

            print(f"Status Code: {response.status_code}")
            print(f"\nResponse Keys: {list(data.keys())}")
            print(f"Page Metadata: {data.get('page_metadata', {})}")

            results = data.get('results', [])
            print(f"\nNumber of Results: {len(results)}")

            if results:
                print(f"\n✓ Found {len(results)} GSA contracts for FY2026")
                print("\nFirst award structure (all fields):")
                print("-" * 100)
                first_award = results[0]

                # Pretty print the first award to see all fields
                print(json.dumps(first_award, indent=2, default=str))

                print("\nAvailable fields in first award:")
                print("-" * 100)
                for key in sorted(first_award.keys()):
                    value = first_award[key]
                    value_type = type(value).__name__
                    print(f"  • {key:<40} ({value_type}): {str(value)[:60]}")
            else:
                print("\n✗ No results found. This might be because FY2026 data isn't available yet.")
                print("  Let's try a different date range...")

    except httpx.HTTPError as e:
        print(f"✗ Error: {e}")
        return

    # Query 2: Try recent data to see if set-aside fields exist
    print("\n\n2. ALTERNATIVE QUERY: GSA Contracts for FY2025 (to find structure)")
    print("-" * 100)

    payload2 = {
        "filters": {
            "agencies": [
                {
                    "type": "toptier",
                    "tier": "toptier",
                    "toptier_name": "General Services Administration",
                    "name": "General Services Administration"
                }
            ],
            "award_type_codes": ["B"],
            "time_period": [
                {
                    "start_date": "2024-10-01",
                    "end_date": "2025-09-30"
                }
            ]
        },
        "fields": [
            "Award ID",
            "Recipient Name",
            "Award Amount",
            "Award Type",
            "Description"
        ],
        "limit": 5,
        "page": 1
    }

    try:
        response2 = httpx.post(
            f"{BASE_URL}/search/spending_by_award/",
            json=payload2,
            timeout=30
        )
        response2.raise_for_status()
        data2 = response2.json()

        results2 = data2.get('results', [])
        print(f"Found {len(results2)} GSA contracts for FY2025")

        if results2:
            print(f"\n✓ Sample award from FY2025 (showing ALL fields):")
            print("-" * 100)
            sample_award = results2[0]
            print(json.dumps(sample_award, indent=2, default=str))

            print("\n\nAll unique fields across results:")
            print("-" * 100)
            all_fields = set()
            for award in results2:
                all_fields.update(award.keys())

            for field in sorted(all_fields):
                print(f"  • {field}")

            # Check specifically for set-aside related fields
            set_aside_keywords = ['set_aside', 'setaside', 'sdvosb', 'veteran', 'business_size',
                                  'recipient_type', 'contract_type', 'small_business', 'type_of_set_aside']

            print("\n\nSearching for set-aside related fields:")
            print("-" * 100)
            found_relevant = False
            for field in sorted(all_fields):
                if any(keyword in field.lower() for keyword in set_aside_keywords):
                    print(f"  ✓ FOUND: {field}")
                    found_relevant = True
                    # Show sample value
                    for award in results2:
                        if field in award:
                            print(f"      Sample value: {award[field]}")
                            break

            if not found_relevant:
                print("  ✗ No set-aside related fields found in standard fields")
                print("    Set-aside info might be in Description or require different filtering")
        else:
            print("✗ No results found for FY2025 either")

    except httpx.HTTPError as e:
        print(f"✗ Error: {e}")
        return

    # Query 3: Try searching with recipient_type or other filters
    print("\n\n3. CHECKING FILTER CAPABILITIES: Testing recipient_type filter")
    print("-" * 100)

    payload3 = {
        "filters": {
            "agencies": [
                {
                    "type": "toptier",
                    "tier": "toptier",
                    "toptier_name": "General Services Administration",
                    "name": "General Services Administration"
                }
            ],
            "award_type_codes": ["B"],
            "time_period": [
                {
                    "start_date": "2024-10-01",
                    "end_date": "2025-09-30"
                }
            ],
            # Try adding recipient type filter
            "recipient": {
                "type": "small_business"
            }
        },
        "fields": [
            "Award ID",
            "Recipient Name",
            "Award Amount",
            "Description"
        ],
        "limit": 3,
        "page": 1
    }

    try:
        response3 = httpx.post(
            f"{BASE_URL}/search/spending_by_award/",
            json=payload3,
            timeout=30
        )
        response3.raise_for_status()
        data3 = response3.json()

        results3 = data3.get('results', [])
        print(f"✓ Filter accepted! Found {len(results3)} results with 'small_business' recipient filter")

    except httpx.HTTPError as e:
        print(f"✗ Filter rejected or error: {e}")
        print("  The 'recipient.type' filter may not be supported this way")

    # Query 4: Keyword search for SDVOSB
    print("\n\n4. KEYWORD SEARCH: Looking for SDVOSB in descriptions")
    print("-" * 100)

    payload4 = {
        "filters": {
            "agencies": [
                {
                    "type": "toptier",
                    "tier": "toptier",
                    "toptier_name": "General Services Administration",
                    "name": "General Services Administration"
                }
            ],
            "award_type_codes": ["B"],
            "time_period": [
                {
                    "start_date": "2024-10-01",
                    "end_date": "2025-09-30"
                }
            ],
            "keywords": ["SDVOSB", "service disabled veteran"]
        },
        "fields": [
            "Award ID",
            "Recipient Name",
            "Award Amount",
            "Description"
        ],
        "limit": 5,
        "page": 1
    }

    try:
        response4 = httpx.post(
            f"{BASE_URL}/search/spending_by_award/",
            json=payload4,
            timeout=30
        )
        response4.raise_for_status()
        data4 = response4.json()

        results4 = data4.get('results', [])
        print(f"✓ Keyword search successful! Found {len(results4)} contracts matching 'SDVOSB'")

        if results4:
            print(f"\nSample SDVOSB contracts:")
            for i, award in enumerate(results4[:3], 1):
                print(f"\n  {i}. {award.get('Recipient Name', 'N/A')}")
                print(f"     Award ID: {award.get('Award ID', 'N/A')}")
                print(f"     Amount: ${award.get('Award Amount', 0):,.2f}")
                print(f"     Description: {award.get('Description', 'N/A')[:80]}")

    except httpx.HTTPError as e:
        print(f"✗ Error: {e}")

    # Summary
    print("\n\n" + "=" * 100)
    print("SUMMARY AND RECOMMENDATIONS")
    print("=" * 100)
    print("""
Based on exploration of the USASpending API, here are recommendations:

1. SET-ASIDE FIELD AVAILABILITY:
   - Check if standard response includes 'set_aside_type' or 'type_of_set_aside' field
   - If not available as a filter, set-aside info likely in Description or requires post-processing

2. FILTERING OPTIONS:
   - Keyword search works (e.g., searching for 'SDVOSB')
   - Recipient type filtering may be supported
   - Direct set-aside type filter may not be exposed

3. RECOMMENDED APPROACH:
   - Add 'set_aside_type' parameter to search_federal_awards tool
   - Use keyword matching to supplement filters where needed
   - Post-process results to identify SDVOSB contracts from description/notes

4. NEXT STEPS:
   - Implement extended search_federal_awards with set-aside support
   - Create specialized queries for each set-aside type
   - Update analyze_small_business to use proper filtering
""")

if __name__ == "__main__":
    explore_gsa_contracts_response()
