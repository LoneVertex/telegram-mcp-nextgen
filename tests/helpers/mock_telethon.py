"""Reusable mock Telethon client and entity factories for MCP tool tests."""

from __future__ import annotations

import datetime
from collections.abc import Callable
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

import pytest
from telethon.tl import types


def make_user(
    user_id: int = 111,
    username: str = "alice",
    first_name: str = "Alice",
    last_name: str = "Smith",
    bot: bool = False,
) -> types.User:
    return types.User(
        id=user_id,
        first_name=first_name,
        last_name=last_name,
        username=username,
        phone="1234567890",
        access_hash=1,
        bot=bot,
        status=types.UserStatusOnline(expires=2000000000),
    )


def make_channel(
    channel_id: int = 222,
    title: str = "Test Group",
    megagroup: bool = True,
    username: str = "testgroup",
) -> types.Channel:
    return types.Channel(
        id=channel_id,
        title=title,
        photo=types.ChatPhotoEmpty(),
        date=datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc),
        creator=True,
        megagroup=megagroup,
        access_hash=2,
        username=username,
    )


class MockTelethonClient:
    """Lightweight async Telethon client mock that records TL requests."""

    def __init__(self, handlers: dict[str, Callable[[Any], Any]] | None = None) -> None:
        self.requests: list[Any] = []
        self.handlers: dict[str, Callable[[Any], Any]] = handlers or {}
        self.default_user = make_user()
        self.default_channel = make_channel()
        self.default_msg = SimpleNamespace(
            id=10,
            message="hello",
            text="hello",
            raw_text="hello",
            date=datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc),
            sender_id=111,
            sender=self.default_user,
            chat=self.default_channel,
            chat_id=-1000000000222,
        )

    def is_connected(self) -> bool:
        return True

    async def connect(self) -> None:
        return None

    async def get_me(self) -> types.User:
        return self.default_user

    async def get_entity(self, target: Any) -> Any:
        return self.default_channel if str(target).startswith("-") else self.default_user

    async def get_input_entity(self, target: Any) -> Any:
        if str(target).startswith("-"):
            return types.InputPeerChannel(channel_id=222, access_hash=2)
        return types.InputPeerUser(user_id=111, access_hash=1)

    async def send_message(self, *args: Any, **kwargs: Any) -> Any:
        self.requests.append(("send_message", args, kwargs))
        return self.default_msg

    async def edit_admin(self, *args: Any, **kwargs: Any) -> None:
        self.requests.append(("edit_admin", args, kwargs))

    async def edit_permissions(self, *args: Any, **kwargs: Any) -> None:
        self.requests.append(("edit_permissions", args, kwargs))

    async def __call__(self, request: Any) -> Any:
        self.requests.append(request)
        name = type(request).__name__
        if name in self.handlers:
            return self.handlers[name](request)
        return SimpleNamespace(
            updates=[],
            chats=[self.default_channel],
            users=[self.default_user],
            messages=[self.default_msg],
        )


def patch_tool_module(
    monkeypatch: pytest.MonkeyPatch,
    module: Any,
    client: MockTelethonClient,
    entity: Any = None,
) -> None:
    resolved = entity if entity is not None else client.default_channel
    if hasattr(module, "get_client"):
        monkeypatch.setattr(module, "get_client", lambda account=None: client)
    if hasattr(module, "ensure_connected"):
        monkeypatch.setattr(module, "ensure_connected", AsyncMock(return_value=None))
    if hasattr(module, "resolve_entity"):
        monkeypatch.setattr(module, "resolve_entity", AsyncMock(return_value=resolved))
    if hasattr(module, "resolve_input_entity"):
        monkeypatch.setattr(
            module,
            "resolve_input_entity",
            AsyncMock(return_value=types.InputPeerChannel(channel_id=222, access_hash=2)),
        )
