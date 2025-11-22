"""Result aggregation and explanation for federal awards.

Aggregates similar awards and provides explanations for why results matched
the user's query.
"""

import logging
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class ResultAggregator:
    """Aggregate and explain federal award results."""

    def __init__(self):
        """Initialize the aggregator."""
        self.logger = logger

    def aggregate_awards_by_recipient(
        self, awards: List[Dict[str, Any]]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Aggregate awards by recipient.

        Args:
            awards: List of award dictionaries

        Returns:
            Dictionary keyed by recipient name with aggregated data:
            {
                'recipient_name': {
                    'count': int,
                    'total_amount': float,
                    'awards': [list of original awards],
                    'award_types': set,
                    'agencies': set
                }
            }
        """
        aggregated = defaultdict(lambda: {
            "count": 0,
            "total_amount": 0.0,
            "awards": [],
            "award_types": set(),
            "agencies": set(),
        })

        for award in awards:
            recipient = award.get("Recipient Name", "Unknown")
            amount = float(award.get("Award Amount", 0))

            aggregated[recipient]["count"] += 1
            aggregated[recipient]["total_amount"] += amount
            aggregated[recipient]["awards"].append(award)
            aggregated[recipient]["award_types"].add(award.get("Award Type", "Unknown"))
            aggregated[recipient]["agencies"].add(
                award.get("awarding_agency_name", "Unknown")
            )

        # Convert sets to lists for JSON serialization
        for recipient_data in aggregated.values():
            recipient_data["award_types"] = list(recipient_data["award_types"])
            recipient_data["agencies"] = list(recipient_data["agencies"])

        return dict(aggregated)

    def aggregate_awards_by_naics(
        self, awards: List[Dict[str, Any]]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Aggregate awards by NAICS code (industry classification).

        Args:
            awards: List of award dictionaries

        Returns:
            Dictionary keyed by NAICS code with aggregated data
        """
        aggregated = defaultdict(lambda: {
            "count": 0,
            "total_amount": 0.0,
            "description": None,
            "recipients": set(),
            "award_types": set(),
        })

        for award in awards:
            naics_code = award.get("NAICS Code", "Unknown")
            naics_desc = award.get("NAICS Description", "")
            amount = float(award.get("Award Amount", 0))

            aggregated[naics_code]["count"] += 1
            aggregated[naics_code]["total_amount"] += amount
            aggregated[naics_code]["description"] = naics_desc
            aggregated[naics_code]["recipients"].add(
                award.get("Recipient Name", "Unknown")
            )
            aggregated[naics_code]["award_types"].add(award.get("Award Type", "Unknown"))

        # Convert sets to lists
        for naics_data in aggregated.values():
            naics_data["recipients"] = list(naics_data["recipients"])
            naics_data["award_types"] = list(naics_data["award_types"])

        return dict(aggregated)

    def explain_match(
        self, award: Dict[str, Any], query_keywords: List[str]
    ) -> Dict[str, Any]:
        """
        Explain why an award matches the query.

        Args:
            award: Award dictionary
            query_keywords: List of keywords from the search query

        Returns:
            Dictionary with explanation:
            {
                'matched_fields': ['field1', 'field2'],
                'match_explanation': 'Human-readable explanation',
                'confidence': 0-100
            }
        """
        matched_fields = []
        keyword_lower = [kw.lower() for kw in query_keywords]

        # Check description
        description = award.get("Description", "").lower()
        if any(kw in description for kw in keyword_lower):
            matched_fields.append("description")

        # Check recipient name
        recipient = award.get("Recipient Name", "").lower()
        if any(kw in recipient for kw in keyword_lower):
            matched_fields.append("recipient_name")

        # Check NAICS description
        naics_desc = award.get("NAICS Description", "").lower()
        if any(kw in naics_desc for kw in keyword_lower):
            matched_fields.append("naics_description")

        # Check PSC description
        psc_desc = award.get("PSC Description", "").lower()
        if any(kw in psc_desc for kw in keyword_lower):
            matched_fields.append("psc_description")

        # Generate explanation
        if not matched_fields:
            # Match by filter criteria (agency, award type, etc.)
            explanation = "Matched by award type, agency, or date filter"
            confidence = 60
        elif len(matched_fields) == 1:
            explanation = f"Matched on {matched_fields[0]}"
            confidence = 75
        else:
            explanation = f"Matched on {', '.join(matched_fields)}"
            confidence = 90

        return {
            "matched_fields": matched_fields,
            "match_explanation": explanation,
            "confidence": confidence,
        }

    def generate_aggregated_summary(
        self,
        awards: List[Dict[str, Any]],
        aggregation_type: str = "recipient",
        limit: int = 10,
    ) -> str:
        """
        Generate a summary of aggregated results.

        Args:
            awards: List of award dictionaries
            aggregation_type: 'recipient' or 'naics'
            limit: Maximum number of aggregations to show

        Returns:
            Formatted aggregation summary
        """
        if aggregation_type == "recipient":
            aggregated = self.aggregate_awards_by_recipient(awards)
        elif aggregation_type == "naics":
            aggregated = self.aggregate_awards_by_naics(awards)
        else:
            return "Invalid aggregation type"

        # Sort by total amount (descending)
        sorted_agg = sorted(
            aggregated.items(),
            key=lambda x: x[1].get("total_amount", 0),
            reverse=True,
        )[:limit]

        output = f"**Top {len(sorted_agg)} {aggregation_type.title()} by Total Award Amount**:\n\n"

        for i, (key, data) in enumerate(sorted_agg, 1):
            count = data.get("count", 0)
            total = data.get("total_amount", 0)

            if aggregation_type == "recipient":
                output += f"{i}. **{key}**\n"
            else:  # naics
                desc = data.get("description", "")
                output += f"{i}. **{key}** ({desc})\n" if desc else f"{i}. **{key}**\n"

            output += f"   • Count: {count} award{'s' if count != 1 else ''}\n"
            output += f"   • Total: ${total:,.2f}\n"

            if aggregation_type == "recipient":
                award_types = data.get("award_types", [])
                agencies = data.get("agencies", [])
                output += f"   • Types: {', '.join(award_types)}\n"
                output += f"   • Agencies: {', '.join(agencies)}\n"
            else:  # naics
                recipients = data.get("recipients", [])
                output += f"   • Top Recipients: {', '.join(recipients[:2])}\n"

            output += "\n"

        return output

    def format_awards_with_explanations(
        self,
        awards: List[Dict[str, Any]],
        query_keywords: List[str],
        total_count: int,
        current_page: int,
        has_next: bool,
    ) -> str:
        """
        Format awards with match explanations.

        Args:
            awards: List of award dictionaries
            query_keywords: Keywords from the search query
            total_count: Total number of results
            current_page: Current page number
            has_next: Whether more results are available

        Returns:
            Formatted output with explanations
        """
        output = f"Found {total_count} total matches (showing {len(awards)} on page {current_page}):\n\n"

        for i, award in enumerate(awards, 1):
            recipient = award.get("Recipient Name", "Unknown Recipient")
            award_id = award.get("Award ID", "N/A")
            amount = float(award.get("Award Amount", 0))
            award_type = award.get("Award Type", "Unknown")

            # Get explanation
            explanation = self.explain_match(award, query_keywords)

            output += f"{i}. {recipient}\n"
            output += f"   Award ID: {award_id}\n"
            output += f"   Amount: ${amount:,.2f}\n"
            output += f"   Type: {award_type}\n"

            # Add explanation
            output += f"   📌 Match: {explanation['match_explanation']} (confidence: {explanation['confidence']}%)\n"

            # Add description if available
            description = award.get("Description", "")
            if description:
                desc = description[:150]
                output += f"   Description: {desc}{'...' if len(description) > 150 else ''}\n"

            output += "\n"

        output += f"--- Page {current_page}"
        if has_next:
            output += " | More results available ---\n"
        else:
            output += " (Last page) ---\n"

        return output
