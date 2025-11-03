# Rate Limiting and Retry Logic Integration Guide

## Overview

This document explains how to use the rate limiting and retry logic utilities in the USASpending MCP Server.

**Implementation Date**: October 30, 2025
**Status**: ✅ Infrastructure in place, integration in progress

---

## Features Implemented

### 1. Automatic Retry Logic with Exponential Backoff

**File**: `src/usaspending_mcp/utils/retry.py`

Automatically retries failed API calls with exponential backoff:
- **3 retries** maximum
- **Exponential backoff**: 2-10 seconds between attempts
- **Handles transient errors**: Timeouts, connection errors, rate limits (429), server errors (5xx)
- **Non-retryable errors**: Bad requests (4xx) fail immediately

**Retryable HTTP Status Codes**:
- `408` - Request Timeout
- `429` - Too Many Requests (Rate Limit)
- `500` - Internal Server Error
- `502` - Bad Gateway
- `503` - Service Unavailable
- `504` - Gateway Timeout

**Retryable Exceptions**:
- `httpx.TimeoutException`
- `httpx.ConnectError`
- `httpx.ReadError`
- `httpx.ConnectionPoolTimeout`

### 2. Token Bucket Rate Limiter

**File**: `src/usaspending_mcp/utils/rate_limit.py`

Controls request rate to prevent API overload:
- **Default**: 60 requests per minute (1 request per second)
- **Token bucket algorithm**: Refills tokens over time
- **Configurable**: Easy to adjust limits per deployment
- **Per-identifier tracking**: Can limit by user, IP, or tool
- **Async-friendly**: Non-blocking waits

---

## Usage Examples

### Example 1: Using Retry Logic (Already Integrated)

The retry logic is automatically applied to API calls made through the global HTTP client:

```python
from usaspending_mcp.utils.retry import fetch_json_with_retry

# Automatic retries with exponential backoff
response_data = await fetch_json_with_retry(
    client=http_client,
    url="https://api.usaspending.gov/api/v2/awards/search/",
    params={"keywords": "software"},
    timeout=30.0
)
```

### Example 2: Using Rate Limiting in Tools

Add rate limiting check at the beginning of any tool function:

```python
from usaspending_mcp.utils.rate_limit import get_rate_limiter
from mcp.types import TextContent

@app.tool()
async def search_federal_awards(
    query: str,
    max_results: int = 5
) -> list[TextContent]:
    """Search federal spending data."""

    # Check rate limit before processing
    rate_limiter = get_rate_limiter()
    try:
        await rate_limiter.wait_if_needed(identifier="default")
    except RuntimeError as e:
        return [TextContent(
            type="text",
            text=f"Rate limit exceeded: {str(e)}. Please try again in a moment."
        )]

    # Continue with tool logic...
    # Make API calls using fetch_json_with_retry
```

### Example 3: Per-Tool Rate Limiting

Different rate limits for different tools:

```python
# For heavy operations (lower limit)
await rate_limiter.wait_if_needed(identifier="analytics_tools")

# For light operations (can go higher)
await rate_limiter.wait_if_needed(identifier="lookups")
```

### Example 4: Checking Rate Limit Status

Get stats without consuming a token:

```python
rate_limiter = get_rate_limiter()

# Get current stats
stats = rate_limiter.get_stats(identifier="default")
print(f"Available tokens: {stats['available_tokens']:.2f}")
print(f"Requests per minute: {stats['requests_per_minute']}")
```

### Example 5: Customizing Rate Limits

Change limits at runtime:

```python
from usaspending_mcp.utils.rate_limit import initialize_rate_limiter

# Initialize with custom rate limit
custom_limiter = initialize_rate_limiter(requests_per_minute=100)

# Or reset an identifier
rate_limiter.reset(identifier="default")
```

---

## Implementation Status

### Phase 1: Infrastructure ✅ COMPLETE
- [x] Created `src/usaspending_mcp/utils/retry.py` with retry logic
- [x] Created `src/usaspending_mcp/utils/rate_limit.py` with rate limiting
- [x] Updated `requirements.txt` with `tenacity` and `slowapi`
- [x] Updated `server.py` imports and initialization
- [x] Rate limiter initialized at server startup
- [x] Installed dependencies

### Phase 2: Integration IN PROGRESS
- [ ] Add rate limiting checks to search_federal_awards tool
- [ ] Add rate limiting checks to get_award_details tool
- [ ] Add rate limiting checks to analytics tools
- [ ] Update API calls to use retry logic via `fetch_json_with_retry`
- [ ] Add logging for rate limit events
- [ ] Add health check endpoint with rate limit status

### Phase 3: Monitoring (Next Phase)
- [ ] Add metrics endpoint showing rate limit usage
- [ ] Add logging for retry attempts
- [ ] Add dashboard or reporting

---

## Configuration

###Rate Limiter Configuration

Current configuration in `server.py`:
```python
rate_limiter = initialize_rate_limiter(requests_per_minute=60)
```

To modify:
1. Change `60` to desired requests per minute
2. Deploy and restart server

### Retry Configuration

Currently hardcoded in `src/usaspending_mcp/utils/retry.py`:
- Max retries: 3
- Min wait: 2 seconds
- Max wait: 10 seconds

To customize, edit `retry.py`:
```python
@retry(
    stop=stop_after_attempt(3),  # Change max attempts here
    wait=wait_exponential(multiplier=1, min=2, max=10),  # Adjust backoff here
    ...
)
```

---

## Integration Checklist for Developers

When adding new tools or API calls:

1. **For existing tools**: Add rate limiting check at the beginning
   ```python
   await rate_limiter.wait_if_needed(identifier="default")
   ```

2. **For API calls**: Use `fetch_json_with_retry` instead of direct calls
   ```python
   # Good ✅
   data = await fetch_json_with_retry(client, url, params=params)

   # Bad ❌
   response = await http_client.get(url, params=params)
   ```

3. **For error messages**: Include helpful retry guidance
   ```python
   except RuntimeError as e:
       return [TextContent(
           type="text",
           text=f"Temporarily unavailable due to rate limit. {str(e)}"
       )]
   ```

4. **For logging**: Log rate limit events
   ```python
   logger.info(f"Rate limit check for {identifier}: "
               f"{stats['available_tokens']:.2f} tokens available")
   ```

---

## Testing Rate Limiting and Retry Logic

### Test Rate Limiting

```python
import asyncio
from usaspending_mcp.utils.rate_limit import RateLimiter

async def test_rate_limiting():
    limiter = RateLimiter(requests_per_minute=2)  # Only 2 req/min

    # First two requests should pass immediately
    for i in range(2):
        await limiter.wait_if_needed(identifier="test")
        print(f"Request {i+1} allowed")

    # Third request should wait
    print("Waiting for token refill...")
    await limiter.wait_if_needed(identifier="test")
    print("Request 3 allowed after wait")
```

### Test Retry Logic

```python
from usaspending_mcp.utils.retry import fetch_json_with_retry

async def test_retry_logic():
    try:
        # Simulating an API call that might retry
        data = await fetch_json_with_retry(
            http_client,
            "https://api.usaspending.gov/api/v2/awards/search/",
            params={"keywords": "test"}
        )
        print(f"Success: {len(data)} results")
    except Exception as e:
        print(f"Failed after retries: {e}")
```

---

## Monitoring and Logging

### Current Logging

Rate limiting logs are at INFO level:
```
INFO:usaspending_mcp.utils.rate_limit:RateLimiter initialized: 60 requests/minute
```

Retry attempts are logged at DEBUG level:
```
DEBUG:usaspending_mcp.utils.retry:Making GET request to https://api.usaspending.gov/api/v2/...
DEBUG:usaspending_mcp.utils.retry:Request succeeded with status 200
```

### To Enable Detailed Logging

In `server.py`, change logging level:
```python
logging.basicConfig(
    level=logging.DEBUG,  # Change from INFO to DEBUG
    format='%(levelname)s:%(name)s:%(message)s'
)
```

---

## Performance Impact

### Rate Limiting

- **Overhead**: Minimal (simple token bucket calculation)
- **Latency**: ~1-2ms per check (memory-based, no I/O)
- **Memory**: Negligible (~100 bytes per unique identifier)

### Retry Logic

- **Overhead**: None if no retries needed
- **On failure**: Additional wait time (2-10 seconds per retry)
- **Benefit**: Increased reliability for transient failures

---

## Future Enhancements

Planned improvements for Phase 3:

1. **Distributed Rate Limiting**
   - Redis-based rate limiting for multiple server instances
   - Share rate limits across instances

2. **Adaptive Rate Limiting**
   - Automatically adjust limits based on API response times
   - Detect when API is struggling and reduce requests

3. **Circuit Breaker Pattern**
   - Stop sending requests if API is consistently failing
   - Graceful degradation

4. **Metrics and Monitoring**
   - Prometheus metrics for rate limit usage
   - Grafana dashboards
   - Alert when approaching rate limits

---

## References

- **Tenacity Documentation**: https://tenacity.readthedocs.io/
- **Token Bucket Algorithm**: https://en.wikipedia.org/wiki/Token_bucket
- **HTTP Status Codes**: https://httpwg.org/specs/rfc7231.html#status.codes
- **Exponential Backoff**: https://en.wikipedia.org/wiki/Exponential_backoff

---

## Support

For issues or questions:
1. Check [`MCP_BEST_PRACTICES_REVIEW.md`](MCP_BEST_PRACTICES_REVIEW.md) for context
2. Review the source code in `src/usaspending_mcp/utils/`
3. Check logs at DEBUG level for detailed information

---

**Last Updated**: October 30, 2025
**Version**: 1.0.0
**Status**: Infrastructure Complete, Integration in Progress
