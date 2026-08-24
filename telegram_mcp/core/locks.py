"""Async keyed lock management for Telegram requests and shared resources."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager


class KeyedLockManager:
    """Provide stable locks by key without exposing mutable lock internals."""

    def __init__(self) -> None:
        self._guard = asyncio.Lock()
        self._locks: dict[str, tuple[asyncio.Lock, int]] = {}

    async def _get(self, key: str) -> asyncio.Lock:
        async with self._guard:
            lock, count = self._locks.get(key, (asyncio.Lock(), 0))
            self._locks[key] = (lock, count + 1)
            return lock

    async def _release_ref(self, key: str, lock: asyncio.Lock) -> None:
        async with self._guard:
            current = self._locks.get(key)
            if current is None or current[0] is not lock:
                return
            _, count = current
            if count <= 1:
                self._locks.pop(key, None)
            else:
                self._locks[key] = (lock, count - 1)

    @asynccontextmanager
    async def hold(self, key: str) -> AsyncIterator[None]:
        """Serialize all operations sharing ``key`` and release on cancellation."""
        normalized = str(key)
        lock = await self._get(normalized)
        try:
            await lock.acquire()
            try:
                yield
            finally:
                lock.release()
        finally:
            await self._release_ref(normalized, lock)

    @property
    def key_count(self) -> int:
        """Return the number of currently referenced keys for diagnostics/tests."""
        return len(self._locks)
