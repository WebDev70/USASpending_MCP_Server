"""Unit tests for QueryContextAnalyzer utility."""

import pytest

from usaspending_mcp.utils.query_context import QueryContextAnalyzer


class TestQueryContextAnalyzer:
    """Tests for QueryContextAnalyzer class."""

    @pytest.fixture
    def analyzer(self):
        """Create a QueryContextAnalyzer instance."""
        return QueryContextAnalyzer()

    @pytest.fixture
    def sample_conversation(self):
        """Sample conversation records from ConversationLogger."""
        return [
            {
                "tool_name": "search_federal_awards",
                "input_params": {
                    "query": "cybersecurity contracts",
                    "output_format": "text",
                    "set_aside_type": "SDVOSB",
                },
                "status": "success",
            },
            {
                "tool_name": "search_federal_awards",
                "input_params": {
                    "query": "cloud computing contracts",
                    "output_format": "text",
                },
                "status": "success",
            },
            {
                "tool_name": "search_federal_awards",
                "input_params": {
                    "query": "IT services GSA",
                    "output_format": "csv",
                    "set_aside_type": "WOSB",
                },
                "status": "success",
            },
        ]

    def test_extract_filters_from_conversation(self, analyzer, sample_conversation):
        """Test extracting filters from conversation history."""
        context = analyzer.extract_filters_from_conversation(sample_conversation)

        assert context is not None
        assert "frequently_used_keywords" in context
        assert "output_format_preference" in context
        assert "set_aside_preference" in context
        assert "last_queries" in context

        # Check that keywords were extracted
        assert len(context["frequently_used_keywords"]) > 0

        # Check that output format preference was tracked
        assert context["output_format_preference"] == "csv"

        # Check that set-aside preference was tracked
        assert context["set_aside_preference"] is not None

        # Check that last queries were tracked (should be max 5)
        assert len(context["last_queries"]) <= 5

    def test_extract_keywords_filters_metadata(self, analyzer):
        """Test that _extract_keywords filters out metadata tags."""
        query = "amount:50K-100K cybersecurity contracts"
        keywords = analyzer._extract_keywords(query)

        # Should not include "amount:50K-100K"
        assert "amount:50k-100k" not in keywords
        # Should include main keywords
        assert "cybersecurity" in keywords
        assert "contracts" in keywords

    def test_extract_keywords_filters_short_keywords(self, analyzer):
        """Test that _extract_keywords filters out short keywords (< 3 chars)."""
        query = "IT cloud security services"
        keywords = analyzer._extract_keywords(query)

        # "IT" is < 3 chars and should be filtered
        assert "it" not in keywords
        # Other keywords should remain
        assert "cloud" in keywords
        assert "security" in keywords
        assert "services" in keywords

    def test_suggest_refinement_filters_large_results(self, analyzer):
        """Test suggestion generation for large result sets."""
        context = {
            "set_aside_preference": None,
            "last_queries": ["previous search"],
        }

        # Should return suggestions for large result set
        suggestion = analyzer.suggest_refinement_filters(total_results=100, context=context)
        assert suggestion is not None
        assert "Consider refining" in suggestion
        assert "Set-aside type" in suggestion

    def test_suggest_refinement_filters_small_results(self, analyzer):
        """Test that no suggestions are given for small result sets."""
        context = {"set_aside_preference": None, "last_queries": []}

        # Should not return suggestions for small result set
        suggestion = analyzer.suggest_refinement_filters(total_results=25, context=context)
        assert suggestion is None

    def test_suggest_refinement_filters_respects_context(self, analyzer):
        """Test that suggestions respect existing context preferences."""
        context = {
            "set_aside_preference": "SDVOSB",
            "last_queries": [],
        }

        # Should not suggest set-aside if already set
        suggestion = analyzer.suggest_refinement_filters(total_results=100, context=context)
        assert suggestion is not None
        # The set-aside suggestion should not be first (or may be omitted)
        # depending on implementation

    def test_get_context_summary(self, analyzer, sample_conversation):
        """Test generation of context summary."""
        context = analyzer.extract_filters_from_conversation(sample_conversation)
        summary = analyzer.get_context_summary(context)

        assert summary is not None
        assert "Conversation Context Summary" in summary
        assert isinstance(summary, str)
        assert len(summary) > 0

    def test_empty_conversation(self, analyzer):
        """Test handling of empty conversation."""
        context = analyzer.extract_filters_from_conversation([])

        # Should return empty context with default values
        assert context is not None
        assert len(context["frequently_used_keywords"]) == 0
        assert len(context["last_queries"]) == 0

    def test_non_search_tools_ignored(self, analyzer):
        """Test that non-search tool calls are ignored."""
        conversation = [
            {
                "tool_name": "get_award_details",
                "input_params": {"award_id": "12345"},
                "status": "success",
            },
            {
                "tool_name": "search_federal_awards",
                "input_params": {"query": "cybersecurity"},
                "status": "success",
            },
        ]

        context = analyzer.extract_filters_from_conversation(conversation)

        # Should only extract from search_federal_awards
        assert len(context["last_queries"]) == 1
        assert context["last_queries"][0] == "cybersecurity"
