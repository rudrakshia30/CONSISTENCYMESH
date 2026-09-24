"""Security tests for rate limiting."""
from __future__ import annotations

import time

import pytest

from backend.core.errors import RateLimitError
from backend.security.rate_limit import RateLimiter


@pytest.mark.security
def test_rate_limiter_allows_under_limit() -> None:
    limiter = RateLimiter(max_requests=5, window_seconds=60)
    for _ in range(5):
        limiter.check_rate_limit("client_1")


@pytest.mark.security
def test_rate_limiter_blocks_over_limit() -> None:
    limiter = RateLimiter(max_requests=3, window_seconds=60)
    limiter.check_rate_limit("client_1")
    limiter.check_rate_limit("client_1")
    limiter.check_rate_limit("client_1")

    with pytest.raises(RateLimitError):
        limiter.check_rate_limit("client_1")


@pytest.mark.security
def test_rate_limiter_window_reset() -> None:
    limiter = RateLimiter(max_requests=2, window_seconds=1)
    limiter.check_rate_limit("client_1")
    limiter.check_rate_limit("client_1")

    with pytest.raises(RateLimitError):
        limiter.check_rate_limit("client_1")

    time.sleep(1.1)
    # Counter reset after window expiration
    limiter.check_rate_limit("client_1")


@pytest.mark.security
def test_independent_client_limits() -> None:
    limiter = RateLimiter(max_requests=2, window_seconds=60)
    limiter.check_rate_limit("client_1")
    limiter.check_rate_limit("client_1")

    # client_2 is under its own limit
    limiter.check_rate_limit("client_2")
