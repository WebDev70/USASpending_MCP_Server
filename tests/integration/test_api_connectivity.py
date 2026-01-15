"""
Integration tests for API connectivity and basic functionality.

These tests are designed to run against live, external APIs and are
marked with the 'integration' marker to separate them from fast, local unit tests.
"""

import httpx
import pytest

# The base URL for the USASpending API, can be overridden by an environment variable for testing
API_BASE_URL = "https://api.usaspending.gov/api/v2"


@pytest.mark.integration
def test_usaspending_api_naics_endpoint_connectivity():
    """
    Tests basic connectivity to the USASpending API and the health of a stable, public endpoint.

    This test hits the live `/api/v2/references/naics/` endpoint to verify:
    1.  A successful (200 OK) response is returned.
    2.  The response body is valid JSON.
    3.  The response contains the expected 'results' key.

    This acts as a simple, read-only health check for the API.
    """
    endpoint_url = f"{API_BASE_URL}/references/naics/"

    try:
        with httpx.Client() as client:
            response = client.get(endpoint_url)

        # 1. Check for a successful HTTP status code
        response.raise_for_status()  # This will raise an exception for 4xx or 5xx status codes

        # 2. Check that we received a valid JSON response
        data = response.json()
        assert isinstance(data, dict), "Response is not a valid JSON object."

        # 3. Check for the presence of the 'results' key, which indicates a valid response structure
        assert "results" in data, "The 'results' key is missing from the API response."
        assert isinstance(
            data["results"], list
        ), "The 'results' key should contain a list."

    except httpx.RequestError as e:
        pytest.fail(f"An error occurred while requesting {e.request.url!r}: {e}")
    except Exception as e:
        pytest.fail(f"The test failed for an unexpected reason: {e}")
