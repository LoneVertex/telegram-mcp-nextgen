"""Async token-bucket rate limiting for Telegram RPC calls."""

from __future__ import annotations

import asyncio
import time


class TokenBucket:
    """A monotonic-clock token bucket safe for concurrent async callers."""

    def __init__(self, capacity: int, refill_per_second: float) -> None:
        if capacity < 1 or refill_per_second <= 0:
            raise ValueError("capacity and refill_per_second must be positive")
        self.capacity = float(capacity)
        self.refill_per_second = refill_per_second
        self._tokens = float(capacity)
        self._updated = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self, tokens: float = 1.0) -> None:
        if tokens <= 0 or tokens > self.capacity:
            raise ValueError("tokens must be greater than zero and within capacity")
        while True:
            async with self._lock:
                now = time.monotonic()
                elapsed = max(0.0, now - self._updated)
                self._tokens = min(self.capacity, self._tokens + elapsed * self.refill_per_second)
                self._updated = now
                if self._tokens >= tokens:
                    self._tokens -= tokens
                    return
                wait_for = (tokens - self._tokens) / self.refill_per_second
            await asyncio.sleep(wait_for)

    @property
    def available(self) -> float:
        now = time.monotonic()
        elapsed = max(0.0, now - self._updated)
        return min(self.capacity, self._tokens + elapsed * self.refill_per_second)
