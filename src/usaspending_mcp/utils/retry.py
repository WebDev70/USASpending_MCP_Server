"""
Retry logic with exponential backoff for API calls.

WHAT IS A RETRY?
Imagine you're trying to call your friend on a busy phone line.
- First try: "Line is busy"
- Wait a bit, try again
- Second try: Still busy, wait longer
- Third try: Connected!

This file does the same thing with API calls!
When the USASpending API is temporarily busy or has a problem,
we don't give up immediately. We wait a bit and try again.

WHY RETRIES ARE IMPORTANT:
1. Network problems are temporary (usually)
2. Servers sometimes go down briefly for maintenance
3. Heavy traffic can cause temporary slowdowns
4. Our users don't want us to give up at the first failure

HOW IT WORKS:
1. Try to make an API request
2. If it fails with a temporary error, wait
3. Try again (first retry)
4. If it fails again, wait LONGER
5. Try again (second retry)
6. If it still fails, give up and report the error

EXPONENTIAL BACKOFF:
We wait longer each time because:
- First wait: 2 seconds
- Second wait: maybe 4 seconds
- Third wait: maybe 8 seconds
This gives the API time to recover from problems.

WHICH ERRORS DO WE RETRY ON?
- Network timeouts (server not responding)
- Connection errors (can't reach the server)
- HTTP 408 (Request Timeout)
- HTTP 429 (Too Many Requests - we hit rate limit)
- HTTP 500 (Server Error)
- HTTP 502 (Bad Gateway)
- HTTP 503 (Service Unavailable)
- HTTP 504 (Gateway Timeout)

WHICH ERRORS DO WE NOT RETRY ON?
- HTTP 404 (Not Found) - The page doesn't exist, retrying won't help
- HTTP 401 (Unauthorized) - Wrong credentials, retrying won't help
- HTTP 400 (Bad Request) - Invalid request, retrying won't help
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

# Logger for this module - records retry attempts
logger = logging.getLogger(__name__)

# ============ RETRYABLE EXCEPTIONS ============
# These are network/connection errors that are usually temporary
# If these happen, we should try again
RETRYABLE_EXCEPTIONS = (
    httpx.TimeoutException,      # Server didn't respond in time
    httpx.ConnectError,          # Can't connect to the server
    httpx.ReadError,             # Error reading response from server
)

# ============ RETRYABLE HTTP STATUS CODES ============
# These HTTP response codes indicate temporary problems
# 4xx codes are usually client errors (don't retry)
# 5xx codes are usually server errors (DO retry)
RETRYABLE_STATUS_CODES = {
    408,  # Request Timeout - client asked too slowly
    429,  # Too Many Requests - we're being rate limited
    500,  # Internal Server Error - something went wrong on the server
    502,  # Bad Gateway - server is acting as a proxy and had issues
    503,  # Service Unavailable - server is temporarily down
    504,  # Gateway Timeout - server is slow to respond
}

# TypeVar is a way to say "this function works with any type"
# We use it to make the code flexible while still being type-safe
T = TypeVar("T")


def is_retryable_http_error(exception: Exception) -> bool:
    """
    Check if an exception is a retryable HTTP error.

    WHAT DOES THIS DO?
    This is a helper function that checks if an error is temporary.
    Think of it like: "Should we try again?"

    HOW IT WORKS:
    1. Check if the exception is an HTTP status error
    2. If so, check if the status code is in our RETRYABLE_STATUS_CODES list
    3. If not an HTTP error, check if it's a network error we can retry on

    Args:
        exception: The error that happened

    Returns:
        True if we should retry, False if we should give up
    """
    # Is this an HTTP status code error (like 404, 500)?
    if isinstance(exception, httpx.HTTPStatusError):
        # Check if it's a code we should retry on (like 503)
        return exception.response.status_code in RETRYABLE_STATUS_CODES
    # Check if it's a network error we should retry on (like timeout)
    return isinstance(exception, RETRYABLE_EXCEPTIONS)


def should_retry_on_exception(exception: Exception) -> bool:
    """
    Determine if an exception should trigger a retry.

    This function is used by the @retry decorator to decide what to do
    when an exception happens during an API call.

    DECISION LOGIC:
    1. Is it a transient network error? (timeout, connection failed)
       → Yes: retry!
    2. Is it an HTTP error with a retryable code? (500, 503, 429)
       → Yes: retry!
    3. Anything else?
       → No: give up immediately

    Args:
        exception: The error that just happened

    Returns:
        True if we should retry, False if we should give up
    """
    # Check for transient network errors first
    # These are usually temporary (server might be restarting)
    if isinstance(exception, RETRYABLE_EXCEPTIONS):
        return True

    # Check for retryable HTTP status codes
    # These indicate temporary server problems
    if isinstance(exception, httpx.HTTPStatusError):
        return exception.response.status_code in RETRYABLE_STATUS_CODES

    # Any other error is permanent (like 404 Not Found)
    # No point retrying, so return False
    return False


# ============ THE MAIN RETRY DECORATOR ============
# This @retry decorator automatically retries the function if it fails
# Let's break down what each parameter does:
#
# stop=stop_after_attempt(3)
#   → Try at most 3 times (initial try + 2 retries)
#
# wait=wait_exponential(multiplier=1, min=2, max=10)
#   → Wait between retries using exponential backoff
#   → min=2: wait at least 2 seconds
#   → max=10: wait at most 10 seconds
#   → multiplier=1: multiply the wait time by 1x
#   → Example: 2 sec → 4 sec → 8 sec → 10 sec
#
# retry=retry_if_exception(should_retry_on_exception)
#   → Use our function above to decide if we should retry
#
# before_sleep=before_sleep_log(logger, logging.DEBUG)
#   → Log a DEBUG message before sleeping/waiting
#
# reraise=True
#   → If all retries fail, raise the original exception
#     (don't swallow the error)
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

    THIS IS THE MAIN FUNCTION THAT HANDLES RETRIES!

    HOW TO USE:
        response = await make_api_call_with_retry(
            client=my_http_client,
            method="GET",
            url="https://api.usaspending.gov/api/v2/awards/",
        )

    THE @retry DECORATOR ABOVE MEANS:
    - If this function fails with a retryable error, it will be called again
    - It will try up to 3 times
    - Between retries, it will wait 2-10 seconds
    - If all 3 attempts fail, the error is raised

    Args:
        client: An httpx AsyncClient for making HTTP requests
               (async means it won't block other code while waiting)
        method: The HTTP method to use (GET, POST, PUT, DELETE, etc.)
        url: The full URL to request (e.g., https://api.example.com/data)
        **kwargs: Any additional arguments for the HTTP request
                 (like headers, parameters, body, etc.)

    Returns:
        The HTTP response from the server

    Raises:
        httpx.HTTPError: If the request fails after all retries
    """
    try:
        # Log that we're about to make a request (helps with debugging)
        logger.debug(f"Making {method} request to {url}")

        # Make the actual HTTP request
        response = await client.request(method, url, **kwargs)

        # Check if the response has an error status code (4xx, 5xx)
        # This will raise HTTPStatusError if there's an error
        response.raise_for_status()

        # Success! Log it and return the response
        logger.debug(f"Request succeeded with status {response.status_code}")
        return response

    except httpx.HTTPStatusError as e:
        # We got an HTTP error (like 404, 500, etc.)

        # Log the error for debugging
        # [:100] means "only the first 100 characters of the response"
        # (to avoid logging huge error messages)
        logger.warning(
            f"HTTP error {e.response.status_code} for {method} {url}: {e.response.text[:100]}"
        )

        # The @retry decorator will check should_retry_on_exception()
        # to decide if we should try again.
        # We always re-raise here and let the decorator handle the retry logic
        if e.response.status_code in RETRYABLE_STATUS_CODES:
            raise  # Will be retried by the @retry decorator
        raise  # Re-raise non-retryable HTTP errors immediately


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
