"""
Retry logic with exponential backoff for API calls.

Handles transient failures gracefully with automatic retries.
"""

import logging
from typing import Any, Callable, TypeVar

import httpx
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)

# Exceptions that trigger retries (transient errors)
RETRYABLE_EXCEPTIONS = (
    httpx.TimeoutException,
    httpx.ConnectError,
    httpx.ReadError,
)

# HTTP status codes that should trigger retries
RETRYABLE_STATUS_CODES = {408, 429, 500, 502, 503, 504}

T = TypeVar("T")


def is_retryable_http_error(exception: Exception) -> bool:
    """Check if exception is a retryable HTTP error."""
    if isinstance(exception, httpx.HTTPStatusError):
        return exception.response.status_code in RETRYABLE_STATUS_CODES
    return isinstance(exception, RETRYABLE_EXCEPTIONS)


def should_retry_on_exception(exception: Exception) -> bool:
    """Determine if an exception should trigger a retry."""
    # Retry on transient network errors
    if isinstance(exception, RETRYABLE_EXCEPTIONS):
        return True
    # Retry on retryable HTTP status codes
    if isinstance(exception, httpx.HTTPStatusError):
        return exception.response.status_code in RETRYABLE_STATUS_CODES
    return False


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception(should_retry_on_exception),
    before_sleep=before_sleep_log(logger, logging.DEBUG),
    reraise=True,
)
async def make_api_call_with_retry(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    **kwargs: Any,
) -> httpx.Response:
    """
    Make an HTTP request with automatic retry on transient failures.

    Args:
        client: httpx AsyncClient instance
        method: HTTP method (GET, POST, etc.)
        url: Request URL
        **kwargs: Additional arguments passed to client.request()

    Returns:
        HTTP response object

    Raises:
        httpx.HTTPError: If all retries fail
    """
    try:
        logger.debug(f"Making {method} request to {url}")
        response = await client.request(method, url, **kwargs)
        response.raise_for_status()
        logger.debug(f"Request succeeded with status {response.status_code}")
        return response
    except httpx.HTTPStatusError as e:
        # Log HTTP errors
        logger.warning(
            f"HTTP error {e.response.status_code} for {method} {url}: {e.response.text[:100]}"
        )
        # Check if it's retryable
        if e.response.status_code in RETRYABLE_STATUS_CODES:
            raise  # Will be retried
        raise  # Re-raise non-retryable HTTP errors


async def fetch_json_with_retry(
    client: httpx.AsyncClient,
    url: str,
    params: dict | None = None,
    timeout: float = 30.0,
) -> dict:
    """
    Fetch JSON data with automatic retries.

    Args:
        client: httpx AsyncClient instance
        url: Request URL
        params: Query parameters
        timeout: Request timeout in seconds

    Returns:
        Parsed JSON response

    Raises:
        httpx.HTTPError: If request fails after all retries
    """
    response = await make_api_call_with_retry(
        client,
        "GET",
        url,
        params=params,
        timeout=timeout,
        headers={"User-Agent": "USASpending-MCP/2.0"},
    )
    return response.json()
