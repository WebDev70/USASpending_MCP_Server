"""
FAR (Federal Acquisition Regulation) Tools

Provides MCP tools for procurement professionals to search and reference
federal acquisition regulations from Parts 14, 15, 16, and 19.
"""

from __future__ import annotations

import re
import logging
from mcp.types import TextContent

from usaspending_mcp.utils.far import (
    get_far_database,
    initialize_far_database
)
from usaspending_mcp.utils.logging import get_logger
from usaspending_mcp.utils.search_analytics import (
    initialize_analytics,
    get_analytics
)

logger = get_logger("far_tools")


def register_far_tools(app):
    """Register all FAR regulatory tools with the FastMCP server."""

    # Initialize FAR database
    try:
        initialize_far_database()
        logger.info("FAR database initialized successfully")
    except Exception as e:
        logger.warning(f"Could not initialize FAR database: {e}")

    @app.tool(
        name="search_far_regulations",
        description="""Search FAR regulations by keyword across parts 14, 15, 16, and 19.

Searches all available FAR sections and returns results ranked by relevance.

PARAMETERS:
-----------
- keyword: Search term (e.g., "best value", "sealed bidding", "small business")
- part: Optional - restrict search to specific part (14, 15, 16, or 19)

RETURNS:
--------
- Matching FAR sections with relevance scores
- Section numbers, titles, and brief previews
- Total count of results

EXAMPLES:
---------
- search_far_regulations("best value") → All sections on best value procurement
- search_far_regulations("small business", "19") → Small business sections
- search_far_regulations("contract negotiation", "15") → Negotiation procedures
""",
    )
    async def search_far_regulations(keyword: str, part: str = None) -> list[TextContent]:
        """Search FAR regulations by keyword"""
        output = "=" * 100 + "\n"
        output += f"FAR SEARCH: '{keyword}'\n"
        if part:
            output += f"Part {part} only\n"
        output += "=" * 100 + "\n\n"

        try:
            far_db = get_far_database()
            results = far_db.search_keyword(keyword, part)

            if results:
                output += f"Found {len(results)} matching sections:\n\n"
                output += f"{'Section':<15} {'Part':<6} {'Title':<50} {'Relevance'}\n"
                output += "-" * 100 + "\n"

                for result in results[:20]:
                    section = result['section']
                    part_num = result['part']
                    title = result['title'][:40]
                    relevance = result['relevance']
                    output += f"{section:<15} {part_num:<6} {title:<50} {relevance}\n"

                if len(results) > 20:
                    output += f"\n... and {len(results) - 20} more results\n"
            else:
                output += f"No sections found matching '{keyword}'\n"

            # Log search event for analytics
            analytics = get_analytics("far")
            analytics.log_search(
                keyword=keyword,
                results_count=len(results),
                filter_value=part,
                search_type="keyword"
            )

        except Exception as e:
            output += f"Error searching FAR: {str(e)}\n"
            logger.error(f"Error in search_far_regulations: {e}")

        output += "\n" + "=" * 100 + "\n"
        return [TextContent(type="text", text=output)]

    @app.tool(
        name="get_far_section",
        description="""Get the complete text of a specific FAR section by number.

PARAMETERS:
-----------
- section_number: FAR section number (e.g., "15.203", "19.001", "14.201")

RETURNS:
--------
- Section number and title
- Full section content
- Related FAR.gov reference URL
- Part number for context

EXAMPLES:
---------
- get_far_section("15.203") → Full text of FAR 15.203 (RFP requirements)
- get_far_section("19.001") → Full text of FAR 19.001 (Small business definitions)
- get_far_section("14.305") → Full text of FAR 14.305 (Sealed bidding evaluation)
""",
    )
    async def get_far_section(section_number: str) -> list[TextContent]:
        """Get a specific FAR section by number"""
        output = "=" * 100 + "\n"
        output += f"FAR SECTION: {section_number}\n"
        output += "=" * 100 + "\n\n"

        try:
            far_db = get_far_database()
            section = far_db.get_section(section_number)

            if section:
                output += f"Section: {section['section']}\n"
                output += f"Part: {section['part']}\n"
                output += f"Title: {section['title']}\n\n"
                output += "-" * 100 + "\n"
                output += "CONTENT:\n"
                output += "-" * 100 + "\n"
                output += section['content'] + "\n\n"
                output += f"Reference: {section['url']}\n"
            else:
                output += f"Section {section_number} not found in FAR database.\n"
                output += "Check section number format (e.g., 15.203, 19.001)\n"

            # Log section lookup for analytics
            analytics = get_analytics("far")
            analytics.log_search(
                keyword=section_number,
                results_count=1 if section else 0,
                search_type="section"
            )

        except Exception as e:
            output += f"Error retrieving section: {str(e)}\n"
            logger.error(f"Error in get_far_section: {e}")

        output += "\n" + "=" * 100 + "\n"
        return [TextContent(type="text", text=output)]

    @app.tool(
        name="get_far_topic_sections",
        description="""Get all FAR sections related to a specific procurement topic.

Finds sections by topic keywords like "best value", "source selection", "small business", etc.

PARAMETERS:
-----------
- topic: Topic keyword (e.g., "best value", "sealed bidding", "small business")
- part: Optional - restrict to specific part (14, 15, 16, or 19)

RETURNS:
--------
- All relevant sections for the topic
- Section numbers and titles
- Part organization

EXAMPLES:
---------
- get_far_topic_sections("best value") → All sections on best value procurement
- get_far_topic_sections("small business") → Small business program sections (Part 19)
- get_far_topic_sections("source selection", "15") → Source selection in Part 15
""",
    )
    async def get_far_topic_sections(topic: str, part: str = None) -> list[TextContent]:
        """Get FAR sections by topic"""
        output = "=" * 100 + "\n"
        output += f"FAR TOPIC LOOKUP: {topic}\n"
        if part:
            output += f"Part {part} only\n"
        output += "=" * 100 + "\n\n"

        try:
            far_db = get_far_database()
            sections = far_db.get_topic_sections(topic, part)

            if sections:
                output += f"Found {len(sections)} sections related to '{topic}':\n\n"
                output += f"{'Section':<15} {'Part':<6} {'Title'}\n"
                output += "-" * 100 + "\n"

                for section in sections[:30]:
                    section_num = section['section']
                    part_num = section['part']
                    title = section['title']
                    output += f"{section_num:<15} {part_num:<6} {title}\n"

                if len(sections) > 30:
                    output += f"\n... and {len(sections) - 30} more sections\n"
            else:
                output += f"No sections found for topic '{topic}'\n"

            # Log topic lookup for analytics
            analytics = get_analytics("far")
            analytics.log_search(
                keyword=topic,
                results_count=len(sections),
                filter_value=part,
                search_type="topic"
            )

        except Exception as e:
            output += f"Error looking up topic: {str(e)}\n"
            logger.error(f"Error in get_far_topic_sections: {e}")

        output += "\n" + "=" * 100 + "\n"
        return [TextContent(type="text", text=output)]

    @app.tool(
        name="get_far_analytics_report",
        description="""Get search analytics and usage patterns from FAR tool usage.

Provides insights into which FAR topics are searched most frequently, identifies
searches that return zero results (potential gaps in topic mappings), and shows
trending search terms across multiple parts.

PARAMETERS:
-----------
- report_type: Type of report to generate (trending, zero_results, cross_part, summary)

RETURNS:
--------
- Analytics summary with trending topics, failed searches, and cross-part topics
- Useful for identifying missing topic mappings and improving FAR search capabilities

EXAMPLES:
---------
- get_far_analytics_report("summary") → Overall analytics summary
- get_far_analytics_report("trending") → Most popular FAR search terms
- get_far_analytics_report("zero_results") → Searches that found no results
- get_far_analytics_report("cross_part") → Searches spanning multiple FAR parts

""",
    )
    async def get_far_analytics_report(report_type: str = "summary") -> list[TextContent]:
        """Get FAR search analytics and usage patterns"""
        output = "=" * 100 + "\n"
        output += f"FAR ANALYTICS REPORT: {report_type.upper()}\n"
        output += "=" * 100 + "\n\n"

        try:
            analytics = get_analytics("far")
            report_type = report_type.lower()

            if report_type == "summary":
                report = analytics.generate_report()
                output += "SUMMARY REPORT\n"
                output += "-" * 100 + "\n"

                output += f"\nTRENDING TOPICS (Top 10):\n"
                if report.get("trending_topics"):
                    for item in report["trending_topics"]:
                        output += f"  {item['keyword']}: {item['searches']} searches ({item['success_rate']*100:.0f}% success)\n"
                else:
                    output += "  No search data available yet\n"

                output += f"\nZERO-RESULT SEARCHES (Gaps in topic mappings):\n"
                if report.get("zero_result_searches"):
                    for item in report["zero_result_searches"][:10]:
                        output += f"  '{item['keyword']}': {item['count']} times\n"
                else:
                    output += "  No zero-result searches found\n"

                output += f"\nCROSS-PART TOPICS (Multi-part searches):\n"
                if report.get("cross_filter_topics"):
                    for item in report["cross_filter_topics"][:10]:
                        output += f"  '{item['keyword']}': {item['count']} times\n"
                else:
                    output += "  No cross-part searches found\n"

                output += f"\n\nOVERALL STATISTICS:\n"
                if report.get("summary"):
                    output += f"  Total Searches: {report['summary'].get('total_searches', 0)}\n"
                    output += f"  Avg Results/Search: {report['summary'].get('avg_results_per_search', 0):.1f}\n"
                    output += f"  Zero-Result Rate: {report['summary'].get('zero_result_percentage', 0):.1f}%\n"

            elif report_type == "trending":
                trending = analytics.get_trending_topics(limit=20)
                output += "TRENDING SEARCH TERMS\n"
                output += "-" * 100 + "\n"
                output += f"{'Keyword':<30} {'Searches':<12} {'Success Rate':<15} {'Failures'}\n"
                output += "-" * 100 + "\n"

                if trending:
                    for item in trending:
                        output += f"{item['keyword']:<30} {item['searches']:<12} {item['success_rate']*100:>6.0f}% {item['failures']:<15}\n"
                else:
                    output += "No search data available yet\n"

            elif report_type == "zero_results":
                zero_results = analytics.get_zero_result_searches()
                output += "ZERO-RESULT SEARCHES (Potential topic mapping gaps)\n"
                output += "-" * 100 + "\n"
                output += f"{'Keyword':<40} {'Occurrences'}\n"
                output += "-" * 100 + "\n"

                if zero_results:
                    for item in zero_results[:30]:
                        output += f"{item['keyword']:<40} {item['count']:<10}\n"
                else:
                    output += "No zero-result searches found\n"

            elif report_type == "cross_part":
                cross_part = analytics.get_cross_part_searches()
                output += "CROSS-PART SEARCHES (Topics matching multiple FAR parts)\n"
                output += "-" * 100 + "\n"
                output += f"{'Keyword':<40} {'Search Count'}\n"
                output += "-" * 100 + "\n"

                if cross_part:
                    for item in cross_part[:30]:
                        output += f"{item['keyword']:<40} {item['count']:<10}\n"
                else:
                    output += "No cross-part searches found\n"

            else:
                output += f"Unknown report type: {report_type}\n"
                output += "Available types: summary, trending, zero_results, cross_part\n"

        except Exception as e:
            output += f"Error generating analytics report: {str(e)}\n"
            logger.error(f"Error in get_far_analytics_report: {e}")

        output += "\n" + "=" * 100 + "\n"
        return [TextContent(type="text", text=output)]

    @app.tool(
        name="check_far_compliance",
        description="""Check compliance of proposed contracting procedures with FAR rules.

Verifies that contracting methods and requirements comply with applicable FAR parts.

PARAMETERS:
-----------
- contracting_method: Method to check (e.g., "sealed_bidding", "negotiation", "small_business")
- requirements: List of planned requirements to verify (e.g., ["best value", "negotiations"])

RETURNS:
--------
- Compliance status (compliant/non-compliant)
- Issues identified
- Applicable FAR sections

EXAMPLES:
---------
- check_far_compliance("sealed_bidding") → Check sealed bidding compliance
- check_far_compliance("negotiation", ["best value"]) → Check negotiation with best value
- check_far_compliance("small_business") → Check small business program compliance
""",
    )
    async def check_far_compliance(contracting_method: str, requirements: list = None) -> list[TextContent]:
        """Check FAR compliance for contracting method"""
        output = "=" * 100 + "\n"
        output += f"FAR COMPLIANCE CHECK: {contracting_method}\n"
        output += "=" * 100 + "\n\n"

        try:
            far_db = get_far_database()
            requirements = requirements or []

            compliance = far_db.check_compliance(contracting_method, requirements)

            output += f"Method: {compliance['method']}\n"
            output += f"Status: {'COMPLIANT' if compliance['compliant'] else 'POTENTIAL ISSUES'}\n"

            if compliance['part']:
                output += f"FAR Part: {compliance['part']}\n"

            if compliance.get('issues'):
                output += f"\nIssues:\n"
                for issue in compliance['issues']:
                    output += f"  - {issue}\n"

            if compliance.get('relevant_sections'):
                output += f"\nRelevant FAR Sections:\n"
                for section in compliance['relevant_sections']:
                    output += f"  {section['section']}: {section['title']}\n"

            # Log compliance check for analytics
            analytics = get_analytics("far")
            analytics.log_search(
                keyword=contracting_method,
                results_count=len(compliance.get('relevant_sections', [])),
                search_type="compliance"
            )

        except Exception as e:
            output += f"Error checking compliance: {str(e)}\n"
            logger.error(f"Error in check_far_compliance: {e}")

        output += "\n" + "=" * 100 + "\n"
        return [TextContent(type="text", text=output)]
