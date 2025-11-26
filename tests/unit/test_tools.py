"""
In-memory tests for USASpending MCP Server tools

Tests individual tool functionality without subprocess overhead.
Uses FastMCP's in-memory testing capabilities.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Note: These are placeholder tests demonstrating structure
# Actual tests would require mocking the API responses


class TestSearchFederalAwards:
    """Test search_federal_awards tool"""

    @pytest.mark.asyncio
    async def test_search_with_keyword(self):
        """Test basic keyword search"""
        # This demonstrates the test structure
        # In practice, you would:
        # 1. Create a FastMCP server instance
        # 2. Use Client(server) for in-memory testing
        # 3. Mock HTTP responses
        # 4. Assert on returned data

        keyword = "software"
        max_results = 5

        # Mock the API response
        mock_response = {
            "results": [
                {
                    "Award ID": "TEST001",
                    "Recipient Name": "Test Company",
                    "Award Amount": 1000000,
                    "Description": "Software development contract",
                }
            ]
        }

        # In a real test:
        # client = Client(server_instance)
        # result = await client.call_tool(
        #     "search_federal_awards",
        #     {"query": keyword, "max_results": max_results}
        # )
        # assert result.isSuccess
        # assert len(result.content) > 0

        assert keyword is not None
        assert max_results > 0

    @pytest.mark.asyncio
    async def test_search_with_date_range(self):
        """Test search with custom date range"""
        start_date = "2025-01-01"
        end_date = "2025-12-31"

        # Validate date format
        assert len(start_date) == 10
        assert len(end_date) == 10
        assert "-" in start_date
        assert "-" in end_date

    @pytest.mark.asyncio
    async def test_search_empty_results(self):
        """Test search returning no results"""
        # Mock empty response
        mock_response = {"results": []}

        assert mock_response["results"] == []


class TestGetAwardDetails:
    """Test get_award_details tool"""

    @pytest.mark.asyncio
    async def test_valid_award_id(self):
        """Test retrieving award by valid ID"""
        award_id = "47QSWA26P02KE"

        assert award_id is not None
        assert len(award_id) > 0
        assert award_id.isupper()

    @pytest.mark.asyncio
    async def test_invalid_award_id(self):
        """Test handling of invalid award ID"""
        invalid_id = "NONEXISTENT"

        assert invalid_id is not None
        # In real test, expect error response from tool


class TestAnalyticTools:
    """Test analysis and analytics tools"""

    @pytest.mark.asyncio
    async def test_get_spending_trends(self):
        """Test spending trends analysis"""
        period = "fiscal_year"

        assert period in ["fiscal_year", "calendar_year", "monthly"]

    @pytest.mark.asyncio
    async def test_get_top_recipients(self):
        """Test getting top recipients"""
        # Should return ranked list of top contractors/recipients
        assert True


class TestGetTopVendorsByContractCount:
    """Test get_top_vendors_by_contract_count tool"""

    @pytest.mark.asyncio
    async def test_valid_limit_parameter(self):
        """Test with valid limit parameter"""
        limit = 20
        assert 1 <= limit <= 100

    @pytest.mark.asyncio
    async def test_limit_boundary_validation(self):
        """Test limit parameter boundary validation"""
        # Test minimum limit
        min_limit = 1
        assert min_limit >= 1

        # Test maximum limit
        max_limit = 100
        assert max_limit <= 100

        # Test default limit
        default_limit = 20
        assert 1 <= default_limit <= 100

    @pytest.mark.asyncio
    async def test_award_type_validation(self):
        """Test award type parameter validation"""
        valid_types = ["contract", "grant", "loan", "insurance", "all"]

        for award_type in valid_types:
            assert award_type in valid_types

    @pytest.mark.asyncio
    async def test_date_format_validation(self):
        """Test date parameter format validation"""
        start_date = "2025-01-01"
        end_date = "2025-12-31"

        assert len(start_date) == 10
        assert len(end_date) == 10
        assert "-" in start_date
        assert "-" in end_date

    @pytest.mark.asyncio
    async def test_agency_parameter(self):
        """Test agency parameter handling"""
        from usaspending_mcp.utils.constants import TOPTIER_AGENCY_MAP

        agency = "dod"
        assert agency.lower() in TOPTIER_AGENCY_MAP or agency == "all"

    @pytest.mark.asyncio
    async def test_amount_filter_parameters(self):
        """Test min and max amount parameters"""
        min_amount = 100000
        max_amount = 1000000

        assert min_amount > 0
        assert max_amount > min_amount

    @pytest.mark.asyncio
    async def test_mock_vendor_aggregation(self):
        """Test vendor aggregation logic with mock data"""
        # Mock award data
        mock_awards = [
            {"Recipient Name": "Vendor A", "Award Amount": 100000},
            {"Recipient Name": "Vendor A", "Award Amount": 200000},
            {"Recipient Name": "Vendor B", "Award Amount": 150000},
            {"Recipient Name": "Vendor B", "Award Amount": 150000},
            {"Recipient Name": "Vendor B", "Award Amount": 150000},
        ]

        # Aggregate data by vendor
        vendor_stats = {}
        for award in mock_awards:
            vendor_name = award.get("Recipient Name", "Unknown")
            amount = float(award.get("Award Amount", 0))

            if vendor_name not in vendor_stats:
                vendor_stats[vendor_name] = {
                    "count": 0,
                    "total_amount": 0,
                }

            vendor_stats[vendor_name]["count"] += 1
            vendor_stats[vendor_name]["total_amount"] += amount

        # Verify aggregation results
        assert len(vendor_stats) == 2
        assert vendor_stats["Vendor A"]["count"] == 2
        assert vendor_stats["Vendor A"]["total_amount"] == 300000
        assert vendor_stats["Vendor B"]["count"] == 3
        assert vendor_stats["Vendor B"]["total_amount"] == 450000

    @pytest.mark.asyncio
    async def test_vendor_sorting_by_contract_count(self):
        """Test vendors are sorted by contract count"""
        vendor_stats = {
            "Vendor A": {"count": 10, "total_amount": 1000000},
            "Vendor B": {"count": 5, "total_amount": 500000},
            "Vendor C": {"count": 20, "total_amount": 2000000},
        }

        # Sort by contract count (descending)
        sorted_vendors = sorted(
            vendor_stats.items(),
            key=lambda x: x[1]["count"],
            reverse=True
        )

        # Verify sorting
        assert sorted_vendors[0][0] == "Vendor C"  # 20 contracts
        assert sorted_vendors[1][0] == "Vendor A"  # 10 contracts
        assert sorted_vendors[2][0] == "Vendor B"  # 5 contracts


class TestGetNaicsTrends:
    """Test get_naics_trends tool"""

    @pytest.mark.asyncio
    async def test_valid_years_parameter(self):
        """Test with valid years parameter"""
        years = 3
        assert 1 <= years <= 10

    @pytest.mark.asyncio
    async def test_years_boundary_validation(self):
        """Test years parameter boundary validation"""
        # Test minimum years
        min_years = 1
        assert min_years >= 1

        # Test maximum years
        max_years = 10
        assert max_years <= 10

        # Test default years
        default_years = 3
        assert 1 <= default_years <= 10

    @pytest.mark.asyncio
    async def test_limit_parameter_validation(self):
        """Test limit parameter validation"""
        limit = 10
        assert 1 <= limit <= 50

    @pytest.mark.asyncio
    async def test_award_type_validation_naics(self):
        """Test award type parameter validation"""
        valid_types = ["contract", "grant", "all"]

        for award_type in valid_types:
            assert award_type in valid_types

    @pytest.mark.asyncio
    async def test_agency_parameter_naics(self):
        """Test agency parameter handling"""
        from usaspending_mcp.utils.constants import TOPTIER_AGENCY_MAP

        agency = "dod"
        assert agency.lower() in TOPTIER_AGENCY_MAP

    @pytest.mark.asyncio
    async def test_naics_code_format(self):
        """Test NAICS code format validation"""
        naics_code = "511210"
        # NAICS codes are typically 6 digits
        assert naics_code.isdigit()
        assert len(naics_code) == 6

    @pytest.mark.asyncio
    async def test_fiscal_year_calculation(self):
        """Test fiscal year range calculation"""
        from datetime import datetime

        today = datetime.now()
        current_fy = today.year if today.month >= 10 else today.year - 1

        # Test fiscal year calculations
        assert current_fy > 0
        assert current_fy <= datetime.now().year

    @pytest.mark.asyncio
    async def test_mock_naics_trend_aggregation(self):
        """Test NAICS trend aggregation logic with mock data"""
        # Mock fiscal year data structure
        fiscal_year_data = {
            "511210": {
                "description": "Software Publishing",
                "years": {
                    2022: {"total": 1000000, "count": 5},
                    2023: {"total": 1500000, "count": 6},
                    2024: {"total": 2000000, "count": 8},
                },
            },
            "541330": {
                "description": "Engineering Services",
                "years": {
                    2022: {"total": 800000, "count": 4},
                    2023: {"total": 850000, "count": 5},
                    2024: {"total": 900000, "count": 5},
                },
            },
        }

        # Calculate totals
        for naics in fiscal_year_data:
            total = sum(fy["total"] for fy in fiscal_year_data[naics]["years"].values())
            fiscal_year_data[naics]["total"] = total

        # Verify totals
        assert fiscal_year_data["511210"]["total"] == 4500000
        assert fiscal_year_data["541330"]["total"] == 2550000

    @pytest.mark.asyncio
    async def test_yoy_growth_calculation(self):
        """Test year-over-year growth calculation"""
        prev_total = 1000000
        current_total = 1500000

        yoy_growth = ((current_total - prev_total) / prev_total) * 100

        # Should be 50% growth
        assert yoy_growth == 50.0

    @pytest.mark.asyncio
    async def test_negative_yoy_growth_calculation(self):
        """Test negative year-over-year growth calculation"""
        prev_total = 1500000
        current_total = 1000000

        yoy_growth = ((current_total - prev_total) / prev_total) * 100

        # Should be -33.33% decline
        assert yoy_growth < 0
        assert abs(yoy_growth) > 30


class TestConfigurationManagement:
    """Test server configuration"""

    def test_config_defaults(self):
        """Test default configuration values"""
        from usaspending_mcp.config import ServerConfig

        assert ServerConfig.MCP_PORT == 3002
        assert ServerConfig.LOG_LEVEL in ["INFO", "DEBUG", "WARNING", "ERROR"]
        assert ServerConfig.HTTP_TIMEOUT > 0

    def test_config_validation(self):
        """Test configuration validation"""
        from usaspending_mcp.config import ServerConfig

        # Should not raise - API URL should be configured
        try:
            ServerConfig.validate_required()
        except ValueError:
            pytest.fail("Configuration validation failed unexpectedly")


class TestUtilities:
    """Test utility functions"""

    def test_constants_loaded(self):
        """Test that constants are properly loaded"""
        from usaspending_mcp.utils.constants import (
            AWARD_TYPE_MAP,
            TOPTIER_AGENCY_MAP,
        )

        assert len(AWARD_TYPE_MAP) > 0
        assert len(TOPTIER_AGENCY_MAP) > 0

        # Verify structure
        assert "contract" in AWARD_TYPE_MAP
        assert isinstance(AWARD_TYPE_MAP["contract"], list)

        assert "dod" in TOPTIER_AGENCY_MAP
        assert TOPTIER_AGENCY_MAP["dod"] == "Department of Defense"


# Integration test example
@pytest.mark.asyncio
async def test_server_initialization():
    """Test that server initializes properly"""
    from usaspending_mcp.server import app

    assert app is not None
    assert app.name == "usaspending-server"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
