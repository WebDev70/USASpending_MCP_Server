"""Relevance scoring for federal awards with context awareness.

Scores awards based on keyword match quality, field placement, and conversation context.
"""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class RelevanceScorer:
    """Score relevance of awards based on query and context."""

    # Field weighting (higher = more relevant)
    FIELD_WEIGHTS = {
        "recipient_name": 3.0,  # Exact recipient match is most relevant
        "description": 2.0,  # Description match is very relevant
        "naics_description": 1.5,  # Industry classification match
        "psc_description": 1.5,  # Product/Service Code match
        "title": 2.0,  # Award title (if available)
        "other": 1.0,  # Default for other matches
    }

    # Match type weighting
    MATCH_TYPE_WEIGHTS = {
        "exact": 1.0,  # Exact match: "cybersecurity" matches "cybersecurity"
        "partial": 0.7,  # Partial match: "cyber" matches "cybersecurity"
        "word": 0.5,  # Word boundary match: "cloud" matches "cloud computing"
    }

    def __init__(self):
        """Initialize the scorer."""
        self.logger = logger

    def score_award(
        self,
        award: Dict[str, Any],
        query_keywords: List[str],
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Score an award based on relevance to query and context.

        Args:
            award: Award dictionary
            query_keywords: List of keywords from search query
            context: Optional conversation context with preferred filters

        Returns:
            Dictionary with scoring details:
            {
                'overall_score': 0-100,
                'keyword_score': 0-100,
                'context_score': 0-100,
                'field_matches': {field: score},
                'explanation': 'Human-readable explanation'
            }
        """
        context = context or {}

        # Calculate keyword relevance score
        keyword_score = self._score_keywords(award, query_keywords)

        # Calculate context alignment score
        context_score = self._score_context_alignment(award, context)

        # Combine scores (weighted average)
        overall_score = int(0.7 * keyword_score + 0.3 * context_score)

        return {
            "overall_score": overall_score,
            "keyword_score": keyword_score,
            "context_score": context_score,
            "explanation": self._explain_score(award, query_keywords, overall_score),
        }

    def _score_keywords(self, award: Dict[str, Any], keywords: List[str]) -> int:
        """
        Score award based on keyword matches.

        Args:
            award: Award dictionary
            keywords: List of keywords

        Returns:
            Score 0-100
        """
        if not keywords:
            return 50  # Default score if no keywords

        field_scores = {}

        # Check each searchable field
        for field, weight in self.FIELD_WEIGHTS.items():
            field_text = self._get_field_text(award, field).lower()

            if not field_text:
                continue

            # Score this field for all keywords
            field_match_score = 0
            matched_keywords = 0

            for keyword in keywords:
                keyword_lower = keyword.lower()
                match_type = self._get_match_type(keyword_lower, field_text)

                if match_type:
                    match_weight = self.MATCH_TYPE_WEIGHTS.get(match_type, 0)
                    field_match_score += match_weight
                    matched_keywords += 1

            if matched_keywords > 0:
                # Normalize to 0-100
                field_scores[field] = int((matched_keywords / len(keywords)) * 100 * weight)

        # Combine field scores (highest score wins, with slight bonus for multiple matches)
        if field_scores:
            max_score = max(field_scores.values())
            # Bonus for matching multiple fields
            num_fields = len(field_scores)
            bonus = min(num_fields * 3, 15)  # Max 15% bonus
            return min(int(max_score + bonus), 100)

        return 0  # No keyword matches

    def _score_context_alignment(
        self, award: Dict[str, Any], context: Dict[str, Any]
    ) -> int:
        """
        Score award based on conversation context alignment.

        Args:
            award: Award dictionary
            context: Conversation context

        Returns:
            Score 0-100
        """
        score = 50  # Baseline score

        # Boost if matches preferred set-aside
        preferred_setaside = context.get("set_aside_preference")
        if preferred_setaside and self._matches_context_pattern(award, preferred_setaside):
            score += 15

        # Boost if matches recent award types used
        # (This would require additional data in the award object)

        return min(score, 100)

    def _get_field_text(self, award: Dict[str, Any], field: str) -> str:
        """
        Extract text from award field for scoring.

        Args:
            award: Award dictionary
            field: Field name

        Returns:
            Text content of the field
        """
        field_map = {
            "recipient_name": "Recipient Name",
            "description": "Description",
            "naics_description": "NAICS Description",
            "psc_description": "PSC Description",
            "title": "Title",
        }

        return award.get(field_map.get(field, field), "")

    def _get_match_type(self, keyword: str, text: str) -> Optional[str]:
        """
        Determine match type between keyword and text.

        Args:
            keyword: Keyword to match
            text: Text to search

        Returns:
            'exact', 'partial', 'word', or None
        """
        # Exact match (full substring)
        if keyword in text:
            return "exact"

        # Partial match (keyword is a substring)
        # Check if keyword is contained as a word boundary match
        words = text.split()
        for word in words:
            if keyword in word:
                return "partial"

        return None

    def _matches_context_pattern(self, award: Dict[str, Any], pattern: str) -> bool:
        """
        Check if award matches a context pattern.

        Args:
            award: Award dictionary
            pattern: Pattern to match (e.g., set-aside code)

        Returns:
            True if award matches pattern
        """
        # This is a placeholder for more sophisticated pattern matching
        # In a real implementation, this would check against actual award attributes
        return True

    def _explain_score(
        self, award: Dict[str, Any], keywords: List[str], score: int
    ) -> str:
        """
        Generate explanation for a relevance score.

        Args:
            award: Award dictionary
            keywords: Keywords used
            score: Overall relevance score

        Returns:
            Human-readable explanation
        """
        if score >= 90:
            return "Highly relevant: Matched on multiple fields"
        elif score >= 70:
            return "Relevant: Matched on primary search criteria"
        elif score >= 50:
            return "Moderately relevant: Matched by filter criteria"
        else:
            return "Low relevance: Limited keyword matches"

    def sort_by_relevance(
        self,
        awards: List[Dict[str, Any]],
        query_keywords: List[str],
        context: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Sort awards by relevance score.

        Args:
            awards: List of award dictionaries
            query_keywords: Keywords from search query
            context: Optional conversation context

        Returns:
            Sorted list of awards with relevance scores added
        """
        scored_awards = []

        for award in awards:
            score_data = self.score_award(award, query_keywords, context)
            award_with_score = dict(award)
            award_with_score["_relevance_score"] = score_data

            scored_awards.append(award_with_score)

        # Sort by relevance score (descending)
        sorted_awards = sorted(
            scored_awards,
            key=lambda a: a.get("_relevance_score", {}).get("overall_score", 0),
            reverse=True,
        )

        return sorted_awards

    def get_scoring_breakdown(
        self, awards: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Get aggregate scoring statistics for a result set.

        Args:
            awards: List of awards (should have _relevance_score)

        Returns:
            Dictionary with scoring statistics
        """
        if not awards:
            return {}

        scores = [
            a.get("_relevance_score", {}).get("overall_score", 0)
            for a in awards
        ]

        return {
            "average_relevance": sum(scores) / len(scores) if scores else 0,
            "max_relevance": max(scores) if scores else 0,
            "min_relevance": min(scores) if scores else 0,
            "high_relevance_count": sum(1 for s in scores if s >= 70),
            "medium_relevance_count": sum(1 for s in scores if 50 <= s < 70),
            "low_relevance_count": sum(1 for s in scores if s < 50),
        }


def create_relevance_scorer() -> RelevanceScorer:
    """Create and return a new RelevanceScorer instance."""
    return RelevanceScorer()
