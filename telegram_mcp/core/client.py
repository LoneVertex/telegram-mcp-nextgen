"""Shared Telethon lifecycle coordinator used by the next-generation tools."""

from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from typing import Any, TypeVar

from telethon import TelegramClient

from ..config import Settings
from .locks import KeyedLockManager
from .rate_limiter import TokenBucket
from .retry import run_with_policy

T = TypeVar("T")


class TelegramClientCoordinator:
    """Own a single session and serialize all operations for that session."""

    def __init__(self, settings: Settings, factory: Callable[..., TelegramClient] | None = None) -> None:
        self.settings = settings
        self._factory = factory or TelegramClient
        self._client: TelegramClient | None = None
        self._closed = False
        self._locks = KeyedLockManager()
        self._limiter = TokenBucket(settings.rate_capacity, settings.rate_refill_per_second)

    async def start(self) -> TelegramClient:
        if self._closed:
            raise RuntimeError("client coordinator is closed")
        if self._client is not None:
            return self._client
        api_id, api_hash = self.settings.require_credentials()
        session: Any = self.settings.session_string or str(self.settings.session_path)
        client = self._factory(session, api_id, api_hash)
        await client.connect()
        if not await client.is_user_authorized():
            raise RuntimeError("Telegram session is not authorized")
        self._client = client
        return client

    @asynccontextmanager
    async def operation(self, key: str = "telegram") -> AsyncIterator[TelegramClient]:
        """Yield a connected client under a per-key lock and rate-limit token."""
        async with self._locks.hold(key):
            await self._limiter.acquire()
            client = await self.start()
            yield client

    async def call(self, operation: Callable[[TelegramClient], Awaitable[T]], *, key: str = "telegram") -> T:
        async with self.operation(key) as client:
            return await run_with_policy(lambda: operation(client), self.settings)

    async def close(self) -> None:
        self._closed = True
        client, self._client = self._client, None
        if client is not None:
            await client.disconnect()

    @property
    def client(self) -> TelegramClient | None:
        return self._client

    @property
    def active_lock_keys(self) -> int:
        return self._locks.key_count
