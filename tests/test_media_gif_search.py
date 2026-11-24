"""Unit tests for media.get_gif_search using @gif inline bot."""

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from telethon.tl import functions, types

from telegram_mcp.tools import media


@pytest.mark.asyncio
async def test_get_gif_search_uses_inline_gif_bot_and_respects_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: list[object] = []
    bot_entity = types.InputUser(user_id=140267078, access_hash=1)

    class _Client:
        async def __call__(self, request: object) -> SimpleNamespace:
            captured.append(request)
            return SimpleNamespace(
                results=[
                    SimpleNamespace(document=SimpleNamespace(id=101)),
                    SimpleNamespace(document=None),
                    SimpleNamespace(document=SimpleNamespace(id=202)),
                    SimpleNamespace(document=SimpleNamespace(id=303)),
                ]
            )

    monkeypatch.setattr(media, "get_client", lambda account=None: _Client())
    monkeypatch.setattr(media, "ensure_connected", AsyncMock(return_value=None))
    monkeypatch.setattr(media, "resolve_entity", AsyncMock(return_value=bot_entity))

    result = await media.get_gif_search(query="cat", limit=2)

    assert json.loads(result) == [101, 202]
    assert len(captured) == 1
    req = captured[0]
    assert isinstance(req, functions.messages.GetInlineBotResultsRequest)
    assert req.query == "cat"


@pytest.mark.asyncio
async def test_get_gif_search_returns_empty_json_when_no_documents(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bot_entity = types.InputUser(user_id=140267078, access_hash=1)

    class _Client:
        async def __call__(self, request: object) -> SimpleNamespace:
            return SimpleNamespace(results=[SimpleNamespace(document=None)])

    monkeypatch.setattr(media, "get_client", lambda account=None: _Client())
    monkeypatch.setattr(media, "ensure_connected", AsyncMock(return_value=None))
    monkeypatch.setattr(media, "resolve_entity", AsyncMock(return_value=bot_entity))

    result = await media.get_gif_search(query="nothing")
    assert result == "[]"


@pytest.mark.asyncio
async def test_get_gif_search_formats_error_on_rpc_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bot_entity = types.InputUser(user_id=140267078, access_hash=1)

    class _Client:
        async def __call__(self, request: object) -> SimpleNamespace:
            raise RuntimeError("RPC failed")

    monkeypatch.setattr(media, "get_client", lambda account=None: _Client())
    monkeypatch.setattr(media, "ensure_connected", AsyncMock(return_value=None))
    monkeypatch.setattr(media, "resolve_entity", AsyncMock(return_value=bot_entity))

    result = await media.get_gif_search(query="cat")
    assert "An error occurred" in result
