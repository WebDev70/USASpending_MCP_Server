"""Query context analyzer for conversation-aware filtering suggestions.

Analyzes conversation history to extract previous filter parameters and
suggest progressive filtering when result sets are large.
"""

import logging
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class QueryContextAnalyzer:
    """Analyze conversation history to extract query context and patterns."""

    def __init__(self):
        """Initialize the analyzer."""
        self.logger = logger

    def extract_filters_from_conversation(
        self, conversation_records: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Extract commonly used filter parameters from conversation history.

        Args:
            conversation_records: List of tool call records from ConversationLogger

        Returns:
            Dictionary with extracted filter patterns:
            {
                'frequently_used_awards': set of award types,
                'frequently_used_agencies': set of agency names,
                'frequently_used_keywords': set of keywords,
                'date_range_preference': (start_date, end_date) tuple or None,
                'output_format_preference': 'text' or 'csv',
                'award_amount_range': (min, max) tuple or None
            }
        """
        context = {
            "frequently_used_awards": set(),
            "frequently_used_agencies": set(),
            "frequently_used_keywords": set(),
            "date_range_preference": None,
            "output_format_preference": "text",
            "award_amount_range": None,
            "set_aside_preference": None,
            "last_queries": [],
        }

        # Extract patterns from search_federal_awards tool calls
        search_calls = [
            r
            for r in conversation_records
            if r.get("tool_name") == "search_federal_awards"
        ]

        if not search_calls:
            return context

        # Extract filter patterns from input parameters
        for record in search_calls:
            try:
                params = record.get("input_params", {})
                query = params.get("query", "")

                # Track keywords (simple extraction from query string)
                if query:
                    # Remove metadata tags (amount:, award_type:, etc.) for keyword extraction
                    cleaned_query = self._extract_keywords(query)
                    context["frequently_used_keywords"].update(cleaned_query)
                    context["last_queries"].append(query)

                # Track output format preference
                if "output_format" in params:
                    context["output_format_preference"] = params["output_format"]

                # Track date ranges (if provided)
                if "start_date" in params and "end_date" in params:
                    context["date_range_preference"] = (
                        params["start_date"],
                        params["end_date"],
                    )

                # Track set-aside preference
                if "set_aside_type" in params and params["set_aside_type"]:
                    context["set_aside_preference"] = params["set_aside_type"]

            except Exception as e:
                self.logger.debug(f"Failed to extract context from record: {e}")

        # Keep only last 5 queries for reference
        context["last_queries"] = context["last_queries"][-5:]

        return context

    def _extract_keywords(self, query: str) -> List[str]:
        """
        Extract keywords from query string, filtering out metadata tags.

        Args:
            query: Raw query string

        Returns:
            List of extracted keywords
        """
        # Remove metadata tags (amount:, award_type:, etc.)
        metadata_prefixes = ["amount:", "award_type:", "agency:", "set_aside:"]

        parts = query.split()
        keywords = []

        for part in parts:
            # Skip if part is a metadata tag
            if any(part.lower().startswith(prefix) for prefix in metadata_prefixes):
                continue
            # Skip if part is too short (< 3 chars)
            if len(part) < 3:
                continue
            keywords.append(part.lower())

        return keywords

    def suggest_refinement_filters(
        self, total_results: int, context: Dict[str, Any]
    ) -> Optional[str]:
        """
        Generate progressive filtering suggestions based on result count.

        Args:
            total_results: Total number of results returned
            context: Query context from extract_filters_from_conversation()

        Returns:
            Suggestion text or None if no suggestion needed
        """
        # Only suggest if results exceed threshold
        LARGE_RESULT_THRESHOLD = 50

        if total_results <= LARGE_RESULT_THRESHOLD:
            return None

        suggestion = f"\n💡 **Tip**: Found {total_results} results. Consider refining with:\n"

        refinement_options = []

        # Suggest based on context
        if not context.get("set_aside_preference"):
            refinement_options.append("• **Set-aside type** (SDVOSB, WOSB, 8A, HUBZone, etc.)")

        # Suggest narrowing by award type
        refinement_options.append(
            "• **Award type** (contract, grant, loan, or specific codes)"
        )

        # Suggest geographic filtering
        refinement_options.append("• **State** or **location** filtering")

        # Suggest amount range
        refinement_options.append("• **Award amount range** (e.g., amount:1M-10M)")

        # Suggest fiscal year narrowing
        refinement_options.append("• **Fiscal year** or **date range**")

        if len(context.get("last_queries", [])) > 1:
            refinement_options.append("• **Or use command**: try_broader_search to expand results")

        suggestion += "\n".join(refinement_options[:3])  # Show top 3 suggestions
        suggestion += "\n\nFor example: `search_federal_awards(\"<your-query>\", set_aside_type=\"SDVOSB\")`\n"

        return suggestion

    def get_context_summary(self, context: Dict[str, Any]) -> str:
        """
        Generate a summary of extracted conversation context.

        Args:
            context: Query context dictionary

        Returns:
            Formatted context summary
        """
        summary = "**Conversation Context Summary**:\n"

        if context["frequently_used_keywords"]:
            summary += (
                f"• Frequent keywords: {', '.join(list(context['frequently_used_keywords'])[:5])}\n"
            )

        if context["set_aside_preference"]:
            summary += f"• Preferred set-aside: {context['set_aside_preference']}\n"

        if context["output_format_preference"] != "text":
            summary += f"• Preferred format: {context['output_format_preference']}\n"

        if context["last_queries"]:
            summary += f"• Recent query pattern recognized\n"

        return summary


def create_query_context_analyzer() -> QueryContextAnalyzer:
    """Create and return a new QueryContextAnalyzer instance."""
    return QueryContextAnalyzer()
