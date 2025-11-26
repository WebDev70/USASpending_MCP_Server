"""
Unit tests for rate limiting utility module.

Tests the token bucket rate limiter implementation for controlling
request rates to prevent API overload.
"""

import asyncio
import time
from unittest.mock import MagicMock, patch

import pytest

from usaspending_mcp.utils.rate_limit import RateLimiter, get_rate_limiter, initialize_rate_limiter


@pytest.mark.unit
class TestRateLimiterBasics:
    """Test basic rate limiter functionality."""

    def test_rate_limiter_initialization(self):
        """Test creating a rate limiter with custom rate."""
        limiter = RateLimiter(requests_per_minute=30)
        assert limiter is not None
        assert limiter.requests_per_minute == 30

    def test_rate_limiter_default_rate(self):
        """Test default rate (60 requests per minute)."""
        limiter = RateLimiter()
        assert limiter.requests_per_minute == 60

    def test_get_stats_initial(self):
        """Test getting stats from new rate limiter."""
        limiter = RateLimiter(requests_per_minute=10)
        stats = limiter.get_stats(identifier="test")

        assert stats is not None
        assert "available_tokens" in stats
        assert "requests_per_minute" in stats
        assert stats["requests_per_minute"] == 10
        # Use approximate equality for floating-point comparison
        assert abs(stats["available_tokens"] - 10.0) < 0.001  # Should have full tokens initially

    def test_reset_identifier(self):
        """Test resetting tokens for an identifier."""
        limiter = RateLimiter(requests_per_minute=5)

        # Consume some tokens by directly manipulating the bucket
        limiter.token_buckets["test1"] = 3.0

        # Check that tokens were consumed
        stats = limiter.get_stats("test1")
        assert stats["available_tokens"] < 5

        # Reset
        limiter.reset("test1")

        # Verify tokens were reset
        stats = limiter.get_stats("test1")
        assert abs(stats["available_tokens"] - 5.0) < 0.001


@pytest.mark.unit
@pytest.mark.asyncio
class TestRateLimiterAsync:
    """Test async rate limiting."""

    async def test_wait_if_needed_available_token(self):
        """Test that wait returns immediately if tokens available."""
        limiter = RateLimiter(requests_per_minute=10)

        start = time.time()
        await limiter.wait_if_needed(identifier="test")
        elapsed = time.time() - start

        # Should return immediately (less than 100ms)
        assert elapsed < 0.1

    async def test_wait_if_needed_consumes_token(self):
        """Test that wait consumes a token."""
        limiter = RateLimiter(requests_per_minute=5)

        stats_before = limiter.get_stats("test")
        available_before = stats_before["available_tokens"]

        await limiter.wait_if_needed(identifier="test")

        stats_after = limiter.get_stats("test")
        available_after = stats_after["available_tokens"]

        assert available_after < available_before

    async def test_concurrent_requests_respect_limit(self):
        """Test that concurrent requests respect rate limit."""
        limiter = RateLimiter(requests_per_minute=3)  # 3 tokens per minute
        identifier = "test"

        # Create tasks that will consume tokens
        async def consume_token():
            await limiter.wait_if_needed(identifier=identifier)
            return True

        # First 3 should succeed immediately
        tasks = [consume_token() for _ in range(3)]
        results = await asyncio.gather(*tasks)
        assert all(results)

        # Check that we're out of tokens (or very close to 0 due to floating-point precision)
        stats = limiter.get_stats(identifier)
        assert stats["available_tokens"] < 0.001

    async def test_different_identifiers_independent(self):
        """Test that different identifiers have independent limits."""
        limiter = RateLimiter(requests_per_minute=2)

        # Consume tokens for identifier 1
        await limiter.wait_if_needed(identifier="id1")

        # Check identifier 2 still has full tokens (use approximate equality for floating-point)
        stats_id2 = limiter.get_stats("id2")
        assert abs(stats_id2["available_tokens"] - 2.0) < 0.001

        # Identifier 1 should have fewer
        stats_id1 = limiter.get_stats("id1")
        assert stats_id1["available_tokens"] < 2


@pytest.mark.unit
class TestGlobalRateLimiter:
    """Test global rate limiter functions."""

    def test_initialize_rate_limiter(self):
        """Test initializing global rate limiter."""
        limiter = initialize_rate_limiter(requests_per_minute=50)
        assert limiter is not None
        assert limiter.requests_per_minute == 50

    def test_get_rate_limiter(self):
        """Test getting global rate limiter."""
        # Initialize first
        initialize_rate_limiter(requests_per_minute=100)

        # Get the limiter
        limiter = get_rate_limiter()
        assert limiter is not None
        assert limiter.requests_per_minute == 100

    def test_get_rate_limiter_returns_same_instance(self):
        """Test that get_rate_limiter returns the same instance."""
        limiter1 = get_rate_limiter()
        limiter2 = get_rate_limiter()
        assert limiter1 is limiter2


@pytest.mark.unit
class TestRateLimiterEdgeCases:
    """Test edge cases and error conditions."""

    def test_zero_requests_per_minute(self):
        """Test limiter with zero requests per minute."""
        limiter = RateLimiter(requests_per_minute=0)
        assert limiter.requests_per_minute == 0

    def test_very_high_requests_per_minute(self):
        """Test limiter with very high requests per minute."""
        limiter = RateLimiter(requests_per_minute=10000)
        assert limiter.requests_per_minute == 10000

        stats = limiter.get_stats("test")
        # Use approximate equality for floating-point comparison
        assert abs(stats["available_tokens"] - 10000.0) < 1.0

    def test_negative_requests_per_minute(self):
        """Test limiter with negative requests per minute."""
        # Should handle gracefully (convert to absolute value or default)
        limiter = RateLimiter(requests_per_minute=-10)
        # The implementation should handle this
        assert limiter is not None

    def test_string_identifier(self):
        """Test using string identifiers."""
        limiter = RateLimiter(requests_per_minute=5)

        # Get stats to initialize the identifier
        stats_before = limiter.get_stats("user_123")
        assert stats_before["available_tokens"] > 0

    def test_unicode_identifier(self):
        """Test using unicode identifiers."""
        limiter = RateLimiter(requests_per_minute=5)

        # Get stats to initialize the identifier with unicode name
        stats_before = limiter.get_stats("用户_123")  # Chinese characters
        assert stats_before["available_tokens"] > 0


@pytest.mark.unit
class TestRateLimiterTokenRefill:
    """Test token refill behavior."""

    def test_token_refill_calculation(self):
        """Test that tokens refill over time."""
        limiter = RateLimiter(requests_per_minute=60)  # 1 token per second
        identifier = "test"

        # Consume all tokens by setting last_update to 1000 seconds ago and tokens to 0
        limiter.last_update[identifier] = time.time() - 1000
        limiter.token_buckets[identifier] = 0.0

        # Get stats (should trigger refill)
        stats = limiter.get_stats(identifier)

        # Should have tokens available now (capped at 60)
        assert stats["available_tokens"] > 0

    def test_refill_time_accuracy(self):
        """Test that refill time is accurate."""
        limiter = RateLimiter(requests_per_minute=60)  # 1 token per second
        identifier = "test"

        # Set last update to 2 seconds ago and no tokens
        limiter.last_update[identifier] = time.time() - 2.0
        limiter.token_buckets[identifier] = 0.0

        stats = limiter.get_stats(identifier)

        # Should have approximately 2 tokens (within 1 token due to processing time)
        assert 1.0 <= stats["available_tokens"] <= 3.0


@pytest.mark.unit
@pytest.mark.asyncio
class TestRateLimiterErrorHandling:
    """Test error handling in rate limiter."""

    async def test_wait_if_needed_with_exception(self):
        """Test that exceptions in wait_if_needed are handled."""
        limiter = RateLimiter(requests_per_minute=5)

        # Should not raise exception
        try:
            await limiter.wait_if_needed(identifier="test")
        except Exception as e:
            pytest.fail(f"wait_if_needed raised exception: {e}")

    async def test_multiple_concurrent_identifiers(self):
        """Test rate limiter with multiple concurrent identifiers."""
        limiter = RateLimiter(requests_per_minute=2)

        async def consume_for_id(identifier):
            await limiter.wait_if_needed(identifier=identifier)
            return identifier

        # Create requests from 3 different identifiers
        tasks = [consume_for_id("id1"), consume_for_id("id2"), consume_for_id("id3")]

        results = await asyncio.gather(*tasks)
        assert len(results) == 3
        assert set(results) == {"id1", "id2", "id3"}
