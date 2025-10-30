"""
FAR (Federal Acquisition Regulation) Tools

Provides MCP tools for procurement professionals to search and reference
federal acquisition regulations from Parts 14, 15, 16, and 19.
"""

import re
import logging
from mcp.types import TextContent
from ..helpers.far_loader import (
    load_far_all_parts,
    get_part_names,
    get_part_descriptions,
    get_full_part_names
)

logger = logging.getLogger(__name__)


def register_far_tools(app):
    """Register all FAR regulatory tools with the FastMCP server."""

    @app.tool(
        name="lookup_far_section",
        description="""Look up a specific FAR (Federal Acquisition Regulation) section by number.

PARAMETERS:
-----------
- section_number: FAR section number (e.g., "15.404-1", "14.305", "16.201", "19.305")

RETURNS:
--------
- Section title and full text content
- Related sections from the same part
- Practical guidance for procurement professionals

EXAMPLES:
---------
- lookup_far_section("15.404") → Information on proposal analysis (Part 15)
- lookup_far_section("14.305") → Sealed bidding evaluation procedures (Part 14)
- lookup_far_section("16.201") → Fixed-price contracts (Part 16)
- lookup_far_section("19.305") → 8(a) Business Development Program (Part 19)
""",
    )
    async def lookup_far_section(section_number: str) -> list[TextContent]:
        """Look up a specific FAR section from any part (14, 15, 16, 19)"""

        output = "=" * 100 + "\n"
        output += f"FAR SECTION LOOKUP: {section_number}\n"
        output += "=" * 100 + "\n\n"

        try:
            all_parts = load_far_all_parts()

            if not all_parts:
                output += "ERROR: FAR data not available\n"
                return [TextContent(type="text", text=output)]

            # Determine which part based on section number prefix
            part_match = re.match(r'^(\d+)\.', section_number)
            if not part_match:
                output += f"Invalid section number format: {section_number}\n"
                output += "Expected format: XX.YYY (e.g., 15.404, 19.305)\n"
                return [TextContent(type="text", text=output)]

            part_num = int(part_match.group(1))
            part_key = f"part{part_num}"

            # Check if we have this part
            if part_key not in all_parts:
                output += f"FAR Part {part_num} not available in this tool.\n"
                output += "Available parts: 14, 15, 16, 19\n"
                return [TextContent(type="text", text=output)]

            far_data = all_parts[part_key]

            # Normalize section number (remove variations like 15.404-1(c))
            base_section = re.match(rf'^({part_num}\.\d+(?:-\d+)?)', section_number)
            if not base_section:
                output += f"Invalid section number for Part {part_num}: {section_number}\n"
                return [TextContent(type="text", text=output)]

            base_section = base_section.group(1)

            if base_section in far_data:
                section_data = far_data[base_section]
                output += f"SECTION: {base_section}\n"

                # Get part name
                part_names = get_part_names()
                part_display = part_names.get(part_num, "Procurement")
                output += f"PART {part_num}: {part_display}\n"
                output += f"TITLE: {section_data.get('title', 'N/A')}\n\n"
                output += "-" * 100 + "\n"
                output += "CONTENT:\n"
                output += "-" * 100 + "\n"
                output += section_data.get('content', 'No content available') + "\n\n"

                # Find related sections in the same part
                related = [s for s in far_data.keys() if s.startswith(f"{part_num}.") and s != base_section]
                if related:
                    output += "-" * 100 + "\n"
                    output += f"RELATED SECTIONS IN PART {part_num} ({len(related)} total):\n"
                    output += "-" * 100 + "\n"
                    for rel_section in sorted(related)[:10]:
                        rel_title = far_data[rel_section].get('title', '')
                        output += f"{rel_section:<15} {rel_title}\n"
                    if len(related) > 10:
                        output += f"... and {len(related) - 10} more\n"
            else:
                output += f"Section {section_number} not found in FAR Part {part_num}.\n\n"
                output += f"Available sections in Part {part_num}:\n"
                for section_num in sorted(far_data.keys())[:20]:
                    output += f"  {section_num}: {far_data[section_num].get('title', '')}\n"
                output += f"\n... and {len(far_data) - 20} more sections available\n"

        except Exception as e:
            output += f"Error looking up section: {str(e)}\n"
            logger.error(f"Error in lookup_far_section: {e}")

        output += "\n" + "=" * 100 + "\n"
        return [TextContent(type="text", text=output)]

    @app.tool(
        name="search_far",
        description="""Search FAR (Parts 14, 15, 16, 19) by keywords or topics.

PARAMETERS:
-----------
- query: Search keywords (e.g., "price analysis", "small business", "cost reimbursement", "sealed bidding")

RETURNS:
--------
- List of matching FAR sections from all available parts
- Section numbers, titles, and part numbers
- Relevance ranking
- Top match details

EXAMPLES:
---------
- search_far("proposal evaluation") → All sections about evaluating proposals
- search_far("small business") → Sections on small business programs (Part 19)
- search_far("cost reimbursement") → Sections on cost-reimbursement contracts
- search_far("sealed bidding") → Sealed bidding procedures (Part 14)
""",
    )
    async def search_far(query: str) -> list[TextContent]:
        """Search all available FAR parts (14, 15, 16, 19) by keywords"""

        output = "=" * 100 + "\n"
        output += f"FAR SEARCH: '{query}' (Parts 14, 15, 16, 19)\n"
        output += "=" * 100 + "\n\n"

        try:
            all_parts = load_far_all_parts()

            if not all_parts:
                output += "ERROR: FAR data not available\n"
                return [TextContent(type="text", text=output)]

            # Search across all parts
            query_lower = query.lower()
            matches = []

            part_names_map = {
                "part14": "Part 14 - Sealed Bidding",
                "part15": "Part 15 - Contracting by Negotiation",
                "part16": "Part 16 - Types of Contracts",
                "part19": "Part 19 - Small Business Programs"
            }

            for part_key, far_data in all_parts.items():
                for section_num, section_data in far_data.items():
                    title = section_data.get('title', '').lower()
                    content = section_data.get('content', '').lower()

                    # Score based on relevance
                    score = 0
                    if query_lower in title:
                        score += 10  # Title match is more important
                    if query_lower in content:
                        score += 1

                    if score > 0:
                        matches.append((score, section_num, section_data, part_key))

            if matches:
                # Sort by score descending, then by section number
                matches.sort(key=lambda x: (-x[0], x[1]))

                output += f"FOUND {len(matches)} MATCHING SECTIONS ACROSS ALL PARTS:\n\n"
                output += f"{'Section':<15} {'Part':<15} {'Title':<50}\n"
                output += "-" * 100 + "\n"

                for score, section_num, section_data, part_key in matches[:20]:
                    part_display = part_key.replace("part", "Part ")
                    title = section_data.get('title', '')[:40]
                    output += f"{section_num:<15} {part_display:<15} {title:<50}\n"

                if len(matches) > 20:
                    output += f"\n... and {len(matches) - 20} more sections\n"

                output += "\n" + "-" * 100 + "\n"
                output += "TOP MATCH DETAILS:\n"
                output += "-" * 100 + "\n"
                top_score, top_section, top_data, top_part_key = matches[0]
                output += f"Section: {top_section}\n"
                output += f"Part: {part_names_map.get(top_part_key, 'Unknown')}\n"
                output += f"Title: {top_data.get('title', '')}\n\n"
                output += top_data.get('content', '')[:500] + "...\n"
            else:
                output += f"No sections found matching '{query}'\n\n"
                output += "Try searching for topics like:\n"
                output += "  - proposal evaluation, source selection, negotiations (Part 15)\n"
                output += "  - sealed bidding, competitive bids (Part 14)\n"
                output += "  - cost reimbursement, fixed price, IDIQ, contract types (Part 16)\n"
                output += "  - small business, 8(a), HUBZone, women-owned (Part 19)\n"

        except Exception as e:
            output += f"Error searching FAR: {str(e)}\n"
            logger.error(f"Error in search_far: {e}")

        output += "\n" + "=" * 100 + "\n"
        return [TextContent(type="text", text=output)]

    @app.tool(
        name="list_far_sections",
        description="""List all available FAR sections from Parts 14, 15, 16, and 19.

RETURNS:
--------
- Complete index of all available FAR sections
- Sections organized by part
- Part titles and descriptions

EXAMPLES:
---------
- list_far_sections() → Full list of all sections from all parts
""",
    )
    async def list_far_sections() -> list[TextContent]:
        """List all available FAR sections from all parts (14, 15, 16, 19)"""

        output = "=" * 100 + "\n"
        output += "FAR SECTIONS INDEX - Parts 14, 15, 16, 19\n"
        output += "=" * 100 + "\n\n"

        try:
            all_parts = load_far_all_parts()

            if not all_parts:
                output += "ERROR: FAR data not available\n"
                return [TextContent(type="text", text=output)]

            part_names_full = get_full_part_names()
            part_descriptions = get_part_descriptions()

            total_sections = 0

            # Process each part in order
            for part_key in ["part14", "part15", "part16", "part19"]:
                if part_key not in all_parts:
                    continue

                far_data = all_parts[part_key]
                part_sections = len(far_data)
                total_sections += part_sections

                output += f"\n{'=' * 100}\n"
                output += f"{part_names_full.get(part_key, 'Unknown Part')}\n"
                output += f"{part_descriptions.get(part_key, '')}\n"
                output += f"{'=' * 100}\n\n"

                # Organize sections by subpart
                subparts = {}
                for section_num in sorted(far_data.keys()):
                    # Extract subpart (14.1, 15.2, 16.3, etc.)
                    match = re.match(rf'^(\d+)\.(\d)', section_num)
                    if match:
                        subpart_num = match.group(2)
                        subpart = f"{match.group(1)}.{subpart_num}"
                        if subpart not in subparts:
                            subparts[subpart] = []
                        subparts[subpart].append((section_num, far_data[section_num]))

                # Print organized by subpart
                for subpart in sorted(subparts.keys()):
                    output += f"Subpart {subpart}:\n"
                    output += "-" * 100 + "\n"
                    for section_num, section_data in subparts[subpart]:
                        title = section_data.get('title', 'N/A')
                        output += f"  {section_num:<15} {title}\n"
                    output += "\n"

                output += f"Subtotal for {part_names_full.get(part_key, 'this part')}: {part_sections} sections\n\n"

            output += "=" * 100 + "\n"
            output += f"GRAND TOTAL: {total_sections} sections available across all parts\n"
            output += "=" * 100 + "\n"

        except Exception as e:
            output += f"Error listing sections: {str(e)}\n"
            logger.error(f"Error in list_far_sections: {e}")

        return [TextContent(type="text", text=output)]
