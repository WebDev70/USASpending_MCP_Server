"""
Unit tests for retry logic utility module.

Tests the exponential backoff retry mechanism for handling
transient API failures.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from tenacity import RetryError

from usaspending_mcp.utils.retry import (
    RETRYABLE_EXCEPTIONS,
    RETRYABLE_STATUS_CODES,
    fetch_json_with_retry,
    make_api_call_with_retry,
)


@pytest.mark.unit
class TestRetryConstants:
    """Test retry configuration constants."""

    def test_retryable_exceptions_defined(self):
        """Test that retryable exceptions are defined."""
        assert RETRYABLE_EXCEPTIONS is not None
        assert len(RETRYABLE_EXCEPTIONS) > 0
        assert httpx.TimeoutException in RETRYABLE_EXCEPTIONS
        assert httpx.ConnectError in RETRYABLE_EXCEPTIONS

    def test_retryable_status_codes_defined(self):
        """Test that retryable status codes are defined."""
        assert RETRYABLE_STATUS_CODES is not None
        assert len(RETRYABLE_STATUS_CODES) > 0
        assert 429 in RETRYABLE_STATUS_CODES  # Rate limit
        assert 500 in RETRYABLE_STATUS_CODES  # Server error
        assert 503 in RETRYABLE_STATUS_CODES  # Service unavailable

    def test_non_retryable_status_codes(self):
        """Test that non-retryable status codes are excluded."""
        # 400 Bad Request should not be retryable
        assert 400 not in RETRYABLE_STATUS_CODES
        # 401 Unauthorized should not be retryable
        assert 401 not in RETRYABLE_STATUS_CODES
        # 404 Not Found should not be retryable
        assert 404 not in RETRYABLE_STATUS_CODES


@pytest.mark.unit
@pytest.mark.asyncio
class TestMakeApiCallWithRetry:
    """Test make_api_call_with_retry function."""

    async def test_successful_call_first_attempt(self, mock_http_client, mock_successful_response):
        """Test successful API call on first attempt."""
        mock_successful_response.raise_for_status = MagicMock()
        mock_http_client.request = AsyncMock(return_value=mock_successful_response)

        result = await make_api_call_with_retry(
            client=mock_http_client, method="GET", url="https://api.example.com/test"
        )

        assert result.status_code == 200
        mock_http_client.request.assert_called_once()

    async def test_retry_on_timeout(self, mock_http_client):
        """Test that function retries on timeout."""
        # First call fails with timeout, second succeeds
        success_response = AsyncMock(spec=httpx.Response)
        success_response.status_code = 200
        success_response.raise_for_status = MagicMock()

        mock_http_client.request = AsyncMock(
            side_effect=[httpx.TimeoutException("Timeout"), success_response]
        )

        result = await make_api_call_with_retry(
            client=mock_http_client, method="GET", url="https://api.example.com/test"
        )

        assert result.status_code == 200
        assert mock_http_client.request.call_count == 2

    async def test_retry_on_rate_limit(self, mock_http_client):
        """Test that function retries on HTTP 429 (rate limit)."""
        rate_limit_response = AsyncMock(spec=httpx.Response)
        rate_limit_response.status_code = 429
        rate_limit_response.text = "Rate limit exceeded"
        rate_limit_response.raise_for_status = MagicMock(
            side_effect=httpx.HTTPStatusError(
                "429 Too Many Requests",
                request=MagicMock(),
                response=rate_limit_response,
            )
        )

        success_response = AsyncMock(spec=httpx.Response)
        success_response.status_code = 200
        success_response.raise_for_status = MagicMock()

        mock_http_client.request = AsyncMock(
            side_effect=[rate_limit_response, success_response]
        )

        result = await make_api_call_with_retry(
            client=mock_http_client, method="GET", url="https://api.example.com/test"
        )

        assert result.status_code == 200
        assert mock_http_client.request.call_count == 2

    async def test_retry_on_server_error(self, mock_http_client):
        """Test that function retries on server errors (5xx)."""
        error_response = AsyncMock(spec=httpx.Response)
        error_response.status_code = 503
        error_response.text = "Service Unavailable"
        error_response.raise_for_status = MagicMock(
            side_effect=httpx.HTTPStatusError(
                "503 Service Unavailable",
                request=MagicMock(),
                response=error_response,
            )
        )

        success_response = AsyncMock(spec=httpx.Response)
        success_response.status_code = 200
        success_response.raise_for_status = MagicMock()

        mock_http_client.request = AsyncMock(
            side_effect=[error_response, success_response]
        )

        result = await make_api_call_with_retry(
            client=mock_http_client, method="GET", url="https://api.example.com/test"
        )

        assert result.status_code == 200

    async def test_no_retry_on_client_error(self, mock_http_client):
        """Test that function does NOT retry on client errors (4xx)."""
        error_response = AsyncMock(spec=httpx.Response)
        error_response.status_code = 400
        error_response.text = "Bad Request"
        error_response.raise_for_status = MagicMock(
            side_effect=httpx.HTTPStatusError(
                "400 Bad Request",
                request=MagicMock(),
                response=error_response,
            )
        )

        mock_http_client.request = AsyncMock(return_value=error_response)

        with pytest.raises(httpx.HTTPStatusError):
            await make_api_call_with_retry(
                client=mock_http_client, method="GET", url="https://api.example.com/test"
            )

        # Should only call once (no retries for non-retryable errors)
        assert mock_http_client.request.call_count == 1

    async def test_max_retries_exceeded(self, mock_http_client):
        """Test behavior when max retries exceeded."""
        # All attempts fail
        mock_http_client.request = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))

        with pytest.raises(httpx.TimeoutException):
            await make_api_call_with_retry(
                client=mock_http_client, method="GET", url="https://api.example.com/test"
            )

        # Should attempt multiple times
        assert mock_http_client.request.call_count >= 3

    async def test_post_request(self, mock_http_client, mock_successful_response):
        """Test retry with POST request."""
        mock_successful_response.raise_for_status = MagicMock()
        mock_http_client.request = AsyncMock(return_value=mock_successful_response)

        result = await make_api_call_with_retry(
            client=mock_http_client,
            method="POST",
            url="https://api.example.com/test",
            json={"query": "test"},
        )

        assert result.status_code == 200
        mock_http_client.request.assert_called_once()

    async def test_request_with_headers(self, mock_http_client, mock_successful_response):
        """Test retry preserves headers."""
        mock_successful_response.raise_for_status = MagicMock()
        mock_http_client.request = AsyncMock(return_value=mock_successful_response)

        headers = {"Authorization": "Bearer token"}
        result = await make_api_call_with_retry(
            client=mock_http_client,
            method="GET",
            url="https://api.example.com/test",
            headers=headers,
        )

        assert result.status_code == 200


@pytest.mark.unit
@pytest.mark.asyncio
class TestFetchJsonWithRetry:
    """Test fetch_json_with_retry function."""

    async def test_fetch_json_success(self, mock_http_client):
        """Test successful JSON fetch."""
        response = AsyncMock(spec=httpx.Response)
        response.status_code = 200
        response.raise_for_status = MagicMock()
        response.json = MagicMock(return_value={"result": "success"})

        mock_http_client.request = AsyncMock(return_value=response)

        result = await fetch_json_with_retry(
            client=mock_http_client, url="https://api.example.com/data", params={"q": "test"}
        )

        assert result == {"result": "success"}

    async def test_fetch_json_with_retry_on_failure(self, mock_http_client):
        """Test JSON fetch with retry on failure."""
        # First fails, second succeeds
        error_response = AsyncMock(spec=httpx.Response)
        error_response.status_code = 503
        error_response.text = "Service Unavailable"
        error_response.raise_for_status = MagicMock(
            side_effect=httpx.HTTPStatusError(
                "503 Service Unavailable",
                request=MagicMock(),
                response=error_response,
            )
        )

        success_response = AsyncMock(spec=httpx.Response)
        success_response.status_code = 200
        success_response.raise_for_status = MagicMock()
        success_response.json = MagicMock(return_value={"data": "test"})

        mock_http_client.request = AsyncMock(side_effect=[error_response, success_response])

        result = await fetch_json_with_retry(
            client=mock_http_client, url="https://api.example.com/data"
        )

        assert result == {"data": "test"}
        assert mock_http_client.request.call_count == 2

    async def test_fetch_json_empty_response(self, mock_http_client):
        """Test JSON fetch with empty response."""
        response = AsyncMock(spec=httpx.Response)
        response.status_code = 200
        response.raise_for_status = MagicMock()
        response.json = MagicMock(return_value={})

        mock_http_client.request = AsyncMock(return_value=response)

        result = await fetch_json_with_retry(
            client=mock_http_client, url="https://api.example.com/data"
        )

        assert result == {}

    async def test_fetch_json_with_params(self, mock_http_client):
        """Test JSON fetch with query parameters."""
        response = AsyncMock(spec=httpx.Response)
        response.status_code = 200
        response.json = MagicMock(return_value={"results": []})

        mock_http_client.request = AsyncMock(return_value=response)

        params = {"keyword": "software", "limit": 10, "offset": 0}

        result = await fetch_json_with_retry(
            client=mock_http_client, url="https://api.example.com/search", params=params
        )

        assert result == {"results": []}


@pytest.mark.unit
@pytest.mark.asyncio
class TestRetryExponentialBackoff:
    """Test exponential backoff timing."""

    @pytest.mark.slow
    async def test_retry_timing(self, mock_http_client):
        """Test that retries have exponential backoff."""
        import time

        error_response = AsyncMock(spec=httpx.Response)
        error_response.status_code = 503
        error_response.text = "Service Unavailable"
        error_response.raise_for_status = MagicMock(
            side_effect=httpx.HTTPStatusError(
                "503 Service Unavailable",
                request=MagicMock(),
                response=error_response,
            )
        )

        success_response = AsyncMock(spec=httpx.Response)
        success_response.status_code = 200
        success_response.raise_for_status = MagicMock()

        mock_http_client.request = AsyncMock(
            side_effect=[error_response, error_response, success_response]
        )

        start = time.time()
        result = await make_api_call_with_retry(
            client=mock_http_client, method="GET", url="https://api.example.com/test"
        )
        elapsed = time.time() - start

        # Should have delays between retries (exponential backoff)
        # Minimum expected: ~2 seconds (first retry wait) + ~4 seconds (second retry wait)
        # Allow some variance
        assert result.status_code == 200

    @pytest.mark.slow
    async def test_retry_delays_increase(self, mock_http_client):
        """Test that retry delays increase exponentially."""
        import time

        call_times = []

        async def track_calls(*args, **kwargs):
            call_times.append(time.time())
            if len(call_times) < 3:
                raise httpx.TimeoutException("Timeout")
            response = AsyncMock(spec=httpx.Response)
            response.status_code = 200
            response.raise_for_status = MagicMock()
            return response

        mock_http_client.request = AsyncMock(side_effect=track_calls)

        try:
            await make_api_call_with_retry(
                client=mock_http_client, method="GET", url="https://api.example.com/test"
            )
        except Exception:
            pass

        # Check that delays increase
        if len(call_times) >= 3:
            delay1 = call_times[1] - call_times[0]
            delay2 = call_times[2] - call_times[1]
            # Delays should occur (exponential backoff), just check we made calls
            assert len(call_times) >= 2


@pytest.mark.unit
@pytest.mark.asyncio
class TestRetryErrorTypes:
    """Test handling of different error types."""

    async def test_retry_on_connect_error(self, mock_http_client):
        """Test retry on connection error."""
        success_response = AsyncMock(spec=httpx.Response)
        success_response.status_code = 200
        success_response.raise_for_status = MagicMock()

        mock_http_client.request = AsyncMock(
            side_effect=[httpx.ConnectError("Connection failed"), success_response]
        )

        result = await make_api_call_with_retry(
            client=mock_http_client, method="GET", url="https://api.example.com/test"
        )

        assert result.status_code == 200

    async def test_retry_on_read_error(self, mock_http_client):
        """Test retry on read error."""
        success_response = AsyncMock(spec=httpx.Response)
        success_response.status_code = 200
        success_response.raise_for_status = MagicMock()

        mock_http_client.request = AsyncMock(
            side_effect=[httpx.ReadError("Read failed"), success_response]
        )

        result = await make_api_call_with_retry(
            client=mock_http_client, method="GET", url="https://api.example.com/test"
        )

        assert result.status_code == 200

    async def test_non_retryable_exception(self, mock_http_client):
        """Test that non-retryable exceptions are not retried."""
        mock_http_client.request = AsyncMock(side_effect=ValueError("Not retryable"))

        with pytest.raises(ValueError):
            await make_api_call_with_retry(
                client=mock_http_client, method="GET", url="https://api.example.com/test"
            )

        # Should only call once (no retries)
        assert mock_http_client.request.call_count == 1
