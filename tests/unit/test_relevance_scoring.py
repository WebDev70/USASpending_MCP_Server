"""Unit tests for RelevanceScorer utility."""

import pytest

from usaspending_mcp.utils.relevance_scoring import RelevanceScorer


class TestRelevanceScorer:
    """Tests for RelevanceScorer class."""

    @pytest.fixture
    def scorer(self):
        """Create a RelevanceScorer instance."""
        return RelevanceScorer()

    @pytest.fixture
    def sample_award(self):
        """Sample award dictionary."""
        return {
            "Recipient Name": "Cybersecurity Solutions Inc",
            "Award ID": "AWARD-001",
            "Award Amount": 100000,
            "Description": "Development of advanced cybersecurity software and tools",
            "NAICS Description": "Computer Systems Design Services",
            "PSC Description": "Software Development",
        }

    def test_score_award_exact_match(self, scorer, sample_award):
        """Test scoring award with exact keyword matches."""
        keywords = ["cybersecurity", "software"]
        score_data = scorer.score_award(sample_award, keywords)

        assert score_data is not None
        assert "overall_score" in score_data
        assert "keyword_score" in score_data
        assert 0 <= score_data["overall_score"] <= 100
        # Should have high score due to multiple matches
        assert score_data["overall_score"] >= 70

    def test_score_award_no_match(self, scorer, sample_award):
        """Test scoring award with no keyword matches."""
        keywords = ["aerospace", "defense"]
        score_data = scorer.score_award(sample_award, keywords)

        assert score_data is not None
        # Should have low score
        assert score_data["overall_score"] < 60

    def test_score_award_partial_match(self, scorer, sample_award):
        """Test scoring award with partial keyword match."""
        keywords = ["cyber", "hardware"]  # "cyber" is partial match in "cybersecurity"
        score_data = scorer.score_award(sample_award, keywords)

        assert score_data is not None
        # Should have medium score
        assert 40 <= score_data["overall_score"] <= 85

    def test_score_award_empty_keywords(self, scorer, sample_award):
        """Test scoring with empty keywords."""
        keywords = []
        score_data = scorer.score_award(sample_award, keywords)

        assert score_data is not None
        # Should have default score
        assert score_data["overall_score"] == 50

    def test_sort_by_relevance(self, scorer):
        """Test sorting awards by relevance."""
        awards = [
            {
                "Recipient Name": "General IT Services",
                "Description": "Information technology consulting",
                "NAICS Description": "Consulting Services",
                "PSC Description": "IT Services",
            },
            {
                "Recipient Name": "Cybersecurity Solutions",
                "Description": "Cybersecurity software development and implementation",
                "NAICS Description": "Computer Systems Design",
                "PSC Description": "Software Development",
            },
            {
                "Recipient Name": "Network Hardware Inc",
                "Description": "Network equipment and hardware sales",
                "NAICS Description": "Hardware Sales",
                "PSC Description": "IT Hardware",
            },
        ]

        keywords = ["cybersecurity", "software"]
        sorted_awards = scorer.sort_by_relevance(awards, keywords)

        assert len(sorted_awards) == 3
        # First award should be highest relevance (Cybersecurity Solutions)
        assert "Cybersecurity Solutions" in sorted_awards[0]["Recipient Name"]
        # Should have relevance scores
        assert "_relevance_score" in sorted_awards[0]

    def test_get_scoring_breakdown(self, scorer):
        """Test getting scoring statistics."""
        awards = [
            {
                "Recipient Name": "High Relevance Corp",
                "_relevance_score": {"overall_score": 90},
            },
            {
                "Recipient Name": "Medium Relevance Corp",
                "_relevance_score": {"overall_score": 60},
            },
            {
                "Recipient Name": "Low Relevance Corp",
                "_relevance_score": {"overall_score": 30},
            },
        ]

        breakdown = scorer.get_scoring_breakdown(awards)

        assert breakdown is not None
        assert "average_relevance" in breakdown
        assert "max_relevance" in breakdown
        assert "min_relevance" in breakdown
        assert "high_relevance_count" in breakdown
        assert "medium_relevance_count" in breakdown
        assert "low_relevance_count" in breakdown

        # Check calculations
        assert breakdown["max_relevance"] == 90
        assert breakdown["min_relevance"] == 30
        assert breakdown["high_relevance_count"] == 1
        assert breakdown["medium_relevance_count"] == 1
        assert breakdown["low_relevance_count"] == 1

    def test_explain_score(self, scorer):
        """Test score explanation."""
        award = {
            "Recipient Name": "Test Corp",
            "Description": "Test description",
        }

        # High score
        explanation = scorer._explain_score(award, ["test"], 95)
        assert "Highly relevant" in explanation

        # Medium score
        explanation = scorer._explain_score(award, ["test"], 65)
        assert "Relevant" in explanation or "relevant" in explanation.lower()

        # Low score
        explanation = scorer._explain_score(award, ["test"], 40)
        assert "Low" in explanation

    def test_get_match_type(self, scorer):
        """Test match type detection."""
        # Exact match
        match = scorer._get_match_type("cyber", "cybersecurity")
        assert match == "exact"

        # No match
        match = scorer._get_match_type("aerospace", "cybersecurity")
        assert match is None

        # Partial word match
        match = scorer._get_match_type("cyber", "cyber-secure systems")
        assert match in ["exact", "partial"]

    def test_relevance_scorer_context_awareness(self, scorer, sample_award):
        """Test relevance scoring with context."""
        keywords = ["software"]
        context = {"set_aside_preference": "SDVOSB"}

        score_data = scorer.score_award(sample_award, keywords, context)

        assert score_data is not None
        # Should have context score
        assert "context_score" in score_data
        assert 0 <= score_data["context_score"] <= 100

    def test_field_weights(self, scorer):
        """Test that field weights are applied correctly."""
        # Award matching recipient name (high weight)
        award_recipient_match = {
            "Recipient Name": "Cybersecurity Corp",
            "Description": "General IT services",
            "NAICS Description": "IT Services",
            "PSC Description": "IT Services",
        }

        # Award matching description (medium weight)
        award_description_match = {
            "Recipient Name": "ABC Corp",
            "Description": "Cybersecurity software development",
            "NAICS Description": "Software Services",
            "PSC Description": "IT Services",
        }

        keywords = ["cybersecurity"]

        score1 = scorer.score_award(award_recipient_match, keywords)["overall_score"]
        score2 = scorer.score_award(award_description_match, keywords)["overall_score"]

        # Recipient name match should score higher (or equal)
        assert score1 >= score2 or abs(score1 - score2) < 10

    def test_empty_awards_list(self, scorer):
        """Test with empty awards list."""
        breakdown = scorer.get_scoring_breakdown([])
        assert breakdown == {}

    def test_awards_missing_relevance_score(self, scorer):
        """Test handling of awards without relevance scores."""
        awards = [
            {"Recipient Name": "Corp 1"},
            {"Recipient Name": "Corp 2", "_relevance_score": {"overall_score": 75}},
        ]

        breakdown = scorer.get_scoring_breakdown(awards)

        # Should handle missing scores gracefully
        assert "average_relevance" in breakdown
        assert breakdown is not None
