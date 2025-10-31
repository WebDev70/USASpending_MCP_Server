"""
Rate limiting implementation for USASpending MCP Server.

Implements token bucket algorithm for rate limiting API calls.
Works with both stdio and HTTP transports.
"""

import asyncio
import logging
import time
from collections import defaultdict
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""
    requests_per_minute: int = 60  # Default: 60 requests per minute
    check_interval: float = 0.1  # Check every 100ms if token available


class RateLimiter:
    """
    Token bucket rate limiter for controlling request rates.

    Allows configurable rate limiting with per-tool or per-server limits.
    Thread-safe for async operations.
    """

    def __init__(
        self,
        requests_per_minute: int = 60,
        check_interval: float = 0.1,
    ):
        """
        Initialize rate limiter.

        Args:
            requests_per_minute: Max requests allowed per minute
            check_interval: How often to check for available tokens (seconds)
        """
        self.requests_per_minute = requests_per_minute
        self.check_interval = check_interval
        self.tokens_per_second = requests_per_minute / 60.0

        # Track tokens for each unique identifier (e.g., user, IP, tool)
        self.token_buckets: dict[str, float] = defaultdict(
            lambda: float(requests_per_minute)
        )
        self.last_update: dict[str, float] = defaultdict(time.time)

        logger.info(
            f"RateLimiter initialized: {requests_per_minute} requests/minute "
            f"({self.tokens_per_second:.2f} tokens/second)"
        )

    def _refill_tokens(self, identifier: str) -> None:
        """
        Refill tokens based on time elapsed since last update.

        Args:
            identifier: Unique identifier for token bucket
        """
        now = time.time()
        time_passed = now - self.last_update[identifier]

        # Add tokens based on time passed
        tokens_to_add = time_passed * self.tokens_per_second
        self.token_buckets[identifier] = min(
            self.requests_per_minute,  # Cap at max
            self.token_buckets[identifier] + tokens_to_add,
        )
        self.last_update[identifier] = now

    async def wait_if_needed(
        self,
        identifier: str = "default",
        max_wait: float = 60.0,
    ) -> bool:
        """
        Wait if necessary until a token is available.

        Args:
            identifier: Unique identifier for rate limiting (e.g., IP, user ID)
            max_wait: Maximum time to wait in seconds

        Returns:
            True if token was acquired, False if timeout

        Raises:
            ValueError: If max_wait is exceeded
        """
        start_time = time.time()
        waited = 0.0

        while True:
            self._refill_tokens(identifier)

            if self.token_buckets[identifier] >= 1.0:
                # Token available, consume it
                self.token_buckets[identifier] -= 1.0
                logger.debug(
                    f"Rate limit check passed for '{identifier}' "
                    f"(remaining: {self.token_buckets[identifier]:.2f})"
                )
                return True

            # No token available, wait
            waited = time.time() - start_time
            if waited > max_wait:
                logger.warning(
                    f"Rate limit timeout for '{identifier}' "
                    f"after waiting {waited:.1f}s"
                )
                raise RuntimeError(
                    f"Rate limit exceeded: waiting >  {max_wait}s for available token"
                )

            # Sleep briefly before checking again
            await asyncio.sleep(self.check_interval)

    def get_available_tokens(self, identifier: str = "default") -> float:
        """
        Get number of available tokens without consuming them.

        Args:
            identifier: Unique identifier

        Returns:
            Number of available tokens (can be fractional)
        """
        self._refill_tokens(identifier)
        return self.token_buckets[identifier]

    def reset(self, identifier: Optional[str] = None) -> None:
        """
        Reset token bucket to full.

        Args:
            identifier: If provided, reset only this identifier.
                       If None, reset all.
        """
        if identifier is None:
            self.token_buckets.clear()
            self.last_update.clear()
            logger.info("All rate limit buckets reset")
        else:
            self.token_buckets[identifier] = float(self.requests_per_minute)
            self.last_update[identifier] = time.time()
            logger.info(f"Rate limit bucket reset for '{identifier}'")

    def get_stats(self, identifier: str = "default") -> dict:
        """
        Get statistics for a rate limit bucket.

        Args:
            identifier: Unique identifier

        Returns:
            Dictionary with rate limit statistics
        """
        self._refill_tokens(identifier)
        return {
            "identifier": identifier,
            "available_tokens": self.token_buckets[identifier],
            "requests_per_minute": self.requests_per_minute,
            "last_updated": self.last_update[identifier],
            "tokens_per_second": self.tokens_per_second,
        }


# Global rate limiter instance
_global_rate_limiter: Optional[RateLimiter] = None


def initialize_rate_limiter(requests_per_minute: int = 60) -> RateLimiter:
    """
    Initialize global rate limiter instance.

    Args:
        requests_per_minute: Max requests per minute

    Returns:
        RateLimiter instance
    """
    global _global_rate_limiter
    _global_rate_limiter = RateLimiter(requests_per_minute=requests_per_minute)
    return _global_rate_limiter


def get_rate_limiter() -> RateLimiter:
    """
    Get or create global rate limiter instance.

    Returns:
        RateLimiter instance
    """
    global _global_rate_limiter
    if _global_rate_limiter is None:
        _global_rate_limiter = RateLimiter()
    return _global_rate_limiter
