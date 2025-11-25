"""
Rate limiting implementation for USASpending MCP Server.

WHAT IS RATE LIMITING?
Imagine you're at a water fountain that can only serve 60 people per minute.
If 200 people show up, we need to make them wait in line, rather than
all 200 rushing at once and breaking the fountain.

Similarly, the USASpending API can only handle so many requests per minute.
If we send too many requests too fast, the API might crash or block us.
Our rate limiter acts like a bouncer - it makes requests wait their turn.

HOW IT WORKS:
- We use a "token bucket" algorithm
- Imagine a bucket that holds tokens
- We get 60 tokens per minute (one per second)
- Each API request costs 1 token
- If we run out of tokens, we wait until more tokens arrive

WHY THIS IS IMPORTANT:
- Prevents overwhelming the USASpending API
- Protects all users from server crashes
- Ensures fair usage for everyone
- Part of good "netiquette" on the internet

ALGORITHM: TOKEN BUCKET
Think of it like a swimming pool:
1. The pool holds up to 60 tokens
2. Every second, 1 new token flows in (from a fountain)
3. Each API request removes 1 token (like someone swimming)
4. If the pool is empty, new requests must wait for tokens to refill
"""

import asyncio
import logging
import time
from collections import defaultdict
from dataclasses import dataclass
from typing import Optional

# Logger for this module - logs rate limiting events
logger = logging.getLogger(__name__)


@dataclass
class RateLimitConfig:
    """
    Configuration for rate limiting.

    This dataclass holds all the settings for how strict our rate limiting is.
    A dataclass is like a simple container for related data.

    Attributes:
        requests_per_minute: How many API calls we allow in 60 seconds
        check_interval: How often we check if a token is available (in seconds)
    """

    # Default: Allow 60 requests per minute (1 per second)
    # This is a reasonable limit that respects the USASpending API
    requests_per_minute: int = 60

    # How often to check if we can make a request
    # 0.1 seconds = 100 milliseconds
    # Checking more often uses more CPU, checking less often causes delays
    # 100ms is a good balance
    check_interval: float = 0.1


class RateLimiter:
    """
    Token bucket rate limiter for controlling request rates.

    This class implements the token bucket algorithm.

    KEY CONCEPTS:
    - Each "identifier" (like a user or IP) gets its own token bucket
    - Tokens are added over time at a steady rate
    - Requests consume tokens
    - If no tokens are available, the request waits
    - Buckets are thread-safe for use with async/await

    THREAD-SAFE FOR ASYNC:
    This means it works correctly even when multiple requests are happening
    at the same time (asynchronous programming). No requests will interfere
    with each other.

    Example:
        limiter = RateLimiter(requests_per_minute=60)
        await limiter.wait_if_needed("user123")  # Wait for a token
        # Make API call here
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
                                (default: 60)
            check_interval: How often to check for available tokens, in seconds
                           (default: 0.1 seconds = 100 milliseconds)
        """
        # Store the rate limit settings
        self.requests_per_minute = requests_per_minute
        self.check_interval = check_interval

        # Calculate how many tokens we add per second
        # If we allow 60 requests per minute, that's 60/60 = 1 token per second
        self.tokens_per_second = requests_per_minute / 60.0

        # Dictionary to track tokens for each identifier
        # Each identifier (user, IP, tool) gets its own token bucket
        # defaultdict automatically creates a new bucket if one doesn't exist
        # New buckets start with the maximum number of tokens (ready to go!)
        self.token_buckets: dict[str, float] = defaultdict(lambda: float(requests_per_minute))

        # Dictionary to track when we last updated each bucket
        # We need this to know how much time has passed so we can add tokens
        self.last_update: dict[str, float] = defaultdict(time.time)

        # Log that we're starting up with these settings
        logger.info(
            f"RateLimiter initialized: {requests_per_minute} requests/minute "
            f"({self.tokens_per_second:.2f} tokens/second)"
        )

    def _refill_tokens(self, identifier: str) -> None:
        """
        Refill tokens based on time elapsed since last update.

        WHAT DOES THIS DO?
        This is the core of the token bucket algorithm!
        Over time, tokens "drip" back into the bucket, like water from a faucet.

        HOW IT WORKS:
        1. Check how much time has passed since last update
        2. Calculate how many tokens should have been added in that time
        3. Add those tokens to the bucket
        4. Make sure we don't add MORE tokens than the maximum
        5. Update the "last update" time

        REAL WORLD EXAMPLE:
        - Your bucket holds 60 tokens max
        - We add 1 token per second
        - If 5 seconds pass, we add 5 tokens
        - If your bucket had 58 tokens, now it has 60 (capped at max)

        Args:
            identifier: The unique identifier for this token bucket
                       (could be a user ID, IP address, tool name, etc.)
        """
        # Get the current time
        now = time.time()

        # How much time has passed since we last updated this bucket?
        # For example, if we last updated at time 100.0 and now it's 105.0,
        # then 5.0 seconds have passed
        time_passed = now - self.last_update[identifier]

        # Calculate how many new tokens have been earned in that time
        # If we earn 1 token per second and 5 seconds passed, that's 5 tokens
        tokens_to_add = time_passed * self.tokens_per_second

        # Update the token bucket, but don't let it exceed the maximum
        # The min() function picks the smaller of two numbers
        # If we have 58 tokens and add 5, that would be 63
        # But our max is 60, so min(60, 63) = 60
        self.token_buckets[identifier] = min(
            self.requests_per_minute,  # This is our maximum (usually 60)
            self.token_buckets[identifier] + tokens_to_add,  # Add new tokens
        )

        # Update the time so next time we know how much time to measure from
        self.last_update[identifier] = now

    async def wait_if_needed(
        self,
        identifier: str = "default",
        max_wait: float = 60.0,
    ) -> bool:
        """
        Wait if necessary until a token is available, then consume it.

        THIS IS THE MAIN METHOD USERS CALL!
        Before making an API request, call this method.
        It will either return immediately (if tokens are available)
        or wait until tokens become available.

        HOW IT WORKS:
        1. Check if we have tokens available
        2. If yes: consume a token and return immediately (fast!)
        3. If no: wait a bit and check again
        4. Repeat until we get a token or timeout
        5. If we wait too long, raise an error

        ANALOGY:
        Think of it like waiting in line at a movie theater:
        - You ask: "Is there a ticket available?"
        - If yes: great, buy one and go in
        - If no: wait 100 milliseconds and ask again
        - After asking many times (up to max_wait), give up and go home

        Args:
            identifier: Unique identifier for rate limiting
                       Examples: "127.0.0.1" (IP), "user123", "default"
            max_wait: Maximum seconds to wait for a token
                     Default: 60 seconds
                     If we can't get a token after this time, raise an error

        Returns:
            True if we successfully got a token
            (The function actually raises an error if it times out,
             so you'll never get False)

        Raises:
            RuntimeError: If we wait longer than max_wait seconds
        """
        # Mark the time we started waiting
        start_time = time.time()

        # Time we've spent waiting so far
        waited = 0.0

        # Loop forever until we get a token or timeout
        while True:
            # First, refill any tokens that have been earned since last check
            self._refill_tokens(identifier)

            # Do we have at least 1 token available?
            if self.token_buckets[identifier] >= 1.0:
                # YES! We can make our API request
                # Consume one token (use it up)
                self.token_buckets[identifier] -= 1.0

                # Log this success for debugging
                logger.debug(
                    f"Rate limit check passed for '{identifier}' "
                    f"(remaining: {self.token_buckets[identifier]:.2f})"
                )

                # We got a token! Return success
                return True

            # NO TOKENS AVAILABLE - we need to wait
            # How long have we been waiting so far?
            waited = time.time() - start_time

            # Have we exceeded our maximum wait time?
            if waited > max_wait:
                # YES - we've waited too long!
                # Log the problem
                logger.warning(
                    f"Rate limit timeout for '{identifier}' " f"after waiting {waited:.1f}s"
                )
                # Raise an error to stop the program
                raise RuntimeError(
                    f"Rate limit exceeded: waiting > {max_wait}s for available token"
                )

            # We're not timed out yet, so sleep briefly before checking again
            # Why sleep? To avoid using 100% CPU constantly checking
            # We sleep for 100 milliseconds (0.1 seconds) by default
            # This is a good balance between responsiveness and CPU usage
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
