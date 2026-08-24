"""Bounded retry policies for Telegram RPC operations."""

from __future__ import annotations

import asyncio
import logging
import random
from collections.abc import Awaitable, Callable
from typing import TypeVar

from telethon.errors import FloodWaitError

from ..config import Settings

LOGGER = logging.getLogger(__name__)
T = TypeVar("T")


async def run_with_policy(
    operation: Callable[[], Awaitable[T]],
    settings: Settings,
    *,
    retry_network: bool = True,
    retry_flood: bool = True,
) -> T:
    """Run an operation with bounded retries when repeating it is safe."""
    flood_attempts = 0
    network_attempts = 0
    while True:
        try:
            return await operation()
        except FloodWaitError as error:
            seconds = int(getattr(error, "seconds", 0) or 0)
            if (
                not retry_flood
                or flood_attempts >= settings.flood_max_retries
                or seconds > settings.flood_max_seconds
            ):
                raise
            base = max(seconds, settings.backoff_base_seconds * (2**flood_attempts))
            jitter = random.uniform(0.0, min(1.0, base * 0.1))
            delay = min(float(settings.flood_max_seconds), base + jitter)
            flood_attempts += 1
            LOGGER.warning("FloodWait received; retry %d after %.2f seconds", flood_attempts, delay)
            await asyncio.sleep(delay)
        except (TimeoutError, ConnectionError, OSError):
            if not retry_network or network_attempts >= settings.flood_max_retries:
                raise
            base = min(settings.flood_max_seconds, settings.backoff_base_seconds * (2**network_attempts))
            jitter = random.uniform(0.0, min(1.0, base * 0.1))
            network_attempts += 1
            await asyncio.sleep(min(float(settings.flood_max_seconds), base + jitter))
