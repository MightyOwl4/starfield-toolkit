"""Token Bucket Filter rate limiter for API request throttling."""
import time


class RateLimiter:
    """Token bucket rate limiter with configurable window and bucket size.

    Tokens refill linearly over the window period. Call acquire() before
    each request — it blocks (sleeps) until a token is available.
    """

    def __init__(self, max_tokens: int = 100, window_seconds: float = 300.0):
        self._max_tokens = max_tokens
        self._window = window_seconds
        self._tokens = float(max_tokens)
        self._last_refill = time.monotonic()

    def _refill(self) -> None:
        now = time.monotonic()
        elapsed = now - self._last_refill
        self._tokens = min(
            self._max_tokens,
            self._tokens + elapsed * (self._max_tokens / self._window),
        )
        self._last_refill = now

    def acquire(self) -> None:
        """Block until a token is available, then consume one."""
        self._refill()
        while self._tokens < 1.0:
            deficit = 1.0 - self._tokens
            sleep_time = deficit * (self._window / self._max_tokens)
            time.sleep(sleep_time)
            self._refill()
        self._tokens -= 1.0
