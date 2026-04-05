"""Tests for the Token Bucket Filter rate limiter."""
import time

from bethesda_creations.rate_limiter import RateLimiter


def test_acquire_consumes_token():
    limiter = RateLimiter(max_tokens=5, window_seconds=10.0)
    limiter.acquire()
    assert limiter._tokens < 5.0


def test_burst_up_to_max_tokens():
    limiter = RateLimiter(max_tokens=3, window_seconds=300.0)
    limiter.acquire()
    limiter.acquire()
    limiter.acquire()
    assert limiter._tokens < 1.0


def test_acquire_blocks_when_empty():
    limiter = RateLimiter(max_tokens=1, window_seconds=1.0)
    limiter.acquire()
    start = time.monotonic()
    limiter.acquire()
    elapsed = time.monotonic() - start
    assert elapsed >= 0.5


def test_refill_over_time():
    limiter = RateLimiter(max_tokens=10, window_seconds=1.0)
    for _ in range(10):
        limiter.acquire()
    time.sleep(0.55)
    limiter._refill()
    assert limiter._tokens >= 4.0


def test_configurable_bucket_size():
    limiter = RateLimiter(max_tokens=50, window_seconds=60.0)
    assert limiter._max_tokens == 50
    for _ in range(50):
        limiter.acquire()
    assert limiter._tokens < 1.0


def test_tokens_never_exceed_max():
    limiter = RateLimiter(max_tokens=5, window_seconds=0.1)
    time.sleep(0.2)
    limiter._refill()
    assert limiter._tokens <= 5.0
