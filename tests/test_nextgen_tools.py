"""Tests for tier registration and next-generation tool safety behavior."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from telegram_mcp import runtime
from telegram_mcp.core.errors import ValidationError, error_response
from telegram_mcp.core.registry import CORE_TOOL_NAMES, allowed_tool_names
from telegram_mcp.db.database import Database
from telegram_mcp.db.repository import MessageRepository
from telegram_mcp.tools import cache


def test_tiers_are_monotonic_and_full_is_compatibility_mode() -> None:
    essential = allowed_tool_names("essential")
    core = allowed_tool_names("core")
    standard = allowed_tool_names("standard")
    assert essential is not None
    assert core is not None
    assert standard is not None
    assert len(essential) == 22
    assert CORE_TOOL_NAMES <= core <= standard
    assert allowed_tool_names("full") is None
    with pytest.raises(ValueError):
        allowed_tool_names("invalid")


@pytest.mark.asyncio
async def test_write_wrapper_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(runtime.settings, "send_enabled", False)
    called = False

    @runtime.with_account(readonly=False)
    async def send_message(*, account: str | None = None) -> str:
        nonlocal called
        called = True
        return "sent"

    result = await send_message(account="default")
    payload = json.loads(result)
    assert payload["error"] == "MutationDisabled"
    assert payload["nothing_sent"] is True
    assert called is False


@pytest.mark.asyncio
async def test_cache_search_runs_against_local_fts(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    database = Database(tmp_path / "cache.db")
    repository = MessageRepository(database)
    repository.upsert_chat(42, "Cache", "channel")
    repository.upsert_messages([
        {"chat_id": 42, "message_id": 1, "sender_name": "Alice", "text": "alpha beta"},
        {"chat_id": 42, "message_id": 2, "sender_name": "Bob", "text": "other text"},
    ])
    monkeypatch.setattr(cache, "_database", database)
    monkeypatch.setattr(cache, "_repository", repository)
    results = await cache.search_cached_messages(42, "alpha", limit=10)
    assert [row["message_id"] for row in results] == [1]
    with pytest.raises(ValidationError):
        await cache.search_cached_messages(42, "", limit=10)
    with pytest.raises(ValidationError):
        await cache.search_cached_messages(42, "alpha", limit=0)


def test_error_response_redacts_unknown_failures() -> None:
    response = error_response(RuntimeError("secret session string and path"))
    assert response == {"error": "InternalServerError", "message": "Internal server error."}
