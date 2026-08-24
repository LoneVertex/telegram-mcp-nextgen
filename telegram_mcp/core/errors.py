"""Typed, redacted errors for MCP responses."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from functools import wraps
from typing import Any, ParamSpec, TypeVar

from telethon.errors import (
    ChannelPrivateError,
    ChatAdminRequiredError,
    FloodWaitError,
    PeerIdInvalidError,
    UserDeactivatedBanError,
)

LOGGER = logging.getLogger(__name__)
P = ParamSpec("P")
R = TypeVar("R")


class TelegramMcpError(Exception):
    """Base exception with an MCP-safe public message."""

    code = "TelegramMcpError"

    def __init__(self, message: str, *, public_message: str | None = None) -> None:
        super().__init__(message)
        self.public_message = public_message or message


class ValidationError(TelegramMcpError):
    code = "ValidationError"


class AuthorizationError(TelegramMcpError):
    code = "AuthorizationError"


class PathError(TelegramMcpError):
    code = "PathError"


class SyncError(TelegramMcpError):
    code = "SyncError"


def error_response(error: BaseException) -> dict[str, Any]:
    """Convert an exception into a stable response without exposing internals."""
    if isinstance(error, TelegramMcpError):
        return {"error": error.code, "message": error.public_message}
    if isinstance(error, FloodWaitError):
        return {
            "error": "FloodWaitError",
            "message": "Telegram requested a temporary wait before retrying.",
            "wait_seconds": int(getattr(error, "seconds", 0) or 0),
        }
    if isinstance(error, ChatAdminRequiredError):
        return {"error": "ChatAdminRequiredError", "message": "Administrator permission is required."}
    if isinstance(error, (PeerIdInvalidError, ChannelPrivateError)):
        return {"error": "PeerUnavailable", "message": "The requested peer is unavailable or inaccessible."}
    if isinstance(error, UserDeactivatedBanError):
        return {"error": "UserDeactivatedBanError", "message": "The Telegram account is deactivated or banned."}
    if isinstance(error, (ValueError, TypeError)):
        return {"error": "InvalidInput", "message": "The supplied input is invalid."}
    LOGGER.exception("Unhandled Telegram MCP failure", exc_info=error)
    return {"error": "InternalServerError", "message": "Internal server error."}


def safe_tool(func: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R | dict[str, Any]]]:
    """Decorate an async tool with safe, non-leaking error conversion."""

    @wraps(func)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R | dict[str, Any]:
        try:
            return await func(*args, **kwargs)
        except BaseException as error:
            if isinstance(error, (KeyboardInterrupt, SystemExit, asyncio.CancelledError)):
                raise
            return error_response(error)

    return wrapper
