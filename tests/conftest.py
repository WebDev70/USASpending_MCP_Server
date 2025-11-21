"""
Shared pytest fixtures and configuration for USASpending MCP Server tests.

Provides common mocks, fixtures, and utilities for all test suites.
"""

import asyncio
import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

# ============================================================================
# Fixtures: Event Loop
# ============================================================================


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ============================================================================
# Fixtures: Mock HTTP Responses
# ============================================================================


@pytest.fixture
def mock_award_response():
    """Mock response for a single award."""
    return {
        "results": [
            {
                "Award ID": "TEST001",
                "Recipient Name": "Test Company Inc",
                "Award Amount": 1000000.00,
                "Description": "Software development contract",
                "Award Date": "2025-01-15",
                "Contracting Agency": "Department of Defense",
                "Contract Type": "Fixed Price",
                "Status": "Active",
            }
        ]
    }


@pytest.fixture
def mock_search_response():
    """Mock response for award search with multiple results."""
    return {
        "results": [
            {
                "Award ID": f"TEST{i:03d}",
                "Recipient Name": f"Company {i}",
                "Award Amount": 1000000.00 * i,
                "Description": f"Contract for service {i}",
                "Award Date": "2025-01-15",
                "Contracting Agency": "Department of Defense",
            }
            for i in range(1, 6)
        ]
    }


@pytest.fixture
def mock_empty_response():
    """Mock empty response (no results)."""
    return {"results": []}


@pytest.fixture
def mock_error_response():
    """Mock error response from API."""
    return {"error": "Invalid query", "message": "The search query is malformed"}


# ============================================================================
# Fixtures: HTTP Client Mocks
# ============================================================================


@pytest.fixture
def mock_http_client():
    """Create a mock async HTTP client."""
    return AsyncMock(spec=httpx.AsyncClient)


@pytest.fixture
def mock_successful_response():
    """Mock successful HTTP response."""
    response = AsyncMock(spec=httpx.Response)
    response.status_code = 200
    response.json = AsyncMock(return_value={"results": []})
    return response


@pytest.fixture
def mock_timeout_response():
    """Mock HTTP timeout response."""
    response = AsyncMock(spec=httpx.Response)
    response.status_code = 408
    response.raise_for_status = MagicMock(side_effect=httpx.TimeoutException("Timeout"))
    return response


@pytest.fixture
def mock_rate_limit_response():
    """Mock HTTP 429 (rate limit) response."""
    response = AsyncMock(spec=httpx.Response)
    response.status_code = 429
    return response


@pytest.fixture
def mock_server_error_response():
    """Mock HTTP 500 (server error) response."""
    response = AsyncMock(spec=httpx.Response)
    response.status_code = 500
    return response


# ============================================================================
# Fixtures: Logging Mocks
# ============================================================================


@pytest.fixture
def mock_logger():
    """Create a mock logger."""
    logger = MagicMock()
    logger.info = MagicMock()
    logger.warning = MagicMock()
    logger.error = MagicMock()
    logger.debug = MagicMock()
    return logger


@pytest.fixture
def capture_logs(caplog):
    """Fixture to capture log messages."""
    return caplog


# ============================================================================
# Fixtures: Rate Limiter
# ============================================================================


@pytest.fixture
def rate_limiter():
    """Create a rate limiter for testing."""
    from usaspending_mcp.utils.rate_limit import RateLimiter

    return RateLimiter(requests_per_minute=10)


# ============================================================================
# Fixtures: Test Data
# ============================================================================


@pytest.fixture
def test_award_ids():
    """List of test award IDs."""
    return ["47QSWA26P02KE", "47QZ33ZAAA44", "12345678ABCD"]


@pytest.fixture
def test_search_queries():
    """List of test search queries."""
    return ["software", "cloud computing", "infrastructure", "consulting", "training"]


@pytest.fixture
def test_vendors():
    """List of test vendor names."""
    return [
        "Acme Corporation",
        "Tech Solutions Inc",
        "Global Systems Ltd",
        "Innovation Partners",
        "Future Technologies LLC",
    ]


# ============================================================================
# Fixtures: Mock FastMCP Server
# ============================================================================


@pytest.fixture
def mock_server():
    """Create a mock FastMCP server."""
    from fastmcp import FastMCP

    return FastMCP(name="test-server")


# ============================================================================
# Markers
# ============================================================================


def pytest_configure(config):
    """Register custom pytest markers."""
    config.addinivalue_line(
        "markers", "asyncio: mark test as async (deselect with '-m \"not asyncio\"')"
    )
    config.addinivalue_line("markers", "unit: mark test as a unit test")
    config.addinivalue_line("markers", "integration: mark test as an integration test")
    config.addinivalue_line("markers", "slow: mark test as slow running")
