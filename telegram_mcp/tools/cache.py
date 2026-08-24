"""Local archive tools for resumable synchronization and context-efficient search."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any

from mcp.types import ToolAnnotations

from telegram_mcp.core.errors import ValidationError
from telegram_mcp.db.database import Database
from telegram_mcp.db.repository import MessageRepository
from telegram_mcp.runtime import (
    ensure_connected,
    get_client,
    get_entity_type,
    get_sender_name,
    mcp,
    resolve_entity,
    settings,
    with_account,
)

_database: Database | None = None
_repository: MessageRepository | None = None
_repository_lock = asyncio.Lock()


def _build_repository() -> tuple[Database, MessageRepository]:
    settings.ensure_directories()
    assert settings.db_path is not None
    database = Database(settings.db_path)
    return database, MessageRepository(database)


async def _repo_async() -> MessageRepository:
    global _database, _repository
    if _repository is not None:
        return _repository
    async with _repository_lock:
        if _repository is None:
            _database, _repository = await asyncio.to_thread(_build_repository)
    assert _repository is not None
    return _repository


def _message_row(chat_id: int, message: Any) -> dict[str, Any]:
    date = getattr(message, "date", None)
    edit_date = getattr(message, "edit_date", None)
    media = getattr(message, "media", None)
    return {
        "chat_id": chat_id,
        "message_id": int(message.id),
        "sender_id": getattr(message, "sender_id", None),
        "sender_name": get_sender_name(message),
        "message_date": date.isoformat() if date else None,
        "edit_date": edit_date.isoformat() if edit_date else None,
        "text": getattr(message, "message", None) or "",
        "topic_id": getattr(message, "reply_to_top_id", None) or getattr(message, "reply_to_msg_id", None),
        "media_type": type(media).__name__ if media is not None else None,
    }


@mcp.tool(annotations=ToolAnnotations(title="Cache Health", readOnlyHint=True))
async def cache_health() -> dict[str, Any]:
    """Return local SQLite/FTS5 integrity and active tier diagnostics."""
    await _repo_async()
    assert _database is not None
    integrity = await asyncio.to_thread(_database.integrity_check)
    return {"status": "ok", "database": integrity, "tier": settings.tier}


@mcp.tool(annotations=ToolAnnotations(title="Search Cached Messages", readOnlyHint=True))
async def search_cached_messages(chat_id: int, query: str, limit: int = 20, offset: int = 0) -> list[dict[str, Any]]:
    """Search the local FTS5 archive without making a Telegram request."""
    if chat_id == 0 or not query.strip():
        raise ValidationError("chat_id and query are required")
    if limit < 1 or limit > settings.max_search_limit or offset < 0:
        raise ValidationError("limit or offset is outside the configured bounds")
    repository = await _repo_async()
    return await asyncio.to_thread(repository.search, chat_id, query, limit, offset)


@mcp.tool(annotations=ToolAnnotations(title="Sync Local Cache", readOnlyHint=True))
@with_account(readonly=True)
async def sync_chat_cache(
    chat_id: int,
    limit: int = 100,
    mode: str = "incremental",
    account: str | None = None,
) -> dict[str, Any]:
    """Synchronize a bounded message window into the local archive."""
    if chat_id == 0 or limit < 1 or limit > settings.max_sync_batch:
        raise ValidationError("chat_id or limit is outside the configured bounds")
    if mode not in {"incremental", "full"}:
        raise ValidationError("mode must be incremental or full")
    repository = await _repo_async()
    client = get_client(account)
    await ensure_connected(client)
    entity = await resolve_entity(chat_id, client)
    marked_chat_id = int(getattr(entity, "id", chat_id))
    checkpoint = await asyncio.to_thread(repository.get_checkpoint, marked_chat_id)
    min_id = 0 if mode == "full" or checkpoint is None else int(checkpoint["last_message_id"])
    await asyncio.to_thread(
        repository.upsert_chat,
        marked_chat_id,
        getattr(entity, "title", str(chat_id)),
        get_entity_type(entity),
    )
    batch: list[dict[str, Any]] = []
    synced_messages = 0
    last_message_id = min_id
    commit_size = min(50, settings.max_sync_batch)
    async for message in client.iter_messages(entity, limit=limit, min_id=min_id, reverse=True):
        batch.append(_message_row(marked_chat_id, message))
        if len(batch) < commit_size:
            continue
        await asyncio.to_thread(repository.upsert_messages, batch)
        last_message_id = max(last_message_id, max(row["message_id"] for row in batch))
        await asyncio.to_thread(repository.checkpoint, marked_chat_id, last_message_id, mode)
        synced_messages += len(batch)
        batch = []
    if batch:
        await asyncio.to_thread(repository.upsert_messages, batch)
        last_message_id = max(last_message_id, max(row["message_id"] for row in batch))
        await asyncio.to_thread(repository.checkpoint, marked_chat_id, last_message_id, mode)
        synced_messages += len(batch)
    return {
        "chat_id": marked_chat_id,
        "mode": mode,
        "synced_messages": synced_messages,
        "last_message_id": last_message_id,
        "synced_at": datetime.now(UTC).isoformat(),
    }
