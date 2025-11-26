"""Unit tests for ResultAggregator utility."""

import pytest

from usaspending_mcp.utils.result_aggregation import ResultAggregator


class TestResultAggregator:
    """Tests for ResultAggregator class."""

    @pytest.fixture
    def aggregator(self):
        """Create a ResultAggregator instance."""
        return ResultAggregator()

    @pytest.fixture
    def sample_awards(self):
        """Sample award dictionaries."""
        return [
            {
                "Recipient Name": "Acme Corp",
                "Award ID": "AWARD-001",
                "Award Amount": 50000,
                "Award Type": "Contract",
                "awarding_agency_name": "Department of Defense",
                "NAICS Code": "541511",
                "NAICS Description": "Custom Computer Programming Services",
                "Description": "Custom software development",
                "PSC Code": "D302",
                "PSC Description": "Software Development",
            },
            {
                "Recipient Name": "Acme Corp",
                "Award ID": "AWARD-002",
                "Award Amount": 75000,
                "Award Type": "Contract",
                "awarding_agency_name": "General Services Administration",
                "NAICS Code": "541511",
                "NAICS Description": "Custom Computer Programming Services",
                "Description": "Software testing and quality assurance",
                "PSC Code": "D302",
                "PSC Description": "Software Development",
            },
            {
                "Recipient Name": "Tech Solutions Inc",
                "Award ID": "AWARD-003",
                "Award Amount": 100000,
                "Award Type": "Contract",
                "awarding_agency_name": "Department of Defense",
                "NAICS Code": "541512",
                "NAICS Description": "Computer Systems Design Services",
                "Description": "IT infrastructure design",
                "PSC Code": "D399",
                "PSC Description": "Other Information Technology Services",
            },
        ]

    def test_aggregate_awards_by_recipient(self, aggregator, sample_awards):
        """Test aggregating awards by recipient."""
        aggregated = aggregator.aggregate_awards_by_recipient(sample_awards)

        assert "Acme Corp" in aggregated
        assert "Tech Solutions Inc" in aggregated

        # Check Acme Corp aggregation
        acme = aggregated["Acme Corp"]
        assert acme["count"] == 2
        assert acme["total_amount"] == 125000
        assert len(acme["awards"]) == 2
        assert "Contract" in acme["award_types"]

        # Check Tech Solutions aggregation
        tech = aggregated["Tech Solutions Inc"]
        assert tech["count"] == 1
        assert tech["total_amount"] == 100000

    def test_aggregate_awards_by_naics(self, aggregator, sample_awards):
        """Test aggregating awards by NAICS code."""
        aggregated = aggregator.aggregate_awards_by_naics(sample_awards)

        assert "541511" in aggregated
        assert "541512" in aggregated

        # Check NAICS 541511 aggregation
        naics_541511 = aggregated["541511"]
        assert naics_541511["count"] == 2
        assert naics_541511["total_amount"] == 125000
        assert "Acme Corp" in naics_541511["recipients"]

        # Check NAICS 541512 aggregation
        naics_541512 = aggregated["541512"]
        assert naics_541512["count"] == 1
        assert naics_541512["total_amount"] == 100000

    def test_explain_match_description(self, aggregator):
        """Test explaining match when query matches description."""
        award = {
            "Recipient Name": "Acme Corp",
            "Description": "cybersecurity software implementation",
            "NAICS Description": "Software Services",
            "PSC Description": "IT Services",
        }

        keywords = ["cybersecurity", "software"]
        explanation = aggregator.explain_match(award, keywords)

        assert explanation is not None
        assert "matched_fields" in explanation
        assert "description" in explanation["matched_fields"]
        assert explanation["confidence"] >= 70

    def test_explain_match_recipient(self, aggregator):
        """Test explaining match when query matches recipient name."""
        award = {
            "Recipient Name": "Cybersecurity Solutions LLC",
            "Description": "General IT services",
            "NAICS Description": "Software Services",
            "PSC Description": "IT Services",
        }

        keywords = ["cybersecurity"]
        explanation = aggregator.explain_match(award, keywords)

        assert explanation is not None
        assert "recipient_name" in explanation["matched_fields"]

    def test_explain_match_no_match(self, aggregator):
        """Test explaining match when keywords don't match."""
        award = {
            "Recipient Name": "Acme Corp",
            "Description": "General IT services",
            "NAICS Description": "Software Services",
            "PSC Description": "IT Services",
        }

        keywords = ["aerospace", "defense"]
        explanation = aggregator.explain_match(award, keywords)

        assert explanation is not None
        assert len(explanation["matched_fields"]) == 0
        assert explanation["confidence"] == 60

    def test_generate_aggregated_summary_by_recipient(self, aggregator, sample_awards):
        """Test generating aggregated summary by recipient."""
        summary = aggregator.generate_aggregated_summary(
            sample_awards, aggregation_type="recipient", limit=5
        )

        assert summary is not None
        assert "Top" in summary
        assert "Acme Corp" in summary
        assert "Tech Solutions Inc" in summary
        assert "$" in summary  # Should have currency format

    def test_generate_aggregated_summary_by_naics(self, aggregator, sample_awards):
        """Test generating aggregated summary by NAICS code."""
        summary = aggregator.generate_aggregated_summary(
            sample_awards, aggregation_type="naics", limit=5
        )

        assert summary is not None
        assert "541511" in summary or "Custom Computer Programming" in summary

    def test_generate_aggregated_summary_respects_limit(self, aggregator, sample_awards):
        """Test that aggregated summary respects limit parameter."""
        summary = aggregator.generate_aggregated_summary(
            sample_awards, aggregation_type="recipient", limit=1
        )

        # Should only show 1 recipient
        assert summary.count("$") >= 1  # At least 1 amount
        # Should not show more than 2 recipients
        assert summary.count("Tech Solutions Inc") <= 1

    def test_format_awards_with_explanations(self, aggregator, sample_awards):
        """Test formatting awards with match explanations."""
        query_keywords = ["software", "cybersecurity"]
        output = aggregator.format_awards_with_explanations(
            sample_awards[:1],
            query_keywords,
            total_count=100,
            current_page=1,
            has_next=True,
        )

        assert output is not None
        assert "100 total matches" in output
        assert "Page 1" in output
        assert "Match:" in output or "📌" in output
        assert "confidence:" in output

    def test_empty_awards_list(self, aggregator):
        """Test aggregation with empty awards list."""
        aggregated = aggregator.aggregate_awards_by_recipient([])
        assert aggregated == {}

        aggregated = aggregator.aggregate_awards_by_naics([])
        assert aggregated == {}

    def test_awards_with_missing_fields(self, aggregator):
        """Test aggregation handles awards with missing fields gracefully."""
        incomplete_awards = [
            {
                "Recipient Name": "Acme Corp",
                "Award Amount": 50000,
                # Missing other fields
            },
            {
                "Award ID": "AWARD-002",
                # Missing Recipient Name
                "Award Amount": 75000,
            },
        ]

        aggregated = aggregator.aggregate_awards_by_recipient(incomplete_awards)
        assert "Acme Corp" in aggregated
        assert "Unknown" in aggregated

        # Should not crash
        assert len(aggregated) > 0
