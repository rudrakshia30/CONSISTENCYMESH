import time

from backend.core.errors import RateLimitError


class RateLimiter:
    """
    Simple in-memory rate limiter using a sliding window per client ID.
    """
    def __init__(self, max_requests: int, window_seconds: int = 60) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: dict[str, list[float]] = {}

    def check_rate_limit(self, client_id: str) -> None:
        """
        Check if a client has exceeded the rate limit.
        Raises RateLimitError if limit exceeded.
        Cleans up expired entries on each check.
        """
        current_time = time.time()

        if client_id not in self.requests:
            self.requests[client_id] = []

        # Clean up expired entries
        cutoff_time = current_time - self.window_seconds
        self.requests[client_id] = [
            req_time for req_time in self.requests[client_id]
            if req_time > cutoff_time
        ]

        if len(self.requests[client_id]) >= self.max_requests:
            raise RateLimitError(f"Rate limit exceeded for client {client_id}.")

        self.requests[client_id].append(current_time)
